"""Pacote de infraestrutura de banco de dados.

Este pacote contém a configuração e os componentes de acesso ao banco de dados
PostgreSQL utilizando SQLAlchemy 2.0 com suporte assíncrono (asyncpg).

Componentes exportados:
    - Base: classe base declarativa para modelos SQLAlchemy
    - DatabaseSession: gerenciador de sessões assíncronas
    - get_async_session: dependency injection para FastAPI
    - async_engine: engine assíncrona configurada
    - AsyncSessionLocal: factory de sessões assíncronas
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from typing import AsyncGenerator

import os


# URL de conexão com o banco de dados PostgreSQL via asyncpg
# Formato esperado: postgresql+asyncpg://usuario:senha@host:porta/nome_banco
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/automacao_juridica",
)

# Engine assíncrona do SQLAlchemy
async_engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
    pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
    pool_pre_ping=True,
    pool_recycle=300,
)

# Factory de sessões assíncronas
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Classe base declarativa para todos os modelos SQLAlchemy do projeto.

    Todos os modelos de domínio que necessitam de persistência devem
    herdar desta classe para garantir registro correto no metadata
    e compatibilidade com Alembic para migrações.
    """

    pass


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Fornece uma sessão assíncrona do banco de dados.

    Dependency injection para uso nos endpoints FastAPI.
    Garante que a sessão seja fechada corretamente após o uso,
    mesmo em caso de exceção.

    Yields:
        AsyncSession: sessão assíncrona do SQLAlchemy pronta para uso.

    Exemplo de uso em um endpoint FastAPI::

        @router.get("/items")
        async def list_items(
            session: AsyncSession = Depends(get_async_session),
        ):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Inicializa o banco de dados criando todas as tabelas.

    Utiliza o metadata da classe Base para criar as tabelas que ainda
    não existem. Em produção, prefira usar Alembic para migrações
    controladas.

    Nota:
        Esta função é útil para ambientes de desenvolvimento e testes.
        Para produção, utilize as migrações Alembic.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Encerra a conexão com o banco de dados.

    Deve ser chamada durante o shutdown da aplicação para liberar
    recursos de conexão de forma limpa.
    """
    await async_engine.dispose()


__all__ = [
    "Base",
    "AsyncSessionLocal",
    "async_engine",
    "get_async_session",
    "init_db",
    "close_db",
    "DATABASE_URL",
]
