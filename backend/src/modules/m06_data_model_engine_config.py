"""Módulo backlog #6: Configuração do Database Engine — Automação Jurídica Assistida.

Responsável pela validação de schema do banco de dados, seleção de engine
assíncrono (asyncpg para PostgreSQL), configuração de connection pool e
verificações de saúde da conexão.

Este módulo complementa o módulo de sessão (infrastructure.database.session)
fornecendo configurações avançadas de engine, validação de schema e
gerenciamento do pool de conexões.

Exemplo de uso:
    from backend.src.modules.m06_data_model_engine_config import (
        EngineConfig,
        get_engine_config,
        validate_database_schema,
        check_database_health,
    )

    config = get_engine_config()
    engine = config.create_async_engine()

    # Verificar saúde da conexão
    health = await check_database_health(engine)
    print(health.status)  # "healthy" ou "unhealthy"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)

from backend.src.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes de configuração padrão do pool
# ---------------------------------------------------------------------------

DEFAULT_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = 20
DEFAULT_POOL_TIMEOUT = 30  # segundos
DEFAULT_POOL_RECYCLE = 1800  # segundos (30 minutos)
DEFAULT_POOL_PRE_PING = True
DEFAULT_ECHO_SQL = False

MIN_POOL_SIZE = 1
MAX_POOL_SIZE = 100
MIN_MAX_OVERFLOW = 0
MAX_MAX_OVERFLOW = 200
MIN_POOL_TIMEOUT = 5
MAX_POOL_TIMEOUT = 120
MIN_POOL_RECYCLE = 300
MAX_POOL_RECYCLE = 7200

# Schemas obrigatórios que devem existir no banco para a aplicação funcionar
REQUIRED_SCHEMAS = ["public"]

# Tabelas essenciais esperadas após migrações Alembic
# TODO: Atualizar esta lista conforme novos módulos forem implementados
EXPECTED_CORE_TABLES = [
    "users",
    "audit_logs",
    "documents",
    "alembic_version",
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DatabaseDialect(str, Enum):
    """Dialetos de banco de dados suportados pela aplicação."""

    POSTGRESQL_ASYNCPG = "postgresql+asyncpg"
    POSTGRESQL_PSYCOPG = "postgresql+psycopg"
    SQLITE_AIOSQLITE = "sqlite+aiosqlite"  # Apenas para testes


class HealthStatus(str, Enum):
    """Status de saúde da conexão com o banco de dados."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


# ---------------------------------------------------------------------------
# Modelos Pydantic para configuração e validação
# ---------------------------------------------------------------------------


class PoolConfig(BaseModel):
    """Configuração do connection pool do SQLAlchemy.

    Valida os parâmetros do pool de conexões garantindo que estejam
    dentro de limites seguros para operação em produção.
    """

    pool_size: int = Field(
        default=DEFAULT_POOL_SIZE,
        ge=MIN_POOL_SIZE,
        le=MAX_POOL_SIZE,
        description="Número de conexões permanentes no pool.",
    )
    max_overflow: int = Field(
        default=DEFAULT_MAX_OVERFLOW,
        ge=MIN_MAX_OVERFLOW,
        le=MAX_MAX_OVERFLOW,
        description="Número máximo de conexões extras além do pool_size.",
    )
    pool_timeout: int = Field(
        default=DEFAULT_POOL_TIMEOUT,
        ge=MIN_POOL_TIMEOUT,
        le=MAX_POOL_TIMEOUT,
        description="Tempo máximo (segundos) para aguardar uma conexão do pool.",
    )
    pool_recycle: int = Field(
        default=DEFAULT_POOL_RECYCLE,
        ge=MIN_POOL_RECYCLE,
        le=MAX_POOL_RECYCLE,
        description="Tempo (segundos) para reciclar conexões ociosas.",
    )
    pool_pre_ping: bool = Field(
        default=DEFAULT_POOL_PRE_PING,
        description="Verificar conexão antes de usar (evita conexões mortas).",
    )

    @field_validator("max_overflow")
    @classmethod
    def validate_max_overflow_ratio(cls, v: int, info: Any) -> int:
        """Valida que max_overflow não exceda 3x o pool_size."""
        pool_size = info.data.get("pool_size", DEFAULT_POOL_SIZE)
        limit = pool_size * 3
        if v > limit:
            raise ValueError(
                f"max_overflow ({v}) não pode exceder 3x o pool_size ({pool_size}). "
                f"Limite calculado: {limit}."
            )
        return v


class EngineConfig(BaseModel):
    """Configuração completa do engine assíncrono do SQLAlchemy.

    Centraliza todas as configurações necessárias para criar e gerenciar
    o engine de banco de dados, incluindo dialect, pool e opções de debug.
    """

    database_url: str = Field(
        ...,
        description="URL de conexão com o banco de dados (formato SQLAlchemy).",
    )
    dialect: DatabaseDialect = Field(
        default=DatabaseDialect.POSTGRESQL_ASYNCPG,
        description="Dialeto do banco de dados.",
    )
    pool: PoolConfig = Field(
        default_factory=PoolConfig,
        description="Configuração do connection pool.",
    )
    echo_sql: bool = Field(
        default=DEFAULT_ECHO_SQL,
        description="Habilitar log de SQL gerado (apenas desenvolvimento).",
    )
    connect_args: dict[str, Any] = Field(
        default_factory=dict,
        description="Argumentos adicionais passados ao driver de conexão.",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Valida formato básico da URL de conexão."""
        if not v:
            raise ValueError("URL do banco de dados não pode ser vazia.")

        valid_prefixes = tuple(d.value for d in DatabaseDialect)
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(
                f"URL do banco de dados deve iniciar com um dos dialetos suportados: "
                f"{', '.join(valid_prefixes)}. Recebido: {v[:30]}..."
            )
        return v

    def build_engine_kwargs(self) -> dict[str, Any]:
        """Constrói o dicionário de argumentos para create_async_engine.

        Returns:
            Dicionário com todos os parâmetros configurados para o engine.
        """
        kwargs: dict[str, Any] = {
            "echo": self.echo_sql,
            "pool_pre_ping": self.pool.pool_pre_ping,
        }

        # SQLite não suporta pool configurável
        if self.dialect != DatabaseDialect.SQLITE_AIOSQLITE:
            kwargs.update(
                {
                    "pool_size": self.pool.pool_size,
                    "max_overflow": self.pool.max_overflow,
                    "pool_timeout": self.pool.pool_timeout,
                    "pool_recycle": self.pool.pool_recycle,
                }
            )

        if self.connect_args:
            kwargs["connect_args"] = self.connect_args

        return kwargs

    def create_engine(self) -> AsyncEngine:
        """Cria e retorna uma instância de AsyncEngine configurada.

        Returns:
            AsyncEngine do SQLAlchemy configurado conforme parâmetros.
        """
        engine_kwargs = self.build_engine_kwargs()

        logger.info(
            "Criando engine assíncrono — dialect=%s, pool_size=%d, max_overflow=%d, "
            "pool_pre_ping=%s, echo=%s",
            self.dialect.value,
            self.pool.pool_size,
            self.pool.max_overflow,
            self.pool.pool_pre_ping,
            self.echo_sql,
        )

        return create_async_engine(self.database_url, **engine_kwargs)


# ---------------------------------------------------------------------------
# Modelos de resposta para health check
# ---------------------------------------------------------------------------


@dataclass
class SchemaValidationResult:
    """Resultado da validação de schema do banco de dados."""

    is_valid: bool
    existing_schemas: list[str] = field(default_factory=list)
    missing_schemas: list[str] = field(default_factory=list)
    existing_tables: list[str] = field(default_factory=list)
    missing_tables: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class DatabaseHealthResult:
    """Resultado da verificação de saúde do banco de dados."""

    status: HealthStatus
    latency_ms: float | None = None
    server_version: str | None = None
    active_connections: int | None = None
    pool_size: int | None = None
    pool_checked_out: int | None = None
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Funções de fábrica e utilitárias
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_engine_config() -> EngineConfig:
    """Obtém a configuração do engine a partir das settings da aplicação.

    Utiliza cache (lru_cache) para garantir instância única (singleton).
    Lê as configurações do módulo de settings centralizado.

    Returns:
        EngineConfig configurado com base nas variáveis de ambiente.
    """
    settings = get_settings()

    # Extrair DATABASE_URL das settings
    # O settings deve expor DATABASE_URL como string
    database_url = str(settings.DATABASE_URL)

    # Determinar dialect a partir da URL
    dialect = DatabaseDialect.POSTGRESQL_ASYNCPG
    for d in DatabaseDialect:
        if database_url.startswith(d.value):
            dialect = d
            break

    # Configurações de pool — usar valores das settings se disponíveis,
    # caso contrário usar defaults seguros
    pool_config_kwargs: dict[str, Any] = {}

    # Tentar ler configurações opcionais de pool das settings
    if hasattr(settings, "DB_POOL_SIZE"):
        pool_config_kwargs["pool_size"] = settings.DB_POOL_SIZE
    if hasattr(settings, "DB_MAX_OVERFLOW"):
        pool_config_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    if hasattr(settings, "DB_POOL_TIMEOUT"):
        pool_config_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
    if hasattr(settings, "DB_POOL_RECYCLE"):
        pool_config_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE
    if hasattr(settings, "DB_POOL_PRE_PING"):
        pool_config_kwargs["pool_pre_ping"] = settings.DB_POOL_PRE_PING

    pool_config = PoolConfig(**pool_config_kwargs)

    # Determinar echo_sql (apenas em desenvolvimento)
    echo_sql = DEFAULT_ECHO_SQL
    if hasattr(settings, "DEBUG"):
        echo_sql = bool(settings.DEBUG)
    elif hasattr(settings, "ENVIRONMENT"):
        echo_sql = str(settings.ENVIRONMENT).lower() in ("development", "dev", "local")

    # Argumentos específicos do asyncpg para PostgreSQL
    connect_args: dict[str, Any] = {}
    if dialect == DatabaseDialect.POSTGRESQL_ASYNCPG:
        connect_args = {
            "server_settings": {
                "application_name": "automacao-juridica-assistida",
                "jit": "off",  # Desabilitar JIT para queries curtas
            },
            "command_timeout": 60,
        }

    return EngineConfig(
        database_url=database_url,
        dialect=dialect,
        pool=pool_config,
        echo_sql=echo_sql,
        connect_args=connect_args,
    )


def create_configured_engine() -> AsyncEngine:
    """Atalho para criar um engine com a configuração padrão da aplicação.

    Returns:
        AsyncEngine configurado e pronto para uso.
    """
    config = get_engine_config()
    return config.create_engine()


# ---------------------------------------------------------------------------
# Funções assíncronas de validação e health check
# ---------------------------------------------------------------------------


async def validate_database_schema(
    engine: AsyncEngine,
    required_schemas: list[str] | None = None,
    expected_tables: list[str] | None = None,
) -> SchemaValidationResult:
    """Valida se o schema do banco de dados contém as estruturas esperadas.

    Verifica a existência de schemas PostgreSQL e tabelas essenciais.
    Útil para validação pós-migração e verificação de integridade.

    Args:
        engine: AsyncEngine do SQLAlchemy para conexão.
        required_schemas: Lista de schemas que devem existir.
            Se None, usa REQUIRED_SCHEMAS.
        expected_tables: Lista de tabelas esperadas no schema public.
            Se None, usa EXPECTED_CORE_TABLES.

    Returns:
        SchemaValidationResult com detalhes da validação.
    """
    if required_schemas is None:
        required_schemas = REQUIRED_SCHEMAS
    if expected_tables is None:
        expected_tables = EXPECTED_CORE_TABLES

    result = SchemaValidationResult(is_valid=True)

    try:
        async with engine.connect() as conn:
            # Verificar schemas existentes
            schema_query = text(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')"
            )
            schema_result = await conn.execute(schema_query)
            result.existing_schemas = [row[0] for row in schema_result.fetchall()]

            # Verificar schemas obrigatórios
            for schema in required_schemas:
                if schema not in result.existing_schemas:
                    result.missing_schemas.append(schema)
                    result.is_valid = False
                    result.errors.append(
                        f"Schema obrigatório '{schema}' não encontrado no banco de dados."
                    )

            # Verificar tabelas no schema public
            table_query = text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
            table_result = await conn.execute(table_query)
            result.existing_tables = [row[0] for row in table_result.fetchall()]

            # Verificar tabelas esperadas
            for table in expected_tables:
                if table not in result.existing_tables:
                    result.missing_tables.append(table)
                    result.is_valid = False
                    result.errors.append(
                        f"Tabela esperada '{table}' não encontrada no schema 'public'. "
                        f"Execute as migrações Alembic."
                    )

    except Exception as exc:
        result.is_valid = False
        result.errors.append(
            f"Erro ao validar schema do banco de dados: {exc!s}"
        )
        logger.exception("Falha na validação de schema do banco de dados.")

    if result.is_valid:
        logger.info(
            "Validação de schema concluída com sucesso — schemas=%s, tabelas=%d",
            result.existing_schemas,
            len(result.existing_tables),
        )
    else:
        logger.warning(
            "Validação de schema encontrou problemas — erros=%s",
            result.errors,
        )

    return result


async def check_database_health(engine: AsyncEngine) -> DatabaseHealthResult:
    """Verifica a saúde da conexão com o banco de dados.

    Executa uma query simples para medir latência, obtém informações
    do servidor e estatísticas do pool de conexões.

    Args:
        engine: AsyncEngine do SQLAlchemy para verificação.

    Returns:
        DatabaseHealthResult com status e métricas da conexão.
    """
    import time

    result = DatabaseHealthResult(status=HealthStatus.HEALTHY)

    # Estatísticas do pool (disponíveis no engine síncrono subjacente)
    try:
        pool = engine.pool
        result.pool_size = pool.size() if hasattr(pool, "size") else None
        result.pool_checked_out = (
            pool.checkedout() if hasattr(pool, "checkedout") else None
        )
    except Exception:
        # Pool pode não estar disponível em todos os cenários
        pass

    try:
        start_time = time.monotonic()

        async with engine.connect() as conn:
            # Query de saúde básica
            ping_result = await conn.execute(text("SELECT 1"))
            ping_result.fetchone()

            elapsed_ms = (time.monotonic() - start_time) * 1000
            result.latency_ms = round(elapsed_ms, 2)

            # Obter versão do servidor
            try:
                version_result = await conn.execute(text("SELECT version()"))
                row = version_result.fetchone()
                if row:
                    result.server_version = str(row[0])
            except Exception:
                pass  # Não crítico

            # Obter contagem de conexões ativas
            try:
                conn_count_result = await conn.execute(
                    text(
                        "SELECT count(*) FROM pg_stat_activity "
                        "WHERE state = 'active'"
                    )
                )
                row = conn_count_result.fetchone()
                if row:
                    result.active_connections = int(row[0])
            except Exception:
                pass  # Não crítico

        # Verificar se latência está degradada (> 500ms)
        if result.latency_ms and result.latency_ms > 500:
            result.status = HealthStatus.DEGRADED
            result.errors.append(
                f"Latência elevada detectada: {result.latency_ms}ms (limite: 500ms)."
            )
            logger.warning(
                "Conexão com banco de dados degradada — latência=%.2fms",
                result.latency_ms,
            )

        logger.info(
            "Health check do banco concluído — status=%s, latência=%.2fms",
            result.status.value,
            result.latency_ms or 0,
        )

    except Exception as exc:
        result.status = HealthStatus.UNHEALTHY
        result.errors.append(
            f"Falha na conexão com o banco de dados: {exc!s}"
        )
        logger.exception("Health check do banco de dados falhou.")

    return result


async def get_pool_status(engine: AsyncEngine) -> dict[str, Any]:
    """Retorna estatísticas detalhadas do connection pool.

    Útil para monitoramento e dashboards operacionais.

    Args:
        engine: AsyncEngine do SQLAlchemy.

    Returns:
        Dicionário com métricas do pool de conexões.
    """
    pool = engine.pool
    status: dict[str, Any] = {
        "pool_class": type(pool).__name__,
    }

    # Métricas disponíveis dependem do tipo de pool
    if hasattr(pool, "size"):
        status["size"] = pool.size()
    if hasattr(pool, "checkedin"):
        status["checked_in"] = pool.checkedin()
    if hasattr(pool, "checkedout"):
        status["checked_out"] = pool.checkedout()
    if hasattr(pool, "overflow"):
        status["overflow"] = pool.overflow()
    if hasattr(pool, "_max_overflow"):
        status["max_overflow"] = pool._max_overflow
    if hasattr(pool, "_pool"):
        status["idle_connections"] = pool._pool.qsize() if hasattr(pool._pool, "qsize") else None

    logger.debug("Status do pool de conexões: %s", status)
    return status


# ---------------------------------------------------------------------------
# Função de inicialização para uso no startup da aplicação
# ---------------------------------------------------------------------------


async def initialize_engine_and_validate(
    skip_schema_validation: bool = False,
) -> tuple[AsyncEngine, DatabaseHealthResult]:
    """Inicializa o engine e executa validações de saúde e schema.

    Função de conveniência para uso no evento de startup do FastAPI.
    Cria o engine, verifica saúde da conexão e opcionalmente valida
    o schema do banco de dados.

    Args:
        skip_schema_validation: Se True, pula a validação de schema.
            Útil em ambientes de teste ou quando migrações ainda não
            foram executadas.

    Returns:
        Tupla com (AsyncEngine, DatabaseHealthResult).

    Raises:
        RuntimeError: Se o banco de dados estiver inacessível.
    """
    engine = create_configured_engine()

    # Verificar saúde
    health = await check_database_health(engine)

    if health.status == HealthStatus.UNHEALTHY:
        await engine.dispose()
        raise RuntimeError(
            f"Banco de dados inacessível durante inicialização. "
            f"Erros: {'; '.join(health.errors)}"
        )

    # Validar schema se solicitado
    if not skip_schema_validation:
        schema_result = await validate_database_schema(engine)
        if not schema_result.is_valid:
            logger.warning(
                "Schema do banco de dados incompleto — tabelas faltando: %s. "
                "Execute 'alembic upgrade head' para aplicar migrações.",
                schema_result.missing_tables,
            )
            # Não levanta exceção, apenas avisa — permite que a aplicação
            # inicie mesmo sem todas as tabelas (útil para primeira execução)

    logger.info(
        "Engine do banco de dados inicializado com sucesso — status=%s",
        health.status.value,
    )

    return engine, health


async def dispose_engine(engine: AsyncEngine) -> None:
    """Encerra o engine e libera todas as conexões do pool.

    Deve ser chamado no evento de shutdown do FastAPI.

    Args:
        engine: AsyncEngine a ser encerrado.
    """
    logger.info("Encerrando engine do banco de dados e liberando conexões do pool.")
    await engine.dispose()
    logger.info("Engine do banco de dados encerrado com sucesso.")
