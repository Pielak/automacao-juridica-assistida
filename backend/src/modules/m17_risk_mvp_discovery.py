"""Módulo backlog #17: Risco mitigação MVP — workshops discovery, MoSCoW, user stories detalhadas.

Este módulo fornece ferramentas para identificação, avaliação e mitigação de riscos
no contexto de MVP para automação jurídica. Inclui funcionalidades para:

- Workshops de discovery com templates estruturados
- Matriz de riscos (probabilidade × impacto)
- Planos de mitigação com responsáveis e prazos
- Integração com priorização MoSCoW e user stories (m03)
- Rastreabilidade entre riscos e user stories afetadas
- Geração de relatórios de risco consolidados

Exemplo de uso:
    from backend.src.modules.m17_risk_mvp_discovery import (
        RiskService,
        RiskCategory,
        RiskProbability,
        RiskImpact,
        RiskItem,
        MitigationPlan,
        DiscoveryWorkshop,
        WorkshopActivity,
        RiskMatrix,
        RiskAssessmentResult,
    )

    # Criar serviço de riscos
    service = RiskService()

    # Registrar um risco
    risk = service.create_risk(
        title="Indisponibilidade da API DataJud",
        description="API do DataJud pode ficar fora do ar em horários de pico",
        category=RiskCategory.TECHNICAL,
        probability=RiskProbability.HIGH,
        impact=RiskImpact.HIGH,
        affected_story_ids=["US-001", "US-005"],
    )

    # Criar plano de mitigação
    plan = service.create_mitigation_plan(
        risk_id=risk.id,
        strategy="Implementar cache local e retry com backoff exponencial",
        owner="Time Backend",
    )

    # Gerar matriz de riscos
    matrix = service.generate_risk_matrix()
"""

from __future__ import annotations

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Importação do módulo peer para integração com user stories e MoSCoW
from backend.src.modules.m03_mvp_user_stories_definition import (
    UserStoryService,
    MoscowPriority,
    UserStory,
    AcceptanceCriterion,
    MVPDefinition,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RiskCategory(str, Enum):
    """Categorias de risco para projetos de automação jurídica."""

    TECHNICAL = "technical"
    LEGAL_COMPLIANCE = "legal_compliance"
    SECURITY = "security"
    INTEGRATION = "integration"
    DATA_PRIVACY = "data_privacy"
    PERFORMANCE = "performance"
    BUSINESS = "business"
    OPERATIONAL = "operational"
    REGULATORY = "regulatory"
    RESOURCE = "resource"


class RiskProbability(str, Enum):
    """Níveis de probabilidade de ocorrência do risco."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class RiskImpact(str, Enum):
    """Níveis de impacto caso o risco se materialize."""

    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskStatus(str, Enum):
    """Status do ciclo de vida de um risco."""

    IDENTIFIED = "identified"
    ASSESSED = "assessed"
    MITIGATING = "mitigating"
    MITIGATED = "mitigated"
    ACCEPTED = "accepted"
    CLOSED = "closed"
    MATERIALIZED = "materialized"


class MitigationStrategy(str, Enum):
    """Estratégias clássicas de tratamento de risco."""

    AVOID = "avoid"
    TRANSFER = "transfer"
    MITIGATE = "mitigate"
    ACCEPT = "accept"


class WorkshopPhase(str, Enum):
    """Fases de um workshop de discovery."""

    IDEATION = "ideation"
    RISK_IDENTIFICATION = "risk_identification"
    PRIORITIZATION = "prioritization"
    MITIGATION_PLANNING = "mitigation_planning"
    REVIEW = "review"


class ActivityType(str, Enum):
    """Tipos de atividade dentro de um workshop."""

    BRAINSTORMING = "brainstorming"
    DOT_VOTING = "dot_voting"
    RISK_STORMING = "risk_storming"
    MOSCOW_RANKING = "moscow_ranking"
    STORY_MAPPING = "story_mapping"
    IMPACT_MAPPING = "impact_mapping"
    RETROSPECTIVE = "retrospective"
    OPEN_DISCUSSION = "open_discussion"


class RiskLevel(str, Enum):
    """Nível de risco calculado (probabilidade × impacto)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Constantes e mapeamentos
# ---------------------------------------------------------------------------

# Pesos numéricos para cálculo da matriz de riscos
PROBABILITY_WEIGHTS: dict[RiskProbability, int] = {
    RiskProbability.VERY_LOW: 1,
    RiskProbability.LOW: 2,
    RiskProbability.MEDIUM: 3,
    RiskProbability.HIGH: 4,
    RiskProbability.VERY_HIGH: 5,
}

IMPACT_WEIGHTS: dict[RiskImpact, int] = {
    RiskImpact.NEGLIGIBLE: 1,
    RiskImpact.LOW: 2,
    RiskImpact.MEDIUM: 3,
    RiskImpact.HIGH: 4,
    RiskImpact.CRITICAL: 5,
}

# Limites para classificação do nível de risco (score = prob × impacto)
RISK_LEVEL_THRESHOLDS: dict[RiskLevel, tuple[int, int]] = {
    RiskLevel.LOW: (1, 4),
    RiskLevel.MEDIUM: (5, 9),
    RiskLevel.HIGH: (10, 16),
    RiskLevel.CRITICAL: (17, 25),
}

# Templates de riscos comuns em projetos de automação jurídica
JURIDICAL_RISK_TEMPLATES: list[dict[str, str]] = [
    {
        "title": "Indisponibilidade da API DataJud",
        "description": "A API do DataJud pode apresentar instabilidade ou indisponibilidade, "
        "impactando consultas processuais em tempo real.",
        "category": RiskCategory.INTEGRATION,
        "suggested_mitigation": "Implementar cache local, retry com backoff exponencial "
        "e fallback para dados em cache.",
    },
    {
        "title": "Vazamento de dados sensíveis (LGPD)",
        "description": "Dados pessoais de partes processuais podem ser expostos "
        "por falha de controle de acesso ou logging inadequado.",
        "category": RiskCategory.DATA_PRIVACY,
        "suggested_mitigation": "Criptografia em repouso e trânsito, mascaramento de PII em logs, "
        "auditoria de acesso e revisão periódica de permissões RBAC.",
    },
    {
        "title": "Alucinação do modelo de IA em análise jurídica",
        "description": "O modelo Claude pode gerar informações jurídicas incorretas "
        "ou inventar referências legislativas inexistentes.",
        "category": RiskCategory.TECHNICAL,
        "suggested_mitigation": "Implementar validação cruzada com base legislativa, "
        "exigir citação de fontes verificáveis e revisão humana obrigatória.",
    },
    {
        "title": "Não conformidade com regulamentações da OAB",
        "description": "Funcionalidades de automação podem violar normas do "
        "Código de Ética da OAB sobre exercício da advocacia.",
        "category": RiskCategory.REGULATORY,
        "suggested_mitigation": "Consultoria jurídica especializada, disclaimers claros "
        "de que a ferramenta é assistiva e não substitui o advogado.",
    },
    {
        "title": "Sobrecarga de processamento assíncrono",
        "description": "Filas Celery podem acumular tarefas em picos de uso, "
        "causando atrasos na análise de documentos.",
        "category": RiskCategory.PERFORMANCE,
        "suggested_mitigation": "Auto-scaling de workers, monitoramento de filas, "
        "limites de concorrência e priorização de tarefas.",
    },
    {
        "title": "Falha na autenticação MFA",
        "description": "Problemas com TOTP ou perda de dispositivo podem "
        "impedir acesso legítimo ao sistema.",
        "category": RiskCategory.SECURITY,
        "suggested_mitigation": "Códigos de recuperação, fluxo de reset via e-mail verificado, "
        "suporte a múltiplos dispositivos MFA.",
    },
]


# ---------------------------------------------------------------------------
# Modelos de dados (Pydantic v2)
# ---------------------------------------------------------------------------


def _generate_id(prefix: str = "RISK") -> str:
    """Gera um identificador único com prefixo."""
    short_uuid = uuid.uuid4().hex[:8].upper()
    return f"{prefix}-{short_uuid}"


class MitigationAction(BaseModel):
    """Ação específica dentro de um plano de mitigação."""

    id: str = Field(default_factory=lambda: _generate_id("ACT"))
    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Descrição da ação de mitigação.",
    )
    owner: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Responsável pela execução da ação.",
    )
    due_date: Optional[date] = Field(
        default=None,
        description="Data limite para conclusão da ação.",
    )
    completed: bool = Field(
        default=False,
        description="Indica se a ação foi concluída.",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Data/hora de conclusão da ação.",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Observações adicionais sobre a ação.",
    )


class MitigationPlan(BaseModel):
    """Plano de mitigação associado a um risco."""

    id: str = Field(default_factory=lambda: _generate_id("MIT"))
    risk_id: str = Field(
        ...,
        description="ID do risco ao qual este plano se refere.",
    )
    strategy: MitigationStrategy = Field(
        default=MitigationStrategy.MITIGATE,
        description="Estratégia de tratamento do risco.",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Descrição geral do plano de mitigação.",
    )
    owner: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Responsável principal pelo plano.",
    )
    actions: list[MitigationAction] = Field(
        default_factory=list,
        description="Lista de ações concretas do plano.",
    )
    residual_probability: Optional[RiskProbability] = Field(
        default=None,
        description="Probabilidade residual após mitigação.",
    )
    residual_impact: Optional[RiskImpact] = Field(
        default=None,
        description="Impacto residual após mitigação.",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data de criação do plano.",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Data da última atualização.",
    )

    @property
    def completion_percentage(self) -> float:
        """Calcula o percentual de conclusão das ações do plano."""
        if not self.actions:
            return 0.0
        completed_count = sum(1 for a in self.actions if a.completed)
        return round((completed_count / len(self.actions)) * 100, 1)

    @property
    def residual_risk_score(self) -> Optional[int]:
        """Calcula o score de risco residual, se disponível."""
        if self.residual_probability and self.residual_impact:
            return (
                PROBABILITY_WEIGHTS[self.residual_probability]
                * IMPACT_WEIGHTS[self.residual_impact]
            )
        return None


class RiskItem(BaseModel):
    """Representa um risco identificado no projeto."""

    id: str = Field(default_factory=lambda: _generate_id("RISK"))
    title: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Título conciso do risco.",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Descrição detalhada do risco e seu contexto.",
    )
    category: RiskCategory = Field(
        ...,
        description="Categoria do risco.",
    )
    probability: RiskProbability = Field(
        ...,
        description="Probabilidade de ocorrência.",
    )
    impact: RiskImpact = Field(
        ...,
        description="Impacto caso o risco se materialize.",
    )
    status: RiskStatus = Field(
        default=RiskStatus.IDENTIFIED,
        description="Status atual do risco.",
    )
    affected_story_ids: list[str] = Field(
        default_factory=list,
        description="IDs das user stories afetadas por este risco.",
    )
    affected_moscow_priorities: list[MoscowPriority] = Field(
        default_factory=list,
        description="Prioridades MoSCoW das stories afetadas.",
    )
    mitigation_plans: list[MitigationPlan] = Field(
        default_factory=list,
        description="Planos de mitigação associados.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags para categorização adicional.",
    )
    identified_by: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Pessoa ou equipe que identificou o risco.",
    )
    identified_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data de identificação do risco.",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Data da última atualização.",
    )
    workshop_id: Optional[str] = Field(
        default=None,
        description="ID do workshop onde o risco foi identificado.",
    )

    @property
    def risk_score(self) -> int:
        """Calcula o score de risco (probabilidade × impacto)."""
        return PROBABILITY_WEIGHTS[self.probability] * IMPACT_WEIGHTS[self.impact]

    @property
    def risk_level(self) -> RiskLevel:
        """Determina o nível de risco com base no score."""
        score = self.risk_score
        for level, (min_val, max_val) in RISK_LEVEL_THRESHOLDS.items():
            if min_val <= score <= max_val:
                return level
        return RiskLevel.CRITICAL

    @property
    def has_mitigation(self) -> bool:
        """Verifica se o risco possui ao menos um plano de mitigação."""
        return len(self.mitigation_plans) > 0


class RiskAssessmentResult(BaseModel):
    """Resultado consolidado de uma avaliação de riscos."""

    total_risks: int = Field(default=0, description="Total de riscos identificados.")
    critical_count: int = Field(default=0, description="Quantidade de riscos críticos.")
    high_count: int = Field(default=0, description="Quantidade de riscos altos.")
    medium_count: int = Field(default=0, description="Quantidade de riscos médios.")
    low_count: int = Field(default=0, description="Quantidade de riscos baixos.")
    unmitigated_count: int = Field(
        default=0, description="Riscos sem plano de mitigação."
    )
    average_risk_score: float = Field(
        default=0.0, description="Score médio de risco."
    )
    top_risks: list[RiskItem] = Field(
        default_factory=list,
        description="Top riscos ordenados por score.",
    )
    risks_by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Distribuição de riscos por categoria.",
    )
    moscow_impact_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Quantidade de riscos por prioridade MoSCoW afetada.",
    )
    assessed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data/hora da avaliação.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recomendações geradas pela avaliação.",
    )


class RiskMatrixCell(BaseModel):
    """Célula individual da matriz de riscos."""

    probability: RiskProbability
    impact: RiskImpact
    risk_level: RiskLevel
    risk_ids: list[str] = Field(default_factory=list)
    count: int = Field(default=0)


class RiskMatrix(BaseModel):
    """Matriz de riscos completa (probabilidade × impacto)."""

    cells: list[RiskMatrixCell] = Field(
        default_factory=list,
        description="Células da matriz com riscos mapeados.",
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data/hora de geração da matriz.",
    )
    total_risks: int = Field(default=0, description="Total de riscos na matriz.")


class WorkshopParticipant(BaseModel):
    """Participante de um workshop de discovery."""

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Nome do participante.",
    )
    role: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Papel/cargo do participante.",
    )
    email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="E-mail do participante.",
    )


class WorkshopActivity(BaseModel):
    """Atividade dentro de um workshop de discovery."""

    id: str = Field(default_factory=lambda: _generate_id("WACT"))
    phase: WorkshopPhase = Field(
        ...,
        description="Fase do workshop à qual a atividade pertence.",
    )
    activity_type: ActivityType = Field(
        ...,
        description="Tipo de atividade.",
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Título da atividade.",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Descrição detalhada da atividade.",
    )
    duration_minutes: int = Field(
        default=30,
        ge=5,
        le=480,
        description="Duração estimada em minutos.",
    )
    outputs: list[str] = Field(
        default_factory=list,
        description="Artefatos/resultados esperados da atividade.",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Notas e observações da atividade.",
    )
    identified_risk_ids: list[str] = Field(
        default_factory=list,
        description="IDs dos riscos identificados nesta atividade.",
    )
    identified_story_ids: list[str] = Field(
        default_factory=list,
        description="IDs das user stories identificadas/refinadas.",
    )


class DiscoveryWorkshop(BaseModel):
    """Workshop de discovery para identificação e mitigação de riscos MVP."""

    id: str = Field(default_factory=lambda: _generate_id("WS"))
    title: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Título do workshop.",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Descrição e objetivos do workshop.",
    )
    scheduled_date: Optional[date] = Field(
        default=None,
        description="Data agendada para o workshop.",
    )
    facilitator: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Nome do facilitador do workshop.",
    )
    participants: list[WorkshopParticipant] = Field(
        default_factory=list,
        description="Lista de participantes.",
    )
    activities: list[WorkshopActivity] = Field(
        default_factory=list,
        description="Atividades planejadas/realizadas.",
    )
    identified_risks: list[str] = Field(
        default_factory=list,
        description="IDs dos riscos identificados durante o workshop.",
    )
    identified_stories: list[str] = Field(
        default_factory=list,
        description="IDs das user stories identificadas/refinadas.",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data de criação do workshop.",
    )
    completed: bool = Field(
        default=False,
        description="Indica se o workshop foi concluído.",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Data/hora de conclusão do workshop.",
    )
    summary: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Resumo executivo do workshop.",
    )

    @property
    def total_duration_minutes(self) -> int:
        """Calcula a duração total estimada do workshop em minutos."""
        return sum(a.duration_minutes for a in self.activities)

    @property
    def total_duration_hours(self) -> float:
        """Calcula a duração total estimada do workshop em horas."""
        return round(self.total_duration_minutes / 60, 1)


# ---------------------------------------------------------------------------
# Serviço principal
# ---------------------------------------------------------------------------


class RiskService:
    """Serviço para gerenciamento de riscos, workshops de discovery e integração MoSCoW.

    Centraliza operações de criação, avaliação e mitigação de riscos,
    além de gerenciar workshops de discovery e gerar relatórios consolidados.
    """

    def __init__(
        self,
        user_story_service: Optional[UserStoryService] = None,
    ) -> None:
        """Inicializa o serviço de riscos.

        Args:
            user_story_service: Instância opcional do serviço de user stories
                para integração com priorização MoSCoW e rastreabilidade.
        """
        self._risks: dict[str, RiskItem] = {}
        self._workshops: dict[str, DiscoveryWorkshop] = {}
        self._user_story_service = user_story_service

    # -- Gestão de Riscos ---------------------------------------------------

    def create_risk(
        self,
        title: str,
        description: str,
        category: RiskCategory,
        probability: RiskProbability,
        impact: RiskImpact,
        affected_story_ids: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        identified_by: Optional[str] = None,
        workshop_id: Optional[str] = None,
    ) -> RiskItem:
        """Cria e registra um novo risco.

        Args:
            title: Título conciso do risco.
            description: Descrição detalhada.
            category: Categoria do risco.
            probability: Probabilidade de ocorrência.
            impact: Impacto caso ocorra.
            affected_story_ids: IDs das user stories afetadas.
            tags: Tags para categorização.
            identified_by: Quem identificou o risco.
            workshop_id: ID do workshop de origem.

        Returns:
            RiskItem criado e registrado.

        Raises:
            ValueError: Se o workshop_id informado não existir.
        """
        if workshop_id and workshop_id not in self._workshops:
            raise ValueError(
                f"Workshop com ID '{workshop_id}' não encontrado. "
                "Verifique o identificador informado."
            )

        # Resolver prioridades MoSCoW das stories afetadas
        moscow_priorities: list[MoscowPriority] = []
        if affected_story_ids and self._user_story_service:
            moscow_priorities = self._resolve_moscow_priorities(affected_story_ids)

        risk = RiskItem(
            title=title,
            description=description,
            category=category,
            probability=probability,
            impact=impact,
            affected_story_ids=affected_story_ids or [],
            affected_moscow_priorities=moscow_priorities,
            tags=tags or [],
            identified_by=identified_by,
            workshop_id=workshop_id,
        )

        self._risks[risk.id] = risk

        # Vincular ao workshop se aplicável
        if workshop_id and workshop_id in self._workshops:
            ws = self._workshops[workshop_id]
            if risk.id not in ws.identified_risks:
                ws.identified_risks.append(risk.id)

        return risk

    def get_risk(self, risk_id: str) -> Optional[RiskItem]:
        """Busca um risco pelo ID.

        Args:
            risk_id: Identificador do risco.

        Returns:
            RiskItem se encontrado, None caso contrário.
        """
        return self._risks.get(risk_id)

    def list_risks(
        self,
        category: Optional[RiskCategory] = None,
        status: Optional[RiskStatus] = None,
        min_level: Optional[RiskLevel] = None,
    ) -> list[RiskItem]:
        """Lista riscos com filtros opcionais.

        Args:
            category: Filtrar por categoria.
            status: Filtrar por status.
            min_level: Nível mínimo de risco para inclusão.

        Returns:
            Lista de riscos filtrados, ordenados por score decrescente.
        """
        risks = list(self._risks.values())

        if category:
            risks = [r for r in risks if r.category == category]

        if status:
            risks = [r for r in risks if r.status == status]

        if min_level:
            level_order = [
                RiskLevel.LOW,
                RiskLevel.MEDIUM,
                RiskLevel.HIGH,
                RiskLevel.CRITICAL,
            ]
            min_idx = level_order.index(min_level)
            risks = [
                r for r in risks if level_order.index(r.risk_level) >= min_idx
            ]

        # Ordenar por score decrescente
        risks.sort(key=lambda r: r.risk_score, reverse=True)
        return risks

    def update_risk_status(
        self,
        risk_id: str,
        new_status: RiskStatus,
    ) -> RiskItem:
        """Atualiza o status de um risco.

        Args:
            risk_id: ID do risco.
            new_status: Novo status.

        Returns:
            RiskItem atualizado.

        Raises:
            ValueError: Se o risco não for encontrado.
        """
        risk = self._risks.get(risk_id)
        if not risk:
            raise ValueError(
                f"Risco com ID '{risk_id}' não encontrado."
            )

        risk.status = new_status
        risk.updated_at = datetime.utcnow()
        return risk

    def delete_risk(self, risk_id: str) -> bool:
        """Remove um risco do registro.

        Args:
            risk_id: ID do risco a remover.

        Returns:
            True se removido, False se não encontrado.
        """
        if risk_id in self._risks:
            del self._risks[risk_id]
            return True
        return False

    # -- Planos de Mitigação ------------------------------------------------

    def create_mitigation_plan(
        self,
        risk_id: str,
        description: str,
        owner: str,
        strategy: MitigationStrategy = MitigationStrategy.MITIGATE,
        actions: Optional[list[dict]] = None,
        residual_probability: Optional[RiskProbability] = None,
        residual_impact: Optional[RiskImpact] = None,
    ) -> MitigationPlan:
        """Cria um plano de mitigação para um risco existente.

        Args:
            risk_id: ID do risco alvo.
            description: Descrição do plano.
            owner: Responsável principal.
            strategy: Estratégia de tratamento.
            actions: Lista de dicts com dados das ações.
            residual_probability: Probabilidade residual esperada.
            residual_impact: Impacto residual esperado.

        Returns:
            MitigationPlan criado e vinculado ao risco.

        Raises:
            ValueError: Se o risco não for encontrado.
        """
        risk = self._risks.get(risk_id)
        if not risk:
            raise ValueError(
                f"Risco com ID '{risk_id}' não encontrado. "
                "Não é possível criar plano de mitigação."
            )

        mitigation_actions = []
        if actions:
            for action_data in actions:
                mitigation_actions.append(MitigationAction(**action_data))

        plan = MitigationPlan(
            risk_id=risk_id,
            strategy=strategy,
            description=description,
            owner=owner,
            actions=mitigation_actions,
            residual_probability=residual_probability,
            residual_impact=residual_impact,
        )

        risk.mitigation_plans.append(plan)
        risk.status = RiskStatus.MITIGATING
        risk.updated_at = datetime.utcnow()

        return plan

    def complete_mitigation_action(
        self,
        risk_id: str,
        plan_id: str,
        action_id: str,
        notes: Optional[str] = None,
    ) -> MitigationAction:
        """Marca uma ação de mitigação como concluída.

        Args:
            risk_id: ID do risco.
            plan_id: ID do plano de mitigação.
            action_id: ID da ação.
            notes: Observações sobre a conclusão.

        Returns:
            MitigationAction atualizada.

        Raises:
            ValueError: Se risco, plano ou ação não forem encontrados.
        """
        risk = self._risks.get(risk_id)
        if not risk:
            raise ValueError(f"Risco com ID '{risk_id}' não encontrado.")

        plan = next(
            (p for p in risk.mitigation_plans if p.id == plan_id),
            None,
        )
        if not plan:
            raise ValueError(
                f"Plano de mitigação com ID '{plan_id}' não encontrado "
                f"no risco '{risk_id}'."
            )

        action = next(
            (a for a in plan.actions if a.id == action_id),
            None,
        )
        if not action:
            raise ValueError(
                f"Ação com ID '{action_id}' não encontrada "
                f"no plano '{plan_id}'."
            )

        action.completed = True
        action.completed_at = datetime.utcnow()
        if notes:
            action.notes = notes

        plan.updated_at = datetime.utcnow()

        # Verificar se todas as ações foram concluídas
        if plan.completion_percentage == 100.0:
            risk.status = RiskStatus.MITIGATED
            risk.updated_at = datetime.utcnow()

        return action

    # -- Workshops de Discovery ---------------------------------------------

    def create_workshop(
        self,
        title: str,
        description: Optional[str] = None,
        scheduled_date: Optional[date] = None,
        facilitator: Optional[str] = None,
        participants: Optional[list[dict]] = None,
    ) -> DiscoveryWorkshop:
        """Cria um novo workshop de discovery.

        Args:
            title: Título do workshop.
            description: Descrição e objetivos.
            scheduled_date: Data agendada.
            facilitator: Nome do facilitador.
            participants: Lista de dicts com dados dos participantes.

        Returns:
            DiscoveryWorkshop criado.
        """
        workshop_participants = []
        if participants:
            for p_data in participants:
                workshop_participants.append(WorkshopParticipant(**p_data))

        workshop = DiscoveryWorkshop(
            title=title,
            description=description,
            scheduled_date=scheduled_date,
            facilitator=facilitator,
            participants=workshop_participants,
        )

        self._workshops[workshop.id] = workshop
        return workshop

    def get_workshop(self, workshop_id: str) -> Optional[DiscoveryWorkshop]:
        """Busca um workshop pelo ID.

        Args:
            workshop_id: Identificador do workshop.

        Returns:
            DiscoveryWorkshop se encontrado, None caso contrário.
        """
        return self._workshops.get(workshop_id)

    def list_workshops(
        self,
        completed_only: bool = False,
    ) -> list[DiscoveryWorkshop]:
        """Lista workshops registrados.

        Args:
            completed_only: Se True, retorna apenas workshops concluídos.

        Returns:
            Lista de workshops.
        """
        workshops = list(self._workshops.values())
        if completed_only:
            workshops = [w for w in workshops if w.completed]
        return workshops

    def add_workshop_activity(
        self,
        workshop_id: str,
        phase: WorkshopPhase,
        activity_type: ActivityType,
        title: str,
        description: Optional[str] = None,
        duration_minutes: int = 30,
        outputs: Optional[list[str]] = None,
    ) -> WorkshopActivity:
        """Adiciona uma atividade a um workshop.

        Args:
            workshop_id: ID do workshop.
            phase: Fase do workshop.
            activity_type: Tipo de atividade.
            title: Título da atividade.
            description: Descrição detalhada.
            duration_minutes: Duração estimada em minutos.
            outputs: Artefatos esperados.

        Returns:
            WorkshopActivity criada.

        Raises:
            ValueError: Se o workshop não for encontrado.
        """
        workshop = self._workshops.get(workshop_id)
        if not workshop:
            raise ValueError(
                f"Workshop com ID '{workshop_id}' não encontrado."
            )

        activity = WorkshopActivity(
            phase=phase,
            activity_type=activity_type,
            title=title,
            description=description,
            duration_minutes=duration_minutes,
            outputs=outputs or [],
        )

        workshop.activities.append(activity)
        return activity

    def complete_workshop(
        self,
        workshop_id: str,
        summary: Optional[str] = None,
    ) -> DiscoveryWorkshop:
        """Marca um workshop como concluído.

        Args:
            workshop_id: ID do workshop.
            summary: Resumo executivo do workshop.

        Returns:
            DiscoveryWorkshop atualizado.

        Raises:
            ValueError: Se o workshop não for encontrado.
        """
        workshop = self._workshops.get(workshop_id)
        if not workshop:
            raise ValueError(
                f"Workshop com ID '{workshop_id}' não encontrado."
            )

        workshop.completed = True
        workshop.completed_at = datetime.utcnow()
        if summary:
            workshop.summary = summary

        return workshop

    def create_discovery_workshop_from_template(
        self,
        title: str,
        facilitator: Optional[str] = None,
        participants: Optional[list[dict]] = None,
        scheduled_date: Optional[date] = None,
    ) -> DiscoveryWorkshop:
        """Cria um workshop de discovery com atividades pré-configuradas.

        Gera um workshop completo com as fases padrão de discovery
        para mitigação de riscos MVP em projetos de automação jurídica.

        Args:
            title: Título do workshop.
            facilitator: Nome do facilitador.
            participants: Lista de participantes.
            scheduled_date: Data agendada.

        Returns:
            DiscoveryWorkshop com atividades template.
        """
        workshop = self.create_workshop(
            title=title,
            description=(
                "Workshop de discovery para identificação e mitigação de riscos "
                "do MVP de automação jurídica. Inclui sessões de brainstorming, "
                "risk storming, priorização MoSCoW e planejamento de mitigação."
            ),
            scheduled_date=scheduled_date,
            facilitator=facilitator,
            participants=participants,
        )

        # Fase 1: Ideação
        self.add_workshop_activity(
            workshop_id=workshop.id,
            phase=WorkshopPhase.IDEATION,
            activity_type=ActivityType.BRAINSTORMING,
            title="Brainstorming de funcionalidades MVP",
            description=(
                "Sessão aberta para identificação de funcionalidades essenciais "
                "do MVP de automação jurídica."
            ),
            duration_minutes=45,
            outputs=["Lista de funcionalidades candidatas", "Mapa de dependências"],
        )

        self.add_workshop_activity(
            workshop_id=workshop.id,
            phase=WorkshopPhase.IDEATION,
            activity_type=ActivityType.STORY_MAPPING,
            title="Mapeamento de user stories",
            description=(
                "Estruturação das funcionalidades em user stories "
                "com critérios de aceite preliminares."
            ),
            duration_minutes=60,
            outputs=["User story map", "Épicos identificados"],
        )

        # Fase 2: Identificação de riscos
        self.add_workshop_activity(
            workshop_id=workshop.id,
            phase=WorkshopPhase.RISK_IDENTIFICATION,
            activity_type=ActivityType.RISK_STORMING,
            title="Risk Storming — riscos técnicos e de integração",
            description=(
                "Identificação de riscos técnicos: API DataJud, modelo IA, "
                "performance, segurança e infraestrutura."
            ),
            duration_minutes=45,
            outputs=["Lista de riscos técnicos", "Categorização preliminar"],
        )

        self.add_workshop_activity(
            workshop_id=workshop.id,
            phase=WorkshopPhase.RISK_IDENTIFICATION,
            activity_type=ActivityType.RISK_STORMING,
            title="Risk Storming — riscos regulatórios e de compliance",
            description=(
                "Identificação de riscos de compliance: LGPD, OAB, "
                "regulamentações setoriais e requisitos legais."
            ),
            duration_minutes=45,
            outputs=["Lista de riscos regulatórios", "Requisitos de compliance"],
        )

        # Fase 3: Priorização
        self.add_workshop_activity(
            workshop_id=workshop.id,
            phase=WorkshopPhase.PRIORITIZATION,
            activity_type=ActivityType.DOT_VOTING,
            title="Votação de severidade dos riscos",
            description=(
                "Votação coletiva para classificar probabilidade e impacto "
                "de cada risco identificado."
            ),
            duration_minutes=30,
            outputs=["Matriz de riscos preenchida", "Ranking de prioridade"],
        )

        self.add_workshop_activity(
            workshop_id=workshop.id,
            phase=WorkshopPhase.PRIORITIZATION,
            activity_type=ActivityType.MOSCOW_RANKING,
            title="Priorização MoSCoW das user stories",
            description=(
                "Classificação das user stories em Must/Should/Could/Won't "
                "considerando os riscos identificados."
            ),
            duration_minutes=45,
            outputs=["Backlog priorizado MoSCoW", "Escopo MVP definido"],
        )

        # Fase 4: Planejamento de mitigação
        self.add_workshop_activity(
            workshop_id=workshop.id,
            phase=WorkshopPhase.MITIGATION_PLANNING,
            activity_type=ActivityType.OPEN_DISCUSSION,
            title="Definição de planos de mitigação",
            description=(
                "Elaboração de planos de mitigação para os riscos "
                "de nível alto e crítico."
            ),
            duration_minutes=60,
            outputs=[
                "Planos de mitigação documentados",
                "Responsáveis definidos",
                "Prazos estabelecidos",
            ],
        )

        # Fase 5: Revisão
        self.add_workshop_activity(
            workshop_id=workshop.id,
            phase=WorkshopPhase.REVIEW,
            activity_type=ActivityType.RETROSPECTIVE,
            title="Revisão e próximos passos",
            description=(
                "Consolidação dos resultados, validação do escopo MVP "
                "e definição de ações imediatas."
            ),
            duration_minutes=30,
            outputs=[
                "Resumo executivo",
                "Lista de ações imediatas",
                "Cronograma de acompanhamento",
            ],
        )

        return workshop

    # -- Riscos a partir de templates jurídicos -----------------------------

    def create_risks_from_templates(
        self,
        probability: RiskProbability = RiskProbability.MEDIUM,
        impact: RiskImpact = RiskImpact.HIGH,
        workshop_id: Optional[str] = None,
        identified_by: Optional[str] = None,
    ) -> list[RiskItem]:
        """Cria riscos a partir dos templates jurídicos pré-definidos.

        Útil para inicializar o registro de riscos com itens comuns
        em projetos de automação jurídica.

        Args:
            probability: Probabilidade padrão para os riscos.
            impact: Impacto padrão para os riscos.
            workshop_id: ID do workshop de origem.
            identified_by: Quem identificou.

        Returns:
            Lista de RiskItems criados.
        """
        created_risks: list[RiskItem] = []

        for template in JURIDICAL_RISK_TEMPLATES:
            risk = self.create_risk(
                title=template["title"],
                description=template["description"],
                category=template["category"],
                probability=probability,
                impact=impact,
                tags=["template", "juridico"],
                identified_by=identified_by or "Template automático",
                workshop_id=workshop_id,
            )
            created_risks.append(risk)

        return created_risks

    # -- Matriz e Avaliação de Riscos ---------------------------------------

    def generate_risk_matrix(self) -> RiskMatrix:
        """Gera a matriz de riscos (probabilidade × impacto) com todos os riscos.

        Returns:
            RiskMatrix com todas as células preenchidas.
        """
        cells: list[RiskMatrixCell] = []

        for prob in RiskProbability:
            for imp in RiskImpact:
                score = PROBABILITY_WEIGHTS[prob] * IMPACT_WEIGHTS[imp]
                level = RiskLevel.LOW
                for lvl, (min_val, max_val) in RISK_LEVEL_THRESHOLDS.items():
                    if min_val <= score <= max_val:
                        level = lvl
                        break

                matching_risks = [
                    r.id
                    for r in self._risks.values()
                    if r.probability == prob and r.impact == imp
                ]

                cells.append(
                    RiskMatrixCell(
                        probability=prob,
                        impact=imp,
                        risk_level=level,
                        risk_ids=matching_risks,
                        count=len(matching_risks),
                    )
                )

        return RiskMatrix(
            cells=cells,
            total_risks=len(self._risks),
        )

    def assess_risks(self, top_n: int = 5) -> RiskAssessmentResult:
        """Realiza avaliação consolidada de todos os riscos registrados.

        Args:
            top_n: Quantidade de top riscos a incluir no resultado.

        Returns:
            RiskAssessmentResult com métricas e recomendações.
        """
        all_risks = list(self._risks.values())

        if not all_risks:
            return RiskAssessmentResult(
                recommendations=[
                    "Nenhum risco registrado. Realize um workshop de discovery "
                    "para identificar riscos do MVP."
                ]
            )

        # Contagens por nível
        critical_count = sum(
            1 for r in all_risks if r.risk_level == RiskLevel.CRITICAL
        )
        high_count = sum(
            1 for r in all_risks if r.risk_level == RiskLevel.HIGH
        )
        medium_count = sum(
            1 for r in all_risks if r.risk_level == RiskLevel.MEDIUM
        )
        low_count = sum(
            1 for r in all_risks if r.risk_level == RiskLevel.LOW
        )

        # Riscos sem mitigação
        unmitigated = sum(1 for r in all_risks if not r.has_mitigation)

        # Score médio
        avg_score = round(
            sum(r.risk_score for r in all_risks) / len(all_risks), 1
        )

        # Top riscos
        sorted_risks = sorted(
            all_risks, key=lambda r: r.risk_score, reverse=True
        )
        top_risks = sorted_risks[:top_n]

        # Distribuição por categoria
        by_category: dict[str, int] = {}
        for r in all_risks:
            cat_key = r.category.value
            by_category[cat_key] = by_category.get(cat_key, 0) + 1

        # Impacto por prioridade MoSCoW
        moscow_summary: dict[str, int] = {}
        for r in all_risks:
            for mp in r.affected_moscow_priorities:
                mp_key = mp.value if hasattr(mp, "value") else str(mp)
                moscow_summary[mp_key] = moscow_summary.get(mp_key, 0) + 1

        # Gerar recomendações
        recommendations = self._generate_recommendations(
            critical_count=critical_count,
            high_count=high_count,
            unmitigated=unmitigated,
            total=len(all_risks),
            avg_score=avg_score,
        )

        return RiskAssessmentResult(
            total_risks=len(all_risks),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            unmitigated_count=unmitigated,
            average_risk_score=avg_score,
            top_risks=top_risks,
            risks_by_category=by_category,
            moscow_impact_summary=moscow_summary,
            recommendations=recommendations,
        )

    # -- Integração com User Stories (m03) ----------------------------------

    def get_risks_for_story(self, story_id: str) -> list[RiskItem]:
        """Retorna todos os riscos que afetam uma user story específica.

        Args:
            story_id: ID da user story.

        Returns:
            Lista de riscos vinculados à story, ordenados por score.
        """
        risks = [
            r
            for r in self._risks.values()
            if story_id in r.affected_story_ids
        ]
        risks.sort(key=lambda r: r.risk_score, reverse=True)
        return risks

    def get_unmitigated_must_have_risks(self) -> list[RiskItem]:
        """Retorna riscos sem mitigação que afetam stories Must Have.

        Identifica riscos críticos que podem bloquear o MVP.

        Returns:
            Lista de riscos sem mitigação vinculados a Must Have stories.
        """
        return [
            r
            for r in self._risks.values()
            if not r.has_mitigation
            and MoscowPriority.MUST_HAVE in r.affected_moscow_priorities
        ]

    def link_risk_to_stories(
        self,
        risk_id: str,
        story_ids: list[str],
    ) -> RiskItem:
        """Vincula um risco a user stories adicionais.

        Args:
            risk_id: ID do risco.
            story_ids: IDs das stories a vincular.

        Returns:
            RiskItem atualizado.

        Raises:
            ValueError: Se o risco não for encontrado.
        """
        risk = self._risks.get(risk_id)
        if not risk:
            raise ValueError(f"Risco com ID '{risk_id}' não encontrado.")

        for sid in story_ids:
            if sid not in risk.affected_story_ids:
                risk.affected_story_ids.append(sid)

        # Atualizar prioridades MoSCoW
        if self._user_story_service:
            risk.affected_moscow_priorities = self._resolve_moscow_priorities(
                risk.affected_story_ids
            )

        risk.updated_at = datetime.utcnow()
        return risk

    # -- Métodos auxiliares privados -----------------------------------------

    def _resolve_moscow_priorities(
        self,
        story_ids: list[str],
    ) -> list[MoscowPriority]:
        """Resolve as prioridades MoSCoW das user stories informadas.

        Args:
            story_ids: IDs das user stories.

        Returns:
            Lista de prioridades MoSCoW únicas.
        """
        priorities: set[MoscowPriority] = set()

        if not self._user_story_service:
            return []

        # TODO: Implementar integração real com UserStoryService.
        # A interface exata de busca depende da API exposta por m03.
        # Exemplo esperado:
        #   for sid in story_ids:
        #       story = self._user_story_service.get_story(sid)
        #       if story and story.moscow_priority:
        #           priorities.add(story.moscow_priority)

        return list(priorities)

    def _generate_recommendations(
        self,
        critical_count: int,
        high_count: int,
        unmitigated: int,
        total: int,
        avg_score: float,
    ) -> list[str]:
        """Gera recomendações com base nas métricas de risco.

        Args:
            critical_count: Quantidade de riscos críticos.
            high_count: Quantidade de riscos altos.
            unmitigated: Quantidade sem mitigação.
            total: Total de riscos.
            avg_score: Score médio.

        Returns:
            Lista de recomendações em PT-BR.
        """
        recommendations: list[str] = []

        if critical_count > 0:
            recommendations.append(
                f"URGENTE: {critical_count} risco(s) crítico(s) identificado(s). "
                "Priorize a criação de planos de mitigação imediatamente."
            )

        if high_count > 2:
            recommendations.append(
                f"ATENÇÃO: {high_count} riscos de nível alto. "
                "Considere reduzir o escopo do MVP para mitigar exposição."
            )

        if unmitigated > 0:
            pct = round((unmitigated / total) * 100, 0)
            recommendations.append(
                f"{unmitigated} risco(s) ({pct}%) sem plano de mitigação. "
                "Agende um workshop de mitigação para endereçá-los."
            )

        if avg_score > 12:
            recommendations.append(
                f"Score médio de risco elevado ({avg_score}). "
                "Revise a viabilidade do escopo atual do MVP."
            )

        must_have_risks = self.get_unmitigated_must_have_risks()
        if must_have_risks:
            recommendations.append(
                f"{len(must_have_risks)} risco(s) sem mitigação afetam stories Must Have. "
                "Estes são bloqueadores potenciais do MVP e devem ser tratados com prioridade máxima."
            )

        if not recommendations:
            recommendations.append(
                "Perfil de risco dentro dos limites aceitáveis. "
                "Continue monitorando e atualizando os planos de mitigação."
            )

        return recommendations


# ---------------------------------------------------------------------------
# Exports públicos
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "RiskCategory",
    "RiskProbability",
    "RiskImpact",
    "RiskStatus",
    "RiskLevel",
    "MitigationStrategy",
    "WorkshopPhase",
    "ActivityType",
    # Modelos
    "RiskItem",
    "MitigationPlan",
    "MitigationAction",
    "RiskAssessmentResult",
    "RiskMatrix",
    "RiskMatrixCell",
    "DiscoveryWorkshop",
    "WorkshopActivity",
    "WorkshopParticipant",
    # Constantes
    "PROBABILITY_WEIGHTS",
    "IMPACT_WEIGHTS",
    "RISK_LEVEL_THRESHOLDS",
    "JURIDICAL_RISK_TEMPLATES",
    # Serviço
    "RiskService",
]
