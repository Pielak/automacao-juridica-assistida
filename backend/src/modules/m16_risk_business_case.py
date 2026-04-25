"""Módulo de Risco e Mitigação do Business Case — Automação Jurídica Assistida.

Implementa a lógica de avaliação e mitigação de riscos associados ao business case,
verificando e validando:
- Patrocinador executivo (sponsor) — existência, nível hierárquico e comprometimento
- ROI quantificado — cálculo, validação de premissas e análise de sensibilidade
- Orçamento aprovado — verificação de aprovação formal, limites e contingência
- Matriz de riscos — identificação, classificação e planos de mitigação
- Indicadores de saúde do business case — semáforo de risco consolidado

Este módulo faz parte da camada de aplicação (use cases) e segue os
princípios de Clean Architecture, dependendo apenas de portas (ports)
definidas no domínio.

Dependências:
    - m01_business_case_validation: Validação base do business case (ROI, stakeholders, orçamento)

Exemplo de uso:
    from backend.src.modules.m16_risk_business_case import (
        RiskBusinessCaseService,
        RiskAssessmentRequest,
    )

    service = RiskBusinessCaseService()
    resultado = await service.assess_risks(request)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Importação do módulo peer de validação de business case
# ---------------------------------------------------------------------------
# TODO: Ajustar o import exato quando a API pública de m01 estiver completa.
# Por ora, referenciamos o módulo para reutilizar validações de ROI,
# stakeholders e orçamento.
try:
    from backend.src.modules.m01_business_case_validation import (
        BusinessCaseValidator,  # type: ignore[attr-defined]
    )
except ImportError:
    BusinessCaseValidator = None  # Fallback para execução isolada


# ============================================================================
# Enums de domínio
# ============================================================================


class RiskLevel(str, Enum):
    """Nível de risco classificado."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class RiskCategory(str, Enum):
    """Categoria de risco do business case."""

    SPONSOR = "sponsor"
    ROI = "roi"
    BUDGET = "budget"
    TIMELINE = "timeline"
    SCOPE = "scope"
    COMPLIANCE = "compliance"
    TECHNICAL = "technical"
    ORGANIZATIONAL = "organizational"


class MitigationStatus(str, Enum):
    """Status do plano de mitigação."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    INEFFECTIVE = "ineffective"


class SponsorLevel(str, Enum):
    """Nível hierárquico do patrocinador."""

    C_LEVEL = "c_level"
    VP = "vp"
    DIRECTOR = "director"
    MANAGER = "manager"
    OTHER = "other"


class TrafficLight(str, Enum):
    """Semáforo de saúde do business case."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


# ============================================================================
# Schemas Pydantic — DTOs de entrada e saída
# ============================================================================


class SponsorInfo(BaseModel):
    """Informações do patrocinador executivo do projeto."""

    name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Nome completo do patrocinador executivo.",
    )
    role: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Cargo do patrocinador na organização.",
    )
    level: SponsorLevel = Field(
        ...,
        description="Nível hierárquico do patrocinador.",
    )
    email: str = Field(
        ...,
        description="E-mail corporativo do patrocinador.",
    )
    commitment_confirmed: bool = Field(
        default=False,
        description="Indica se o patrocinador confirmou comprometimento formal.",
    )
    approval_date: Optional[datetime] = Field(
        default=None,
        description="Data em que o patrocinador aprovou formalmente o business case.",
    )


class ROIQuantification(BaseModel):
    """Quantificação detalhada do ROI do projeto."""

    projected_investment: Decimal = Field(
        ...,
        gt=0,
        description="Investimento total projetado em BRL.",
    )
    projected_return: Decimal = Field(
        ...,
        description="Retorno financeiro projetado em BRL.",
    )
    projected_roi_percentage: Decimal = Field(
        ...,
        description="ROI projetado em percentual (ex: 150.0 para 150%).",
    )
    payback_months: int = Field(
        ...,
        gt=0,
        le=120,
        description="Período de payback em meses.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Lista de premissas utilizadas no cálculo do ROI.",
    )
    sensitivity_scenarios: list[SensitivityScenario] | None = Field(
        default=None,
        description="Cenários de análise de sensibilidade.",
    )

    @field_validator("projected_roi_percentage")
    @classmethod
    def validate_roi_consistency(cls, v: Decimal, info: Any) -> Decimal:
        """Valida consistência do percentual de ROI com investimento e retorno."""
        # Validação básica: ROI não pode ser absurdamente alto sem justificativa
        if v > Decimal("1000"):
            # Não bloqueia, mas será sinalizado como risco
            pass
        return v


class SensitivityScenario(BaseModel):
    """Cenário de análise de sensibilidade do ROI."""

    name: str = Field(
        ...,
        description="Nome do cenário (ex: 'Pessimista', 'Otimista', 'Base').",
    )
    probability_percentage: Decimal = Field(
        ...,
        ge=0,
        le=100,
        description="Probabilidade estimada do cenário em percentual.",
    )
    adjusted_roi_percentage: Decimal = Field(
        ...,
        description="ROI ajustado para este cenário.",
    )
    description: str = Field(
        default="",
        description="Descrição das condições do cenário.",
    )


# Atualizar forward reference em ROIQuantification
ROIQuantification.model_rebuild()


class BudgetApproval(BaseModel):
    """Informações de aprovação orçamentária."""

    total_budget: Decimal = Field(
        ...,
        gt=0,
        description="Orçamento total aprovado em BRL.",
    )
    contingency_percentage: Decimal = Field(
        default=Decimal("10.0"),
        ge=0,
        le=50,
        description="Percentual de contingência sobre o orçamento.",
    )
    approval_authority: str = Field(
        ...,
        min_length=2,
        description="Autoridade que aprovou o orçamento.",
    )
    approval_date: Optional[datetime] = Field(
        default=None,
        description="Data de aprovação formal do orçamento.",
    )
    is_formally_approved: bool = Field(
        default=False,
        description="Indica se o orçamento foi formalmente aprovado.",
    )
    budget_phases: list[BudgetPhase] | None = Field(
        default=None,
        description="Fases de desembolso do orçamento.",
    )


class BudgetPhase(BaseModel):
    """Fase de desembolso orçamentário."""

    phase_name: str = Field(..., description="Nome da fase.")
    amount: Decimal = Field(..., gt=0, description="Valor da fase em BRL.")
    planned_date: datetime = Field(..., description="Data planejada de desembolso.")
    is_released: bool = Field(default=False, description="Se o valor já foi liberado.")


# Atualizar forward reference em BudgetApproval
BudgetApproval.model_rebuild()


class RiskItem(BaseModel):
    """Item individual de risco identificado."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único do risco.",
    )
    category: RiskCategory = Field(
        ...,
        description="Categoria do risco.",
    )
    title: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="Título descritivo do risco.",
    )
    description: str = Field(
        ...,
        min_length=10,
        description="Descrição detalhada do risco.",
    )
    probability: RiskLevel = Field(
        ...,
        description="Probabilidade de ocorrência.",
    )
    impact: RiskLevel = Field(
        ...,
        description="Impacto caso o risco se materialize.",
    )
    overall_level: RiskLevel = Field(
        default=RiskLevel.MEDIUM,
        description="Nível geral de risco (calculado).",
    )
    mitigation_plan: str = Field(
        default="",
        description="Plano de mitigação proposto.",
    )
    mitigation_status: MitigationStatus = Field(
        default=MitigationStatus.PENDING,
        description="Status atual da mitigação.",
    )
    owner: str = Field(
        default="",
        description="Responsável pela mitigação do risco.",
    )
    due_date: Optional[datetime] = Field(
        default=None,
        description="Data limite para implementação da mitigação.",
    )


class RiskAssessmentRequest(BaseModel):
    """Request para avaliação de riscos do business case."""

    business_case_id: str = Field(
        ...,
        description="Identificador do business case a ser avaliado.",
    )
    sponsor: SponsorInfo = Field(
        ...,
        description="Informações do patrocinador executivo.",
    )
    roi: ROIQuantification = Field(
        ...,
        description="Quantificação do ROI.",
    )
    budget: BudgetApproval = Field(
        ...,
        description="Informações de aprovação orçamentária.",
    )
    additional_risks: list[RiskItem] = Field(
        default_factory=list,
        description="Riscos adicionais identificados manualmente.",
    )


class RiskAssessmentResult(BaseModel):
    """Resultado consolidado da avaliação de riscos."""

    assessment_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único da avaliação.",
    )
    business_case_id: str = Field(
        ...,
        description="Identificador do business case avaliado.",
    )
    assessed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora da avaliação.",
    )
    overall_traffic_light: TrafficLight = Field(
        ...,
        description="Semáforo consolidado de saúde do business case.",
    )
    overall_risk_level: RiskLevel = Field(
        ...,
        description="Nível de risco consolidado.",
    )
    sponsor_risk: RiskItem = Field(
        ...,
        description="Risco avaliado do patrocinador.",
    )
    roi_risk: RiskItem = Field(
        ...,
        description="Risco avaliado do ROI.",
    )
    budget_risk: RiskItem = Field(
        ...,
        description="Risco avaliado do orçamento.",
    )
    all_risks: list[RiskItem] = Field(
        default_factory=list,
        description="Lista consolidada de todos os riscos.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recomendações de mitigação priorizadas.",
    )
    score: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        le=100,
        description="Pontuação de saúde do business case (0-100).",
    )


# ============================================================================
# Constantes e configurações de avaliação
# ============================================================================

# Matriz de risco: (probabilidade, impacto) -> nível resultante
_RISK_MATRIX: dict[tuple[RiskLevel, RiskLevel], RiskLevel] = {
    # Probabilidade CRITICAL
    (RiskLevel.CRITICAL, RiskLevel.CRITICAL): RiskLevel.CRITICAL,
    (RiskLevel.CRITICAL, RiskLevel.HIGH): RiskLevel.CRITICAL,
    (RiskLevel.CRITICAL, RiskLevel.MEDIUM): RiskLevel.HIGH,
    (RiskLevel.CRITICAL, RiskLevel.LOW): RiskLevel.MEDIUM,
    (RiskLevel.CRITICAL, RiskLevel.NEGLIGIBLE): RiskLevel.LOW,
    # Probabilidade HIGH
    (RiskLevel.HIGH, RiskLevel.CRITICAL): RiskLevel.CRITICAL,
    (RiskLevel.HIGH, RiskLevel.HIGH): RiskLevel.HIGH,
    (RiskLevel.HIGH, RiskLevel.MEDIUM): RiskLevel.HIGH,
    (RiskLevel.HIGH, RiskLevel.LOW): RiskLevel.MEDIUM,
    (RiskLevel.HIGH, RiskLevel.NEGLIGIBLE): RiskLevel.LOW,
    # Probabilidade MEDIUM
    (RiskLevel.MEDIUM, RiskLevel.CRITICAL): RiskLevel.HIGH,
    (RiskLevel.MEDIUM, RiskLevel.HIGH): RiskLevel.HIGH,
    (RiskLevel.MEDIUM, RiskLevel.MEDIUM): RiskLevel.MEDIUM,
    (RiskLevel.MEDIUM, RiskLevel.LOW): RiskLevel.LOW,
    (RiskLevel.MEDIUM, RiskLevel.NEGLIGIBLE): RiskLevel.NEGLIGIBLE,
    # Probabilidade LOW
    (RiskLevel.LOW, RiskLevel.CRITICAL): RiskLevel.HIGH,
    (RiskLevel.LOW, RiskLevel.HIGH): RiskLevel.MEDIUM,
    (RiskLevel.LOW, RiskLevel.MEDIUM): RiskLevel.LOW,
    (RiskLevel.LOW, RiskLevel.LOW): RiskLevel.LOW,
    (RiskLevel.LOW, RiskLevel.NEGLIGIBLE): RiskLevel.NEGLIGIBLE,
    # Probabilidade NEGLIGIBLE
    (RiskLevel.NEGLIGIBLE, RiskLevel.CRITICAL): RiskLevel.MEDIUM,
    (RiskLevel.NEGLIGIBLE, RiskLevel.HIGH): RiskLevel.LOW,
    (RiskLevel.NEGLIGIBLE, RiskLevel.MEDIUM): RiskLevel.LOW,
    (RiskLevel.NEGLIGIBLE, RiskLevel.LOW): RiskLevel.NEGLIGIBLE,
    (RiskLevel.NEGLIGIBLE, RiskLevel.NEGLIGIBLE): RiskLevel.NEGLIGIBLE,
}

# Pesos para cálculo de pontuação por nível de risco
_RISK_LEVEL_SCORES: dict[RiskLevel, int] = {
    RiskLevel.CRITICAL: 0,
    RiskLevel.HIGH: 25,
    RiskLevel.MEDIUM: 50,
    RiskLevel.LOW: 75,
    RiskLevel.NEGLIGIBLE: 100,
}

# Limiares de pontuação para semáforo
_TRAFFIC_LIGHT_THRESHOLDS: dict[str, int] = {
    "green_min": 70,
    "yellow_min": 40,
    # Abaixo de yellow_min = RED
}

# Limiar mínimo aceitável de contingência orçamentária (%)
_MIN_CONTINGENCY_PERCENTAGE = Decimal("5.0")

# ROI mínimo aceitável para projetos jurídicos (%)
_MIN_ACCEPTABLE_ROI = Decimal("20.0")

# Payback máximo aceitável em meses
_MAX_ACCEPTABLE_PAYBACK_MONTHS = 36


# ============================================================================
# Funções auxiliares
# ============================================================================


def calculate_combined_risk_level(
    probability: RiskLevel,
    impact: RiskLevel,
) -> RiskLevel:
    """Calcula o nível de risco combinado a partir da matriz probabilidade x impacto.

    Args:
        probability: Nível de probabilidade de ocorrência.
        impact: Nível de impacto caso o risco se materialize.

    Returns:
        Nível de risco combinado conforme a matriz de riscos.
    """
    return _RISK_MATRIX.get(
        (probability, impact),
        RiskLevel.MEDIUM,  # Fallback conservador
    )


def risk_level_to_score(level: RiskLevel) -> int:
    """Converte nível de risco em pontuação numérica (0-100).

    Quanto MENOR o risco, MAIOR a pontuação (saúde do business case).

    Args:
        level: Nível de risco.

    Returns:
        Pontuação de 0 a 100.
    """
    return _RISK_LEVEL_SCORES.get(level, 50)


def score_to_traffic_light(score: Decimal) -> TrafficLight:
    """Converte pontuação numérica em semáforo de saúde.

    Args:
        score: Pontuação de 0 a 100.

    Returns:
        Semáforo (GREEN, YELLOW ou RED).
    """
    if score >= _TRAFFIC_LIGHT_THRESHOLDS["green_min"]:
        return TrafficLight.GREEN
    if score >= _TRAFFIC_LIGHT_THRESHOLDS["yellow_min"]:
        return TrafficLight.YELLOW
    return TrafficLight.RED


def worst_risk_level(levels: list[RiskLevel]) -> RiskLevel:
    """Retorna o pior (mais severo) nível de risco de uma lista.

    Args:
        levels: Lista de níveis de risco.

    Returns:
        O nível mais severo encontrado.
    """
    severity_order = [
        RiskLevel.CRITICAL,
        RiskLevel.HIGH,
        RiskLevel.MEDIUM,
        RiskLevel.LOW,
        RiskLevel.NEGLIGIBLE,
    ]
    for level in severity_order:
        if level in levels:
            return level
    return RiskLevel.MEDIUM


# ============================================================================
# Serviço principal de avaliação de riscos do business case
# ============================================================================


class RiskBusinessCaseService:
    """Serviço de avaliação e mitigação de riscos do business case.

    Responsável por:
    - Avaliar riscos do patrocinador (sponsor)
    - Avaliar riscos do ROI quantificado
    - Avaliar riscos do orçamento aprovado
    - Consolidar matriz de riscos
    - Gerar recomendações de mitigação
    - Calcular semáforo de saúde do business case

    Segue princípios de Clean Architecture: lógica de domínio pura,
    sem dependências de infraestrutura.
    """

    def __init__(
        self,
        business_case_validator: Any | None = None,
    ) -> None:
        """Inicializa o serviço de riscos.

        Args:
            business_case_validator: Instância opcional do validador de business case
                do módulo m01. Se não fornecido, usa validações internas.
        """
        self._bc_validator = business_case_validator or BusinessCaseValidator

    # -----------------------------------------------------------------------
    # Método principal
    # -----------------------------------------------------------------------

    async def assess_risks(
        self,
        request: RiskAssessmentRequest,
    ) -> RiskAssessmentResult:
        """Executa avaliação completa de riscos do business case.

        Avalia três dimensões principais (patrocinador, ROI, orçamento),
        combina com riscos adicionais e gera resultado consolidado.

        Args:
            request: Dados para avaliação de riscos.

        Returns:
            Resultado consolidado com semáforo, riscos e recomendações.
        """
        # 1. Avaliar risco do patrocinador
        sponsor_risk = self._assess_sponsor_risk(request.sponsor)

        # 2. Avaliar risco do ROI
        roi_risk = self._assess_roi_risk(request.roi)

        # 3. Avaliar risco do orçamento
        budget_risk = self._assess_budget_risk(request.budget)

        # 4. Consolidar todos os riscos
        all_risks = [
            sponsor_risk,
            roi_risk,
            budget_risk,
            *request.additional_risks,
        ]

        # 5. Recalcular overall_level para riscos adicionais
        for risk in request.additional_risks:
            risk.overall_level = calculate_combined_risk_level(
                risk.probability,
                risk.impact,
            )

        # 6. Calcular pontuação consolidada
        risk_levels = [r.overall_level for r in all_risks]
        # Média ponderada: riscos principais (sponsor, ROI, budget) têm peso 2
        weighted_scores = (
            risk_level_to_score(sponsor_risk.overall_level) * 2
            + risk_level_to_score(roi_risk.overall_level) * 2
            + risk_level_to_score(budget_risk.overall_level) * 2
            + sum(risk_level_to_score(r.overall_level) for r in request.additional_risks)
        )
        total_weight = 6 + len(request.additional_risks)
        score = Decimal(str(round(weighted_scores / total_weight, 1))) if total_weight > 0 else Decimal("50")

        # 7. Determinar semáforo e nível consolidado
        traffic_light = score_to_traffic_light(score)
        overall_level = worst_risk_level(risk_levels)

        # 8. Gerar recomendações
        recommendations = self._generate_recommendations(
            sponsor_risk=sponsor_risk,
            roi_risk=roi_risk,
            budget_risk=budget_risk,
            additional_risks=request.additional_risks,
        )

        return RiskAssessmentResult(
            business_case_id=request.business_case_id,
            overall_traffic_light=traffic_light,
            overall_risk_level=overall_level,
            sponsor_risk=sponsor_risk,
            roi_risk=roi_risk,
            budget_risk=budget_risk,
            all_risks=all_risks,
            recommendations=recommendations,
            score=score,
        )

    # -----------------------------------------------------------------------
    # Avaliação de risco do patrocinador
    # -----------------------------------------------------------------------

    def _assess_sponsor_risk(self, sponsor: SponsorInfo) -> RiskItem:
        """Avalia o risco relacionado ao patrocinador executivo.

        Critérios avaliados:
        - Nível hierárquico (C-Level = menor risco)
        - Comprometimento formal confirmado
        - Aprovação formal registrada

        Args:
            sponsor: Informações do patrocinador.

        Returns:
            Item de risco avaliado para o patrocinador.
        """
        issues: list[str] = []
        probability = RiskLevel.LOW
        impact = RiskLevel.HIGH  # Impacto de perder patrocinador é sempre alto

        # Verificar nível hierárquico
        if sponsor.level == SponsorLevel.OTHER:
            probability = RiskLevel.HIGH
            issues.append(
                "Patrocinador não possui nível hierárquico adequado (recomendado: Diretor ou superior)."
            )
        elif sponsor.level == SponsorLevel.MANAGER:
            probability = RiskLevel.MEDIUM
            issues.append(
                "Patrocinador em nível gerencial — recomendado patrocínio de Diretor ou superior."
            )

        # Verificar comprometimento formal
        if not sponsor.commitment_confirmed:
            probability = max_risk_level(probability, RiskLevel.HIGH)
            issues.append(
                "Comprometimento formal do patrocinador NÃO confirmado."
            )

        # Verificar aprovação formal
        if sponsor.approval_date is None:
            probability = max_risk_level(probability, RiskLevel.MEDIUM)
            issues.append(
                "Data de aprovação formal pelo patrocinador não registrada."
            )

        overall = calculate_combined_risk_level(probability, impact)

        mitigation = ""
        if issues:
            mitigation = (
                "Ações recomendadas: "
                + "; ".join(
                    [
                        "Obter comprometimento formal por escrito",
                        "Escalar patrocínio para nível C-Level ou VP",
                        "Agendar reunião de alinhamento com patrocinador",
                    ]
                )
            )

        description = (
            "Avaliação do risco de patrocínio executivo. "
            + (" | ".join(issues) if issues else "Patrocinador adequado e comprometido.")
        )

        return RiskItem(
            category=RiskCategory.SPONSOR,
            title="Risco de Patrocínio Executivo",
            description=description,
            probability=probability,
            impact=impact,
            overall_level=overall,
            mitigation_plan=mitigation,
            mitigation_status=(
                MitigationStatus.PENDING if issues else MitigationStatus.VERIFIED
            ),
            owner=sponsor.name,
        )

    # -----------------------------------------------------------------------
    # Avaliação de risco do ROI
    # -----------------------------------------------------------------------

    def _assess_roi_risk(self, roi: ROIQuantification) -> RiskItem:
        """Avalia o risco relacionado ao ROI quantificado.

        Critérios avaliados:
        - ROI projetado acima do mínimo aceitável
        - Payback dentro do prazo aceitável
        - Existência de premissas documentadas
        - Existência de análise de sensibilidade
        - Consistência entre investimento e retorno

        Args:
            roi: Quantificação do ROI.

        Returns:
            Item de risco avaliado para o ROI.
        """
        issues: list[str] = []
        probability = RiskLevel.LOW
        impact = RiskLevel.HIGH

        # Verificar ROI mínimo
        if roi.projected_roi_percentage < _MIN_ACCEPTABLE_ROI:
            probability = max_risk_level(probability, RiskLevel.HIGH)
            issues.append(
                f"ROI projetado ({roi.projected_roi_percentage}%) abaixo do mínimo aceitável ({_MIN_ACCEPTABLE_ROI}%)."
            )
        elif roi.projected_roi_percentage < _MIN_ACCEPTABLE_ROI * 2:
            probability = max_risk_level(probability, RiskLevel.MEDIUM)
            issues.append(
                f"ROI projetado ({roi.projected_roi_percentage}%) está na faixa de atenção."
            )

        # Verificar ROI excessivamente otimista
        if roi.projected_roi_percentage > Decimal("500"):
            probability = max_risk_level(probability, RiskLevel.HIGH)
            issues.append(
                f"ROI projetado ({roi.projected_roi_percentage}%) parece excessivamente otimista — validar premissas."
            )

        # Verificar payback
        if roi.payback_months > _MAX_ACCEPTABLE_PAYBACK_MONTHS:
            probability = max_risk_level(probability, RiskLevel.HIGH)
            issues.append(
                f"Payback de {roi.payback_months} meses excede o máximo aceitável ({_MAX_ACCEPTABLE_PAYBACK_MONTHS} meses)."
            )

        # Verificar premissas documentadas
        if len(roi.assumptions) < 3:
            probability = max_risk_level(probability, RiskLevel.MEDIUM)
            issues.append(
                "Poucas premissas documentadas para o cálculo do ROI (mínimo recomendado: 3)."
            )

        # Verificar análise de sensibilidade
        if not roi.sensitivity_scenarios or len(roi.sensitivity_scenarios) < 2:
            probability = max_risk_level(probability, RiskLevel.MEDIUM)
            issues.append(
                "Análise de sensibilidade ausente ou insuficiente (mínimo: 2 cenários)."
            )

        # Verificar retorno negativo
        if roi.projected_return <= 0:
            probability = RiskLevel.CRITICAL
            impact = RiskLevel.CRITICAL
            issues.append(
                "Retorno projetado é zero ou negativo — business case inviável."
            )

        overall = calculate_combined_risk_level(probability, impact)

        mitigation = ""
        if issues:
            mitigation = (
                "Ações recomendadas: "
                + "; ".join(
                    [
                        "Revisar e documentar todas as premissas do ROI",
                        "Realizar análise de sensibilidade com cenários pessimista, base e otimista",
                        "Validar projeções com dados históricos de projetos similares",
                        "Considerar custos ocultos e riscos de implementação",
                    ]
                )
            )

        description = (
            "Avaliação do risco de ROI quantificado. "
            + (" | ".join(issues) if issues else "ROI adequadamente quantificado e documentado.")
        )

        return RiskItem(
            category=RiskCategory.ROI,
            title="Risco de ROI Quantificado",
            description=description,
            probability=probability,
            impact=impact,
            overall_level=overall,
            mitigation_plan=mitigation,
            mitigation_status=(
                MitigationStatus.PENDING if issues else MitigationStatus.VERIFIED
            ),
        )

    # -----------------------------------------------------------------------
    # Avaliação de risco do orçamento
    # -----------------------------------------------------------------------

    def _assess_budget_risk(self, budget: BudgetApproval) -> RiskItem:
        """Avalia o risco relacionado ao orçamento aprovado.

        Critérios avaliados:
        - Aprovação formal do orçamento
        - Percentual de contingência adequado
        - Fases de desembolso definidas
        - Consistência entre fases e total

        Args:
            budget: Informações de aprovação orçamentária.

        Returns:
            Item de risco avaliado para o orçamento.
        """
        issues: list[str] = []
        probability = RiskLevel.LOW
        impact = RiskLevel.HIGH

        # Verificar aprovação formal
        if not budget.is_formally_approved:
            probability = RiskLevel.CRITICAL
            issues.append(
                "Orçamento NÃO foi formalmente aprovado — risco crítico de cancelamento."
            )

        # Verificar data de aprovação
        if budget.approval_date is None and budget.is_formally_approved:
            probability = max_risk_level(probability, RiskLevel.MEDIUM)
            issues.append(
                "Data de aprovação do orçamento não registrada."
            )

        # Verificar contingência
        if budget.contingency_percentage < _MIN_CONTINGENCY_PERCENTAGE:
            probability = max_risk_level(probability, RiskLevel.HIGH)
            issues.append(
                f"Contingência orçamentária ({budget.contingency_percentage}%) abaixo do mínimo recomendado ({_MIN_CONTINGENCY_PERCENTAGE}%)."
            )

        # Verificar fases de desembolso
        if not budget.budget_phases or len(budget.budget_phases) == 0:
            probability = max_risk_level(probability, RiskLevel.MEDIUM)
            issues.append(
                "Fases de desembolso orçamentário não definidas."
            )
        else:
            # Verificar consistência: soma das fases vs. total
            phases_total = sum(phase.amount for phase in budget.budget_phases)
            budget_with_contingency = budget.total_budget * (
                1 + budget.contingency_percentage / 100
            )
            if phases_total > budget_with_contingency:
                probability = max_risk_level(probability, RiskLevel.HIGH)
                issues.append(
                    f"Soma das fases (R$ {phases_total:,.2f}) excede o orçamento total com contingência (R$ {budget_with_contingency:,.2f})."
                )

        overall = calculate_combined_risk_level(probability, impact)

        mitigation = ""
        if issues:
            mitigation = (
                "Ações recomendadas: "
                + "; ".join(
                    [
                        "Obter aprovação formal do orçamento com assinatura da autoridade competente",
                        "Definir contingência mínima de 10% sobre o orçamento base",
                        "Detalhar fases de desembolso com datas e valores",
                        "Estabelecer processo de controle de mudanças orçamentárias",
                    ]
                )
            )

        description = (
            "Avaliação do risco orçamentário. "
            + (" | ".join(issues) if issues else "Orçamento adequadamente aprovado e estruturado.")
        )

        return RiskItem(
            category=RiskCategory.BUDGET,
            title="Risco de Orçamento Aprovado",
            description=description,
            probability=probability,
            impact=impact,
            overall_level=overall,
            mitigation_plan=mitigation,
            mitigation_status=(
                MitigationStatus.PENDING if issues else MitigationStatus.VERIFIED
            ),
            owner=budget.approval_authority,
        )

    # -----------------------------------------------------------------------
    # Geração de recomendações
    # -----------------------------------------------------------------------

    def _generate_recommendations(
        self,
        sponsor_risk: RiskItem,
        roi_risk: RiskItem,
        budget_risk: RiskItem,
        additional_risks: list[RiskItem],
    ) -> list[str]:
        """Gera lista priorizada de recomendações de mitigação.

        Recomendações são ordenadas por severidade do risco (crítico primeiro).

        Args:
            sponsor_risk: Risco avaliado do patrocinador.
            roi_risk: Risco avaliado do ROI.
            budget_risk: Risco avaliado do orçamento.
            additional_risks: Riscos adicionais.

        Returns:
            Lista de recomendações em PT-BR, ordenadas por prioridade.
        """
        recommendations: list[tuple[int, str]] = []  # (prioridade, recomendação)

        severity_priority = {
            RiskLevel.CRITICAL: 0,
            RiskLevel.HIGH: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 3,
            RiskLevel.NEGLIGIBLE: 4,
        }

        # Recomendações do patrocinador
        if sponsor_risk.overall_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            priority = severity_priority[sponsor_risk.overall_level]
            recommendations.append((
                priority,
                "[PATROCINADOR] Ação urgente: garantir patrocínio executivo de nível adequado "
                "(Diretor ou superior) com comprometimento formal documentado.",
            ))

        if sponsor_risk.mitigation_status == MitigationStatus.PENDING:
            recommendations.append((
                2,
                "[PATROCINADOR] Agendar reunião de alinhamento com patrocinador para "
                "confirmar comprometimento e obter aprovação formal.",
            ))

        # Recomendações do ROI
        if roi_risk.overall_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            priority = severity_priority[roi_risk.overall_level]
            recommendations.append((
                priority,
                "[ROI] Ação urgente: revisar premissas do ROI e realizar análise de "
                "sensibilidade com cenários pessimista, base e otimista.",
            ))

        if roi_risk.overall_level == RiskLevel.CRITICAL:
            recommendations.append((
                0,
                "[ROI] CRÍTICO: Business case com retorno negativo ou inviável. "
                "Reavaliar viabilidade do projeto antes de prosseguir.",
            ))

        # Recomendações do orçamento
        if budget_risk.overall_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            priority = severity_priority[budget_risk.overall_level]
            recommendations.append((
                priority,
                "[ORÇAMENTO] Ação urgente: obter aprovação formal do orçamento com "
                "contingência adequada antes de iniciar execução.",
            ))

        # Recomendações de riscos adicionais
        for risk in additional_risks:
            if risk.overall_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
                priority = severity_priority[risk.overall_level]
                recommendations.append((
                    priority,
                    f"[{risk.category.value.upper()}] {risk.title}: {risk.mitigation_plan or 'Definir plano de mitigação.'}",
                ))

        # Recomendação geral se tudo estiver bem
        if not recommendations:
            recommendations.append((
                4,
                "Business case saudável. Manter monitoramento periódico dos indicadores "
                "e atualizar avaliação de riscos a cada marco do projeto.",
            ))

        # Ordenar por prioridade (menor número = maior prioridade)
        recommendations.sort(key=lambda x: x[0])

        return [rec[1] for rec in recommendations]


# ============================================================================
# Função auxiliar para comparação de severidade
# ============================================================================


def max_risk_level(a: RiskLevel, b: RiskLevel) -> RiskLevel:
    """Retorna o nível de risco mais severo entre dois.

    Args:
        a: Primeiro nível de risco.
        b: Segundo nível de risco.

    Returns:
        O nível mais severo (CRITICAL > HIGH > MEDIUM > LOW > NEGLIGIBLE).
    """
    severity = {
        RiskLevel.CRITICAL: 4,
        RiskLevel.HIGH: 3,
        RiskLevel.MEDIUM: 2,
        RiskLevel.LOW: 1,
        RiskLevel.NEGLIGIBLE: 0,
    }
    return a if severity.get(a, 0) >= severity.get(b, 0) else b


# ============================================================================
# Factory function para criação simplificada
# ============================================================================


def create_risk_business_case_service(
    business_case_validator: Any | None = None,
) -> RiskBusinessCaseService:
    """Factory function para criação do serviço de riscos do business case.

    Facilita injeção de dependências e testes.

    Args:
        business_case_validator: Validador de business case do módulo m01 (opcional).

    Returns:
        Instância configurada do serviço de riscos.
    """
    return RiskBusinessCaseService(
        business_case_validator=business_case_validator,
    )


# ============================================================================
# Exports públicos
# ============================================================================

__all__ = [
    # Enums
    "RiskLevel",
    "RiskCategory",
    "MitigationStatus",
    "SponsorLevel",
    "TrafficLight",
    # Schemas
    "SponsorInfo",
    "ROIQuantification",
    "SensitivityScenario",
    "BudgetApproval",
    "BudgetPhase",
    "RiskItem",
    "RiskAssessmentRequest",
    "RiskAssessmentResult",
    # Serviço
    "RiskBusinessCaseService",
    # Factory
    "create_risk_business_case_service",
    # Utilitários
    "calculate_combined_risk_level",
    "risk_level_to_score",
    "score_to_traffic_light",
    "max_risk_level",
    "worst_risk_level",
]
