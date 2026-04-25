"""Model SQLAlchemy para Case (processo cível) — Automação Jurídica Assistida.

Define o modelo de dados para processos cíveis, incluindo número CNJ,
partes envolvidas, status processual, tribunal de origem e metadados
de auditoria. Segue o padrão de numeração única do CNJ (Resolução 65/2008).

Exemplo de uso:
    from backend.src.infrastructure.database.models.case import Case

    novo_caso = Case(
        cnj_number="0000001-23.2024.8.26.0100",
        plaintiff="João da Silva",
        defendant="Empresa XYZ Ltda.",
        court="TJSP",
        status=CaseStatus.ACTIVE,
        subject="Indenização por danos morais",
    )
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.infrastructure.database.session import Base


class CaseStatus(str, enum.Enum):
    """Status possíveis de um processo cível.

    Representa o ciclo de vida processual simplificado para
    fins de acompanhamento na plataforma.
    """

    DRAFT = "draft"
    """Rascunho — processo cadastrado mas ainda não protocolado."""

    ACTIVE = "active"
    """Ativo — processo em tramitação regular."""

    SUSPENDED = "suspended"
    """Suspenso — tramitação temporariamente suspensa."""

    CLOSED = "closed"
    """Encerrado — processo arquivado ou transitado em julgado."""

    ARCHIVED = "archived"
    """Arquivado — removido da visualização ativa, mantido para auditoria."""


class CasePriority(str, enum.Enum):
    """Níveis de prioridade para triagem e organização de processos."""

    LOW = "low"
    """Baixa prioridade."""

    MEDIUM = "medium"
    """Prioridade média (padrão)."""

    HIGH = "high"
    """Alta prioridade."""

    URGENT = "urgent"
    """Urgente — requer atenção imediata."""


# Regex para validação do formato CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
# Exemplo: 0000001-23.2024.8.26.0100
CNJ_NUMBER_REGEX = r"^\d{7}-\d{2}\.\d{4}\.\d{1,2}\.\d{2}\.\d{4}$


class Case(Base):
    """Modelo de processo cível.

    Representa um processo judicial no sistema, armazenando informações
    essenciais como número CNJ, partes, tribunal, status e metadados
    de auditoria para rastreabilidade completa.

    Attributes:
        id: Identificador único UUID do registro.
        cnj_number: Número único do processo no padrão CNJ.
        plaintiff: Nome da parte autora (polo ativo).
        defendant: Nome da parte ré (polo passivo).
        court: Sigla ou nome do tribunal de origem (ex: TJSP, TRF3).
        court_division: Vara ou câmara responsável.
        subject: Assunto ou objeto da ação.
        status: Status atual do processo.
        priority: Nível de prioridade para organização interna.
        description: Descrição detalhada ou observações sobre o processo.
        filing_date: Data de distribuição/protocolo do processo.
        closing_date: Data de encerramento, quando aplicável.
        responsible_user_id: UUID do usuário responsável pelo acompanhamento.
        created_at: Timestamp de criação do registro.
        updated_at: Timestamp da última atualização.
    """

    __tablename__ = "cases"

    # --- Chave primária ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único do processo",
    )

    # --- Identificação processual ---
    cnj_number: Mapped[str] = mapped_column(
        String(25),
        unique=True,
        nullable=False,
        index=True,
        comment="Número único do processo no padrão CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO)",
    )

    # --- Partes ---
    plaintiff: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Nome da parte autora (polo ativo)",
    )

    defendant: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Nome da parte ré (polo passivo)",
    )

    # --- Tribunal e jurisdição ---
    court: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Sigla ou nome do tribunal de origem (ex: TJSP, TRF3)",
    )

    court_division: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Vara, câmara ou turma responsável",
    )

    # --- Assunto e descrição ---
    subject: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Assunto ou objeto da ação",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Descrição detalhada ou observações sobre o processo",
    )

    # --- Status e prioridade ---
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status", native_enum=True),
        nullable=False,
        default=CaseStatus.DRAFT,
        index=True,
        comment="Status atual do processo",
    )

    priority: Mapped[CasePriority] = mapped_column(
        Enum(CasePriority, name="case_priority", native_enum=True),
        nullable=False,
        default=CasePriority.MEDIUM,
        index=True,
        comment="Nível de prioridade do processo",
    )

    # --- Datas processuais ---
    filing_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de distribuição/protocolo do processo",
    )

    closing_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data de encerramento do processo",
    )

    # --- Responsável ---
    responsible_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="UUID do usuário responsável pelo acompanhamento",
    )
    # TODO: Adicionar ForeignKey("users.id") quando o model User estiver disponível.
    # Exemplo: ForeignKey("users.id", ondelete="SET NULL")

    # --- Auditoria ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp de criação do registro",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp da última atualização",
    )

    # --- Relacionamentos ---
    # TODO: Descomentar quando os models relacionados estiverem disponíveis.
    # documents: Mapped[list["Document"]] = relationship(
    #     "Document", back_populates="case", lazy="selectin",
    #     cascade="all, delete-orphan",
    # )
    # analyses: Mapped[list["Analysis"]] = relationship(
    #     "Analysis", back_populates="case", lazy="selectin",
    # )

    # --- Constraints e índices compostos ---
    __table_args__ = (
        CheckConstraint(
            f"cnj_number ~ '{CNJ_NUMBER_REGEX}'",
            name="ck_cases_cnj_number_format",
        ),
        CheckConstraint(
            "closing_date IS NULL OR closing_date >= filing_date",
            name="ck_cases_closing_after_filing",
        ),
        Index(
            "ix_cases_status_priority",
            "status",
            "priority",
            postgresql_using="btree",
        ),
        Index(
            "ix_cases_court_status",
            "court",
            "status",
            postgresql_using="btree",
        ),
        Index(
            "ix_cases_plaintiff_trgm",
            "plaintiff",
            postgresql_using="gin",
            postgresql_ops={"plaintiff": "gin_trgm_ops"},
        ),
        Index(
            "ix_cases_defendant_trgm",
            "defendant",
            postgresql_using="gin",
            postgresql_ops={"defendant": "gin_trgm_ops"},
        ),
        {
            "comment": "Tabela de processos cíveis — Automação Jurídica Assistida",
        },
    )

    def __repr__(self) -> str:
        """Representação textual do processo para debug e logs."""
        return (
            f"<Case(id={self.id!r}, cnj_number={self.cnj_number!r}, "
            f"status={self.status!r}, court={self.court!r})>"
        )

    def __str__(self) -> str:
        """Representação legível do processo."""
        return f"Processo {self.cnj_number} — {self.plaintiff} vs {self.defendant}"

    @property
    def is_active(self) -> bool:
        """Verifica se o processo está em tramitação ativa."""
        return self.status == CaseStatus.ACTIVE

    @property
    def is_closed(self) -> bool:
        """Verifica se o processo está encerrado ou arquivado."""
        return self.status in (CaseStatus.CLOSED, CaseStatus.ARCHIVED)
