"""Middleware de logging estruturado com correlação de request ID.

Este middleware é responsável por:
- Gerar e propagar um request ID único para cada requisição (correlação).
- Registrar logs estruturados de início e fim de cada requisição.
- Medir a duração de cada request.
- Vincular o request ID ao contexto de logging via structlog.
"""

import time
import uuid
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

# Nome do header HTTP para propagação do request ID
REQUEST_ID_HEADER = "X-Request-ID"

# Contexto assíncrono para armazenar o request ID da requisição corrente
# Permite acesso ao request_id em qualquer ponto da cadeia de chamadas
import contextvars

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

logger = structlog.get_logger(__name__)


def get_current_request_id() -> str | None:
    """Retorna o request ID da requisição corrente.

    Útil para vincular logs em camadas mais profundas (services, repositories)
    ao request que os originou.

    Returns:
        O request ID como string ou None se não houver requisição ativa.
    """
    return request_id_ctx.get()


def _extract_client_ip(request: Request) -> str:
    """Extrai o IP do cliente, considerando proxies reversos (ex.: Nginx).

    Verifica o header X-Forwarded-For antes de usar o IP direto da conexão.

    Args:
        request: Objeto de requisição Starlette.

    Returns:
        Endereço IP do cliente como string.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # O primeiro IP da lista é o cliente original
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "desconhecido"


def _sanitize_path(path: str) -> str:
    """Sanitiza o path para evitar log injection.

    Remove caracteres de controle e limita o tamanho do path logado.

    Args:
        path: Path da requisição HTTP.

    Returns:
        Path sanitizado.
    """
    # Remove caracteres de controle (newlines, tabs, etc.) para prevenir log injection
    sanitized = path.replace("\n", "").replace("\r", "").replace("\t", "")
    # Limita tamanho para evitar abuso
    max_length = 2048
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "...[truncado]"
    return sanitized


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware de logging estruturado com correlação de request ID.

    Para cada requisição HTTP:
    1. Gera ou reutiliza um request ID (header X-Request-ID).
    2. Vincula o request ID ao contexto de logging (structlog).
    3. Registra log de início da requisição com metadados relevantes.
    4. Mede a duração total do processamento.
    5. Registra log de conclusão com status code e duração.
    6. Inclui o request ID no header de resposta para rastreabilidade.

    Attributes:
        SLOW_REQUEST_THRESHOLD_SECONDS: Limiar em segundos para marcar
            requisições como lentas nos logs.
    """

    SLOW_REQUEST_THRESHOLD_SECONDS: float = 5.0

    def __init__(self, app: ASGIApp) -> None:
        """Inicializa o middleware de logging.

        Args:
            app: Aplicação ASGI encapsulada por este middleware.
        """
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Processa a requisição adicionando logging estruturado e correlação.

        Args:
            request: Objeto de requisição HTTP recebida.
            call_next: Próximo handler na cadeia de middlewares.

        Returns:
            Objeto de resposta HTTP com header X-Request-ID adicionado.
        """
        # 1. Gerar ou reutilizar request ID
        request_id = request.headers.get(REQUEST_ID_HEADER)
        if not request_id:
            request_id = str(uuid.uuid4())

        # 2. Armazenar no contexto assíncrono para acesso em camadas internas
        token = request_id_ctx.set(request_id)

        # 3. Extrair metadados da requisição
        method = request.method
        path = _sanitize_path(request.url.path)
        query_string = str(request.url.query) if request.url.query else ""
        client_ip = _extract_client_ip(request)
        user_agent = request.headers.get("User-Agent", "desconhecido")

        # 4. Vincular request ID ao contexto do structlog
        bound_logger = logger.bind(
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
        )

        # 5. Log de início da requisição
        bound_logger.info(
            "Requisição recebida",
            query_string=query_string,
            user_agent=user_agent,
        )

        # 6. Medir duração e processar
        start_time = time.perf_counter()
        status_code = 500  # Valor padrão caso ocorra exceção não tratada

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            bound_logger.error(
                "Erro não tratado durante processamento da requisição",
                duration_ms=round(duration_ms, 2),
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            # Resetar contexto antes de propagar
            request_id_ctx.reset(token)
            raise

        # 7. Calcular duração
        duration_seconds = time.perf_counter() - start_time
        duration_ms = duration_seconds * 1000

        # 8. Determinar nível de log baseado no status code
        log_kwargs = {
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }

        is_slow = duration_seconds >= self.SLOW_REQUEST_THRESHOLD_SECONDS
        if is_slow:
            log_kwargs["slow_request"] = True
            log_kwargs["threshold_seconds"] = self.SLOW_REQUEST_THRESHOLD_SECONDS

        if status_code >= 500:
            bound_logger.error("Requisição concluída com erro do servidor", **log_kwargs)
        elif status_code >= 400:
            bound_logger.warning("Requisição concluída com erro do cliente", **log_kwargs)
        elif is_slow:
            bound_logger.warning("Requisição concluída (lenta)", **log_kwargs)
        else:
            bound_logger.info("Requisição concluída com sucesso", **log_kwargs)

        # 9. Adicionar request ID ao header de resposta para rastreabilidade
        response.headers[REQUEST_ID_HEADER] = request_id

        # 10. Resetar contexto
        request_id_ctx.reset(token)

        return response


def configure_structlog() -> None:
    """Configura o structlog com processadores adequados para produção.

    Deve ser chamada uma vez durante a inicialização da aplicação (lifespan).
    Configura formatação JSON para produção e formatação legível para
    desenvolvimento.
    """
    import os

    is_development = os.getenv("ENVIRONMENT", "development").lower() == "development"

    # Processadores compartilhados
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_development:
        # Formatação legível para desenvolvimento
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(
            colors=True
        )
    else:
        # JSON estruturado para produção (compatível com ELK, Datadog, etc.)
        renderer = structlog.processors.JSONRenderer(ensure_ascii=False)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
