"""Middleware de rate limiting por IP/usuário via Redis sliding window.

Implementa controle de taxa de requisições utilizando o algoritmo de
janela deslizante (sliding window) com Redis como backend de armazenamento.
Suporta limitação por endereço IP para rotas públicas e por ID de usuário
para rotas autenticadas.

Exemplo de uso:
    from backend.src.api.middleware.rate_limiter import RateLimiterMiddleware

    app.add_middleware(
        RateLimiterMiddleware,
        redis_url="redis://localhost:6379/0",
        default_limit=100,
        default_window=60,
    )
"""

import time
import logging
from typing import Optional, Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None  # type: ignore[assignment]

from backend.src.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

# Rotas que devem ser isentas de rate limiting (health checks, docs, etc.)
DEFAULT_EXEMPT_PATHS: set[str] = {
    "/health",
    "/healthz",
    "/readiness",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Cabeçalhos padrão de rate limit (RFC draft-ietf-httpapi-ratelimit-headers)
HEADER_LIMIT = "X-RateLimit-Limit"
HEADER_REMAINING = "X-RateLimit-Remaining"
HEADER_RESET = "X-RateLimit-Reset"
HEADER_RETRY_AFTER = "Retry-After"


def _get_client_ip(request: Request) -> str:
    """Extrai o endereço IP real do cliente considerando proxies reversos.

    Verifica os cabeçalhos X-Forwarded-For e X-Real-IP antes de recorrer
    ao endereço do socket direto.

    Args:
        request: Objeto de requisição Starlette.

    Returns:
        Endereço IP do cliente como string.
    """
    # X-Forwarded-For pode conter múltiplos IPs: "client, proxy1, proxy2"
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # O primeiro IP é o do cliente original
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fallback para o IP do socket
    if request.client:
        return request.client.host

    return "unknown"


def _get_user_id_from_request(request: Request) -> Optional[str]:
    """Tenta extrair o ID do usuário autenticado do estado da requisição.

    O middleware de autenticação JWT deve ter populado `request.state.user_id`
    antes deste middleware ser executado, caso a rota seja autenticada.

    Args:
        request: Objeto de requisição Starlette.

    Returns:
        ID do usuário como string ou None se não autenticado.
    """
    # Tenta obter do state (populado pelo middleware de autenticação)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return str(user_id)
    return None


class SlidingWindowRateLimiter:
    """Implementação de rate limiter com algoritmo de janela deslizante via Redis.

    Utiliza sorted sets do Redis para rastrear timestamps de requisições,
    permitindo um controle preciso de taxa com janela deslizante.

    Attributes:
        redis_client: Cliente Redis assíncrono.
        key_prefix: Prefixo para chaves no Redis.
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "rate_limit",
    ) -> None:
        """Inicializa o rate limiter com conexão Redis.

        Args:
            redis_url: URL de conexão com o Redis.
            key_prefix: Prefixo para as chaves de rate limiting no Redis.
        """
        self.key_prefix = key_prefix
        self._redis_client: Optional["aioredis.Redis"] = None
        self._redis_url = redis_url

    async def _get_redis(self) -> "aioredis.Redis":
        """Obtém ou cria a conexão Redis de forma lazy.

        Returns:
            Cliente Redis assíncrono conectado.

        Raises:
            RuntimeError: Se a biblioteca redis não estiver instalada.
        """
        if aioredis is None:
            raise RuntimeError(
                "A biblioteca 'redis' é necessária para o rate limiter. "
                "Instale com: pip install redis[hiredis]"
            )

        if self._redis_client is None:
            self._redis_client = aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        return self._redis_client

    def _build_key(self, identifier: str) -> str:
        """Constrói a chave Redis para o identificador fornecido.

        Args:
            identifier: Identificador único (IP ou user_id).

        Returns:
            Chave formatada para uso no Redis.
        """
        return f"{self.key_prefix}:{identifier}"

    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int, int, int]:
        """Verifica e registra uma requisição no sliding window.

        Utiliza um sorted set do Redis onde cada membro é um timestamp
        único e o score é o timestamp em microsegundos. Remove entradas
        fora da janela e verifica se o limite foi excedido.

        Args:
            identifier: Identificador único do cliente (IP ou user_id).
            max_requests: Número máximo de requisições permitidas na janela.
            window_seconds: Tamanho da janela em segundos.

        Returns:
            Tupla com:
                - allowed (bool): Se a requisição é permitida.
                - remaining (int): Requisições restantes na janela.
                - reset_at (int): Timestamp Unix de quando a janela reseta.
                - retry_after (int): Segundos até poder tentar novamente (0 se permitido).
        """
        try:
            redis = await self._get_redis()
            key = self._build_key(identifier)
            now = time.time()
            window_start = now - window_seconds
            reset_at = int(now + window_seconds)

            # Pipeline atômico para operações no sorted set
            pipe = redis.pipeline(transaction=True)

            # Remove entradas fora da janela deslizante
            pipe.zremrangebyscore(key, 0, window_start)

            # Conta requisições na janela atual
            pipe.zcard(key)

            # Adiciona a requisição atual com score = timestamp
            # Usa timestamp com microsegundos como membro para unicidade
            member = f"{now}:{id(identifier)}"
            pipe.zadd(key, {member: now})

            # Define TTL para limpeza automática
            pipe.expire(key, window_seconds + 1)

            results = await pipe.execute()

            # results[1] é o zcard (contagem ANTES de adicionar a nova requisição)
            current_count = results[1]

            if current_count >= max_requests:
                # Limite excedido — remove a entrada que acabamos de adicionar
                await redis.zrem(key, member)

                # Calcula quando a entrada mais antiga expira
                oldest_entries = await redis.zrange(key, 0, 0, withscores=True)
                if oldest_entries:
                    oldest_score = float(oldest_entries[0][1])
                    retry_after = max(1, int((oldest_score + window_seconds) - now) + 1)
                else:
                    retry_after = window_seconds

                remaining = 0
                return False, remaining, reset_at, retry_after

            remaining = max(0, max_requests - current_count - 1)
            return True, remaining, reset_at, 0

        except Exception as exc:
            # Em caso de falha no Redis, permite a requisição (fail-open)
            # para não derrubar o serviço por indisponibilidade do Redis
            logger.warning(
                "Falha ao verificar rate limit no Redis. "
                "Permitindo requisição (fail-open). Erro: %s",
                str(exc),
            )
            return True, max_requests, int(time.time() + window_seconds), 0

    async def close(self) -> None:
        """Fecha a conexão com o Redis de forma graciosa."""
        if self._redis_client is not None:
            await self._redis_client.close()
            self._redis_client = None


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Middleware Starlette para rate limiting por IP/usuário via Redis.

    Aplica limites de taxa diferenciados para requisições autenticadas
    (por user_id) e não autenticadas (por IP). Utiliza o algoritmo de
    janela deslizante para controle preciso.

    Attributes:
        limiter: Instância do SlidingWindowRateLimiter.
        default_limit: Limite padrão de requisições por janela.
        default_window: Tamanho padrão da janela em segundos.
        authenticated_limit: Limite para usuários autenticados.
        authenticated_window: Janela para usuários autenticados.
        exempt_paths: Conjunto de caminhos isentos de rate limiting.
    """

    def __init__(
        self,
        app: ASGIApp,
        redis_url: Optional[str] = None,
        default_limit: int = 100,
        default_window: int = 60,
        authenticated_limit: Optional[int] = None,
        authenticated_window: Optional[int] = None,
        exempt_paths: Optional[set[str]] = None,
        key_prefix: str = "rate_limit",
    ) -> None:
        """Inicializa o middleware de rate limiting.

        Args:
            app: Aplicação ASGI.
            redis_url: URL de conexão Redis. Se None, tenta obter de settings.
            default_limit: Máximo de requisições por janela (padrão: 100).
            default_window: Tamanho da janela em segundos (padrão: 60).
            authenticated_limit: Limite para usuários autenticados.
                Se None, usa 2x o default_limit.
            authenticated_window: Janela para autenticados em segundos.
                Se None, usa o default_window.
            exempt_paths: Caminhos isentos de rate limiting.
            key_prefix: Prefixo para chaves Redis.
        """
        super().__init__(app)

        # Resolve a URL do Redis
        if redis_url is None:
            try:
                settings = get_settings()
                redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            except Exception:
                redis_url = "redis://localhost:6379/0"
                logger.warning(
                    "Não foi possível obter REDIS_URL das configurações. "
                    "Usando valor padrão: %s",
                    redis_url,
                )

        self.limiter = SlidingWindowRateLimiter(
            redis_url=redis_url,
            key_prefix=key_prefix,
        )

        self.default_limit = default_limit
        self.default_window = default_window
        self.authenticated_limit = authenticated_limit or (default_limit * 2)
        self.authenticated_window = authenticated_window or default_window
        self.exempt_paths = exempt_paths if exempt_paths is not None else DEFAULT_EXEMPT_PATHS

        logger.info(
            "Middleware de rate limiting configurado — "
            "limite padrão: %d req/%ds, "
            "limite autenticado: %d req/%ds",
            self.default_limit,
            self.default_window,
            self.authenticated_limit,
            self.authenticated_window,
        )

    def _is_exempt(self, path: str) -> bool:
        """Verifica se o caminho está isento de rate limiting.

        Args:
            path: Caminho da requisição.

        Returns:
            True se o caminho deve ser isento.
        """
        # Verifica correspondência exata
        if path in self.exempt_paths:
            return True

        # Verifica se o caminho começa com algum path isento
        for exempt in self.exempt_paths:
            if path.startswith(exempt + "/"):
                return True

        return False

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Processa a requisição aplicando rate limiting.

        Determina o identificador (user_id ou IP), verifica o limite
        e adiciona cabeçalhos de rate limit à resposta.

        Args:
            request: Objeto de requisição HTTP.
            call_next: Próximo handler na cadeia de middleware.

        Returns:
            Resposta HTTP com cabeçalhos de rate limit ou 429 se excedido.
        """
        # Ignora rotas isentas
        if self._is_exempt(request.url.path):
            return await call_next(request)

        # Determina identificador e limites baseado na autenticação
        user_id = _get_user_id_from_request(request)

        if user_id:
            identifier = f"user:{user_id}"
            max_requests = self.authenticated_limit
            window_seconds = self.authenticated_window
        else:
            client_ip = _get_client_ip(request)
            identifier = f"ip:{client_ip}"
            max_requests = self.default_limit
            window_seconds = self.default_window

        # Verifica rate limit
        allowed, remaining, reset_at, retry_after = await self.limiter.check_rate_limit(
            identifier=identifier,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        if not allowed:
            logger.warning(
                "Rate limit excedido para '%s' — "
                "limite: %d req/%ds, retry_after: %ds",
                identifier,
                max_requests,
                window_seconds,
                retry_after,
            )

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Limite de requisições excedido. Tente novamente em breve.",
                    "retry_after": retry_after,
                },
                headers={
                    HEADER_LIMIT: str(max_requests),
                    HEADER_REMAINING: "0",
                    HEADER_RESET: str(reset_at),
                    HEADER_RETRY_AFTER: str(retry_after),
                },
            )

        # Processa a requisição normalmente
        response = await call_next(request)

        # Adiciona cabeçalhos informativos de rate limit
        response.headers[HEADER_LIMIT] = str(max_requests)
        response.headers[HEADER_REMAINING] = str(remaining)
        response.headers[HEADER_RESET] = str(reset_at)

        return response
