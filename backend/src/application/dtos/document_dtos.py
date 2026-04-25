"""DTOs (Data Transfer Objects) para o módulo de documentos.

Define os schemas Pydantic v2 para validação e serialização de dados
relacionados a upload, resposta e filtragem de documentos jurídicos.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ---------------------------------------------------------------------------
# Enums de domínio
# ---------------------------------------------------------------------------


class DocumentStatus(StrEnum):
    """Status do ciclo de vida de um documento jurídico."""

    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    ERROR = "error"
    ARCHIVED = "archived"


class DocumentType(StrEnum):
    """Tipos de documento jurídico suportados pela plataforma."""

    PETICAO_INICIAL = "peticao_inicial"
    CONTESTACAO = "contestacao"
    RECURSO = "recurso"
    SENTENCA = "sentenca"
    ACORDAO = "acordao"
    PARECER = "parecer"
    CONTRATO = "contrato"
    PROCURACAO = "procuracao"
    OUTROS = "outros"


# ---------------------------------------------------------------------------
# Constantes de validação
# ---------------------------------------------------------------------------

ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}

# Tamanho máximo de arquivo: 50 MB
MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024

# Tamanho máximo do nome do arquivo
MAX_FILENAME_LENGTH: int = 255


# ---------------------------------------------------------------------------
# DTOs de entrada (request)
# ---------------------------------------------------------------------------


class DocumentUpload(BaseModel):
    """DTO para upload de um novo documento jurídico.

    Valida metadados enviados junto ao arquivo. O conteúdo binário do arquivo
    é tratado separadamente via ``python-multipart`` no endpoint.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "filename": "peticao_inicial_processo_123.pdf",
                    "mime_type": "application/pdf",
                    "file_size_bytes": 1_048_576,
                    "document_type": "peticao_inicial",
                    "description": "Petição inicial do processo nº 0001234-56.2024.8.26.0100",
                    "tags": ["cível", "indenização"],
                }
            ]
        },
    )

    filename: Annotated[
        str,
        Field(
            min_length=1,
            max_length=MAX_FILENAME_LENGTH,
            description="Nome original do arquivo enviado pelo usuário.",
            examples=["peticao_inicial.pdf"],
        ),
    ]

    mime_type: Annotated[
        str,
        Field(
            description="Tipo MIME do arquivo. Apenas PDF, DOC, DOCX e TXT são aceitos.",
            examples=["application/pdf"],
        ),
    ]

    file_size_bytes: Annotated[
        int,
        Field(
            gt=0,
            le=MAX_FILE_SIZE_BYTES,
            description=(
                f"Tamanho do arquivo em bytes. Máximo permitido: "
                f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
            ),
            examples=[1_048_576],
        ),
    ]

    document_type: Annotated[
        DocumentType,
        Field(
            description="Classificação do tipo de documento jurídico.",
            examples=[DocumentType.PETICAO_INICIAL],
        ),
    ]

    description: Annotated[
        str | None,
        Field(
            default=None,
            max_length=1000,
            description="Descrição opcional do documento para facilitar a busca.",
            examples=["Petição inicial do processo nº 0001234-56.2024.8.26.0100"],
        ),
    ]

    tags: Annotated[
        list[str],
        Field(
            default_factory=list,
            max_length=20,
            description="Lista de tags para categorização. Máximo de 20 tags.",
            examples=[["cível", "indenização"]],
        ),
    ]

    case_number: Annotated[
        str | None,
        Field(
            default=None,
            max_length=50,
            description="Número do processo judicial associado (formato CNJ ou livre).",
            examples=["0001234-56.2024.8.26.0100"],
        ),
    ]

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, value: str) -> str:
        """Valida se o tipo MIME está entre os permitidos."""
        if value not in ALLOWED_MIME_TYPES:
            tipos_permitidos = ", ".join(sorted(ALLOWED_MIME_TYPES))
            raise ValueError(
                f"Tipo MIME '{value}' não é suportado. "
                f"Tipos permitidos: {tipos_permitidos}"
            )
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        """Normaliza e valida as tags do documento."""
        normalized: list[str] = []
        for tag in value:
            tag_clean = tag.strip().lower()
            if not tag_clean:
                continue
            if len(tag_clean) > 50:
                raise ValueError(
                    f"Cada tag deve ter no máximo 50 caracteres. "
                    f"Tag '{tag_clean[:20]}...' excede o limite."
                )
            normalized.append(tag_clean)
        # Remove duplicatas preservando ordem
        seen: set[str] = set()
        unique: list[str] = []
        for tag in normalized:
            if tag not in seen:
                seen.add(tag)
                unique.append(tag)
        return unique

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        """Valida o nome do arquivo contra caracteres perigosos."""
        # Previne path traversal
        dangerous_patterns = ["..", "/", "\\", "\x00"]
        for pattern in dangerous_patterns:
            if pattern in value:
                raise ValueError(
                    f"Nome de arquivo contém caractere(s) não permitido(s): '{pattern}'"
                )
        return value


# ---------------------------------------------------------------------------
# DTOs de saída (response)
# ---------------------------------------------------------------------------


class DocumentResponse(BaseModel):
    """DTO de resposta com dados completos de um documento.

    Retornado em operações de leitura individual (GET /documents/{id}).
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "filename": "peticao_inicial.pdf",
                    "mime_type": "application/pdf",
                    "file_size_bytes": 1_048_576,
                    "document_type": "peticao_inicial",
                    "status": "uploaded",
                    "description": "Petição inicial do processo nº 0001234-56.2024.8.26.0100",
                    "tags": ["cível", "indenização"],
                    "case_number": "0001234-56.2024.8.26.0100",
                    "owner_id": "f9e8d7c6-b5a4-3210-fedc-ba9876543210",
                    "storage_path": "documents/2024/01/a1b2c3d4.pdf",
                    "analysis_summary": None,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                }
            ]
        },
    )

    id: Annotated[
        uuid.UUID,
        Field(description="Identificador único do documento."),
    ]

    filename: Annotated[
        str,
        Field(description="Nome original do arquivo."),
    ]

    mime_type: Annotated[
        str,
        Field(description="Tipo MIME do arquivo."),
    ]

    file_size_bytes: Annotated[
        int,
        Field(description="Tamanho do arquivo em bytes."),
    ]

    document_type: Annotated[
        DocumentType,
        Field(description="Classificação do tipo de documento jurídico."),
    ]

    status: Annotated[
        DocumentStatus,
        Field(description="Status atual do documento no ciclo de vida."),
    ]

    description: Annotated[
        str | None,
        Field(default=None, description="Descrição do documento."),
    ]

    tags: Annotated[
        list[str],
        Field(default_factory=list, description="Tags de categorização."),
    ]

    case_number: Annotated[
        str | None,
        Field(default=None, description="Número do processo judicial associado."),
    ]

    owner_id: Annotated[
        uuid.UUID,
        Field(description="ID do usuário proprietário do documento."),
    ]

    storage_path: Annotated[
        str | None,
        Field(
            default=None,
            description="Caminho interno de armazenamento (não exposto ao cliente em contextos públicos).",
        ),
    ]

    analysis_summary: Annotated[
        str | None,
        Field(
            default=None,
            description="Resumo gerado pela análise de IA, quando disponível.",
        ),
    ]

    page_count: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Número de páginas do documento, quando aplicável.",
        ),
    ]

    created_at: Annotated[
        datetime,
        Field(description="Data e hora de criação do registro."),
    ]

    updated_at: Annotated[
        datetime,
        Field(description="Data e hora da última atualização."),
    ]


class DocumentResponsePublic(BaseModel):
    """DTO de resposta pública (sem campos internos como storage_path).

    Utilizado em listagens e contextos onde dados internos não devem ser expostos.
    """

    model_config = ConfigDict(from_attributes=True)

    id: Annotated[uuid.UUID, Field(description="Identificador único do documento.")]
    filename: Annotated[str, Field(description="Nome original do arquivo.")]
    mime_type: Annotated[str, Field(description="Tipo MIME do arquivo.")]
    file_size_bytes: Annotated[int, Field(description="Tamanho do arquivo em bytes.")]
    document_type: Annotated[DocumentType, Field(description="Tipo de documento jurídico.")]
    status: Annotated[DocumentStatus, Field(description="Status atual do documento.")]
    description: Annotated[str | None, Field(default=None, description="Descrição do documento.")]
    tags: Annotated[list[str], Field(default_factory=list, description="Tags de categorização.")]
    case_number: Annotated[str | None, Field(default=None, description="Número do processo.")]
    analysis_summary: Annotated[
        str | None,
        Field(default=None, description="Resumo da análise de IA."),
    ]
    page_count: Annotated[int | None, Field(default=None, description="Número de páginas.")]
    created_at: Annotated[datetime, Field(description="Data de criação.")]
    updated_at: Annotated[datetime, Field(description="Data da última atualização.")]


# ---------------------------------------------------------------------------
# DTOs de filtragem e paginação
# ---------------------------------------------------------------------------


class SortOrder(StrEnum):
    """Direção de ordenação para listagens."""

    ASC = "asc"
    DESC = "desc"


class DocumentSortField(StrEnum):
    """Campos permitidos para ordenação de documentos."""

    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    FILENAME = "filename"
    FILE_SIZE = "file_size_bytes"
    DOCUMENT_TYPE = "document_type"
    STATUS = "status"


class DocumentListFilter(BaseModel):
    """DTO para filtragem e paginação na listagem de documentos.

    Utilizado como query parameters no endpoint GET /documents.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "search": "petição inicial",
                    "document_type": "peticao_inicial",
                    "status": "uploaded",
                    "tags": ["cível"],
                    "case_number": "0001234-56.2024.8.26.0100",
                    "created_after": "2024-01-01T00:00:00Z",
                    "created_before": "2024-12-31T23:59:59Z",
                    "sort_by": "created_at",
                    "sort_order": "desc",
                    "page": 1,
                    "page_size": 20,
                }
            ]
        },
    )

    # --- Filtros de busca ---

    search: Annotated[
        str | None,
        Field(
            default=None,
            max_length=200,
            description=(
                "Termo de busca textual. Pesquisa em nome do arquivo, "
                "descrição e resumo de análise."
            ),
            examples=["petição inicial"],
        ),
    ]

    document_type: Annotated[
        DocumentType | None,
        Field(
            default=None,
            description="Filtrar por tipo de documento jurídico.",
        ),
    ]

    status: Annotated[
        DocumentStatus | None,
        Field(
            default=None,
            description="Filtrar por status do documento.",
        ),
    ]

    tags: Annotated[
        list[str] | None,
        Field(
            default=None,
            max_length=10,
            description="Filtrar por tags (operação AND — documento deve conter todas).",
        ),
    ]

    case_number: Annotated[
        str | None,
        Field(
            default=None,
            max_length=50,
            description="Filtrar por número do processo judicial.",
        ),
    ]

    owner_id: Annotated[
        uuid.UUID | None,
        Field(
            default=None,
            description="Filtrar por ID do proprietário. Usado internamente para RBAC.",
        ),
    ]

    # --- Filtros de data ---

    created_after: Annotated[
        datetime | None,
        Field(
            default=None,
            description="Retornar apenas documentos criados após esta data (inclusive).",
        ),
    ]

    created_before: Annotated[
        datetime | None,
        Field(
            default=None,
            description="Retornar apenas documentos criados antes desta data (inclusive).",
        ),
    ]

    # --- Ordenação ---

    sort_by: Annotated[
        DocumentSortField,
        Field(
            default=DocumentSortField.CREATED_AT,
            description="Campo para ordenação dos resultados.",
        ),
    ]

    sort_order: Annotated[
        SortOrder,
        Field(
            default=SortOrder.DESC,
            description="Direção da ordenação: ascendente ou descendente.",
        ),
    ]

    # --- Paginação ---

    page: Annotated[
        int,
        Field(
            default=1,
            ge=1,
            le=10_000,
            description="Número da página (começa em 1).",
        ),
    ]

    page_size: Annotated[
        int,
        Field(
            default=20,
            ge=1,
            le=100,
            description="Quantidade de itens por página. Máximo: 100.",
        ),
    ]

    @model_validator(mode="after")
    def validate_date_range(self) -> "DocumentListFilter":
        """Valida que o intervalo de datas é coerente."""
        if (
            self.created_after is not None
            and self.created_before is not None
            and self.created_after > self.created_before
        ):
            raise ValueError(
                "A data 'created_after' não pode ser posterior a 'created_before'. "
                "Verifique o intervalo de datas informado."
            )
        return self

    @property
    def offset(self) -> int:
        """Calcula o offset para consultas SQL baseado na paginação."""
        return (self.page - 1) * self.page_size


# ---------------------------------------------------------------------------
# DTO de resposta paginada
# ---------------------------------------------------------------------------


class PaginatedDocumentResponse(BaseModel):
    """DTO de resposta paginada para listagem de documentos.

    Encapsula os resultados junto com metadados de paginação.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [],
                    "total": 150,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 8,
                    "has_next": True,
                    "has_previous": False,
                }
            ]
        },
    )

    items: Annotated[
        list[DocumentResponsePublic],
        Field(description="Lista de documentos da página atual."),
    ]

    total: Annotated[
        int,
        Field(ge=0, description="Total de documentos que atendem aos filtros."),
    ]

    page: Annotated[
        int,
        Field(ge=1, description="Página atual."),
    ]

    page_size: Annotated[
        int,
        Field(ge=1, description="Tamanho da página."),
    ]

    total_pages: Annotated[
        int,
        Field(ge=0, description="Total de páginas disponíveis."),
    ]

    has_next: Annotated[
        bool,
        Field(description="Indica se existe uma próxima página."),
    ]

    has_previous: Annotated[
        bool,
        Field(description="Indica se existe uma página anterior."),
    ]

    @classmethod
    def build(
        cls,
        items: list[DocumentResponsePublic],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedDocumentResponse":
        """Constrói a resposta paginada calculando metadados automaticamente.

        Args:
            items: Lista de documentos da página.
            total: Total de registros encontrados.
            page: Número da página atual.
            page_size: Tamanho da página.

        Returns:
            Instância de PaginatedDocumentResponse com metadados calculados.
        """
        total_pages = max(1, -(-total // page_size))  # ceil division
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
