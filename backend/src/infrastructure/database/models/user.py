"""Model SQLAlchemy para a entidade User (advogado) — Automação Jurídica Assistida.

Define o modelo de usuário do sistema com campos específicos para o domínio
jurídico, incluindo número OAB, seccional, roles RBAC, hash de senha e
timestamps de auditoria.

Exemplo de uso:
    from backend.src.infrastructure.database.models.user import User

    user = User(
        full_name="Maria Silva",
        email="maria@escritorio.com.br",
        oab_number="123456",
        oab_section="SP",
        hashed_password="$2b$12$...",
        role="advogado",
    )
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.src.infrastructure.database.session import Base


class User(Base):
    """Modelo de usuário (advogado) do sistema de automação jurídica.

    Representa um profissional jurídico cadastrado na plataforma, com
    informações de identificação profissional (OAB), credenciais de
    acesso, controle de permissões via RBAC e campos de auditoria.

    Attributes:
        id: Identificador único UUID v4, gerado automaticamente pelo PostgreSQL.
        full_name: Nome completo do advogado.
        email: Endereço de e-mail único, utilizado para login.
        oab_number: Número de inscrição na OAB.
        oab_section: Seccional da OAB (UF com 2 caracteres, ex: "SP", "RJ").
        hashed_password: Hash bcrypt da senha do usuário.
        role: Papel do usuário no sistema para controle RBAC.
        is_active: Indica se a conta está ativa. Contas desativadas não podem autenticar.
        is_verified: Indica se o e-mail do usuário foi verificado.
        mfa_enabled: Indica se a autenticação multifator (MFA/TOTP) está habilitada.
        mfa_secret: Segredo TOTP para geração de códigos MFA (criptografado).
        last_login_at: Data/hora do último login bem-sucedido.
        failed_login_attempts: Contador de tentativas de login falhas consecutivas.
        locked_until: Data/hora até a qual a conta permanece bloqueada por tentativas falhas.
        created_at: Data/hora de criação do registro (preenchido automaticamente).
        updated_at: Data/hora da última atualização (atualizado automaticamente).
    """

    __tablename__ = "users"

    __table_args__ = (
        UniqueConstraint(
            "oab_number",
            "oab_section",
            name="uq_users_oab_number_section",
        ),
        Index("ix_users_email", "email", unique=True),
        Index("ix_users_oab_number", "oab_number"),
        Index("ix_users_role", "role"),
        Index("ix_users_is_active", "is_active"),
        {
            "comment": "Tabela de usuários (advogados) do sistema de automação jurídica.",
        },
    )

    # --- Identificação ---

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Identificador único UUID v4 do usuário.",
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Nome completo do advogado.",
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
        comment="Endereço de e-mail único para autenticação.",
    )

    # --- Dados profissionais (OAB) ---

    oab_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Número de inscrição na OAB.",
    )

    oab_section: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        comment="Seccional da OAB (UF, ex: SP, RJ, MG).",
    )

    # --- Credenciais ---

    hashed_password: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Hash bcrypt da senha do usuário.",
    )

    # --- RBAC ---

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="advogado",
        server_default=text("'advogado'"),
        comment="Papel do usuário no sistema (advogado, admin, gestor).",
    )

    # --- Status da conta ---

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Indica se a conta está ativa.",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="Indica se o e-mail foi verificado.",
    )

    # --- MFA (Autenticação Multifator) ---

    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="Indica se MFA via TOTP está habilitado.",
    )

    mfa_secret: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        default=None,
        comment="Segredo TOTP para MFA (armazenado criptografado).",
    )

    # --- Controle de login e bloqueio ---

    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Data/hora do último login bem-sucedido.",
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Contador de tentativas de login falhas consecutivas.",
    )

    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Data/hora até a qual a conta está bloqueada.",
    )

    # --- Timestamps de auditoria ---

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Data/hora de criação do registro.",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Data/hora da última atualização do registro.",
    )

    def __repr__(self) -> str:
        """Representação textual do usuário para depuração."""
        return (
            f"<User("
            f"id={self.id!r}, "
            f"email={self.email!r}, "
            f"oab={self.oab_number}/{self.oab_section}, "
            f"role={self.role!r}, "
            f"active={self.is_active}"
            f")>"
        )

    @property
    def is_locked(self) -> bool:
        """Verifica se a conta está atualmente bloqueada por tentativas falhas.

        Returns:
            True se a conta está bloqueada e o período de bloqueio ainda não expirou.
        """
        if self.locked_until is None:
            return False
        from datetime import timezone as tz

        now = datetime.now(tz=tz.utc)
        return self.locked_until > now

    @property
    def oab_display(self) -> str:
        """Retorna a inscrição OAB formatada para exibição.

        Returns:
            String no formato "OAB/UF NÚMERO" (ex: "OAB/SP 123456").
        """
        return f"OAB/{self.oab_section} {self.oab_number}"
