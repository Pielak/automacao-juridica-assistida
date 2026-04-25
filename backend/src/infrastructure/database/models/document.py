"""Model SQLAlchemy para Documento — Automação Jurídica Assistida.

Define o modelo de persistência para documentos jurídicos (petições, decisões,
contratos, pareceres, etc.) com metadados completos, caminho de armazenamento,
hash de integridade e controle de ciclo de vida.

Exemplo de uso:
    from backend.src.infrastructure.database.models.document import Document

    doc = Document(
        title="Petição Inicial - Processo 1234",
        document_type=DocumentType.PETICAO,
        storage_path="/storage/2024/01/abc123.pdf",
        file_hash="sha256:a1b2c3d4...",
        mime_type="application/pdf",
        file_size_bytes=204800,
        owner_id=user.id,
    )
    session.add(doc)
    await session.commit()
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.infrastructure.database.session import Base


class DocumentType(str, enum.Enum):
    """Tipos de documento jurídico suportados pelo sistema."""

    PETICAO = "peticao"
    DECISAO = "decisao"
    SENTENCA = "sentenca"
    ACORDAO = "acordao"
    CONTRATO = "contrato"
    PARECER = "parecer"
    PROCURACAO = "procuracao"
    RECURSO = "recurso"
    DESPACHO = "despacho"
    NOTIFICACAO = "notificacao"
    OUTROS = "outros"


class DocumentStatus(str, enum.Enum):
    """Status do ciclo de vida do documento.

    Representa os estados possíveis de um documento desde o upload
    até sua eventual exclusão lógica ou arquivamento.
    """

    PENDING_UPLOAD = "pending_upload"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    DELETED = "deleted"


class Document(Base):
    """Modelo de persistência para documentos jurídicos.

    Armazena metadados completos do documento, incluindo informações de
    armazenamento, hash de integridade (SHA-256), tipo de documento,
    status do ciclo de vida e referências ao proprietário.

    Attributes:
        id: Identificador único UUID do documento.
        title: Título descritivo do documento.
        description: Descrição opcional com detalhes adicionais.
        document_type: Tipo do documento jurídico (petição, decisão, etc.).
        status: Status atual no ciclo de vida do documento.
        storage_path: Caminho relativo no sistema de armazenamento de arquivos.
        original_filename: Nome original do arquivo enviado pelo usuário.
        mime_type: Tipo MIME do arquivo (ex: application/pdf).
        file_size_bytes: Tamanho do arquivo em bytes.
        file_hash: Hash SHA-256 do conteúdo para verificação de integridade.
        page_count: Número de páginas (quando aplicável, ex: PDF).
        owner_id: UUID do usuário proprietário do documento.
        process_number: Número do processo judicial associado (opcional).
        court: Tribunal ou vara associada (opcional).
        parties: Partes envolvidas no documento (texto livre, opcional).
        tags: Tags para categorização livre, separadas por vírgula.
        is_confidential: Indica se o documento possui classificação confidencial.
        is_deleted: Flag de exclusão lógica (soft delete).
        analyzed_at: Data/hora em que a análise por IA foi concluída.
        created_at: Data/hora de criação do registro.
        updated_at: Data/hora da última atualização do registro.
    """

    __tablename__ = "documents"

    # --- Identificação ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Identificador único do documento",
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Título descritivo do documento",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Descrição detalhada do documento",
    )

    # --- Classificação ---
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type_enum", native_enum=True),
        nullable=False,
        default=DocumentType.OUTROS,
        comment="Tipo do documento jurídico",
    )

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status_enum", native_enum=True),
        nullable=False,
        default=DocumentStatus.PENDING_UPLOAD,
        comment="Status atual no ciclo de vida do documento",
    )

    # --- Armazenamento e integridade ---
    storage_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="Caminho relativo no sistema de armazenamento",
    )

    original_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Nome original do arquivo enviado pelo usuário",
    )

    mime_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Tipo MIME do arquivo (ex: application/pdf)",
    )

    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Tamanho do arquivo em bytes",
    )

    file_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        comment="Hash SHA-256 do conteúdo para verificação de integridade",
    )

    page_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Número de páginas do documento (quando aplicável)",
    )

    # --- Propriedade e associação ---
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="UUID do usuário proprietário do documento",
    )

    # --- Metadados jurídicos ---
    process_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Número do processo judicial (formato CNJ quando aplicável)",
    )

    court: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Tribunal ou vara associada ao documento",
    )

    parties: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Partes envolvidas (texto livre)",
    )

    tags: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Tags de categorização separadas por vírgula",
    )

    # --- Controle de acesso e exclusão lógica ---
    is_confidential: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Indica se o documento é confidencial",
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
        comment="Flag de exclusão lógica (soft delete)",
    )

    # --- Timestamps ---
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora da conclusão da análise por IA",
    )

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
    # TODO: Descomentar quando o model User estiver disponível em
    # backend/src/infrastructure/database/models/user.py
    # owner: Mapped["User"] = relationship(
    #     "User",
    #     back_populates="documents",
    #     lazy="selectin",
    # )

    # TODO: Adicionar relacionamento com model de análise (Analysis) quando
    # disponível, para vincular resultados de análise por IA ao documento.
    # analyses: Mapped[list["Analysis"]] = relationship(
    #     "Analysis",
    #     back_populates="document",
    #     lazy="selectin",
    #     cascade="all, delete-orphan",
    # )

    # --- Índices compostos ---
    __table_args__ = (
        Index(
            "ix_documents_owner_status",
            "owner_id",
            "status",
            postgresql_where=(is_deleted.is_(False)),
        ),
        Index(
            "ix_documents_type_status",
            "document_type",
            "status",
            postgresql_where=(is_deleted.is_(False)),
        ),
        Index(
            "ix_documents_created_at_desc",
            created_at.desc(),
            postgresql_where=(is_deleted.is_(False)),
        ),
        Index(
            "ix_documents_process_number_partial",
            "process_number",
            postgresql_where=("process_number IS NOT NULL"),
        ),
        {
            "comment": "Tabela de documentos jurídicos com metadados, "
            "armazenamento e controle de ciclo de vida",
        },
    )

    def __repr__(self) -> str:
        """Representação textual do documento para depuração."""
        return (
            f"<Document("
            f"id={self.id!r}, "
            f"title={self.title!r}, "
            f"type={self.document_type!r}, "
            f"status={self.status!r}"
            f")>"
        )

    def __str__(self) -> str:
        """Representação amigável do documento."""
        return f"{self.title} ({self.document_type.value}) — {self.status.value}"

    @property
    def is_analyzed(self) -> bool:
        """Verifica se o documento já foi analisado por IA."""
        return self.analyzed_at is not None

    @property
    def hash_algorithm(self) -> str:
        """Retorna o algoritmo de hash utilizado, extraído do prefixo do hash.

        Returns:
            Nome do algoritmo (ex: 'sha256') ou 'unknown' se não identificado.
        """
        if ":" in self.file_hash:
            return self.file_hash.split(":", 1)[0]
        return "unknown"

    @property
    def hash_value(self) -> str:
        """Retorna apenas o valor do hash, sem o prefixo do algoritmo.

        Returns:
            Valor hexadecimal do hash.
        """
        if ":" in self.file_hash:
            return self.file_hash.split(":", 1)[1]
        return self.file_hash

    @property
    def tags_list(self) -> list[str]:
        """Retorna as tags como lista de strings.

        Returns:
            Lista de tags ou lista vazia se não houver tags.
        """
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
