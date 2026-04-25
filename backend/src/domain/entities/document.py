"""Entidade de domínio Document.

Define a entidade central de documentos jurídicos com regras de negócio
relativas a tipos permitidos, tamanho máximo, hash de integridade e
ciclo de vida do documento.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


# ---------------------------------------------------------------------------
# Constantes de domínio
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
"""Tamanho máximo permitido para upload de documentos (50 MB)."""

ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "application/rtf",
        "image/png",
        "image/jpeg",
        "image/tiff",
    }
)
"""Tipos MIME aceitos para documentos jurídicos."""

ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".rtf",
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".tif",
    }
)
"""Extensões de arquivo permitidas para upload."""

HASH_ALGORITHM: str = "sha256"
"""Algoritmo utilizado para cálculo do hash de integridade."""


# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------


class DocumentType(str, Enum):
    """Tipos de documento jurídico suportados pelo sistema."""

    PETICAO_INICIAL = "peticao_inicial"
    CONTESTACAO = "contestacao"
    RECURSO = "recurso"
    PARECER = "parecer"
    CONTRATO = "contrato"
    PROCURACAO = "procuracao"
    SENTENCA = "sentenca"
    ACORDAO = "acordao"
    DESPACHO = "despacho"
    CERTIDAO = "certidao"
    OFICIO = "oficio"
    OUTROS = "outros"


class DocumentStatus(str, Enum):
    """Ciclo de vida do documento dentro do sistema.

    Transições válidas:
        PENDING  -> UPLOADED
        UPLOADED -> PROCESSING | REJECTED
        PROCESSING -> ANALYZED | FAILED
        ANALYZED -> ARCHIVED
        REJECTED -> (terminal)
        FAILED   -> PROCESSING  (retry)
        ARCHIVED -> (terminal)
    """

    PENDING = "pending"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    REJECTED = "rejected"
    FAILED = "failed"
    ARCHIVED = "archived"


# Mapa de transições válidas: estado_atual -> {estados_destino}
_VALID_TRANSITIONS: dict[DocumentStatus, frozenset[DocumentStatus]] = {
    DocumentStatus.PENDING: frozenset({DocumentStatus.UPLOADED}),
    DocumentStatus.UPLOADED: frozenset(
        {DocumentStatus.PROCESSING, DocumentStatus.REJECTED}
    ),
    DocumentStatus.PROCESSING: frozenset(
        {DocumentStatus.ANALYZED, DocumentStatus.FAILED}
    ),
    DocumentStatus.ANALYZED: frozenset({DocumentStatus.ARCHIVED}),
    DocumentStatus.REJECTED: frozenset(),
    DocumentStatus.FAILED: frozenset({DocumentStatus.PROCESSING}),
    DocumentStatus.ARCHIVED: frozenset(),
}


# ---------------------------------------------------------------------------
# Exceções de domínio
# ---------------------------------------------------------------------------


class DocumentDomainError(Exception):
    """Exceção base para erros de domínio relacionados a documentos."""


class InvalidDocumentTypeError(DocumentDomainError):
    """Tipo MIME ou extensão de arquivo não permitido."""


class FileSizeExceededError(DocumentDomainError):
    """Tamanho do arquivo excede o limite máximo permitido."""


class IntegrityCheckFailedError(DocumentDomainError):
    """Falha na verificação de integridade (hash) do documento."""


class InvalidStatusTransitionError(DocumentDomainError):
    """Transição de status inválida para o ciclo de vida do documento."""


# ---------------------------------------------------------------------------
# Entidade de domínio
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """Entidade de domínio que representa um documento jurídico.

    Encapsula todas as regras de negócio relativas a validação de tipo,
    tamanho, integridade e ciclo de vida de documentos no sistema de
    automação jurídica.

    Attributes:
        id: Identificador único do documento (UUID v4).
        owner_id: Identificador do usuário proprietário.
        filename: Nome original do arquivo enviado.
        mime_type: Tipo MIME do arquivo.
        extension: Extensão do arquivo (com ponto, ex: '.pdf').
        size_bytes: Tamanho do arquivo em bytes.
        document_type: Classificação jurídica do documento.
        status: Estado atual no ciclo de vida.
        sha256_hash: Hash SHA-256 do conteúdo para verificação de integridade.
        storage_path: Caminho no storage onde o arquivo está armazenado.
        description: Descrição opcional fornecida pelo usuário.
        metadata: Metadados adicionais extraídos ou informados.
        created_at: Data/hora de criação do registro.
        updated_at: Data/hora da última atualização.
    """

    owner_id: UUID
    filename: str
    mime_type: str
    extension: str
    size_bytes: int
    document_type: DocumentType

    # Campos com valores padrão
    id: UUID = field(default_factory=uuid4)
    status: DocumentStatus = field(default=DocumentStatus.PENDING)
    sha256_hash: Optional[str] = field(default=None)
    storage_path: Optional[str] = field(default=None)
    description: Optional[str] = field(default=None)
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # ------------------------------------------------------------------
    # Validações de domínio
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Executa validações de domínio na criação da entidade."""
        self.validate_mime_type()
        self.validate_extension()
        self.validate_file_size()

    def validate_mime_type(self) -> None:
        """Valida se o tipo MIME do arquivo é permitido.

        Raises:
            InvalidDocumentTypeError: Se o tipo MIME não está na lista de permitidos.
        """
        if self.mime_type not in ALLOWED_MIME_TYPES:
            raise InvalidDocumentTypeError(
                f"Tipo MIME '{self.mime_type}' não é permitido. "
                f"Tipos aceitos: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
            )

    def validate_extension(self) -> None:
        """Valida se a extensão do arquivo é permitida.

        Raises:
            InvalidDocumentTypeError: Se a extensão não está na lista de permitidas.
        """
        ext_lower = self.extension.lower()
        if ext_lower not in ALLOWED_EXTENSIONS:
            raise InvalidDocumentTypeError(
                f"Extensão '{self.extension}' não é permitida. "
                f"Extensões aceitas: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

    def validate_file_size(self) -> None:
        """Valida se o tamanho do arquivo está dentro do limite permitido.

        Raises:
            FileSizeExceededError: Se o tamanho excede o máximo permitido.
        """
        if self.size_bytes <= 0:
            raise FileSizeExceededError(
                "O tamanho do arquivo deve ser maior que zero."
            )
        if self.size_bytes > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
            file_mb = self.size_bytes / (1024 * 1024)
            raise FileSizeExceededError(
                f"Tamanho do arquivo ({file_mb:.1f} MB) excede o limite "
                f"máximo permitido de {max_mb:.0f} MB."
            )

    # ------------------------------------------------------------------
    # Integridade
    # ------------------------------------------------------------------

    @staticmethod
    def compute_hash(content: bytes) -> str:
        """Calcula o hash SHA-256 do conteúdo do arquivo.

        Args:
            content: Conteúdo binário do arquivo.

        Returns:
            String hexadecimal do hash SHA-256.
        """
        return hashlib.sha256(content).hexdigest()

    def set_hash(self, content: bytes) -> None:
        """Define o hash de integridade a partir do conteúdo do arquivo.

        Args:
            content: Conteúdo binário do arquivo.
        """
        self.sha256_hash = self.compute_hash(content)
        self._touch()

    def verify_integrity(self, content: bytes) -> bool:
        """Verifica a integridade do documento comparando hashes.

        Args:
            content: Conteúdo binário do arquivo a ser verificado.

        Returns:
            True se o hash confere, False caso contrário.

        Raises:
            IntegrityCheckFailedError: Se nenhum hash de referência foi definido.
        """
        if self.sha256_hash is None:
            raise IntegrityCheckFailedError(
                "Hash de referência não definido. "
                "Não é possível verificar a integridade do documento."
            )
        computed = self.compute_hash(content)
        return computed == self.sha256_hash

    # ------------------------------------------------------------------
    # Ciclo de vida (state machine)
    # ------------------------------------------------------------------

    def transition_to(self, new_status: DocumentStatus) -> None:
        """Realiza a transição de status do documento.

        Valida se a transição é permitida de acordo com o ciclo de vida
        definido antes de efetuar a mudança.

        Args:
            new_status: Novo status desejado.

        Raises:
            InvalidStatusTransitionError: Se a transição não é permitida.
        """
        allowed = _VALID_TRANSITIONS.get(self.status, frozenset())
        if new_status not in allowed:
            allowed_names = (
                ", ".join(s.value for s in allowed) if allowed else "nenhum"
            )
            raise InvalidStatusTransitionError(
                f"Transição de '{self.status.value}' para '{new_status.value}' "
                f"não é permitida. Transições válidas a partir de "
                f"'{self.status.value}': {allowed_names}."
            )
        self.status = new_status
        self._touch()

    def mark_as_uploaded(self, storage_path: str) -> None:
        """Marca o documento como enviado e define o caminho de armazenamento.

        Args:
            storage_path: Caminho no storage onde o arquivo foi salvo.
        """
        self.transition_to(DocumentStatus.UPLOADED)
        self.storage_path = storage_path

    def mark_as_processing(self) -> None:
        """Marca o documento como em processamento (análise por IA)."""
        self.transition_to(DocumentStatus.PROCESSING)

    def mark_as_analyzed(self) -> None:
        """Marca o documento como analisado com sucesso."""
        self.transition_to(DocumentStatus.ANALYZED)

    def mark_as_rejected(self, reason: str) -> None:
        """Marca o documento como rejeitado.

        Args:
            reason: Motivo da rejeição.
        """
        self.transition_to(DocumentStatus.REJECTED)
        self.metadata["rejection_reason"] = reason

    def mark_as_failed(self, error_detail: str) -> None:
        """Marca o documento como falho no processamento.

        Args:
            error_detail: Detalhes do erro ocorrido.
        """
        self.transition_to(DocumentStatus.FAILED)
        self.metadata["last_error"] = error_detail

    def archive(self) -> None:
        """Arquiva o documento (estado terminal)."""
        self.transition_to(DocumentStatus.ARCHIVED)

    # ------------------------------------------------------------------
    # Consultas de estado
    # ------------------------------------------------------------------

    @property
    def is_terminal(self) -> bool:
        """Verifica se o documento está em um estado terminal."""
        return len(_VALID_TRANSITIONS.get(self.status, frozenset())) == 0

    @property
    def is_processable(self) -> bool:
        """Verifica se o documento pode ser enviado para processamento."""
        return DocumentStatus.PROCESSING in _VALID_TRANSITIONS.get(
            self.status, frozenset()
        )

    @property
    def size_mb(self) -> float:
        """Retorna o tamanho do arquivo em megabytes."""
        return self.size_bytes / (1024 * 1024)

    # ------------------------------------------------------------------
    # Utilitários internos
    # ------------------------------------------------------------------

    def _touch(self) -> None:
        """Atualiza o timestamp de última modificação."""
        self.updated_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        """Representação textual da entidade Document."""
        return (
            f"Document(id={self.id!r}, filename={self.filename!r}, "
            f"type={self.document_type.value!r}, status={self.status.value!r}, "
            f"size={self.size_mb:.2f}MB)"
        )

    def __eq__(self, other: object) -> bool:
        """Igualdade baseada no identificador da entidade."""
        if not isinstance(other, Document):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash baseado no identificador da entidade."""
        return hash(self.id)
