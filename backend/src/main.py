"""Entry-point da aplicação FastAPI — Automação Jurídica Assistida.

Cria a instância principal da aplicação FastAPI, registra routers,
middlewares, exception handlers e gerencia o ciclo de vida (lifespan)
da aplicação incluindo conexões com banco de dados e Redis.

Exemplo de uso:
    # Desenvolvimento:
    uvicorn backend.src.main:app --reload --host 0.0.0.0 --port 8000

    # Produção (via gunicorn + uvicorn workers):
    gunicorn backend.src.main:app -k uvicorn.workers.UvicornWorker
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.src.api.middleware.authentication import AuthenticationMiddleware
from backend.src.api.middleware.logging_middleware import LoggingMiddleware
from backend.src.api.middleware.rate_limiter import RateLimiterMiddleware
from backend.src.api.router import router as api_router
from backend.src.infrastructure.config.settings import get_settings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
settings = get_settings()

# Caminhos públicos que não exigem autenticação JWT
PUBLIC_PATHS: list[str] = [
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
]


# ---------------------------------------------------------------------------
# Lifespan — gerenciamento do ciclo de vida da aplicação
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação.

    Responsável por inicializar e encerrar recursos compartilhados como
    conexões com banco de dados, pool Redis e demais serviços de
    infraestrutura.

    Args:
        app: Instância da aplicação FastAPI.

    Yields:
        None — controle retorna à aplicação durante a execução.
    """
    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------
    logger.info("Iniciando aplicação Automação Jurídica Assistida...")

    # TODO: Inicializar pool de conexões do banco de dados (SQLAlchemy async engine)
    # TODO: Inicializar pool de conexões Redis para cache e rate limiting
    # TODO: Verificar conectividade com serviços externos (Anthropic API, etc.)

    logger.info(
        "Aplicação inicializada com sucesso.",
        environment=settings.ENVIRONMENT if hasattr(settings, "ENVIRONMENT") else "unknown",
    )

    yield

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    logger.info("Encerrando aplicação Automação Jurídica Assistida...")

    # TODO: Fechar pool de conexões do banco de dados
    # TODO: Fechar pool de conexões Redis
    # TODO: Aguardar finalização de tarefas Celery em andamento (graceful)

    logger.info("Aplicação encerrada com sucesso.")


# ---------------------------------------------------------------------------
# Criação da aplicação FastAPI
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    """Cria e configura a instância principal da aplicação FastAPI.

    Registra middlewares na ordem correta (LIFO — último registrado é o
    primeiro a processar), inclui routers, e configura exception handlers
    globais.

    Returns:
        Instância configurada da aplicação FastAPI.
    """
    application = FastAPI(
        title="Automação Jurídica Assistida",
        description=(
            "API REST para automação de processos jurídicos assistida por "
            "inteligência artificial. Oferece funcionalidades de gestão de "
            "casos, análise de documentos, chat jurídico e trilha de auditoria."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # Middlewares (ordem de registro: LIFO)
    # O último middleware registrado é o primeiro a interceptar o request.
    # Ordem de execução desejada:
    #   1. Logging (primeiro a capturar, último a finalizar)
    #   2. Rate Limiting
    #   3. CORS
    #   4. Autenticação
    # Logo, registramos na ordem inversa:
    # ------------------------------------------------------------------

    _register_middlewares(application)

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    application.include_router(api_router, prefix="/api/v1")

    # ------------------------------------------------------------------
    # Exception Handlers
    # ------------------------------------------------------------------
    _register_exception_handlers(application)

    return application


# ---------------------------------------------------------------------------
# Registro de middlewares
# ---------------------------------------------------------------------------
def _register_middlewares(application: FastAPI) -> None:
    """Registra todos os middlewares da aplicação na ordem correta.

    Args:
        application: Instância da aplicação FastAPI.
    """
    # 4. Autenticação JWT (executa por último na cadeia de request)
    application.add_middleware(
        AuthenticationMiddleware,
        public_paths=PUBLIC_PATHS,
    )

    # 3. CORS — permite requisições cross-origin do frontend
    allowed_origins = (
        getattr(settings, "CORS_ORIGINS", ["http://localhost:5173"])
        if hasattr(settings, "CORS_ORIGINS")
        else ["http://localhost:5173"]
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 2. Rate Limiting por IP/usuário via Redis sliding window
    redis_url = (
        str(settings.REDIS_URL)
        if hasattr(settings, "REDIS_URL")
        else "redis://localhost:6379/0"
    )
    application.add_middleware(
        RateLimiterMiddleware,
        redis_url=redis_url,
        default_limit=100,
        default_window=60,
    )

    # 1. Logging estruturado com correlação de request ID (primeiro a executar)
    application.add_middleware(LoggingMiddleware)


# ---------------------------------------------------------------------------
# Exception Handlers globais
# ---------------------------------------------------------------------------
def _register_exception_handlers(application: FastAPI) -> None:
    """Registra exception handlers globais para tratamento padronizado de erros.

    Args:
        application: Instância da aplicação FastAPI.
    """

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Trata erros de validação de request (Pydantic / FastAPI).

        Retorna resposta padronizada com detalhes dos campos inválidos
        em português.

        Args:
            request: Objeto de requisição HTTP.
            exc: Exceção de validação capturada.

        Returns:
            JSONResponse com status 422 e detalhes do erro.
        """
        logger.warning(
            "Erro de validação na requisição.",
            path=request.url.path,
            method=request.method,
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Erro de validação nos dados enviados.",
                "errors": _format_validation_errors(exc.errors()),
            },
        )

    @application.exception_handler(ValueError)
    async def value_error_handler(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        """Trata erros de valor inesperados na camada de negócio.

        Args:
            request: Objeto de requisição HTTP.
            exc: Exceção ValueError capturada.

        Returns:
            JSONResponse com status 400 e mensagem descritiva.
        """
        logger.warning(
            "Erro de valor na requisição.",
            path=request.url.path,
            detail=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @application.exception_handler(PermissionError)
    async def permission_error_handler(
        request: Request, exc: PermissionError
    ) -> JSONResponse:
        """Trata erros de permissão / autorização.

        Args:
            request: Objeto de requisição HTTP.
            exc: Exceção PermissionError capturada.

        Returns:
            JSONResponse com status 403 e mensagem descritiva.
        """
        logger.warning(
            "Acesso negado.",
            path=request.url.path,
            detail=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Acesso negado. Você não possui permissão para esta operação."},
        )

    @application.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Trata exceções não capturadas (fallback global).

        Registra o erro completo nos logs e retorna mensagem genérica
        ao cliente para não expor detalhes internos.

        Args:
            request: Objeto de requisição HTTP.
            exc: Exceção genérica capturada.

        Returns:
            JSONResponse com status 500 e mensagem genérica.
        """
        logger.error(
            "Erro interno não tratado.",
            path=request.url.path,
            method=request.method,
            error_type=type(exc).__name__,
            error_detail=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Erro interno do servidor. Tente novamente mais tarde."
            },
        )


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def _format_validation_errors(errors: list[dict]) -> list[dict]:
    """Formata erros de validação Pydantic para resposta padronizada.

    Transforma a lista de erros do Pydantic em um formato mais amigável,
    com campos traduzidos e mensagens em português quando possível.

    Args:
        errors: Lista de dicionários de erro do Pydantic.

    Returns:
        Lista de dicionários formatados com campo, mensagem e tipo do erro.
    """
    formatted = []
    for error in errors:
        formatted.append(
            {
                "campo": " -> ".join(str(loc) for loc in error.get("loc", [])),
                "mensagem": error.get("msg", "Valor inválido."),
                "tipo": error.get("type", "desconhecido"),
            }
        )
    return formatted


# ---------------------------------------------------------------------------
# Configuração de logging estruturado
# ---------------------------------------------------------------------------
def _configure_logging() -> None:
    """Configura o logging estruturado com structlog.

    Define processadores, formatadores e nível de log baseado
    nas configurações do ambiente.
    """
    log_level = (
        getattr(settings, "LOG_LEVEL", "INFO")
        if hasattr(settings, "LOG_LEVEL")
        else "INFO"
    )

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------
_configure_logging()
app = create_app()
