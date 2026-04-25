"""Barrel export de todos os models SQLAlchemy — Automação Jurídica Assistida.

Centraliza a exportação de todos os modelos de banco de dados do sistema,
incluindo a classe Base declarativa do SQLAlchemy e todos os modelos de
domínio (User, Case, Document, Analysis, AuditLog, ChatSession, ChatMessage).

Este módulo facilita imports consistentes em toda a aplicação:
    from backend.src.infrastructure.database.models import Base, User, Case

Todos os modelos são registrados na mesma instância de Base, garantindo que
o Alembic consiga detectar todas as tabelas para migrações automáticas.

Exemplo de uso:
    from backend.src.infrastructure.database.models import (
        Base,
        User,
        Case,
        Document,
        Analysis,
        AuditLog,
        ChatSession,
        ChatMessage,
    )

    # Criar todas as tabelas (útil em testes)
    Base.metadata.create_all(bind=engine)
"""

from backend.src.infrastructure.database.models.user import User
from backend.src.infrastructure.database.models.case import Case
from backend.src.infrastructure.database.models.document import Document
from backend.src.infrastructure.database.models.analysis import Analysis
from backend.src.infrastructure.database.models.audit_log import AuditLog
from backend.src.infrastructure.database.models.chat_session import (
    ChatSession,
    ChatMessage,
)

# A classe Base declarativa é importada do modelo User por convenção;
# todos os demais modelos herdam da mesma instância de Base.
# TODO: Quando o módulo base.py dedicado for criado, importar Base de lá.
# Por ora, re-exportamos a partir do primeiro modelo que a define.
try:
    from backend.src.infrastructure.database.models.user import Base
except ImportError:
    # Fallback: se Base não estiver definida em user.py, tenta import direto
    # do módulo de configuração de banco de dados.
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):  # type: ignore[no-redef]
        """Classe base declarativa fallback para models SQLAlchemy."""

        pass

__all__ = [
    "Base",
    "User",
    "Case",
    "Document",
    "Analysis",
    "AuditLog",
    "ChatSession",
    "ChatMessage",
]
