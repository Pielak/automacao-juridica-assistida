"""Entidade de domínio Analysis.

Representa uma análise jurídica realizada sobre um documento,
incluindo tipos de análise, status do ciclo de vida e validação de resultados.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class AnalysisType(StrEnum):
    """Tipos de análise jurídica suportados pelo sistema."""

    SUMMARY = "summary"
    """Resumo executivo do documento."""

    RISK_ASSESSMENT = "risk_assessment"
    """Avaliação de riscos jurídicos."""

    CLAUSE_REVIEW = "clause_review"
    """Revisão de cláusulas contratuais."""

    COMPLIANCE_CHECK = "compliance_check"
    """Verificação de conformidade regulatória."""

    PRECEDENT_SEARCH = "precedent_search"
    """Busca de precedentes jurisprudenciais."""

    ARGUMENT_GENERATION = "argument_generation"
    """Geração de argumentos jurídicos."""

    DOCUMENT_COMPARISON = "document_comparison"
    """Comparação entre documentos."""

    CUSTOM = "custom"
    """Análise personalizada definida pelo usuário."""


class AnalysisStatus(StrEnum):
    """Status do ciclo de vida de uma análise."""

    PENDING = "pending"
    """Análise criada, aguardando processamento."""

    QUEUED = "queued"
    """Análise enfileirada para processamento pelo worker."""

    PROCESSING = "processing"
    """Análise em andamento (chamada à API Anthropic em curso)."""

    COMPLETED = "completed"
    """Análise concluída com sucesso."""

    FAILED = "failed"
    """Análise falhou durante o processamento."""

    CANCELLED = "cancelled"
    """Análise cancelada pelo usuário ou pelo sistema."""

    EXPIRED = "expired"
    """Análise expirada (resultado não mais válido)."""


class RiskLevel(StrEnum):
    """Níveis de risco identificados em uma análise."""

    LOW = "low"
    """Risco baixo."""

    MEDIUM = "medium"
    """Risco médio."""

    HIGH = "high"
    """Risco alto."""

    CRITICAL = "critical"
    """Risco crítico — requer atenção imediata."""


class AnalysisResultItem(BaseModel):
    """Item individual de resultado de uma análise.

    Representa uma descoberta, recomendação ou observação
    extraída durante o processamento da análise.
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Título descritivo do item de resultado.",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Descrição detalhada do item de resultado.",
    )
    risk_level: RiskLevel | None = Field(
        default=None,
        description="Nível de risco associado, quando aplicável.",
    )
    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Pontuação de confiança do resultado (0.0 a 1.0).",
    )
    references: list[str] = Field(
        default_factory=list,
        description="Referências legais, artigos ou precedentes citados.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados adicionais específicos do tipo de análise.",
    )


class AnalysisResult(BaseModel):
    """Resultado completo de uma análise jurídica.

    Contém o resumo, itens individuais de resultado e métricas
    agregadas do processamento.
    """

    summary: str = Field(
        ...,
        min_length=1,
        description="Resumo geral dos resultados da análise.",
    )
    items: list[AnalysisResultItem] = Field(
        default_factory=list,
        description="Lista de itens individuais de resultado.",
    )
    overall_risk_level: RiskLevel | None = Field(
        default=None,
        description="Nível de risco geral consolidado.",
    )
    tokens_used: int = Field(
        default=0,
        ge=0,
        description="Total de tokens consumidos na chamada à API.",
    )
    model_used: str = Field(
        default="",
        description="Identificador do modelo de IA utilizado.",
    )
    raw_response: dict[str, Any] | None = Field(
        default=None,
        description="Resposta bruta da API para auditoria (armazenada criptografada).",
    )

    @field_validator("items")
    @classmethod
    def validate_items_not_empty_when_provided(cls, v: list[AnalysisResultItem]) -> list[AnalysisResultItem]:
        """Valida que, se itens forem fornecidos, a lista não esteja vazia."""
        # Lista vazia é permitida (análise pode não ter itens individuais)
        return v


class Analysis(BaseModel):
    """Entidade de domínio que representa uma análise jurídica.

    Encapsula todo o ciclo de vida de uma análise, desde a criação
    até a conclusão ou falha, incluindo validações de negócio e
    transições de estado.

    Attributes:
        id: Identificador único da análise.
        document_id: ID do documento sendo analisado.
        user_id: ID do usuário que solicitou a análise.
        analysis_type: Tipo de análise a ser realizada.
        status: Status atual no ciclo de vida.
        prompt_template: Template de prompt utilizado (se customizado).
        custom_instructions: Instruções adicionais do usuário.
        result: Resultado da análise, quando concluída.
        error_message: Mensagem de erro, quando falha.
        retry_count: Número de tentativas de processamento.
        max_retries: Número máximo de tentativas permitidas.
        created_at: Data/hora de criação.
        started_at: Data/hora de início do processamento.
        completed_at: Data/hora de conclusão.
        updated_at: Data/hora da última atualização.
    """

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Identificador único da análise.",
    )
    document_id: uuid.UUID = Field(
        ...,
        description="ID do documento sendo analisado.",
    )
    user_id: uuid.UUID = Field(
        ...,
        description="ID do usuário que solicitou a análise.",
    )
    analysis_type: AnalysisType = Field(
        ...,
        description="Tipo de análise jurídica a ser realizada.",
    )
    status: AnalysisStatus = Field(
        default=AnalysisStatus.PENDING,
        description="Status atual da análise no ciclo de vida.",
    )
    prompt_template: str | None = Field(
        default=None,
        max_length=10000,
        description="Template de prompt customizado, se aplicável.",
    )
    custom_instructions: str | None = Field(
        default=None,
        max_length=5000,
        description="Instruções adicionais fornecidas pelo usuário.",
    )
    result: AnalysisResult | None = Field(
        default=None,
        description="Resultado da análise, preenchido após conclusão.",
    )
    error_message: str | None = Field(
        default=None,
        max_length=2000,
        description="Mensagem de erro em caso de falha.",
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Número de tentativas de processamento realizadas.",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Número máximo de tentativas permitidas.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora de criação da análise.",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Data/hora de início do processamento.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Data/hora de conclusão da análise.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora da última atualização.",
    )

    # Transições de estado válidas
    _VALID_TRANSITIONS: dict[AnalysisStatus, set[AnalysisStatus]] = {
        AnalysisStatus.PENDING: {AnalysisStatus.QUEUED, AnalysisStatus.CANCELLED},
        AnalysisStatus.QUEUED: {
            AnalysisStatus.PROCESSING,
            AnalysisStatus.CANCELLED,
        },
        AnalysisStatus.PROCESSING: {
            AnalysisStatus.COMPLETED,
            AnalysisStatus.FAILED,
            AnalysisStatus.CANCELLED,
        },
        AnalysisStatus.FAILED: {
            AnalysisStatus.QUEUED,  # retry
            AnalysisStatus.CANCELLED,
        },
        AnalysisStatus.COMPLETED: {AnalysisStatus.EXPIRED},
        AnalysisStatus.CANCELLED: set(),  # estado terminal
        AnalysisStatus.EXPIRED: set(),  # estado terminal
    }

    @model_validator(mode="after")
    def validate_result_consistency(self) -> "Analysis":
        """Valida consistência entre status e resultado.

        Garante que análises concluídas possuam resultado e que
        análises não concluídas não possuam resultado preenchido.
        """
        if self.status == AnalysisStatus.COMPLETED and self.result is None:
            raise ValueError(
                "Análise com status 'completed' deve possuir resultado preenchido."
            )
        if self.status == AnalysisStatus.FAILED and self.error_message is None:
            raise ValueError(
                "Análise com status 'failed' deve possuir mensagem de erro."
            )
        return self

    def can_transition_to(self, new_status: AnalysisStatus) -> bool:
        """Verifica se a transição de estado é válida.

        Args:
            new_status: Status de destino desejado.

        Returns:
            True se a transição é permitida, False caso contrário.
        """
        valid_targets = self._VALID_TRANSITIONS.get(self.status, set())
        return new_status in valid_targets

    def transition_to(
        self,
        new_status: AnalysisStatus,
        *,
        result: AnalysisResult | None = None,
        error_message: str | None = None,
    ) -> "Analysis":
        """Realiza transição de estado com validação.

        Cria uma nova instância da entidade com o estado atualizado,
        mantendo imutabilidade.

        Args:
            new_status: Status de destino.
            result: Resultado da análise (obrigatório para COMPLETED).
            error_message: Mensagem de erro (obrigatório para FAILED).

        Returns:
            Nova instância de Analysis com estado atualizado.

        Raises:
            ValueError: Se a transição de estado não for válida.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Transição de estado inválida: '{self.status}' → '{new_status}'. "
                f"Transições permitidas a partir de '{self.status}': "
                f"{self._VALID_TRANSITIONS.get(self.status, set())}."
            )

        now = datetime.now(timezone.utc)
        update_data: dict[str, Any] = {
            "status": new_status,
            "updated_at": now,
        }

        if new_status == AnalysisStatus.PROCESSING:
            update_data["started_at"] = now

        if new_status == AnalysisStatus.COMPLETED:
            if result is None:
                raise ValueError(
                    "Resultado é obrigatório ao concluir uma análise."
                )
            update_data["result"] = result
            update_data["completed_at"] = now

        if new_status == AnalysisStatus.FAILED:
            if error_message is None:
                raise ValueError(
                    "Mensagem de erro é obrigatória ao marcar análise como falha."
                )
            update_data["error_message"] = error_message
            update_data["completed_at"] = now

        if new_status == AnalysisStatus.QUEUED and self.status == AnalysisStatus.FAILED:
            update_data["retry_count"] = self.retry_count + 1
            update_data["error_message"] = None
            update_data["started_at"] = None
            update_data["completed_at"] = None

        return self.model_copy(update=update_data)

    def can_retry(self) -> bool:
        """Verifica se a análise pode ser reenfileirada para nova tentativa.

        Returns:
            True se o status é FAILED e o limite de tentativas não foi atingido.
        """
        return (
            self.status == AnalysisStatus.FAILED
            and self.retry_count < self.max_retries
        )

    def retry(self) -> "Analysis":
        """Reenfileira a análise para nova tentativa de processamento.

        Returns:
            Nova instância de Analysis com status QUEUED e contador incrementado.

        Raises:
            ValueError: Se a análise não pode ser reenfileirada.
        """
        if not self.can_retry():
            if self.status != AnalysisStatus.FAILED:
                raise ValueError(
                    f"Apenas análises com status 'failed' podem ser reenfileiradas. "
                    f"Status atual: '{self.status}'."
                )
            raise ValueError(
                f"Número máximo de tentativas atingido ({self.max_retries}). "
                f"Tentativas realizadas: {self.retry_count}."
            )
        return self.transition_to(AnalysisStatus.QUEUED)

    @property
    def is_terminal(self) -> bool:
        """Verifica se a análise está em um estado terminal.

        Returns:
            True se a análise está em estado terminal (sem transições possíveis).
        """
        return len(self._VALID_TRANSITIONS.get(self.status, set())) == 0

    @property
    def is_active(self) -> bool:
        """Verifica se a análise está em processamento ativo.

        Returns:
            True se a análise está pendente, enfileirada ou em processamento.
        """
        return self.status in {
            AnalysisStatus.PENDING,
            AnalysisStatus.QUEUED,
            AnalysisStatus.PROCESSING,
        }

    @property
    def duration_seconds(self) -> float | None:
        """Calcula a duração do processamento em segundos.

        Returns:
            Duração em segundos se início e fim estão definidos, None caso contrário.
        """
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    model_config = {
        "frozen": False,
        "str_strip_whitespace": True,
        "validate_assignment": True,
    }
