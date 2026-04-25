"""Módulo de rotas de health check — Automação Jurídica Assistida.

Fornece endpoints para verificação de saúde da aplicação:
- GET /health — Liveness probe (sempre responde se o processo está ativo).
- GET /health/ready — Readiness probe (verifica dependências: DB, Redis, storage).

Exemplo de uso:
    from backend.src.api.routes.health_routes import router as health_router
    app.include_router(health_router)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


# ---------------------------------------------------------------------------
# Schemas de resposta
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Schema de resposta para o endpoint de liveness."""

    status: str = Field(
        ...,
        description="Estado geral da aplicação.",
        examples=["ok"],
    )
    timestamp: str = Field(
        ...,
        description="Data/hora UTC da verificação no formato ISO 8601.",
    )
    version: str = Field(
        ...,
        description="Versão da aplicação.",
    )


class DependencyCheck(BaseModel):
    """Resultado da verificação de uma dependência individual."""

    status: str = Field(
        ...,
        description="Estado da dependência: 'ok' ou 'indisponível'.",
    )
    latency_ms: float | None = Field(
        default=None,
        description="Latência da verificação em milissegundos.",
    )
    detail: str | None = Field(
        default=None,
        description="Detalhes adicionais em caso de falha.",
    )


class ReadinessResponse(BaseModel):
    """Schema de resposta para o endpoint de readiness."""

    status: str = Field(
        ...,
        description="Estado geral: 'ok' se todas as dependências estão saudáveis, 'degradado' caso contrário.",
    )
    timestamp: str = Field(
        ...,
        description="Data/hora UTC da verificação no formato ISO 8601.",
    )
    checks: dict[str, DependencyCheck] = Field(
        ...,
        description="Mapa de dependência → resultado da verificação.",
    )


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# TODO: Extrair versão de um arquivo de configuração ou variável de ambiente.
_APP_VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# Funções auxiliares de verificação
# ---------------------------------------------------------------------------


async def _check_database(session: AsyncSession) -> DependencyCheck:
    """Verifica conectividade com o PostgreSQL executando uma query simples."""
    start = time.monotonic()
    try:
        result = await session.execute(text("SELECT 1"))
        _ = result.scalar_one()
        latency = (time.monotonic() - start) * 1000
        return DependencyCheck(status="ok", latency_ms=round(latency, 2))
    except Exception as exc:  # noqa: BLE001
        latency = (time.monotonic() - start) * 1000
        logger.error(
            "Falha na verificação de saúde do banco de dados.",
            error=str(exc),
            latency_ms=round(latency, 2),
        )
        return DependencyCheck(
            status="indisponível",
            latency_ms=round(latency, 2),
            detail=f"Erro ao conectar ao PostgreSQL: {exc!s}",
        )


async def _check_redis() -> DependencyCheck:
    """Verifica conectividade com o Redis.

    TODO: Injetar cliente Redis quando o módulo de cache/sessão estiver
    implementado. Por enquanto retorna status indicando que a verificação
    ainda não foi configurada.
    """
    start = time.monotonic()
    try:
        # TODO: Substituir pelo ping real ao Redis quando o módulo de
        # infraestrutura de cache estiver disponível.
        # Exemplo esperado:
        #   from backend.src.infrastructure.cache.redis import get_redis_client
        #   redis = get_redis_client()
        #   await redis.ping()
        latency = (time.monotonic() - start) * 1000
        return DependencyCheck(
            status="não configurado",
            latency_ms=round(latency, 2),
            detail="Verificação do Redis ainda não implementada — aguardando módulo de cache.",
        )
    except Exception as exc:  # noqa: BLE001
        latency = (time.monotonic() - start) * 1000
        logger.error(
            "Falha na verificação de saúde do Redis.",
            error=str(exc),
            latency_ms=round(latency, 2),
        )
        return DependencyCheck(
            status="indisponível",
            latency_ms=round(latency, 2),
            detail=f"Erro ao conectar ao Redis: {exc!s}",
        )


async def _check_storage() -> DependencyCheck:
    """Verifica conectividade com o serviço de armazenamento de arquivos.

    TODO: Injetar cliente de storage (S3/MinIO/local) quando o módulo de
    armazenamento estiver implementado.
    """
    start = time.monotonic()
    try:
        # TODO: Substituir pela verificação real do storage quando o módulo
        # de infraestrutura de armazenamento estiver disponível.
        # Exemplo esperado:
        #   from backend.src.infrastructure.storage.client import get_storage_client
        #   storage = get_storage_client()
        #   await storage.health_check()
        latency = (time.monotonic() - start) * 1000
        return DependencyCheck(
            status="não configurado",
            latency_ms=round(latency, 2),
            detail="Verificação do storage ainda não implementada — aguardando módulo de armazenamento.",
        )
    except Exception as exc:  # noqa: BLE001
        latency = (time.monotonic() - start) * 1000
        logger.error(
            "Falha na verificação de saúde do storage.",
            error=str(exc),
            latency_ms=round(latency, 2),
        )
        return DependencyCheck(
            status="indisponível",
            latency_ms=round(latency, 2),
            detail=f"Erro ao conectar ao storage: {exc!s}",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness — verificação básica de vida da aplicação",
    description=(
        "Retorna HTTP 200 se o processo da aplicação está ativo. "
        "Utilizado como liveness probe pelo orquestrador (ex.: Kubernetes)."
    ),
)
async def liveness() -> HealthResponse:
    """Endpoint de liveness probe.

    Sempre retorna 200 se o processo FastAPI estiver respondendo.
    Não verifica dependências externas.
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        version=_APP_VERSION,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness — verificação de prontidão com dependências",
    description=(
        "Verifica a saúde de todas as dependências críticas (banco de dados, "
        "Redis, storage). Retorna HTTP 200 se todas estão saudáveis ou "
        "HTTP 503 se alguma está indisponível. Utilizado como readiness "
        "probe pelo orquestrador."
    ),
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Uma ou mais dependências estão indisponíveis.",
            "model": ReadinessResponse,
        },
    },
)
async def readiness(
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """Endpoint de readiness probe.

    Executa verificações de saúde em paralelo para todas as dependências
    externas e retorna o resultado consolidado.

    Returns:
        ReadinessResponse com status geral e detalhes por dependência.
        HTTP 503 se qualquer dependência crítica estiver indisponível.
    """
    # Executa verificações
    db_check = await _check_database(session)
    redis_check = await _check_redis()
    storage_check = await _check_storage()

    checks: dict[str, DependencyCheck] = {
        "database": db_check,
        "redis": redis_check,
        "storage": storage_check,
    }

    # Dependências críticas que determinam se a aplicação está pronta.
    # Redis e storage são marcados como "não configurado" durante o scaffold,
    # então só consideramos "indisponível" como falha real.
    critical_statuses = [db_check.status]
    has_failure = any(s == "indisponível" for s in critical_statuses)

    overall_status = "degradado" if has_failure else "ok"
    timestamp = datetime.now(tz=timezone.utc).isoformat()

    response_data = ReadinessResponse(
        status=overall_status,
        timestamp=timestamp,
        checks=checks,
    )

    if has_failure:
        logger.warning(
            "Readiness check falhou — dependência(s) indisponível(is).",
            checks={k: v.status for k, v in checks.items()},
        )
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response_data.model_dump(),
        )

    logger.debug(
        "Readiness check concluído com sucesso.",
        checks={k: v.status for k, v in checks.items()},
    )
    return response_data
