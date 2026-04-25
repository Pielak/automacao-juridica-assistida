"""Model SQLAlchemy para Analysis — resultado de análise de IA.

Define o modelo de persistência para armazenar resultados de análises
realizadas pela IA (Claude/Anthropic) sobre documentos jurídicos.
Inclui tipo de análise, resultado em formato JSON, nível de confiança
e metadados de rastreabilidade.

Exemplo de uso:
    from backend.src.infrastructure.database.models.analysis import Analysis

    analysis = Analysis(
        document_id=doc_uuid,
        user_id=user_uuid,
        analysis_type=AnalysisType.SUMMARIZATION,
        result={"summary": "...", "key_points": [...]},
        confidence=0.92,
    )
    session.add(analysis)
    await session.commit()
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.infrastructure.database.session import Base


class AnalysisType(str, enum.Enum):
    """Tipos de análise suportados pela plataforma.

    Cada tipo corresponde a uma capacidade distinta do pipeline de IA
    aplicada a documentos jurídicos.
    """

    SUMMARIZATION = "summarization"
    """Sumarização — geração de resumo estruturado do documento."""

    RISK_ASSESSMENT = "risk_assessment"
    """Avaliação de riscos — identificação de cláusulas e riscos jurídicos."""

    CLAUSE_EXTRACTION = "clause_extraction"
    """Extração de cláusulas — identificação e categorização de cláusulas."""

    LEGAL_OPINION = "legal_opinion"
    """Parecer jurídico — geração de opinião legal assistida."""

    COMPLIANCE_CHECK = "compliance_check"
    """Verificação de conformidade — análise de aderência a normas."""

    SEMANTIC_SEARCH = "semantic_search"
    """Busca semântica — consulta por similaridade em base vetorial."""

    CUSTOM = "custom"
    """Análise personalizada — tipo definido pelo usuário."""


class AnalysisStatus(str, enum.Enum):
    """Status do ciclo de vida de uma análise."""

    PENDING = "pending"
    """Pendente — análise criada mas ainda não iniciada."""

    PROCESSING = "processing"
    """Em processamento — análise sendo executada pela IA."""

    COMPLETED = "completed"
    """Concluída — análise finalizada com sucesso."""

    FAILED = "failed"
    """Falha — análise encerrada com erro."""

    CANCELLED = "cancelled"
    """Cancelada — análise cancelada pelo usuário ou sistema."""


class Analysis(Base):
    """Modelo de persistência para resultados de análise de IA.

    Armazena o resultado completo de uma análise realizada sobre um documento
    jurídico, incluindo o tipo de análise, o resultado estruturado em JSON,
    o nível de confiança (confidence score) e metadados para auditoria.

    Attributes:
        id: Identificador único da análise (UUID v4).
        document_id: Referência ao documento analisado.
        user_id: Referência ao usuário que solicitou a análise.
        analysis_type: Tipo de análise realizada.
        status: Status atual do ciclo de vida da análise.
        result: Resultado estruturado da análise em formato JSON.
        confidence: Nível de confiança do resultado (0.0 a 1.0).
        model_version: Versão/identificador do modelo de IA utilizado.
        prompt_tokens: Quantidade de tokens consumidos no prompt.
        completion_tokens: Quantidade de tokens gerados na resposta.
        processing_time_ms: Tempo de processamento em milissegundos.
        error_message: Mensagem de erro caso a análise tenha falhado.
        metadata_extra: Metadados adicionais livres (parâmetros, configurações).
        created_at: Data/hora de criação do registro.
        updated_at: Data/hora da última atualização.
    """

    __tablename__ = "analyses"
    __table_args__ = (
        Index("ix_analyses_document_id", "document_id"),
        Index("ix_analyses_user_id", "user_id"),
        Index("ix_analyses_analysis_type", "analysis_type"),
        Index("ix_analyses_status", "status"),
        Index("ix_analyses_created_at", "created_at"),
        Index(
            "ix_analyses_document_type",
            "document_id",
            "analysis_type",
        ),
        {"comment": "Resultados de análises de IA sobre documentos jurídicos"},
    )

    # --- Chave primária ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único da análise",
    )

    # --- Chaves estrangeiras ---
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Referência ao documento analisado",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Usuário que solicitou a análise",
    )

    # --- Campos de classificação ---
    analysis_type: Mapped[AnalysisType] = mapped_column(
        Enum(AnalysisType, name="analysis_type_enum", create_constraint=True),
        nullable=False,
        comment="Tipo de análise realizada",
    )

    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status_enum", create_constraint=True),
        nullable=False,
        default=AnalysisStatus.PENDING,
        server_default="pending",
        comment="Status atual da análise",
    )

    # --- Resultado da análise ---
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="Resultado estruturado da análise em formato JSON",
    )

    confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=None,
        comment="Nível de confiança do resultado (0.0 a 1.0)",
    )

    # --- Metadados do modelo de IA ---
    model_version: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        comment="Versão ou identificador do modelo de IA utilizado (ex: claude-3-sonnet)",
    )

    prompt_tokens: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        default=None,
        comment="Quantidade de tokens consumidos no prompt",
    )

    completion_tokens: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        default=None,
        comment="Quantidade de tokens gerados na resposta",
    )

    processing_time_ms: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        default=None,
        comment="Tempo de processamento em milissegundos",
    )

    # --- Tratamento de erros ---
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Mensagem de erro caso a análise tenha falhado",
    )

    # --- Metadados extras ---
    metadata_extra: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        comment="Metadados adicionais (parâmetros de configuração, contexto, etc.)",
    )

    # --- Timestamps ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Data/hora de criação do registro",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Data/hora da última atualização",
    )

    # --- Relacionamentos ---
    # TODO: Descomentar quando os models Document e User estiverem definidos
    # document = relationship("Document", back_populates="analyses", lazy="selectin")
    # user = relationship("User", back_populates="analyses", lazy="selectin")

    def __repr__(self) -> str:
        """Representação textual do objeto Analysis para depuração."""
        return (
            f"<Analysis("
            f"id={self.id!r}, "
            f"type={self.analysis_type!r}, "
            f"status={self.status!r}, "
            f"confidence={self.confidence!r}"
            f")>"
        )

    @property
    def is_completed(self) -> bool:
        """Verifica se a análise foi concluída com sucesso."""
        return self.status == AnalysisStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Verifica se a análise falhou."""
        return self.status == AnalysisStatus.FAILED

    @property
    def is_processing(self) -> bool:
        """Verifica se a análise está em processamento."""
        return self.status == AnalysisStatus.PROCESSING

    @property
    def total_tokens(self) -> Optional[int]:
        """Calcula o total de tokens consumidos (prompt + completion).

        Returns:
            Total de tokens ou None se algum dos valores não estiver disponível.
        """
        if self.prompt_tokens is not None and self.completion_tokens is not None:
            return self.prompt_tokens + self.completion_tokens
        return None
