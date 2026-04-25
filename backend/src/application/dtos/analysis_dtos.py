"""DTOs (Data Transfer Objects) para o módulo de análise jurídica.

Define os schemas Pydantic v2 para requisições, respostas e status
relacionados à análise de documentos jurídicos assistida por IA.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnalysisType(str, Enum):
    """Tipos de análise jurídica disponíveis."""

    SUMMARY = "summary"
    RISK_ASSESSMENT = "risk_assessment"
    CLAUSE_EXTRACTION = "clause_extraction"
    COMPLIANCE_CHECK = "compliance_check"
    LEGAL_OPINION = "legal_opinion"
    CONTRACT_REVIEW = "contract_review"
    JURISPRUDENCE_SEARCH = "jurisprudence_search"


class AnalysisStatusEnum(str, Enum):
    """Estados possíveis do ciclo de vida de uma análise."""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisPriority(str, Enum):
    """Níveis de prioridade para processamento da análise."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# ---------------------------------------------------------------------------
# Request DTOs
# ---------------------------------------------------------------------------


class AnalysisRequest(BaseModel):
    """DTO de requisição para criação de uma nova análise jurídica.

    Utilizado pelo endpoint de criação de análise para validar
    os dados de entrada fornecidos pelo usuário.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "analysis_type": "risk_assessment",
                "priority": "normal",
                "instructions": "Analisar cláusulas de rescisão e identificar riscos contratuais.",
                "parameters": {"focus_areas": ["rescisão", "multa", "garantias"]},
            }
        }
    )

    document_id: UUID = Field(
        ...,
        description="Identificador único do documento a ser analisado.",
    )
    analysis_type: AnalysisType = Field(
        ...,
        description="Tipo de análise jurídica a ser realizada.",
    )
    priority: AnalysisPriority = Field(
        default=AnalysisPriority.NORMAL,
        description="Prioridade de processamento da análise.",
    )
    instructions: str | None = Field(
        default=None,
        min_length=10,
        max_length=2000,
        description=(
            "Instruções adicionais em linguagem natural para guiar a análise. "
            "Mínimo de 10 caracteres quando fornecido."
        ),
    )
    parameters: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Parâmetros adicionais específicos do tipo de análise "
            "(ex.: áreas de foco, idioma de saída, nível de detalhe)."
        ),
    )


class AnalysisCancelRequest(BaseModel):
    """DTO de requisição para cancelamento de uma análise em andamento."""

    reason: str | None = Field(
        default=None,
        max_length=500,
        description="Motivo do cancelamento da análise.",
    )


# ---------------------------------------------------------------------------
# Response DTOs
# ---------------------------------------------------------------------------


class AnalysisResultSection(BaseModel):
    """Seção individual do resultado de uma análise.

    Cada análise pode produzir múltiplas seções (ex.: resumo,
    riscos identificados, recomendações).
    """

    model_config = ConfigDict(from_attributes=True)

    title: str = Field(
        ...,
        description="Título da seção do resultado.",
    )
    content: str = Field(
        ...,
        description="Conteúdo textual da seção.",
    )
    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Pontuação de confiança da IA para esta seção (0.0 a 1.0).",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Metadados adicionais da seção (ex.: referências, artigos citados).",
    )


class AnalysisResult(BaseModel):
    """Resultado completo de uma análise jurídica."""

    model_config = ConfigDict(from_attributes=True)

    sections: list[AnalysisResultSection] = Field(
        default_factory=list,
        description="Seções do resultado da análise.",
    )
    overall_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Pontuação geral de confiança da análise (0.0 a 1.0).",
    )
    tokens_used: int | None = Field(
        default=None,
        ge=0,
        description="Quantidade de tokens consumidos na chamada à IA.",
    )
    model_version: str | None = Field(
        default=None,
        description="Versão do modelo de IA utilizado na análise.",
    )
    raw_output: str | None = Field(
        default=None,
        description="Saída bruta do modelo (disponível apenas para administradores).",
    )


class AnalysisResponse(BaseModel):
    """DTO de resposta completa de uma análise jurídica.

    Retornado pelos endpoints de consulta e criação de análise,
    contendo todos os dados relevantes incluindo status e resultado.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "user_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "analysis_type": "risk_assessment",
                "status": "completed",
                "priority": "normal",
                "instructions": "Analisar cláusulas de rescisão e identificar riscos contratuais.",
                "result": {
                    "sections": [
                        {
                            "title": "Riscos Identificados",
                            "content": "Foram identificados 3 riscos principais...",
                            "confidence_score": 0.92,
                        }
                    ],
                    "overall_confidence": 0.89,
                    "tokens_used": 4521,
                    "model_version": "claude-3-sonnet",
                },
                "error_message": None,
                "created_at": "2024-01-15T10:30:00Z",
                "started_at": "2024-01-15T10:30:05Z",
                "completed_at": "2024-01-15T10:30:45Z",
            }
        },
    )

    id: UUID = Field(
        ...,
        description="Identificador único da análise.",
    )
    document_id: UUID = Field(
        ...,
        description="Identificador do documento analisado.",
    )
    user_id: UUID = Field(
        ...,
        description="Identificador do usuário que solicitou a análise.",
    )
    analysis_type: AnalysisType = Field(
        ...,
        description="Tipo de análise realizada.",
    )
    status: AnalysisStatusEnum = Field(
        ...,
        description="Status atual da análise.",
    )
    priority: AnalysisPriority = Field(
        ...,
        description="Prioridade de processamento da análise.",
    )
    instructions: str | None = Field(
        default=None,
        description="Instruções fornecidas pelo usuário.",
    )
    parameters: dict[str, Any] | None = Field(
        default=None,
        description="Parâmetros utilizados na análise.",
    )
    result: AnalysisResult | None = Field(
        default=None,
        description="Resultado da análise (disponível quando status é 'completed').",
    )
    error_message: str | None = Field(
        default=None,
        description="Mensagem de erro (disponível quando status é 'failed').",
    )
    created_at: datetime = Field(
        ...,
        description="Data e hora de criação da solicitação de análise.",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Data e hora de início do processamento.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Data e hora de conclusão (sucesso ou falha).",
    )


# ---------------------------------------------------------------------------
# Status / Listagem DTOs
# ---------------------------------------------------------------------------


class AnalysisStatus(BaseModel):
    """DTO resumido de status de uma análise.

    Utilizado para polling de status e listagens onde o resultado
    completo não é necessário.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        ...,
        description="Identificador único da análise.",
    )
    document_id: UUID = Field(
        ...,
        description="Identificador do documento analisado.",
    )
    analysis_type: AnalysisType = Field(
        ...,
        description="Tipo de análise solicitada.",
    )
    status: AnalysisStatusEnum = Field(
        ...,
        description="Status atual da análise.",
    )
    priority: AnalysisPriority = Field(
        ...,
        description="Prioridade de processamento.",
    )
    progress_percentage: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Percentual de progresso estimado (0-100).",
    )
    error_message: str | None = Field(
        default=None,
        description="Mensagem de erro, se aplicável.",
    )
    created_at: datetime = Field(
        ...,
        description="Data e hora de criação.",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Data e hora de início do processamento.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Data e hora de conclusão.",
    )


class AnalysisListResponse(BaseModel):
    """DTO de resposta paginada para listagem de análises."""

    model_config = ConfigDict(from_attributes=True)

    items: list[AnalysisStatus] = Field(
        ...,
        description="Lista de análises na página atual.",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total de análises encontradas.",
    )
    page: int = Field(
        ...,
        ge=1,
        description="Número da página atual.",
    )
    page_size: int = Field(
        ...,
        ge=1,
        le=100,
        description="Quantidade de itens por página.",
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total de páginas disponíveis.",
    )


class AnalysisListQuery(BaseModel):
    """DTO para parâmetros de consulta na listagem de análises."""

    document_id: UUID | None = Field(
        default=None,
        description="Filtrar por documento específico.",
    )
    analysis_type: AnalysisType | None = Field(
        default=None,
        description="Filtrar por tipo de análise.",
    )
    status: AnalysisStatusEnum | None = Field(
        default=None,
        description="Filtrar por status.",
    )
    priority: AnalysisPriority | None = Field(
        default=None,
        description="Filtrar por prioridade.",
    )
    created_after: datetime | None = Field(
        default=None,
        description="Filtrar análises criadas após esta data.",
    )
    created_before: datetime | None = Field(
        default=None,
        description="Filtrar análises criadas antes desta data.",
    )
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
