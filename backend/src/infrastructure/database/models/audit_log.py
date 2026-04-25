"""Model SQLAlchemy para trilha de auditoria completa — Automação Jurídica Assistida.

Define o modelo AuditLog que registra todas as ações relevantes do sistema,
incluindo informações sobre o usuário, ação realizada, timestamp, payload
detalhado e metadados de contexto (IP, user-agent, request ID).

Este modelo é fundamental para conformidade com requisitos de compliance
jurídico (LGPD, auditoria de acessos e modificações em documentos sensíveis).

Exemplo de uso:
    from backend.src.infrastructure.database.models.audit_log import AuditLog

    log_entry = AuditLog(
        user_id=user.id,
        action="document.create",
        resource_type="document",
        resource_id=str(doc.id),
        payload={"title": "Petição Inicial", "file_size": 102400},
        ip_address="192.168.1.10",
        user_agent="Mozilla/5.0 ...",
        request_id="abc-123-def",
    )
    session.add(log_entry)
    await session.commit()
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.src.infrastructure.database.session import Base


class AuditLog(Base):
    """Modelo de trilha de auditoria para registro completo de ações do sistema.

    Armazena informações detalhadas sobre cada ação realizada, permitindo
    rastreabilidade completa para fins de compliance, segurança e análise
    forense. Todos os registros são imutáveis (append-only).

    Attributes:
        id: Identificador único do registro de auditoria (UUID v4).
        user_id: ID do usuário que realizou a ação (nullable para ações do sistema).
        action: Identificador da ação realizada (ex: 'document.create', 'auth.login').
        resource_type: Tipo do recurso afetado (ex: 'document', 'user', 'analysis').
        resource_id: ID do recurso afetado pela ação.
        payload: Dados detalhados da ação em formato JSON (antes/depois, parâmetros).
        ip_address: Endereço IP de origem da requisição.
        user_agent: User-Agent do navegador/cliente.
        request_id: ID de correlação da requisição para rastreamento distribuído.
        status: Resultado da ação ('success', 'failure', 'error').
        error_detail: Detalhes do erro, caso a ação tenha falhado.
        created_at: Timestamp de criação do registro (imutável).
    """

    __tablename__ = "audit_logs"

    # --- Chave primária ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Identificador único do registro de auditoria.",
    )

    # --- Identificação do ator ---
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="ID do usuário que realizou a ação. Nulo para ações automáticas do sistema.",
    )

    # --- Descrição da ação ---
    action: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Identificador da ação (ex: 'document.create', 'auth.login', 'analysis.start').",
    )

    # --- Recurso afetado ---
    resource_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Tipo do recurso afetado pela ação (ex: 'document', 'user', 'chat_session').",
    )

    resource_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Identificador do recurso afetado pela ação.",
    )

    # --- Payload detalhado ---
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="Dados detalhados da ação em JSON (parâmetros, estado anterior/posterior, metadados).",
    )

    # --- Contexto da requisição ---
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # Suporta IPv4 e IPv6
        nullable=True,
        comment="Endereço IP de origem da requisição.",
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="User-Agent do navegador ou cliente HTTP.",
    )

    request_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="ID de correlação da requisição para rastreamento entre camadas.",
    )

    # --- Resultado da ação ---
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        server_default=text("'success'"),
        index=True,
        comment="Resultado da ação: 'success', 'failure' ou 'error'.",
    )

    error_detail: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detalhes do erro caso a ação tenha falhado.",
    )

    # --- Timestamps ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
        index=True,
        comment="Timestamp de criação do registro de auditoria (imutável).",
    )

    # --- Índices compostos para consultas frequentes ---
    __table_args__ = (
        Index(
            "ix_audit_logs_user_action",
            "user_id",
            "action",
            postgresql_using="btree",
        ),
        Index(
            "ix_audit_logs_resource",
            "resource_type",
            "resource_id",
            postgresql_using="btree",
        ),
        Index(
            "ix_audit_logs_created_at_desc",
            created_at.desc(),
            postgresql_using="btree",
        ),
        Index(
            "ix_audit_logs_user_created",
            "user_id",
            created_at.desc(),
            postgresql_using="btree",
        ),
        {
            "comment": "Trilha de auditoria completa do sistema de Automação Jurídica Assistida.",
        },
    )

    def __repr__(self) -> str:
        """Representação textual do registro de auditoria para depuração."""
        return (
            f"<AuditLog("
            f"id={self.id!r}, "
            f"user_id={self.user_id!r}, "
            f"action={self.action!r}, "
            f"resource_type={self.resource_type!r}, "
            f"resource_id={self.resource_id!r}, "
            f"status={self.status!r}, "
            f"created_at={self.created_at!r}"
            f")>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Converte o registro de auditoria para dicionário serializável.

        Útil para exportação de logs e integração com sistemas externos
        de monitoramento e compliance.

        Returns:
            Dicionário com todos os campos do registro de auditoria.
        """
        return {
            "id": str(self.id) if self.id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "payload": self.payload,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "status": self.status,
            "error_detail": self.error_detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
