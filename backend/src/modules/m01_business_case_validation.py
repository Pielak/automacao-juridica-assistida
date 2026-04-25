"""Módulo de Validação de Business Case — Automação Jurídica Assistida.

Implementa a lógica de validação do business case do projeto, verificando:
- ROI (Retorno sobre Investimento) projetado e realizado
- Stakeholders envolvidos e seus papéis
- Orçamento previsto vs. realizado
- Timeline do projeto com marcos (milestones)
- KPIs (Indicadores-Chave de Performance)

Este módulo faz parte da camada de aplicação (use cases) e segue os
princípios de Clean Architecture, dependendo apenas de portas (ports)
definidas no domínio.

Exemplo de uso:
    from backend.src.modules.m01_business_case_validation import (
        BusinessCaseValidator,
        BusinessCaseInput,
    )

    validator = BusinessCaseValidator(audit_repository=audit_repo)
    resultado = await validator.validate(business_case_input)
    print(resultado.is_valid)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.src.infrastructure.config.settings import get_settings
from backend.src.domain.ports.audit_repository_port import (
    AuditRepositoryPort,
)

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------


class StakeholderRole(str, Enum):
    """Papéis possíveis de stakeholders no business case."""

    SPONSOR = "sponsor"
    OWNER = "owner"
    CONTRIBUTOR = "contributor"
    REVIEWER = "reviewer"
    BENEFICIARY = "beneficiary"


class RiskLevel(str, Enum):
    """Níveis de risco identificados no business case."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationSeverity(str, Enum):
    """Severidade de um problema encontrado na validação."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class KPICategory(str, Enum):
    """Categorias de KPIs suportadas."""

    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    QUALITY = "quality"
    COMPLIANCE = "compliance"
    CUSTOMER_SATISFACTION = "customer_satisfaction"


# ---------------------------------------------------------------------------
# Schemas de Entrada (Pydantic v2)
# ---------------------------------------------------------------------------


class StakeholderInput(BaseModel):
    """Dados de um stakeholder do business case."""

    name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Nome completo do stakeholder.",
    )
    role: StakeholderRole = Field(
        ...,
        description="Papel do stakeholder no projeto.",
    )
    department: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Departamento ou área do stakeholder.",
    )
    email: str = Field(
        ...,
        description="E-mail de contato do stakeholder.",
    )
    is_decision_maker: bool = Field(
        default=False,
        description="Indica se o stakeholder é tomador de decisão.",
    )


class BudgetLineItem(BaseModel):
    """Item de linha do orçamento."""

    description: str = Field(
        ...,
        min_length=3,
        max_length=300,
        description="Descrição do item de orçamento.",
    )
    category: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Categoria do custo (ex: infraestrutura, pessoal, licenças).",
    )
    estimated_cost: Decimal = Field(
        ...,
        ge=0,
        description="Custo estimado em BRL.",
    )
    actual_cost: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Custo realizado em BRL (preenchido após execução).",
    )


class BudgetInput(BaseModel):
    """Dados de orçamento do business case."""

    total_estimated: Decimal = Field(
        ...,
        gt=0,
        description="Orçamento total estimado em BRL.",
    )
    total_approved: Decimal = Field(
        ...,
        gt=0,
        description="Orçamento total aprovado em BRL.",
    )
    currency: str = Field(
        default="BRL",
        description="Moeda do orçamento.",
    )
    line_items: list[BudgetLineItem] = Field(
        default_factory=list,
        description="Itens detalhados do orçamento.",
    )
    contingency_percentage: Decimal = Field(
        default=Decimal("10.0"),
        ge=0,
        le=50,
        description="Percentual de contingência sobre o orçamento (0-50%).",
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Valida que a moeda é suportada."""
        supported = {"BRL", "USD", "EUR"}
        if v.upper() not in supported:
            raise ValueError(
                f"Moeda '{v}' não suportada. Moedas aceitas: {', '.join(supported)}."
            )
        return v.upper()


class MilestoneInput(BaseModel):
    """Marco (milestone) da timeline do projeto."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Nome do marco.",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Descrição detalhada do marco.",
    )
    planned_date: date = Field(
        ...,
        description="Data planejada para conclusão do marco.",
    )
    actual_date: Optional[date] = Field(
        default=None,
        description="Data real de conclusão (preenchida após execução).",
    )
    is_critical: bool = Field(
        default=False,
        description="Indica se o marco está no caminho crítico.",
    )
    deliverables: list[str] = Field(
        default_factory=list,
        description="Lista de entregáveis associados ao marco.",
    )


class TimelineInput(BaseModel):
    """Dados de timeline do business case."""

    start_date: date = Field(
        ...,
        description="Data de início do projeto.",
    )
    planned_end_date: date = Field(
        ...,
        description="Data planejada de término do projeto.",
    )
    milestones: list[MilestoneInput] = Field(
        default_factory=list,
        description="Marcos do projeto.",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> TimelineInput:
        """Valida que a data de término é posterior à data de início."""
        if self.planned_end_date <= self.start_date:
            raise ValueError(
                "A data planejada de término deve ser posterior à data de início."
            )
        return self


class KPIInput(BaseModel):
    """Indicador-chave de performance (KPI)."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Nome do KPI.",
    )
    category: KPICategory = Field(
        ...,
        description="Categoria do KPI.",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Descrição do que o KPI mede.",
    )
    target_value: Decimal = Field(
        ...,
        description="Valor-alvo do KPI.",
    )
    current_value: Optional[Decimal] = Field(
        default=None,
        description="Valor atual do KPI (preenchido durante execução).",
    )
    unit: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Unidade de medida (ex: %, R$, horas, processos).",
    )
    measurement_frequency: str = Field(
        default="mensal",
        description="Frequência de medição do KPI.",
    )


class ROIInput(BaseModel):
    """Dados de ROI (Retorno sobre Investimento)."""

    total_investment: Decimal = Field(
        ...,
        gt=0,
        description="Investimento total previsto em BRL.",
    )
    expected_annual_benefit: Decimal = Field(
        ...,
        gt=0,
        description="Benefício anual esperado em BRL.",
    )
    payback_period_months: int = Field(
        ...,
        gt=0,
        le=120,
        description="Período de payback esperado em meses (máx. 10 anos).",
    )
    discount_rate: Decimal = Field(
        default=Decimal("12.0"),
        ge=0,
        le=100,
        description="Taxa de desconto anual para cálculo de VPL (%).",
    )
    projection_years: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Número de anos para projeção do ROI.",
    )
    intangible_benefits: list[str] = Field(
        default_factory=list,
        description="Lista de benefícios intangíveis (ex: melhoria de imagem, compliance).",
    )


class BusinessCaseInput(BaseModel):
    """Schema principal de entrada para validação do business case."""

    title: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="Título do business case.",
    )
    description: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="Descrição detalhada do business case.",
    )
    requester_id: uuid.UUID = Field(
        ...,
        description="ID do usuário solicitante.",
    )
    stakeholders: list[StakeholderInput] = Field(
        ...,
        min_length=1,
        description="Lista de stakeholders envolvidos.",
    )
    roi: ROIInput = Field(
        ...,
        description="Dados de ROI projetado.",
    )
    budget: BudgetInput = Field(
        ...,
        description="Dados de orçamento.",
    )
    timeline: TimelineInput = Field(
        ...,
        description="Dados de timeline do projeto.",
    )
    kpis: list[KPIInput] = Field(
        ...,
        min_length=1,
        description="Lista de KPIs definidos.",
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.MEDIUM,
        description="Nível de risco geral do business case.",
    )
    justification: str = Field(
        ...,
        min_length=20,
        max_length=3000,
        description="Justificativa para o investimento.",
    )


# ---------------------------------------------------------------------------
# DTOs de Resultado da Validação
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    """Representa um problema encontrado durante a validação."""

    code: str
    message: str
    severity: ValidationSeverity
    field: str = ""
    suggestion: str = ""


@dataclass
class ROIAnalysis:
    """Resultado da análise de ROI."""

    calculated_roi_percentage: Decimal
    net_present_value: Decimal
    payback_period_months: int
    is_viable: bool
    analysis_notes: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Resultado completo da validação do business case."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    is_valid: bool = False
    overall_score: Decimal = Decimal("0")
    issues: list[ValidationIssue] = field(default_factory=list)
    roi_analysis: Optional[ROIAnalysis] = None
    validated_at: datetime = field(default_factory=datetime.utcnow)
    summary: str = ""

    @property
    def errors(self) -> list[ValidationIssue]:
        """Retorna apenas os problemas com severidade ERROR ou CRITICAL."""
        return [
            issue
            for issue in self.issues
            if issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
        ]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Retorna apenas os problemas com severidade WARNING."""
        return [
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        ]

    @property
    def has_critical_issues(self) -> bool:
        """Verifica se há problemas críticos."""
        return any(
            issue.severity == ValidationSeverity.CRITICAL
            for issue in self.issues
        )


# ---------------------------------------------------------------------------
# Constantes de Validação
# ---------------------------------------------------------------------------

# Limites configuráveis para validação do business case
MIN_ROI_PERCENTAGE = Decimal("5.0")  # ROI mínimo aceitável: 5%
MIN_STAKEHOLDER_COUNT = 1
MAX_PAYBACK_MONTHS = 36  # Payback máximo recomendado: 3 anos
MIN_KPI_COUNT = 1
MIN_CRITICAL_MILESTONES = 1
BUDGET_VARIANCE_THRESHOLD = Decimal("20.0")  # Variação máxima aceitável: 20%
MIN_KPI_CATEGORIES = 2  # Mínimo de categorias distintas de KPIs


# ---------------------------------------------------------------------------
# Validador Principal
# ---------------------------------------------------------------------------


class BusinessCaseValidator:
    """Validador de business case para projetos de automação jurídica.

    Implementa validações abrangentes de ROI, stakeholders, orçamento,
    timeline e KPIs, registrando eventos de auditoria para rastreabilidade.

    Attributes:
        _audit_repository: Porta do repositório de auditoria para registro
            de eventos de validação.
    """

    def __init__(
        self,
        audit_repository: Optional[AuditRepositoryPort] = None,
    ) -> None:
        """Inicializa o validador de business case.

        Args:
            audit_repository: Implementação do repositório de auditoria.
                Se None, os eventos de auditoria não serão registrados.
        """
        self._audit_repository = audit_repository
        self._settings = get_settings()

    async def validate(
        self,
        business_case: BusinessCaseInput,
    ) -> ValidationResult:
        """Executa a validação completa do business case.

        Realiza todas as verificações de viabilidade, incluindo ROI,
        stakeholders, orçamento, timeline e KPIs.

        Args:
            business_case: Dados do business case a ser validado.

        Returns:
            ValidationResult com o resultado detalhado da validação.
        """
        logger.info(
            "Iniciando validação de business case",
            title=business_case.title,
            requester_id=str(business_case.requester_id),
        )

        result = ValidationResult()
        issues: list[ValidationIssue] = []

        # Executar todas as validações
        issues.extend(self._validate_roi(business_case.roi))
        issues.extend(self._validate_stakeholders(business_case.stakeholders))
        issues.extend(self._validate_budget(business_case.budget, business_case.roi))
        issues.extend(self._validate_timeline(business_case.timeline))
        issues.extend(self._validate_kpis(business_case.kpis))
        issues.extend(self._validate_risk_alignment(business_case))

        # Calcular análise de ROI
        roi_analysis = self._calculate_roi_analysis(business_case.roi)

        # Calcular score geral
        overall_score = self._calculate_overall_score(issues, roi_analysis)

        # Determinar se é válido (sem erros críticos e score >= 60)
        has_blocking_issues = any(
            issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
            for issue in issues
        )
        is_valid = not has_blocking_issues and overall_score >= Decimal("60")

        # Montar resultado
        result.is_valid = is_valid
        result.overall_score = overall_score
        result.issues = issues
        result.roi_analysis = roi_analysis
        result.summary = self._generate_summary(is_valid, overall_score, issues)

        # Registrar evento de auditoria
        await self._record_audit_event(business_case, result)

        logger.info(
            "Validação de business case concluída",
            title=business_case.title,
            is_valid=is_valid,
            overall_score=str(overall_score),
            total_issues=len(issues),
            errors=len(result.errors),
            warnings=len(result.warnings),
        )

        return result

    # -----------------------------------------------------------------------
    # Validações Individuais
    # -----------------------------------------------------------------------

    def _validate_roi(self, roi: ROIInput) -> list[ValidationIssue]:
        """Valida os dados de ROI do business case.

        Args:
            roi: Dados de ROI a serem validados.

        Returns:
            Lista de problemas encontrados na validação de ROI.
        """
        issues: list[ValidationIssue] = []

        # Calcular ROI percentual
        roi_percentage = self._compute_roi_percentage(roi)

        if roi_percentage < Decimal("0"):
            issues.append(
                ValidationIssue(
                    code="ROI_NEGATIVE",
                    message=f"ROI projetado é negativo ({roi_percentage:.1f}%). "
                    "O investimento não se paga no período projetado.",
                    severity=ValidationSeverity.CRITICAL,
                    field="roi",
                    suggestion="Revise os benefícios esperados ou reduza o investimento total.",
                )
            )
        elif roi_percentage < MIN_ROI_PERCENTAGE:
            issues.append(
                ValidationIssue(
                    code="ROI_BELOW_MINIMUM",
                    message=f"ROI projetado ({roi_percentage:.1f}%) está abaixo do mínimo "
                    f"aceitável de {MIN_ROI_PERCENTAGE}%.",
                    severity=ValidationSeverity.ERROR,
                    field="roi.expected_annual_benefit",
                    suggestion="Considere identificar benefícios adicionais ou otimizar custos.",
                )
            )

        # Validar período de payback
        if roi.payback_period_months > MAX_PAYBACK_MONTHS:
            issues.append(
                ValidationIssue(
                    code="PAYBACK_TOO_LONG",
                    message=f"Período de payback ({roi.payback_period_months} meses) excede "
                    f"o máximo recomendado de {MAX_PAYBACK_MONTHS} meses.",
                    severity=ValidationSeverity.WARNING,
                    field="roi.payback_period_months",
                    suggestion="Avalie formas de acelerar o retorno do investimento.",
                )
            )

        # Validar coerência entre investimento e benefício
        annual_ratio = roi.expected_annual_benefit / roi.total_investment
        if annual_ratio > Decimal("10"):
            issues.append(
                ValidationIssue(
                    code="ROI_UNREALISTIC",
                    message="A relação benefício/investimento parece irrealista "
                    f"(benefício anual é {annual_ratio:.1f}x o investimento total).",
                    severity=ValidationSeverity.WARNING,
                    field="roi.expected_annual_benefit",
                    suggestion="Revise as premissas de benefício para garantir realismo.",
                )
            )

        # Verificar se há benefícios intangíveis documentados
        if not roi.intangible_benefits:
            issues.append(
                ValidationIssue(
                    code="NO_INTANGIBLE_BENEFITS",
                    message="Nenhum benefício intangível foi documentado.",
                    severity=ValidationSeverity.INFO,
                    field="roi.intangible_benefits",
                    suggestion="Documente benefícios como melhoria de compliance, "
                    "satisfação do cliente ou redução de riscos.",
                )
            )

        return issues

    def _validate_stakeholders(
        self, stakeholders: list[StakeholderInput]
    ) -> list[ValidationIssue]:
        """Valida os stakeholders do business case.

        Args:
            stakeholders: Lista de stakeholders a serem validados.

        Returns:
            Lista de problemas encontrados na validação de stakeholders.
        """
        issues: list[ValidationIssue] = []

        # Verificar se há pelo menos um sponsor
        sponsors = [
            s for s in stakeholders if s.role == StakeholderRole.SPONSOR
        ]
        if not sponsors:
            issues.append(
                ValidationIssue(
                    code="NO_SPONSOR",
                    message="Nenhum sponsor (patrocinador) foi identificado.",
                    severity=ValidationSeverity.ERROR,
                    field="stakeholders",
                    suggestion="Todo business case precisa de pelo menos um sponsor executivo.",
                )
            )

        # Verificar se há pelo menos um owner
        owners = [
            s for s in stakeholders if s.role == StakeholderRole.OWNER
        ]
        if not owners:
            issues.append(
                ValidationIssue(
                    code="NO_OWNER",
                    message="Nenhum owner (responsável) foi identificado.",
                    severity=ValidationSeverity.ERROR,
                    field="stakeholders",
                    suggestion="Defina um responsável direto pelo business case.",
                )
            )

        # Verificar se há tomadores de decisão
        decision_makers = [s for s in stakeholders if s.is_decision_maker]
        if not decision_makers:
            issues.append(
                ValidationIssue(
                    code="NO_DECISION_MAKER",
                    message="Nenhum tomador de decisão foi identificado entre os stakeholders.",
                    severity=ValidationSeverity.WARNING,
                    field="stakeholders",
                    suggestion="Identifique quem tem autoridade para aprovar o business case.",
                )
            )

        # Verificar duplicatas de e-mail
        emails = [s.email.lower() for s in stakeholders]
        if len(emails) != len(set(emails)):
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_STAKEHOLDER_EMAIL",
                    message="Existem stakeholders com e-mails duplicados.",
                    severity=ValidationSeverity.WARNING,
                    field="stakeholders",
                    suggestion="Verifique se não há stakeholders cadastrados em duplicidade.",
                )
            )

        # Verificar diversidade de departamentos
        departments = {s.department.lower() for s in stakeholders}
        if len(departments) < 2 and len(stakeholders) >= 3:
            issues.append(
                ValidationIssue(
                    code="LOW_DEPARTMENT_DIVERSITY",
                    message="Todos os stakeholders pertencem ao mesmo departamento.",
                    severity=ValidationSeverity.INFO,
                    field="stakeholders",
                    suggestion="Considere envolver stakeholders de outras áreas impactadas.",
                )
            )

        return issues

    def _validate_budget(
        self, budget: BudgetInput, roi: ROIInput
    ) -> list[ValidationIssue]:
        """Valida os dados de orçamento do business case.

        Args:
            budget: Dados de orçamento a serem validados.
            roi: Dados de ROI para validação cruzada.

        Returns:
            Lista de problemas encontrados na validação de orçamento.
        """
        issues: list[ValidationIssue] = []

        # Verificar se orçamento aprovado é compatível com estimado
        if budget.total_approved > budget.total_estimated:
            issues.append(
                ValidationIssue(
                    code="APPROVED_EXCEEDS_ESTIMATED",
                    message="O orçamento aprovado excede o orçamento estimado.",
                    severity=ValidationSeverity.INFO,
                    field="budget.total_approved",
                    suggestion="Verifique se a aprovação inclui contingência.",
                )
            )

        # Verificar variação entre estimado e aprovado
        if budget.total_estimated > Decimal("0"):
            variance = abs(
                (budget.total_approved - budget.total_estimated)
                / budget.total_estimated
                * Decimal("100")
            )
            if variance > BUDGET_VARIANCE_THRESHOLD:
                issues.append(
                    ValidationIssue(
                        code="BUDGET_HIGH_VARIANCE",
                        message=f"Variação de {variance:.1f}% entre orçamento estimado e aprovado "
                        f"excede o limite de {BUDGET_VARIANCE_THRESHOLD}%.",
                        severity=ValidationSeverity.WARNING,
                        field="budget",
                        suggestion="Revise as estimativas ou justifique a variação.",
                    )
                )

        # Verificar se há itens de linha detalhados
        if not budget.line_items:
            issues.append(
                ValidationIssue(
                    code="NO_BUDGET_LINE_ITEMS",
                    message="O orçamento não possui itens detalhados.",
                    severity=ValidationSeverity.WARNING,
                    field="budget.line_items",
                    suggestion="Detalhe o orçamento em itens de linha para maior transparência.",
                )
            )
        else:
            # Verificar se soma dos itens é compatível com total estimado
            items_total = sum(
                item.estimated_cost for item in budget.line_items
            )
            if items_total > Decimal("0"):
                items_variance = abs(
                    (items_total - budget.total_estimated)
                    / budget.total_estimated
                    * Decimal("100")
                )
                if items_variance > Decimal("5.0"):
                    issues.append(
                        ValidationIssue(
                            code="BUDGET_ITEMS_MISMATCH",
                            message=f"A soma dos itens de orçamento (R$ {items_total:,.2f}) "
                            f"diverge do total estimado (R$ {budget.total_estimated:,.2f}) "
                            f"em {items_variance:.1f}%.",
                            severity=ValidationSeverity.ERROR,
                            field="budget.line_items",
                            suggestion="Ajuste os itens de linha para que a soma corresponda ao total.",
                        )
                    )

        # Validação cruzada: orçamento vs. investimento do ROI
        if budget.total_estimated != roi.total_investment:
            issues.append(
                ValidationIssue(
                    code="BUDGET_ROI_MISMATCH",
                    message=f"O orçamento estimado (R$ {budget.total_estimated:,.2f}) "
                    f"diverge do investimento total do ROI (R$ {roi.total_investment:,.2f}).",
                    severity=ValidationSeverity.ERROR,
                    field="budget.total_estimated",
                    suggestion="Alinhe o orçamento com o investimento declarado no ROI.",
                )
            )

        # Verificar contingência
        if budget.contingency_percentage == Decimal("0"):
            issues.append(
                ValidationIssue(
                    code="NO_CONTINGENCY",
                    message="Nenhuma contingência orçamentária foi definida.",
                    severity=ValidationSeverity.WARNING,
                    field="budget.contingency_percentage",
                    suggestion="Recomenda-se uma contingência de pelo menos 10% para projetos jurídicos.",
                )
            )

        return issues

    def _validate_timeline(
        self, timeline: TimelineInput
    ) -> list[ValidationIssue]:
        """Valida a timeline do business case.

        Args:
            timeline: Dados de timeline a serem validados.

        Returns:
            Lista de problemas encontrados na validação de timeline.
        """
        issues: list[ValidationIssue] = []

        # Verificar se há milestones
        if not timeline.milestones:
            issues.append(
                ValidationIssue(
                    code="NO_MILESTONES",
                    message="Nenhum marco (milestone) foi definido na timeline.",
                    severity=ValidationSeverity.ERROR,
                    field="timeline.milestones",
                    suggestion="Defina marcos intermediários para acompanhamento do progresso.",
                )
            )
            return issues

        # Verificar se há milestones críticos
        critical_milestones = [
            m for m in timeline.milestones if m.is_critical
        ]
        if len(critical_milestones) < MIN_CRITICAL_MILESTONES:
            issues.append(
                ValidationIssue(
                    code="NO_CRITICAL_MILESTONES",
                    message="Nenhum marco foi marcado como crítico.",
                    severity=ValidationSeverity.WARNING,
                    field="timeline.milestones",
                    suggestion="Identifique os marcos que estão no caminho crítico do projeto.",
                )
            )

        # Verificar se milestones estão dentro do período do projeto
        for milestone in timeline.milestones:
            if milestone.planned_date < timeline.start_date:
                issues.append(
                    ValidationIssue(
                        code="MILESTONE_BEFORE_START",
                        message=f"O marco '{milestone.name}' tem data planejada "
                        f"({milestone.planned_date}) anterior ao início do projeto "
                        f"({timeline.start_date}).",
                        severity=ValidationSeverity.ERROR,
                        field="timeline.milestones",
                        suggestion="Ajuste a data do marco para dentro do período do projeto.",
                    )
                )
            if milestone.planned_date > timeline.planned_end_date:
                issues.append(
                    ValidationIssue(
                        code="MILESTONE_AFTER_END",
                        message=f"O marco '{milestone.name}' tem data planejada "
                        f"({milestone.planned_date}) posterior ao término do projeto "
                        f"({timeline.planned_end_date}).",
                        severity=ValidationSeverity.ERROR,
                        field="timeline.milestones",
                        suggestion="Ajuste a data do marco ou estenda a timeline do projeto.",
                    )
                )

        # Verificar se milestones têm entregáveis
        milestones_without_deliverables = [
            m for m in timeline.milestones if not m.deliverables
        ]
        if milestones_without_deliverables:
            names = ", ".join(
                m.name for m in milestones_without_deliverables[:3]
            )
            issues.append(
                ValidationIssue(
                    code="MILESTONES_WITHOUT_DELIVERABLES",
                    message=f"Os seguintes marcos não possuem entregáveis definidos: {names}.",
                    severity=ValidationSeverity.INFO,
                    field="timeline.milestones",
                    suggestion="Associe entregáveis concretos a cada marco.",
                )
            )

        # Verificar duração total do projeto
        duration_days = (timeline.planned_end_date - timeline.start_date).days
        if duration_days > 365 * 3:
            issues.append(
                ValidationIssue(
                    code="TIMELINE_TOO_LONG",
                    message=f"A duração do projeto ({duration_days} dias / "
                    f"{duration_days // 30} meses) excede 3 anos.",
                    severity=ValidationSeverity.WARNING,
                    field="timeline",
                    suggestion="Considere dividir o projeto em fases menores.",
                )
            )

        return issues

    def _validate_kpis(self, kpis: list[KPIInput]) -> list[ValidationIssue]:
        """Valida os KPIs do business case.

        Args:
            kpis: Lista de KPIs a serem validados.

        Returns:
            Lista de problemas encontrados na validação de KPIs.
        """
        issues: list[ValidationIssue] = []

        # Verificar diversidade de categorias
        categories = {kpi.category for kpi in kpis}
        if len(categories) < MIN_KPI_CATEGORIES:
            issues.append(
                ValidationIssue(
                    code="LOW_KPI_DIVERSITY",
                    message=f"Apenas {len(categories)} categoria(s) de KPI definida(s). "
                    f"Recomenda-se pelo menos {MIN_KPI_CATEGORIES} categorias distintas.",
                    severity=ValidationSeverity.WARNING,
                    field="kpis",
                    suggestion="Inclua KPIs de categorias variadas (financeiro, operacional, "
                    "qualidade, compliance).",
                )
            )

        # Verificar se há KPI financeiro (obrigatório para business case)
        has_financial_kpi = any(
            kpi.category == KPICategory.FINANCIAL for kpi in kpis
        )
        if not has_financial_kpi:
            issues.append(
                ValidationIssue(
                    code="NO_FINANCIAL_KPI",
                    message="Nenhum KPI financeiro foi definido.",
                    severity=ValidationSeverity.ERROR,
                    field="kpis",
                    suggestion="Inclua pelo menos um KPI financeiro para mensurar o retorno.",
                )
            )

        # Verificar se há KPI de compliance (recomendado para domínio jurídico)
        has_compliance_kpi = any(
            kpi.category == KPICategory.COMPLIANCE for kpi in kpis
        )
        if not has_compliance_kpi:
            issues.append(
                ValidationIssue(
                    code="NO_COMPLIANCE_KPI",
                    message="Nenhum KPI de compliance foi definido.",
                    severity=ValidationSeverity.INFO,
                    field="kpis",
                    suggestion="Para projetos jurídicos, KPIs de compliance são altamente recomendados.",
                )
            )

        # Verificar nomes duplicados
        kpi_names = [kpi.name.lower().strip() for kpi in kpis]
        if len(kpi_names) != len(set(kpi_names)):
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_KPI_NAMES",
                    message="Existem KPIs com nomes duplicados.",
                    severity=ValidationSeverity.WARNING,
                    field="kpis",
                    suggestion="Renomeie os KPIs para que cada um tenha um nome único.",
                )
            )

        return issues

    def _validate_risk_alignment(
        self, business_case: BusinessCaseInput
    ) -> list[ValidationIssue]:
        """Valida o alinhamento entre nível de risco e demais parâmetros.

        Args:
            business_case: Dados completos do business case.

        Returns:
            Lista de problemas encontrados na validação de alinhamento de risco.
        """
        issues: list[ValidationIssue] = []

        # Se risco é alto/crítico, verificar se contingência é adequada
        if business_case.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            if business_case.budget.contingency_percentage < Decimal("15.0"):
                issues.append(
                    ValidationIssue(
                        code="LOW_CONTINGENCY_FOR_RISK",
                        message=f"Contingência de {business_case.budget.contingency_percentage}% "
                        f"é baixa para um projeto com risco {business_case.risk_level.value}.",
                        severity=ValidationSeverity.WARNING,
                        field="budget.contingency_percentage",
                        suggestion="Para projetos de alto risco, recomenda-se contingência de pelo menos 15-20%.",
                    )
                )

        # Se risco é crítico, verificar se há sponsor executivo
        if business_case.risk_level == RiskLevel.CRITICAL:
            sponsors = [
                s
                for s in business_case.stakeholders
                if s.role == StakeholderRole.SPONSOR and s.is_decision_maker
            ]
            if not sponsors:
                issues.append(
                    ValidationIssue(
                        code="CRITICAL_RISK_NO_EXECUTIVE_SPONSOR",
                        message="Projetos com risco crítico necessitam de um sponsor executivo "
                        "com poder de decisão.",
                        severity=ValidationSeverity.ERROR,
                        field="stakeholders",
                        suggestion="Adicione um sponsor executivo como tomador de decisão.",
                    )
                )

        return issues

    # -----------------------------------------------------------------------
    # Cálculos Auxiliares
    # -----------------------------------------------------------------------

    def _compute_roi_percentage(self, roi: ROIInput) -> Decimal:
        """Calcula o percentual de ROI projetado.

        Fórmula: ((Benefício Total - Investimento) / Investimento) * 100

        Args:
            roi: Dados de ROI.

        Returns:
            Percentual de ROI calculado.
        """
        total_benefit = roi.expected_annual_benefit * roi.projection_years
        if roi.total_investment == Decimal("0"):
            return Decimal("0")
        return (
            (total_benefit - roi.total_investment)
            / roi.total_investment
            * Decimal("100")
        )

    def _calculate_roi_analysis(self, roi: ROIInput) -> ROIAnalysis:
        """Calcula a análise detalhada de ROI.

        Inclui cálculo de VPL (Valor Presente Líquido) e análise de viabilidade.

        Args:
            roi: Dados de ROI.

        Returns:
            Análise detalhada de ROI.
        """
        roi_percentage = self._compute_roi_percentage(roi)

        # Calcular VPL (Valor Presente Líquido)
        discount_rate = float(roi.discount_rate) / 100.0
        npv = float(-roi.total_investment)
        for year in range(1, roi.projection_years + 1):
            npv += float(roi.expected_annual_benefit) / ((1 + discount_rate) ** year)
        npv_decimal = Decimal(str(round(npv, 2)))

        # Determinar viabilidade
        is_viable = roi_percentage >= MIN_ROI_PERCENTAGE and npv_decimal > Decimal("0")

        # Notas de análise
        notes: list[str] = []
        if roi_percentage >= Decimal("50"):
            notes.append("ROI projetado é excelente (>= 50%).")
        elif roi_percentage >= Decimal("20"):
            notes.append("ROI projetado é bom (>= 20%).")
        elif roi_percentage >= MIN_ROI_PERCENTAGE:
            notes.append("ROI projetado é aceitável, mas marginal.")
        else:
            notes.append("ROI projetado está abaixo do mínimo aceitável.")

        if npv_decimal > Decimal("0"):
            notes.append(f"VPL positivo de R$ {npv_decimal:,.2f} indica viabilidade financeira.")
        else:
            notes.append(f"VPL negativo de R$ {npv_decimal:,.2f} indica inviabilidade financeira.")

        if roi.intangible_benefits:
            notes.append(
                f"{len(roi.intangible_benefits)} benefício(s) intangível(is) documentado(s) "
                "reforçam a justificativa."
            )

        return ROIAnalysis(
            calculated_roi_percentage=roi_percentage,
            net_present_value=npv_decimal,
            payback_period_months=roi.payback_period_months,
            is_viable=is_viable,
            analysis_notes=notes,
        )

    def _calculate_overall_score(
        self,
        issues: list[ValidationIssue],
        roi_analysis: ROIAnalysis,
    ) -> Decimal:
        """Calcula o score geral do business case (0-100).

        O score é baseado na quantidade e severidade dos problemas encontrados,
        combinado com a viabilidade do ROI.

        Args:
            issues: Lista de problemas encontrados.
            roi_analysis: Análise de ROI calculada.

        Returns:
            Score geral de 0 a 100.
        """
        base_score = Decimal("100")

        # Penalidades por severidade
        penalties = {
            ValidationSeverity.CRITICAL: Decimal("30"),
            ValidationSeverity.ERROR: Decimal("15"),
            ValidationSeverity.WARNING: Decimal("5"),
            ValidationSeverity.INFO: Decimal("1"),
        }

        for issue in issues:
            base_score -= penalties.get(issue.severity, Decimal("0"))

        # Bônus por ROI viável
        if roi_analysis.is_viable:
            base_score += Decimal("5")

        # Limitar entre 0 e 100
        return max(Decimal("0"), min(Decimal("100"), base_score))

    def _generate_summary(
        self,
        is_valid: bool,
        score: Decimal,
        issues: list[ValidationIssue],
    ) -> str:
        """Gera um resumo textual da validação.

        Args:
            is_valid: Se o business case é válido.
            score: Score geral calculado.
            issues: Lista de problemas encontrados.

        Returns:
            Resumo textual da validação.
        """
        critical_count = sum(
            1 for i in issues if i.severity == ValidationSeverity.CRITICAL
        )
        error_count = sum(
            1 for i in issues if i.severity == ValidationSeverity.ERROR
        )
        warning_count = sum(
            1 for i in issues if i.severity == ValidationSeverity.WARNING
        )

        status = "APROVADO" if is_valid else "REPROVADO"

        summary_parts = [
            f"Business case {status} com score {score:.0f}/100.",
        ]

        if critical_count:
            summary_parts.append(f"{critical_count} problema(s) crítico(s).")
        if error_count:
            summary_parts.append(f"{error_count} erro(s).")
        if warning_count:
            summary_parts.append(f"{warning_count} aviso(s).")

        if not issues:
            summary_parts.append("Nenhum problema identificado.")

        return " ".join(summary_parts)

    # -----------------------------------------------------------------------
    # Auditoria
    # -----------------------------------------------------------------------

    async def _record_audit_event(
        self,
        business_case: BusinessCaseInput,
        result: ValidationResult,
    ) -> None:
        """Registra evento de auditoria da validação do business case.

        Args:
            business_case: Dados do business case validado.
            result: Resultado da validação.
        """
        if self._audit_repository is None:
            logger.debug(
                "Repositório de auditoria não configurado; evento não registrado."
            )
            return

        try:
            # TODO: Chamar o método correto do AuditRepositoryPort quando
            # a interface completa estiver disponível. O DTO exato de
            # criação de evento de auditoria depende da definição final
            # em audit_repository_port.py.
            audit_data: dict[str, Any] = {
                "event_type": "business_case_validation",
                "entity_type": "business_case",
                "entity_id": str(result.id),
                "actor_id": str(business_case.requester_id),
                "action": "validate",
                "result": "approved" if result.is_valid else "rejected",
                "metadata": {
                    "title": business_case.title,
                    "score": str(result.overall_score),
                    "total_issues": len(result.issues),
                    "errors": len(result.errors),
                    "warnings": len(result.warnings),
                    "has_critical_issues": result.has_critical_issues,
                },
                "timestamp": result.validated_at.isoformat(),
            }

            # TODO: Substituir por chamada tipada ao repositório de auditoria
            # quando a interface estiver completamente definida:
            # await self._audit_repository.create(audit_event_dto)
            logger.info(
                "Evento de auditoria preparado para registro",
                audit_data=audit_data,
            )

        except Exception as exc:
            # Falha na auditoria não deve bloquear a validação
            logger.error(
                "Falha ao registrar evento de auditoria",
                error=str(exc),
                business_case_title=business_case.title,
            )
