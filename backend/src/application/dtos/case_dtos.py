"""DTOs (Data Transfer Objects) para o módulo de casos jurídicos.

Define os schemas Pydantic v2 para criação, atualização, resposta e filtragem
de casos jurídicos no sistema de Automação Jurídica Assistida.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CaseStatus(str, Enum):
    """Status possíveis de um caso jurídico no sistema."""

    DRAFT = "draft"
    ACTIVE = "active"
    IN_ANALYSIS = "in_analysis"
    AWAITING_DOCUMENTS = "awaiting_documents"
    AWAITING_REVIEW = "awaiting_review"
    CLOSED = "closed"
    ARCHIVED = "archived"


class CasePriority(str, Enum):
    """Níveis de prioridade para triagem e ordenação de casos."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class CaseArea(str, Enum):
    """Áreas do direito suportadas pelo sistema."""

    CIVIL = "civil"
    CRIMINAL = "criminal"
    LABOR = "labor"
    TAX = "tax"
    ADMINISTRATIVE = "administrative"
    CONSUMER = "consumer"
    FAMILY = "family"
    CORPORATE = "corporate"
    ENVIRONMENTAL = "environmental"
    OTHER = "other"


class SortField(str, Enum):
    """Campos disponíveis para ordenação na listagem de casos."""

    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    TITLE = "title"
    STATUS = "status"
    PRIORITY = "priority"
    DUE_DATE = "due_date"


class SortOrder(str, Enum):
    """Direção da ordenação."""

    ASC = "asc"
    DESC = "desc"


# ---------------------------------------------------------------------------
# DTOs de entrada
# ---------------------------------------------------------------------------


class CaseCreate(BaseModel):
    """DTO para criação de um novo caso jurídico.

    Contém todos os campos obrigatórios e opcionais necessários
    para registrar um caso no sistema.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "title": "Ação de Indenização — Contrato 2024/001",
                    "description": "Ação de indenização por descumprimento contratual.",
                    "case_number": "0001234-56.2024.8.26.0100",
                    "area": "civil",
                    "priority": "medium",
                    "client_name": "Empresa Exemplo Ltda.",
                    "opposing_party": "Fornecedor ABC S.A.",
                }
            ]
        },
    )

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Título descritivo do caso jurídico.",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Descrição detalhada do caso, incluindo contexto e objetivos.",
    )
    case_number: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Número do processo no formato CNJ (ex.: 0001234-56.2024.8.26.0100).",
    )
    area: CaseArea = Field(
        ...,
        description="Área do direito à qual o caso pertence.",
    )
    priority: CasePriority = Field(
        default=CasePriority.MEDIUM,
        description="Nível de prioridade do caso.",
    )
    client_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Nome completo ou razão social do cliente.",
    )
    opposing_party: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Nome da parte adversa, se conhecida.",
    )
    court: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Vara / tribunal responsável pelo caso.",
    )
    due_date: Optional[date] = Field(
        default=None,
        description="Data-limite ou prazo relevante para o caso.",
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Tags para categorização e busca (máximo 20).",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Observações internas sobre o caso.",
    )

    @field_validator("case_number")
    @classmethod
    def validate_case_number_format(cls, value: Optional[str]) -> Optional[str]:
        """Valida formato básico do número de processo CNJ, se fornecido."""
        if value is None:
            return value
        # Remove espaços extras
        value = value.strip()
        if value == "":
            return None
        # Validação básica de comprimento — formato CNJ completo tem 25 caracteres
        # Aceita formatos parciais pois nem todo caso tem número CNJ
        if len(value) < 5:
            raise ValueError(
                "Número do processo deve ter pelo menos 5 caracteres."
            )
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        """Normaliza e valida as tags do caso."""
        cleaned: list[str] = []
        for tag in value:
            tag = tag.strip().lower()
            if tag and len(tag) <= 50:
                cleaned.append(tag)
        # Remove duplicatas preservando ordem
        seen: set[str] = set()
        unique: list[str] = []
        for tag in cleaned:
            if tag not in seen:
                seen.add(tag)
                unique.append(tag)
        return unique

    @field_validator("due_date")
    @classmethod
    def validate_due_date_not_in_past(cls, value: Optional[date]) -> Optional[date]:
        """Garante que a data-limite não esteja no passado."""
        if value is not None and value < date.today():
            raise ValueError(
                "A data-limite não pode estar no passado."
            )
        return value


class CaseUpdate(BaseModel):
    """DTO para atualização parcial de um caso jurídico existente.

    Todos os campos são opcionais — apenas os campos enviados
    serão atualizados (PATCH semântico).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=255,
        description="Novo título do caso.",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Nova descrição do caso.",
    )
    case_number: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Número do processo atualizado.",
    )
    area: Optional[CaseArea] = Field(
        default=None,
        description="Nova área do direito.",
    )
    status: Optional[CaseStatus] = Field(
        default=None,
        description="Novo status do caso.",
    )
    priority: Optional[CasePriority] = Field(
        default=None,
        description="Nova prioridade do caso.",
    )
    client_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=255,
        description="Nome atualizado do cliente.",
    )
    opposing_party: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Nome atualizado da parte adversa.",
    )
    court: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Vara / tribunal atualizado.",
    )
    due_date: Optional[date] = Field(
        default=None,
        description="Nova data-limite.",
    )
    tags: Optional[list[str]] = Field(
        default=None,
        max_length=20,
        description="Nova lista de tags (substitui a anterior).",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Observações internas atualizadas.",
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        """Normaliza e valida as tags, se fornecidas."""
        if value is None:
            return value
        cleaned: list[str] = []
        for tag in value:
            tag = tag.strip().lower()
            if tag and len(tag) <= 50:
                cleaned.append(tag)
        seen: set[str] = set()
        unique: list[str] = []
        for tag in cleaned:
            if tag not in seen:
                seen.add(tag)
                unique.append(tag)
        return unique


# ---------------------------------------------------------------------------
# DTOs de saída
# ---------------------------------------------------------------------------


class CaseResponse(BaseModel):
    """DTO de resposta com dados completos de um caso jurídico.

    Utilizado em endpoints de detalhe (GET /cases/{id}) e como item
    em listagens paginadas.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        description="Identificador único do caso.",
    )
    title: str = Field(
        description="Título do caso.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Descrição detalhada do caso.",
    )
    case_number: Optional[str] = Field(
        default=None,
        description="Número do processo (formato CNJ).",
    )
    area: CaseArea = Field(
        description="Área do direito.",
    )
    status: CaseStatus = Field(
        description="Status atual do caso.",
    )
    priority: CasePriority = Field(
        description="Prioridade do caso.",
    )
    client_name: str = Field(
        description="Nome do cliente.",
    )
    opposing_party: Optional[str] = Field(
        default=None,
        description="Nome da parte adversa.",
    )
    court: Optional[str] = Field(
        default=None,
        description="Vara / tribunal.",
    )
    due_date: Optional[date] = Field(
        default=None,
        description="Data-limite do caso.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags de categorização.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Observações internas.",
    )
    owner_id: UUID = Field(
        description="ID do usuário responsável pelo caso.",
    )
    document_count: int = Field(
        default=0,
        description="Quantidade de documentos vinculados ao caso.",
    )
    created_at: datetime = Field(
        description="Data e hora de criação do registro.",
    )
    updated_at: datetime = Field(
        description="Data e hora da última atualização.",
    )


class CaseSummaryResponse(BaseModel):
    """DTO resumido para listagens — omite campos pesados como notas."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Identificador único do caso.")
    title: str = Field(description="Título do caso.")
    case_number: Optional[str] = Field(default=None, description="Número do processo.")
    area: CaseArea = Field(description="Área do direito.")
    status: CaseStatus = Field(description="Status atual.")
    priority: CasePriority = Field(description="Prioridade.")
    client_name: str = Field(description="Nome do cliente.")
    due_date: Optional[date] = Field(default=None, description="Data-limite.")
    tags: list[str] = Field(default_factory=list, description="Tags.")
    document_count: int = Field(default=0, description="Quantidade de documentos.")
    created_at: datetime = Field(description="Data de criação.")
    updated_at: datetime = Field(description="Última atualização.")


# ---------------------------------------------------------------------------
# DTO de filtragem / listagem
# ---------------------------------------------------------------------------


class CaseListFilter(BaseModel):
    """DTO para filtragem e paginação na listagem de casos.

    Utilizado como query parameters no endpoint GET /cases.
    Suporta busca textual, filtros por status/área/prioridade,
    intervalo de datas e paginação offset-based.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Busca textual
    search: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Termo de busca — pesquisa em título, descrição, número do processo e nome do cliente.",
    )

    # Filtros categóricos
    status: Optional[list[CaseStatus]] = Field(
        default=None,
        description="Filtrar por um ou mais status.",
    )
    area: Optional[list[CaseArea]] = Field(
        default=None,
        description="Filtrar por uma ou mais áreas do direito.",
    )
    priority: Optional[list[CasePriority]] = Field(
        default=None,
        description="Filtrar por uma ou mais prioridades.",
    )
    tags: Optional[list[str]] = Field(
        default=None,
        description="Filtrar por tags (OR — retorna casos que possuam ao menos uma).",
    )

    # Filtros de data
    created_after: Optional[datetime] = Field(
        default=None,
        description="Retornar apenas casos criados após esta data/hora.",
    )
    created_before: Optional[datetime] = Field(
        default=None,
        description="Retornar apenas casos criados antes desta data/hora.",
    )
    due_date_from: Optional[date] = Field(
        default=None,
        description="Data-limite mínima (inclusive).",
    )
    due_date_to: Optional[date] = Field(
        default=None,
        description="Data-limite máxima (inclusive).",
    )

    # Filtro por responsável
    owner_id: Optional[UUID] = Field(
        default=None,
        description="Filtrar por ID do usuário responsável.",
    )

    # Ordenação
    sort_by: SortField = Field(
        default=SortField.UPDATED_AT,
        description="Campo para ordenação dos resultados.",
    )
    sort_order: SortOrder = Field(
        default=SortOrder.DESC,
        description="Direção da ordenação (asc ou desc).",
    )

    # Paginação
    page: int = Field(
        default=1,
        ge=1,
        description="Número da página (inicia em 1).",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Quantidade de itens por página (máximo 100).",
    )

    @property
    def offset(self) -> int:
        """Calcula o offset para consultas SQL baseado na página atual."""
        return (self.page - 1) * self.page_size

    @field_validator("search")
    @classmethod
    def sanitize_search(cls, value: Optional[str]) -> Optional[str]:
        """Remove espaços extras do termo de busca."""
        if value is None:
            return value
        value = " ".join(value.split())
        return value if value else None

    @field_validator("tags")
    @classmethod
    def normalize_filter_tags(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        """Normaliza tags de filtro para lowercase."""
        if value is None:
            return value
        return [tag.strip().lower() for tag in value if tag.strip()]


class PaginatedCaseResponse(BaseModel):
    """DTO para resposta paginada de listagem de casos."""

    items: list[CaseSummaryResponse] = Field(
        description="Lista de casos na página atual.",
    )
    total: int = Field(
        ge=0,
        description="Total de casos que atendem aos filtros.",
    )
    page: int = Field(
        ge=1,
        description="Página atual.",
    )
    page_size: int = Field(
        ge=1,
        description="Tamanho da página.",
    )
    total_pages: int = Field(
        ge=0,
        description="Total de páginas disponíveis.",
    )

    @classmethod
    def build(
        cls,
        items: list[CaseSummaryResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedCaseResponse:
        """Constrói a resposta paginada calculando o total de páginas."""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
