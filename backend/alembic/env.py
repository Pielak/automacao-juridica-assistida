"""Configuração do ambiente Alembic para migrações assíncronas do PostgreSQL.

Este módulo configura o Alembic para trabalhar com SQLAlchemy 2.0 assíncrono
(asyncpg), carregando os metadados de todos os modelos registrados na Base
declarativa e suportando migrações tanto online quanto offline.

Projeto: Automação Jurídica Assistida
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Importa Base com todos os modelos registrados para detecção automática de tabelas.
# O barrel export em models/__init__.py garante que todos os modelos
# (User, Case, Document, Analysis, AuditLog, ChatSession, ChatMessage)
# estejam registrados na metadata da Base.
from backend.src.infrastructure.database.models import Base

# Objeto de configuração do Alembic, que dá acesso aos valores
# definidos no arquivo alembic.ini.
config = context.config

# Configura logging a partir do arquivo .ini do Alembic,
# caso a seção [loggers] esteja presente.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData alvo para operações de 'autogenerate' do Alembic.
# Contém as definições de todas as tabelas dos modelos importados.
target_metadata = Base.metadata


def _get_database_url() -> str:
    """Obtém a URL de conexão com o banco de dados.

    Prioriza a variável de ambiente DATABASE_URL sobre o valor configurado
    no alembic.ini (sqlalchemy.url). Isso permite configuração dinâmica
    em diferentes ambientes (desenvolvimento, staging, produção) sem
    alterar o arquivo de configuração.

    Para uso com asyncpg, a URL deve utilizar o scheme
    'postgresql+asyncpg://...' em vez de 'postgresql://'.

    Returns:
        URL de conexão com o banco de dados PostgreSQL.

    Raises:
        ValueError: Se nenhuma URL de banco de dados for configurada.
    """
    url = os.environ.get("DATABASE_URL")
    if url:
        # Garante compatibilidade: converte scheme padrão para asyncpg
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    url_from_config = config.get_main_option("sqlalchemy.url")
    if url_from_config:
        return url_from_config

    raise ValueError(
        "URL do banco de dados não configurada. "
        "Defina a variável de ambiente DATABASE_URL ou configure "
        "sqlalchemy.url no alembic.ini."
    )


def run_migrations_offline() -> None:
    """Executa migrações no modo 'offline'.

    No modo offline, o Alembic gera o SQL das migrações sem conectar
    ao banco de dados. Útil para gerar scripts SQL que serão executados
    manualmente ou por ferramentas de CI/CD.

    Configura o contexto apenas com a URL e os metadados alvo,
    sem criar uma Engine real.
    """
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Executa as migrações dentro de uma conexão síncrona.

    Função auxiliar chamada tanto pelo modo online síncrono quanto
    pelo wrapper assíncrono. Configura o contexto do Alembic com
    a conexão fornecida e executa as migrações pendentes.

    Args:
        connection: Conexão SQLAlchemy ativa com o banco de dados.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Inclui schemas de objetos na comparação de autogenerate
        include_schemas=True,
        # Renderiza tipos de coluna como imports para melhor legibilidade
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Executa migrações no modo 'online' assíncrono.

    Cria uma engine assíncrona (asyncpg) a partir da configuração,
    estabelece uma conexão e executa as migrações de forma assíncrona.
    Utiliza NullPool para evitar problemas com pool de conexões
    durante migrações.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Executa migrações no modo 'online' (conectado ao banco).

    Ponto de entrada para migrações online. Delega para a função
    assíncrona que cria a engine asyncpg e executa as migrações.
    Utiliza asyncio.run() para executar a coroutine no event loop.
    """
    asyncio.run(run_async_migrations())


# Determina o modo de execução e chama a função apropriada.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
