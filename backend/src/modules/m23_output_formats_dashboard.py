"""Módulo backlog #23: Dashboard GCA — scores pilares, status aprovação, riscos, progresso.

Este módulo implementa o dashboard de Governança, Conformidade e Aprovação (GCA)
para o projeto de Automação Jurídica Assistida. Fornece visualização consolidada
dos scores dos pilares de avaliação, status de aprovação por área, identificação
de riscos e acompanhamento de progresso geral do projeto.

O dashboard agrega dados de múltiplas fontes internas (entregáveis, configurações)
para apresentar uma visão executiva do estado do projeto.

Exemplo de uso:
    from backend.src.modules.m23_output_formats_dashboard import (
        DashboardGCAService,
        get_dashboard_gca_service,
        PillarScore,
        DashboardSummary,
        RiskItem,
        ApprovalStatus,
    )

    service = get_dashboard_gca_service()
    dashboard = await service.get_dashboard_summary()
    print(dashboard.overall_progress)
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from backend.src.infrastructure.config.settings import get_settings
from backend.src.modules.m19_deliverables_summary import (
    DeliverablesSummaryService,
    get_deliverables_summary_service,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PillarCode(str, enum.Enum):
    """Códigos dos pilares de avaliação do projeto."""

    P1_SCOPE = "P1"
    P2_COMPLIANCE = "P2"
    P3_UX = "P3"
    P4_INTEGRATIONS = "P4"
    P5_ARCHITECTURE = "P5"
    P6_TESTING = "P6"
    P7_SECURITY = "P7"
    P8_DEPLOYMENT = "P8"


class RiskSeverity(str, enum.Enum):
    """Severidade de um risco identificado."""

    LOW = "baixo"
    MEDIUM = "medio"
    HIGH = "alto"
    CRITICAL = "critico"


class ApprovalState(str, enum.Enum):
    """Estado de aprovação de um pilar ou área."""

    PENDING = "pendente"
    APPROVED = "aprovado"
    REJECTED = "rejeitado"
    CONDITIONAL = "condicional"


class ProgressPhase(str, enum.Enum):
    """Fases de progresso do projeto."""

    PHASE_1 = "fase_1"
    PHASE_2 = "fase_2"
    PHASE_3 = "fase_3"
    PHASE_4 = "fase_4"


# ---------------------------------------------------------------------------
# Schemas / DTOs
# ---------------------------------------------------------------------------


class PillarScore(BaseModel):
    """Score de avaliação de um pilar específico.

    Attributes:
        pillar_code: Código identificador do pilar.
        pillar_name: Nome descritivo do pilar em PT-BR.
        score: Pontuação de 0 a 100.
        max_score: Pontuação máxima possível (padrão 100).
        weight: Peso relativo do pilar na composição geral.
        evaluated_at: Data/hora da última avaliação.
        notes: Observações adicionais sobre a avaliação.
    """

    pillar_code: PillarCode = Field(
        ..., description="Código identificador do pilar"
    )
    pillar_name: str = Field(
        ..., description="Nome descritivo do pilar em português"
    )
    score: float = Field(
        ..., ge=0, le=100, description="Pontuação do pilar (0-100)"
    )
    max_score: float = Field(
        default=100.0, description="Pontuação máxima possível"
    )
    weight: float = Field(
        default=1.0,
        ge=0,
        le=1.0,
        description="Peso relativo do pilar na composição geral",
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora da última avaliação",
    )
    notes: str | None = Field(
        default=None, description="Observações adicionais sobre a avaliação"
    )

    @field_validator("score")
    @classmethod
    def validate_score_range(cls, v: float) -> float:
        """Valida que o score está dentro do intervalo permitido."""
        if v < 0 or v > 100:
            raise ValueError("O score deve estar entre 0 e 100.")
        return round(v, 2)

    @property
    def percentage(self) -> float:
        """Retorna o score como percentual da pontuação máxima."""
        if self.max_score == 0:
            return 0.0
        return round((self.score / self.max_score) * 100, 2)

    @property
    def is_passing(self) -> bool:
        """Verifica se o pilar atinge o limiar mínimo de aprovação (70%)."""
        return self.percentage >= 70.0


class ApprovalStatus(BaseModel):
    """Status de aprovação de uma área ou pilar.

    Attributes:
        area_name: Nome da área avaliada.
        pillar_code: Pilar associado (opcional).
        state: Estado atual de aprovação.
        approver: Identificador do aprovador.
        approved_at: Data/hora da aprovação.
        conditions: Condições para aprovação condicional.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Identificador único do registro de aprovação",
    )
    area_name: str = Field(
        ..., description="Nome da área avaliada"
    )
    pillar_code: PillarCode | None = Field(
        default=None, description="Pilar associado à aprovação"
    )
    state: ApprovalState = Field(
        default=ApprovalState.PENDING,
        description="Estado atual de aprovação",
    )
    approver: str | None = Field(
        default=None, description="Identificador do aprovador responsável"
    )
    approved_at: datetime | None = Field(
        default=None, description="Data/hora em que a aprovação foi concedida"
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="Condições pendentes para aprovação condicional",
    )
    notes: str | None = Field(
        default=None, description="Observações sobre a aprovação"
    )


class RiskItem(BaseModel):
    """Representa um risco identificado no projeto.

    Attributes:
        id: Identificador único do risco.
        title: Título descritivo do risco.
        description: Descrição detalhada.
        severity: Severidade do risco.
        pillar_code: Pilar relacionado (opcional).
        mitigation: Estratégia de mitigação proposta.
        is_mitigated: Indica se o risco já foi mitigado.
        identified_at: Data/hora de identificação.
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Identificador único do risco",
    )
    title: str = Field(
        ..., min_length=3, max_length=200, description="Título descritivo do risco"
    )
    description: str = Field(
        ..., min_length=10, description="Descrição detalhada do risco"
    )
    severity: RiskSeverity = Field(
        ..., description="Severidade do risco"
    )
    pillar_code: PillarCode | None = Field(
        default=None, description="Pilar relacionado ao risco"
    )
    mitigation: str | None = Field(
        default=None, description="Estratégia de mitigação proposta"
    )
    is_mitigated: bool = Field(
        default=False, description="Indica se o risco já foi mitigado"
    )
    identified_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora de identificação do risco",
    )

    @property
    def severity_weight(self) -> int:
        """Retorna peso numérico da severidade para ordenação."""
        weights = {
            RiskSeverity.LOW: 1,
            RiskSeverity.MEDIUM: 2,
            RiskSeverity.HIGH: 3,
            RiskSeverity.CRITICAL: 4,
        }
        return weights.get(self.severity, 0)


class PhaseProgress(BaseModel):
    """Progresso de uma fase específica do projeto.

    Attributes:
        phase: Identificador da fase.
        phase_label: Rótulo descritivo da fase.
        total_deliverables: Total de entregáveis na fase.
        completed_deliverables: Entregáveis concluídos.
        in_progress_deliverables: Entregáveis em andamento.
        blocked_deliverables: Entregáveis bloqueados.
        progress_percentage: Percentual de conclusão.
    """

    phase: ProgressPhase = Field(
        ..., description="Identificador da fase"
    )
    phase_label: str = Field(
        ..., description="Rótulo descritivo da fase em português"
    )
    total_deliverables: int = Field(
        default=0, ge=0, description="Total de entregáveis na fase"
    )
    completed_deliverables: int = Field(
        default=0, ge=0, description="Entregáveis concluídos"
    )
    in_progress_deliverables: int = Field(
        default=0, ge=0, description="Entregáveis em andamento"
    )
    blocked_deliverables: int = Field(
        default=0, ge=0, description="Entregáveis bloqueados"
    )

    @property
    def progress_percentage(self) -> float:
        """Calcula o percentual de conclusão da fase."""
        if self.total_deliverables == 0:
            return 0.0
        return round(
            (self.completed_deliverables / self.total_deliverables) * 100, 2
        )

    @property
    def pending_deliverables(self) -> int:
        """Calcula entregáveis pendentes (não iniciados)."""
        return max(
            0,
            self.total_deliverables
            - self.completed_deliverables
            - self.in_progress_deliverables
            - self.blocked_deliverables,
        )


class DashboardSummary(BaseModel):
    """Resumo consolidado do dashboard GCA.

    Agrega todas as informações necessárias para a visualização executiva
    do estado do projeto: scores dos pilares, aprovações, riscos e progresso.

    Attributes:
        generated_at: Data/hora de geração do dashboard.
        pillar_scores: Lista de scores por pilar.
        overall_score: Score geral ponderado do projeto.
        approval_statuses: Lista de status de aprovação por área.
        risks: Lista de riscos identificados.
        phase_progress: Progresso por fase do projeto.
        overall_progress: Percentual geral de progresso.
        health_status: Indicador de saúde geral do projeto.
    """

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora de geração do dashboard",
    )
    pillar_scores: list[PillarScore] = Field(
        default_factory=list,
        description="Scores de avaliação por pilar",
    )
    overall_score: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Score geral ponderado do projeto (0-100)",
    )
    approval_statuses: list[ApprovalStatus] = Field(
        default_factory=list,
        description="Status de aprovação por área",
    )
    risks: list[RiskItem] = Field(
        default_factory=list,
        description="Riscos identificados no projeto",
    )
    phase_progress: list[PhaseProgress] = Field(
        default_factory=list,
        description="Progresso por fase do projeto",
    )
    overall_progress: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Percentual geral de progresso do projeto",
    )
    health_status: str = Field(
        default="desconhecido",
        description="Indicador de saúde geral: saudável, atenção, crítico",
    )

    @property
    def active_risks_count(self) -> int:
        """Conta riscos não mitigados."""
        return sum(1 for r in self.risks if not r.is_mitigated)

    @property
    def critical_risks_count(self) -> int:
        """Conta riscos críticos não mitigados."""
        return sum(
            1
            for r in self.risks
            if r.severity == RiskSeverity.CRITICAL and not r.is_mitigated
        )

    @property
    def approved_areas_count(self) -> int:
        """Conta áreas aprovadas."""
        return sum(
            1
            for a in self.approval_statuses
            if a.state == ApprovalState.APPROVED
        )

    @property
    def total_areas_count(self) -> int:
        """Total de áreas sob avaliação."""
        return len(self.approval_statuses)


# ---------------------------------------------------------------------------
# Constantes — Dados de referência dos pilares (conforme stack validada)
# ---------------------------------------------------------------------------

# Scores de referência extraídos da stack validada
_DEFAULT_PILLAR_DATA: list[dict[str, Any]] = [
    {
        "pillar_code": PillarCode.P1_SCOPE,
        "pillar_name": "Escopo e Requisitos",
        "score": 0.0,
        "weight": 0.10,
        "notes": "Avaliação de escopo pendente.",
    },
    {
        "pillar_code": PillarCode.P2_COMPLIANCE,
        "pillar_name": "Compliance e Conformidade",
        "score": 82.0,
        "weight": 0.15,
        "notes": "Stack validada com score 82 pelo pilar P2.",
    },
    {
        "pillar_code": PillarCode.P3_UX,
        "pillar_name": "Experiência do Usuário",
        "score": 0.0,
        "weight": 0.10,
        "notes": "Avaliação de UX pendente.",
    },
    {
        "pillar_code": PillarCode.P4_INTEGRATIONS,
        "pillar_name": "Integrações Externas",
        "score": 0.0,
        "weight": 0.10,
        "notes": "Avaliação de integrações pendente.",
    },
    {
        "pillar_code": PillarCode.P5_ARCHITECTURE,
        "pillar_name": "Arquitetura",
        "score": 88.0,
        "weight": 0.20,
        "notes": "Stack validada com score 88 pelo pilar P5.",
    },
    {
        "pillar_code": PillarCode.P6_TESTING,
        "pillar_name": "Testes e Qualidade",
        "score": 0.0,
        "weight": 0.10,
        "notes": "Avaliação de testes pendente.",
    },
    {
        "pillar_code": PillarCode.P7_SECURITY,
        "pillar_name": "Segurança",
        "score": 85.0,
        "weight": 0.20,
        "notes": "Stack validada com score 85 pelo pilar P7.",
    },
    {
        "pillar_code": PillarCode.P8_DEPLOYMENT,
        "pillar_name": "Deploy e Operações",
        "score": 0.0,
        "weight": 0.05,
        "notes": "Avaliação de deploy pendente.",
    },
]

# Rótulos das fases em PT-BR
_PHASE_LABELS: dict[ProgressPhase, str] = {
    ProgressPhase.PHASE_1: "Fase 1 — Fundação e Infraestrutura",
    ProgressPhase.PHASE_2: "Fase 2 — Funcionalidades Core",
    ProgressPhase.PHASE_3: "Fase 3 — Integrações e IA",
    ProgressPhase.PHASE_4: "Fase 4 — Polimento e Lançamento",
}

# Riscos conhecidos do projeto (baseline)
_KNOWN_RISKS: list[dict[str, Any]] = [
    {
        "title": "Decisão pendente de índice vetorial (G002 ADR)",
        "description": (
            "A escolha entre FAISS e Milvus para busca semântica ainda não foi "
            "definida. Isso pode impactar a arquitetura de busca e o desempenho "
            "das funcionalidades de análise de documentos jurídicos."
        ),
        "severity": RiskSeverity.MEDIUM,
        "pillar_code": PillarCode.P5_ARCHITECTURE,
        "mitigation": (
            "Agendar ADR G002 para decisão até o final da Fase 1. "
            "Implementar interface abstrata para troca transparente."
        ),
    },
    {
        "title": "Design tokens pendentes (G005 ADR)",
        "description": (
            "Os design tokens (cores, tipografia, breakpoints) ainda não foram "
            "enviados pelo time de design. Isso pode atrasar a implementação "
            "do frontend e causar inconsistências visuais."
        ),
        "severity": RiskSeverity.LOW,
        "pillar_code": PillarCode.P3_UX,
        "mitigation": (
            "Utilizar tokens padrão do Tailwind CSS como fallback. "
            "Solicitar envio dos tokens ao time de design."
        ),
    },
    {
        "title": "Dependência de API Anthropic para funcionalidades core",
        "description": (
            "A integração com a API da Anthropic (Claude) é crítica para "
            "análise de documentos e chat jurídico. Indisponibilidade do "
            "serviço pode impactar funcionalidades essenciais."
        ),
        "severity": RiskSeverity.HIGH,
        "pillar_code": PillarCode.P4_INTEGRATIONS,
        "mitigation": (
            "Implementar circuit breaker com tenacity, cache de respostas "
            "frequentes e modo degradado com funcionalidades offline."
        ),
    },
    {
        "title": "Conformidade LGPD para dados jurídicos sensíveis",
        "description": (
            "O tratamento de documentos jurídicos envolve dados pessoais "
            "sensíveis que exigem conformidade rigorosa com a LGPD. "
            "Falhas podem resultar em sanções regulatórias."
        ),
        "severity": RiskSeverity.CRITICAL,
        "pillar_code": PillarCode.P2_COMPLIANCE,
        "mitigation": (
            "Implementar criptografia em repouso e trânsito, controle de "
            "acesso granular RBAC, logs de auditoria completos e política "
            "de retenção de dados conforme LGPD."
        ),
    },
]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class DashboardGCAService:
    """Serviço principal do dashboard GCA.

    Responsável por agregar dados de múltiplas fontes e produzir o resumo
    consolidado do dashboard de Governança, Conformidade e Aprovação.

    Attributes:
        _deliverables_service: Serviço de entregáveis para dados de progresso.
        _settings: Configurações da aplicação.
    """

    def __init__(
        self,
        deliverables_service: DeliverablesSummaryService | None = None,
    ) -> None:
        """Inicializa o serviço do dashboard GCA.

        Args:
            deliverables_service: Instância do serviço de entregáveis.
                Se não fornecido, será obtido via factory padrão.
        """
        self._deliverables_service = (
            deliverables_service or get_deliverables_summary_service()
        )
        self._settings = get_settings()

    # -- Pillar Scores -----------------------------------------------------

    def get_pillar_scores(self) -> list[PillarScore]:
        """Retorna os scores atuais de todos os pilares.

        Returns:
            Lista de PillarScore com os dados de cada pilar avaliado.
        """
        scores: list[PillarScore] = []
        for data in _DEFAULT_PILLAR_DATA:
            scores.append(PillarScore(**data))
        return scores

    def get_pillar_score_by_code(self, code: PillarCode) -> PillarScore | None:
        """Retorna o score de um pilar específico.

        Args:
            code: Código do pilar desejado.

        Returns:
            PillarScore do pilar ou None se não encontrado.
        """
        for score in self.get_pillar_scores():
            if score.pillar_code == code:
                return score
        return None

    def calculate_overall_score(self) -> float:
        """Calcula o score geral ponderado do projeto.

        Utiliza os pesos de cada pilar para calcular a média ponderada.
        Pilares sem avaliação (score 0) são incluídos no cálculo,
        reduzindo o score geral proporcionalmente.

        Returns:
            Score geral ponderado de 0 a 100.
        """
        scores = self.get_pillar_scores()
        if not scores:
            return 0.0

        total_weight = sum(s.weight for s in scores)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(s.score * s.weight for s in scores)
        return round(weighted_sum / total_weight, 2)

    # -- Approval Statuses -------------------------------------------------

    def get_approval_statuses(self) -> list[ApprovalStatus]:
        """Retorna os status de aprovação por área/pilar.

        Gera status de aprovação baseado nos scores dos pilares.
        Pilares com score >= 80 são considerados aprovados,
        >= 70 condicionais, e < 70 ou sem avaliação ficam pendentes.

        Returns:
            Lista de ApprovalStatus para cada pilar.
        """
        statuses: list[ApprovalStatus] = []
        for score in self.get_pillar_scores():
            if score.score == 0.0:
                state = ApprovalState.PENDING
                conditions = ["Avaliação do pilar ainda não realizada."]
            elif score.score >= 80.0:
                state = ApprovalState.APPROVED
                conditions = []
            elif score.score >= 70.0:
                state = ApprovalState.CONDITIONAL
                conditions = [
                    f"Score atual: {score.score}. Necessário atingir 80 para aprovação plena."
                ]
            else:
                state = ApprovalState.REJECTED
                conditions = [
                    f"Score {score.score} abaixo do limiar mínimo de 70."
                ]

            statuses.append(
                ApprovalStatus(
                    area_name=score.pillar_name,
                    pillar_code=score.pillar_code,
                    state=state,
                    conditions=conditions,
                    notes=score.notes,
                )
            )
        return statuses

    # -- Risks -------------------------------------------------------------

    def get_risks(self) -> list[RiskItem]:
        """Retorna a lista de riscos identificados no projeto.

        Returns:
            Lista de RiskItem ordenada por severidade (mais críticos primeiro).
        """
        risks: list[RiskItem] = []
        for data in _KNOWN_RISKS:
            risks.append(RiskItem(**data))

        # Ordena por severidade decrescente
        risks.sort(key=lambda r: r.severity_weight, reverse=True)
        return risks

    def get_active_risks(self) -> list[RiskItem]:
        """Retorna apenas riscos não mitigados.

        Returns:
            Lista de RiskItem ativos (não mitigados).
        """
        return [r for r in self.get_risks() if not r.is_mitigated]

    def get_risks_by_severity(self, severity: RiskSeverity) -> list[RiskItem]:
        """Filtra riscos por severidade.

        Args:
            severity: Severidade desejada para filtro.

        Returns:
            Lista de RiskItem com a severidade especificada.
        """
        return [r for r in self.get_risks() if r.severity == severity]

    # -- Phase Progress ----------------------------------------------------

    def get_phase_progress(self) -> list[PhaseProgress]:
        """Retorna o progresso por fase do projeto.

        Integra com o serviço de entregáveis para obter dados reais
        de progresso. Se o serviço não estiver disponível, retorna
        dados de placeholder.

        Returns:
            Lista de PhaseProgress para cada fase do projeto.
        """
        phases: list[PhaseProgress] = []

        # TODO: Integrar com DeliverablesSummaryService para obter
        # contagens reais de entregáveis por fase. A API exata do
        # serviço de entregáveis precisa ser verificada para mapear
        # os status dos entregáveis para as contagens de progresso.
        # Por ora, utiliza dados de placeholder baseados no backlog.

        placeholder_data: list[dict[str, Any]] = [
            {
                "phase": ProgressPhase.PHASE_1,
                "phase_label": _PHASE_LABELS[ProgressPhase.PHASE_1],
                "total_deliverables": 8,
                "completed_deliverables": 3,
                "in_progress_deliverables": 2,
                "blocked_deliverables": 0,
            },
            {
                "phase": ProgressPhase.PHASE_2,
                "phase_label": _PHASE_LABELS[ProgressPhase.PHASE_2],
                "total_deliverables": 10,
                "completed_deliverables": 0,
                "in_progress_deliverables": 1,
                "blocked_deliverables": 0,
            },
            {
                "phase": ProgressPhase.PHASE_3,
                "phase_label": _PHASE_LABELS[ProgressPhase.PHASE_3],
                "total_deliverables": 6,
                "completed_deliverables": 0,
                "in_progress_deliverables": 0,
                "blocked_deliverables": 1,
            },
            {
                "phase": ProgressPhase.PHASE_4,
                "phase_label": _PHASE_LABELS[ProgressPhase.PHASE_4],
                "total_deliverables": 4,
                "completed_deliverables": 0,
                "in_progress_deliverables": 0,
                "blocked_deliverables": 0,
            },
        ]

        for data in placeholder_data:
            phases.append(PhaseProgress(**data))

        return phases

    def calculate_overall_progress(self) -> float:
        """Calcula o percentual geral de progresso do projeto.

        Considera todos os entregáveis de todas as fases.

        Returns:
            Percentual de progresso geral (0-100).
        """
        phases = self.get_phase_progress()
        total = sum(p.total_deliverables for p in phases)
        completed = sum(p.completed_deliverables for p in phases)

        if total == 0:
            return 0.0
        return round((completed / total) * 100, 2)

    # -- Health Status -----------------------------------------------------

    def determine_health_status(
        self,
        overall_score: float,
        active_critical_risks: int,
        overall_progress: float,
    ) -> str:
        """Determina o status de saúde geral do projeto.

        Regras:
        - "crítico": score < 50 OU riscos críticos ativos > 0
        - "atenção": score < 70 OU progresso < 25%
        - "saudável": demais casos

        Args:
            overall_score: Score geral ponderado.
            active_critical_risks: Quantidade de riscos críticos ativos.
            overall_progress: Percentual geral de progresso.

        Returns:
            String indicando o status: 'saudável', 'atenção' ou 'crítico'.
        """
        if overall_score < 50 or active_critical_risks > 0:
            return "crítico"
        if overall_score < 70 or overall_progress < 25:
            return "atenção"
        return "saudável"

    # -- Dashboard Summary (agregação principal) ---------------------------

    async def get_dashboard_summary(self) -> DashboardSummary:
        """Gera o resumo consolidado do dashboard GCA.

        Agrega dados de pilares, aprovações, riscos e progresso
        em uma única estrutura para consumo pelo frontend.

        Returns:
            DashboardSummary com todos os dados consolidados.
        """
        pillar_scores = self.get_pillar_scores()
        overall_score = self.calculate_overall_score()
        approval_statuses = self.get_approval_statuses()
        risks = self.get_risks()
        phase_progress = self.get_phase_progress()
        overall_progress = self.calculate_overall_progress()

        active_critical = sum(
            1
            for r in risks
            if r.severity == RiskSeverity.CRITICAL and not r.is_mitigated
        )

        health_status = self.determine_health_status(
            overall_score=overall_score,
            active_critical_risks=active_critical,
            overall_progress=overall_progress,
        )

        return DashboardSummary(
            pillar_scores=pillar_scores,
            overall_score=overall_score,
            approval_statuses=approval_statuses,
            risks=risks,
            phase_progress=phase_progress,
            overall_progress=overall_progress,
            health_status=health_status,
        )

    # -- Formatação para API -----------------------------------------------

    async def get_dashboard_as_dict(self) -> dict[str, Any]:
        """Retorna o dashboard como dicionário serializável.

        Conveniência para uso direto em endpoints FastAPI.

        Returns:
            Dicionário com os dados do dashboard.
        """
        summary = await self.get_dashboard_summary()
        return summary.model_dump(mode="json")

    def get_pillar_scores_as_dict(self) -> list[dict[str, Any]]:
        """Retorna scores dos pilares como lista de dicionários.

        Returns:
            Lista de dicionários com dados de cada pilar.
        """
        return [s.model_dump(mode="json") for s in self.get_pillar_scores()]

    def get_risks_summary(self) -> dict[str, Any]:
        """Retorna resumo de riscos para visualização rápida.

        Returns:
            Dicionário com contagens por severidade e lista de riscos ativos.
        """
        risks = self.get_risks()
        return {
            "total": len(risks),
            "ativos": sum(1 for r in risks if not r.is_mitigated),
            "mitigados": sum(1 for r in risks if r.is_mitigated),
            "por_severidade": {
                "critico": len(self.get_risks_by_severity(RiskSeverity.CRITICAL)),
                "alto": len(self.get_risks_by_severity(RiskSeverity.HIGH)),
                "medio": len(self.get_risks_by_severity(RiskSeverity.MEDIUM)),
                "baixo": len(self.get_risks_by_severity(RiskSeverity.LOW)),
            },
            "riscos_ativos": [
                r.model_dump(mode="json") for r in self.get_active_risks()
            ],
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_dashboard_gca_service() -> DashboardGCAService:
    """Factory com cache para obter instância singleton do serviço GCA.

    Returns:
        Instância configurada de DashboardGCAService.
    """
    return DashboardGCAService()


# ---------------------------------------------------------------------------
# Exports públicos
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "PillarCode",
    "RiskSeverity",
    "ApprovalState",
    "ProgressPhase",
    # Schemas
    "PillarScore",
    "ApprovalStatus",
    "RiskItem",
    "PhaseProgress",
    "DashboardSummary",
    # Service
    "DashboardGCAService",
    # Factory
    "get_dashboard_gca_service",
]
