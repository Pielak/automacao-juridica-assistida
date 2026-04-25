"""Módulo backlog #19: Lista consolidada de entregáveis priorizados por fase.

Este módulo define a estrutura de dados e a lógica de negócio para gerenciar
os entregáveis do projeto de Automação Jurídica Assistida, organizados por
fases de implementação com priorização clara.

Cada entregável possui metadados como fase, prioridade, status, dependências
e critérios de aceitação, permitindo rastreabilidade completa do progresso
do projeto.

Exemplo de uso:
    from backend.src.modules.m19_deliverables_summary import (
        DeliverablesSummaryService,
        get_deliverables_summary_service,
    )

    service = get_deliverables_summary_service()
    resumo = service.get_summary_by_phase(phase=ProjectPhase.PHASE_1_MVP)
    todos = service.list_all_deliverables()
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------


class ProjectPhase(str, enum.Enum):
    """Fases do projeto de Automação Jurídica Assistida."""

    PHASE_1_MVP = "fase_1_mvp"
    PHASE_2_CORE = "fase_2_core"
    PHASE_3_ADVANCED = "fase_3_avancado"
    PHASE_4_OPTIMIZATION = "fase_4_otimizacao"
    PHASE_5_SCALE = "fase_5_escala"


class DeliverablePriority(str, enum.Enum):
    """Níveis de prioridade dos entregáveis."""

    CRITICAL = "critico"
    HIGH = "alta"
    MEDIUM = "media"
    LOW = "baixa"


class DeliverableStatus(str, enum.Enum):
    """Status possíveis de um entregável."""

    NOT_STARTED = "nao_iniciado"
    IN_PROGRESS = "em_andamento"
    IN_REVIEW = "em_revisao"
    COMPLETED = "concluido"
    BLOCKED = "bloqueado"
    CANCELLED = "cancelado"


class DeliverableCategory(str, enum.Enum):
    """Categorias funcionais dos entregáveis."""

    AUTHENTICATION = "autenticacao"
    DOCUMENT_MANAGEMENT = "gestao_documentos"
    AI_ANALYSIS = "analise_ia"
    CHAT_INTERFACE = "interface_chat"
    DATAJUD_INTEGRATION = "integracao_datajud"
    AUDIT_COMPLIANCE = "auditoria_compliance"
    INFRASTRUCTURE = "infraestrutura"
    FRONTEND = "frontend"
    TESTING = "testes"
    DOCUMENTATION = "documentacao"
    SECURITY = "seguranca"
    DEVOPS = "devops"


# ---------------------------------------------------------------------------
# Schemas Pydantic
# ---------------------------------------------------------------------------


class AcceptanceCriteria(BaseModel):
    """Critério de aceitação individual de um entregável."""

    id: UUID = Field(default_factory=uuid4, description="Identificador único do critério.")
    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Descrição do critério de aceitação em PT-BR.",
    )
    is_met: bool = Field(default=False, description="Indica se o critério foi atendido.")
    verified_at: Optional[datetime] = Field(
        default=None, description="Data/hora em que o critério foi verificado."
    )
    verified_by: Optional[str] = Field(
        default=None, description="Responsável pela verificação."
    )


class Deliverable(BaseModel):
    """Modelo de dados de um entregável do projeto."""

    id: UUID = Field(default_factory=uuid4, description="Identificador único do entregável.")
    code: str = Field(
        ...,
        pattern=r"^E\d{3}$",
        description="Código do entregável no formato E001, E002, etc.",
    )
    title: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Título descritivo do entregável.",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Descrição detalhada do entregável.",
    )
    phase: ProjectPhase = Field(..., description="Fase do projeto à qual o entregável pertence.")
    priority: DeliverablePriority = Field(..., description="Nível de prioridade.")
    category: DeliverableCategory = Field(..., description="Categoria funcional.")
    status: DeliverableStatus = Field(
        default=DeliverableStatus.NOT_STARTED, description="Status atual do entregável."
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Lista de códigos de entregáveis dos quais este depende (ex: ['E001', 'E002']).",
    )
    acceptance_criteria: list[AcceptanceCriteria] = Field(
        default_factory=list, description="Critérios de aceitação do entregável."
    )
    responsible_team: Optional[str] = Field(
        default=None, description="Equipe ou pessoa responsável."
    )
    estimated_effort_hours: Optional[float] = Field(
        default=None, ge=0, description="Estimativa de esforço em horas."
    )
    target_date: Optional[date] = Field(
        default=None, description="Data alvo para conclusão."
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Data/hora de conclusão efetiva."
    )
    notes: Optional[str] = Field(
        default=None, max_length=1000, description="Observações adicionais."
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Data de criação do registro."
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Data da última atualização."
    )

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies_format(cls, v: list[str]) -> list[str]:
        """Valida que todas as dependências seguem o formato de código esperado."""
        import re

        pattern = re.compile(r"^E\d{3}$")
        for dep in v:
            if not pattern.match(dep):
                raise ValueError(
                    f"Dependência '{dep}' não segue o formato esperado (E001, E002, etc.)."
                )
        return v

    @property
    def completion_percentage(self) -> float:
        """Calcula o percentual de critérios de aceitação atendidos."""
        if not self.acceptance_criteria:
            return 0.0
        met = sum(1 for c in self.acceptance_criteria if c.is_met)
        return round((met / len(self.acceptance_criteria)) * 100, 2)

    @property
    def is_blocked(self) -> bool:
        """Indica se o entregável está bloqueado."""
        return self.status == DeliverableStatus.BLOCKED


class PhaseSummary(BaseModel):
    """Resumo consolidado de uma fase do projeto."""

    phase: ProjectPhase = Field(..., description="Fase do projeto.")
    phase_display_name: str = Field(..., description="Nome amigável da fase.")
    total_deliverables: int = Field(default=0, description="Total de entregáveis na fase.")
    completed: int = Field(default=0, description="Quantidade concluída.")
    in_progress: int = Field(default=0, description="Quantidade em andamento.")
    blocked: int = Field(default=0, description="Quantidade bloqueada.")
    not_started: int = Field(default=0, description="Quantidade não iniciada.")
    completion_percentage: float = Field(
        default=0.0, description="Percentual de conclusão da fase."
    )
    total_estimated_hours: float = Field(
        default=0.0, description="Total de horas estimadas para a fase."
    )
    deliverables: list[Deliverable] = Field(
        default_factory=list, description="Entregáveis da fase."
    )


class ProjectSummary(BaseModel):
    """Resumo geral do projeto com todas as fases."""

    project_name: str = Field(
        default="Automação Jurídica Assistida",
        description="Nome do projeto.",
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data/hora de geração do resumo.",
    )
    total_deliverables: int = Field(default=0, description="Total geral de entregáveis.")
    overall_completion_percentage: float = Field(
        default=0.0, description="Percentual geral de conclusão."
    )
    phases: list[PhaseSummary] = Field(
        default_factory=list, description="Resumo por fase."
    )
    critical_path: list[str] = Field(
        default_factory=list,
        description="Códigos dos entregáveis no caminho crítico.",
    )


# ---------------------------------------------------------------------------
# Nomes amigáveis das fases
# ---------------------------------------------------------------------------

PHASE_DISPLAY_NAMES: dict[ProjectPhase, str] = {
    ProjectPhase.PHASE_1_MVP: "Fase 1 — MVP (Produto Mínimo Viável)",
    ProjectPhase.PHASE_2_CORE: "Fase 2 — Funcionalidades Core",
    ProjectPhase.PHASE_3_ADVANCED: "Fase 3 — Recursos Avançados",
    ProjectPhase.PHASE_4_OPTIMIZATION: "Fase 4 — Otimização e Performance",
    ProjectPhase.PHASE_5_SCALE: "Fase 5 — Escala e Expansão",
}


# ---------------------------------------------------------------------------
# Catálogo de entregáveis do projeto
# ---------------------------------------------------------------------------


def _build_default_deliverables() -> list[Deliverable]:
    """Constrói a lista padrão de entregáveis priorizados por fase.

    Returns:
        Lista de entregáveis com metadados completos.
    """
    deliverables: list[Deliverable] = []

    # ===================================================================
    # FASE 1 — MVP
    # ===================================================================

    deliverables.extend(
        [
            Deliverable(
                code="E001",
                title="Infraestrutura base do projeto",
                description=(
                    "Configuração inicial do repositório, Docker Compose para desenvolvimento, "
                    "CI/CD básico, estrutura de pastas seguindo Clean Architecture, "
                    "configuração de linters e formatadores."
                ),
                phase=ProjectPhase.PHASE_1_MVP,
                priority=DeliverablePriority.CRITICAL,
                category=DeliverableCategory.INFRASTRUCTURE,
                dependencies=[],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Repositório configurado com estrutura Clean Architecture."
                    ),
                    AcceptanceCriteria(
                        description="Docker Compose funcional com PostgreSQL, Redis e aplicação."
                    ),
                    AcceptanceCriteria(
                        description="Pipeline CI básico executando linters e testes."
                    ),
                    AcceptanceCriteria(
                        description="Arquivo settings.py com Pydantic Settings validando variáveis de ambiente."
                    ),
                ],
                responsible_team="DevOps / Backend",
                estimated_effort_hours=40.0,
            ),
            Deliverable(
                code="E002",
                title="Módulo de autenticação e autorização",
                description=(
                    "Implementação completa do sistema de autenticação com JWT (RS256), "
                    "refresh tokens, MFA via TOTP, RBAC com perfis (admin, advogado, "
                    "estagiário, cliente), gestão de sessões e logout seguro."
                ),
                phase=ProjectPhase.PHASE_1_MVP,
                priority=DeliverablePriority.CRITICAL,
                category=DeliverableCategory.AUTHENTICATION,
                dependencies=["E001"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Login com JWT RS256 e refresh token funcional."
                    ),
                    AcceptanceCriteria(
                        description="MFA via TOTP implementado e testado."
                    ),
                    AcceptanceCriteria(
                        description="RBAC com pelo menos 4 perfis configurados."
                    ),
                    AcceptanceCriteria(
                        description="Testes unitários com cobertura mínima de 80%."
                    ),
                ],
                responsible_team="Backend",
                estimated_effort_hours=60.0,
            ),
            Deliverable(
                code="E003",
                title="CRUD de usuários e perfis",
                description=(
                    "Endpoints REST para criação, leitura, atualização e desativação "
                    "de usuários. Inclui validação de dados, paginação, filtros e "
                    "associação de perfis RBAC."
                ),
                phase=ProjectPhase.PHASE_1_MVP,
                priority=DeliverablePriority.HIGH,
                category=DeliverableCategory.AUTHENTICATION,
                dependencies=["E002"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Endpoints CRUD de usuários documentados via OpenAPI."
                    ),
                    AcceptanceCriteria(
                        description="Validação de entrada com Pydantic v2."
                    ),
                    AcceptanceCriteria(
                        description="Paginação e filtros funcionais."
                    ),
                ],
                responsible_team="Backend",
                estimated_effort_hours=30.0,
            ),
            Deliverable(
                code="E004",
                title="Módulo de gestão de documentos jurídicos",
                description=(
                    "Upload, armazenamento, versionamento e recuperação de documentos "
                    "jurídicos. Suporte a PDF, DOCX e TXT. Validação de tipo e tamanho, "
                    "varredura de segurança, metadados e organização por caso/processo."
                ),
                phase=ProjectPhase.PHASE_1_MVP,
                priority=DeliverablePriority.CRITICAL,
                category=DeliverableCategory.DOCUMENT_MANAGEMENT,
                dependencies=["E002"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Upload de documentos PDF, DOCX e TXT funcional."
                    ),
                    AcceptanceCriteria(
                        description="Validação de tipo MIME e tamanho máximo."
                    ),
                    AcceptanceCriteria(
                        description="Versionamento de documentos implementado."
                    ),
                    AcceptanceCriteria(
                        description="Metadados indexados e pesquisáveis."
                    ),
                ],
                responsible_team="Backend",
                estimated_effort_hours=50.0,
            ),
            Deliverable(
                code="E005",
                title="Interface frontend — Login e Dashboard",
                description=(
                    "Telas de login com suporte a MFA, dashboard principal com "
                    "visão geral de processos, documentos recentes e notificações. "
                    "Layout responsivo com Tailwind CSS."
                ),
                phase=ProjectPhase.PHASE_1_MVP,
                priority=DeliverablePriority.HIGH,
                category=DeliverableCategory.FRONTEND,
                dependencies=["E002"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Tela de login funcional com fluxo MFA."
                    ),
                    AcceptanceCriteria(
                        description="Dashboard responsivo renderizando dados reais."
                    ),
                    AcceptanceCriteria(
                        description="Guards de autenticação no React Router."
                    ),
                ],
                responsible_team="Frontend",
                estimated_effort_hours=45.0,
            ),
            Deliverable(
                code="E006",
                title="Trilha de auditoria básica",
                description=(
                    "Registro de eventos de auditoria para ações críticas: login, "
                    "logout, CRUD de usuários, upload/download de documentos. "
                    "Logs estruturados com structlog e persistência em banco."
                ),
                phase=ProjectPhase.PHASE_1_MVP,
                priority=DeliverablePriority.HIGH,
                category=DeliverableCategory.AUDIT_COMPLIANCE,
                dependencies=["E001", "E002"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Eventos de auditoria registrados para todas as ações críticas."
                    ),
                    AcceptanceCriteria(
                        description="Logs estruturados com correlation ID por request."
                    ),
                    AcceptanceCriteria(
                        description="Consulta de logs de auditoria via endpoint protegido."
                    ),
                ],
                responsible_team="Backend",
                estimated_effort_hours=35.0,
            ),
        ]
    )

    # ===================================================================
    # FASE 2 — FUNCIONALIDADES CORE
    # ===================================================================

    deliverables.extend(
        [
            Deliverable(
                code="E007",
                title="Integração com API Anthropic (Claude)",
                description=(
                    "Módulo de integração com a API da Anthropic para análise de "
                    "documentos jurídicos. Inclui retry com tenacity, circuit breaker, "
                    "rate limiting, cache de respostas e tratamento de erros."
                ),
                phase=ProjectPhase.PHASE_2_CORE,
                priority=DeliverablePriority.CRITICAL,
                category=DeliverableCategory.AI_ANALYSIS,
                dependencies=["E001", "E004"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Chamadas à API Anthropic com retry e circuit breaker."
                    ),
                    AcceptanceCriteria(
                        description="Rate limiting configurável por usuário/plano."
                    ),
                    AcceptanceCriteria(
                        description="Cache de respostas para documentos já analisados."
                    ),
                    AcceptanceCriteria(
                        description="Logs de uso e custos da API registrados."
                    ),
                ],
                responsible_team="Backend",
                estimated_effort_hours=55.0,
            ),
            Deliverable(
                code="E008",
                title="Análise automatizada de documentos jurídicos",
                description=(
                    "Use cases de análise de petições, contratos e pareceres via IA. "
                    "Extração de entidades, classificação de tipo documental, "
                    "identificação de cláusulas relevantes e geração de resumos."
                ),
                phase=ProjectPhase.PHASE_2_CORE,
                priority=DeliverablePriority.CRITICAL,
                category=DeliverableCategory.AI_ANALYSIS,
                dependencies=["E004", "E007"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Análise de petições com extração de entidades."
                    ),
                    AcceptanceCriteria(
                        description="Classificação automática de tipo documental."
                    ),
                    AcceptanceCriteria(
                        description="Geração de resumos com qualidade validada."
                    ),
                ],
                responsible_team="Backend / IA",
                estimated_effort_hours=70.0,
            ),
            Deliverable(
                code="E009",
                title="Interface de chat jurídico assistido",
                description=(
                    "Chat interativo no frontend para consultas jurídicas assistidas "
                    "por IA. Histórico de conversas, contexto de documentos, "
                    "sugestões de perguntas e formatação de respostas jurídicas."
                ),
                phase=ProjectPhase.PHASE_2_CORE,
                priority=DeliverablePriority.HIGH,
                category=DeliverableCategory.CHAT_INTERFACE,
                dependencies=["E005", "E007"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Interface de chat funcional com histórico."
                    ),
                    AcceptanceCriteria(
                        description="Contexto de documentos vinculado à conversa."
                    ),
                    AcceptanceCriteria(
                        description="Respostas formatadas com referências jurídicas."
                    ),
                ],
                responsible_team="Frontend / Backend",
                estimated_effort_hours=60.0,
            ),
            Deliverable(
                code="E010",
                title="Processamento assíncrono com Celery",
                description=(
                    "Configuração do Celery com Redis como broker para processamento "
                    "assíncrono de tarefas pesadas: análise de documentos, geração "
                    "de relatórios, integrações externas. Monitoramento com Flower."
                ),
                phase=ProjectPhase.PHASE_2_CORE,
                priority=DeliverablePriority.HIGH,
                category=DeliverableCategory.INFRASTRUCTURE,
                dependencies=["E001"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Celery configurado com Redis como broker."
                    ),
                    AcceptanceCriteria(
                        description="Tarefas de análise executando de forma assíncrona."
                    ),
                    AcceptanceCriteria(
                        description="Monitoramento de filas via Flower ou equivalente."
                    ),
                ],
                responsible_team="Backend / DevOps",
                estimated_effort_hours=35.0,
            ),
            Deliverable(
                code="E011",
                title="Frontend — Gestão de documentos e upload",
                description=(
                    "Interface para upload de documentos com drag-and-drop (react-dropzone), "
                    "listagem com filtros, preview de documentos, download e "
                    "gerenciamento de versões."
                ),
                phase=ProjectPhase.PHASE_2_CORE,
                priority=DeliverablePriority.HIGH,
                category=DeliverableCategory.FRONTEND,
                dependencies=["E004", "E005"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Upload drag-and-drop com validação de tipo e tamanho."
                    ),
                    AcceptanceCriteria(
                        description="Listagem de documentos com filtros e paginação."
                    ),
                    AcceptanceCriteria(
                        description="Preview de PDF inline."
                    ),
                ],
                responsible_team="Frontend",
                estimated_effort_hours=40.0,
            ),
        ]
    )

    # ===================================================================
    # FASE 3 — RECURSOS AVANÇADOS
    # ===================================================================

    deliverables.extend(
        [
            Deliverable(
                code="E012",
                title="Integração com DataJud",
                description=(
                    "Módulo de integração com a API do DataJud para consulta de "
                    "processos judiciais. State machine para ciclo de vida de "
                    "documentos DataJud, sincronização periódica e cache."
                ),
                phase=ProjectPhase.PHASE_3_ADVANCED,
                priority=DeliverablePriority.HIGH,
                category=DeliverableCategory.DATAJUD_INTEGRATION,
                dependencies=["E007", "E010"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Consulta de processos via API DataJud funcional."
                    ),
                    AcceptanceCriteria(
                        description="State machine do ciclo de vida implementada."
                    ),
                    AcceptanceCriteria(
                        description="Sincronização periódica via Celery beat."
                    ),
                ],
                responsible_team="Backend",
                estimated_effort_hours=65.0,
            ),
            Deliverable(
                code="E013",
                title="Busca semântica em documentos",
                description=(
                    "Implementação de busca semântica utilizando embeddings e índice "
                    "vetorial (FAISS ou Milvus — decisão pendente G002 ADR). "
                    "Permite encontrar documentos e trechos relevantes por similaridade."
                ),
                phase=ProjectPhase.PHASE_3_ADVANCED,
                priority=DeliverablePriority.MEDIUM,
                category=DeliverableCategory.AI_ANALYSIS,
                dependencies=["E007", "E008"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Indexação vetorial de documentos funcional."
                    ),
                    AcceptanceCriteria(
                        description="Busca por similaridade retornando resultados relevantes."
                    ),
                    AcceptanceCriteria(
                        description="ADR G002 decidida e implementada."
                    ),
                ],
                responsible_team="Backend / IA",
                estimated_effort_hours=55.0,
            ),
            Deliverable(
                code="E014",
                title="Relatórios e exportação",
                description=(
                    "Geração de relatórios consolidados de análises jurídicas, "
                    "exportação em PDF e DOCX, templates personalizáveis e "
                    "agendamento de relatórios periódicos."
                ),
                phase=ProjectPhase.PHASE_3_ADVANCED,
                priority=DeliverablePriority.MEDIUM,
                category=DeliverableCategory.DOCUMENT_MANAGEMENT,
                dependencies=["E008", "E010"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Geração de relatórios em PDF funcional."
                    ),
                    AcceptanceCriteria(
                        description="Templates de relatório personalizáveis."
                    ),
                    AcceptanceCriteria(
                        description="Agendamento de relatórios via Celery beat."
                    ),
                ],
                responsible_team="Backend / Frontend",
                estimated_effort_hours=45.0,
            ),
            Deliverable(
                code="E015",
                title="Auditoria avançada e compliance LGPD",
                description=(
                    "Extensão do módulo de auditoria com relatórios de compliance, "
                    "gestão de consentimento LGPD, anonimização de dados pessoais, "
                    "retenção configurável e exportação de dados do titular."
                ),
                phase=ProjectPhase.PHASE_3_ADVANCED,
                priority=DeliverablePriority.HIGH,
                category=DeliverableCategory.AUDIT_COMPLIANCE,
                dependencies=["E006"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Relatórios de compliance LGPD gerados automaticamente."
                    ),
                    AcceptanceCriteria(
                        description="Endpoint de exportação de dados do titular (DSAR)."
                    ),
                    AcceptanceCriteria(
                        description="Anonimização de dados pessoais implementada."
                    ),
                ],
                responsible_team="Backend / Compliance",
                estimated_effort_hours=50.0,
            ),
        ]
    )

    # ===================================================================
    # FASE 4 — OTIMIZAÇÃO E PERFORMANCE
    # ===================================================================

    deliverables.extend(
        [
            Deliverable(
                code="E016",
                title="Otimização de performance e cache",
                description=(
                    "Implementação de estratégias de cache multinível (Redis + in-memory), "
                    "otimização de queries SQL, connection pooling, compressão de "
                    "respostas e lazy loading no frontend."
                ),
                phase=ProjectPhase.PHASE_4_OPTIMIZATION,
                priority=DeliverablePriority.MEDIUM,
                category=DeliverableCategory.INFRASTRUCTURE,
                dependencies=["E007", "E008"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Cache Redis configurado para endpoints frequentes."
                    ),
                    AcceptanceCriteria(
                        description="Tempo de resposta P95 < 500ms para endpoints principais."
                    ),
                    AcceptanceCriteria(
                        description="Queries otimizadas com EXPLAIN ANALYZE."
                    ),
                ],
                responsible_team="Backend / DevOps",
                estimated_effort_hours=40.0,
            ),
            Deliverable(
                code="E017",
                title="Testes end-to-end e carga",
                description=(
                    "Suite de testes E2E com Playwright/Cypress, testes de carga "
                    "com Locust, testes de segurança (OWASP ZAP), e integração "
                    "completa no pipeline CI/CD."
                ),
                phase=ProjectPhase.PHASE_4_OPTIMIZATION,
                priority=DeliverablePriority.HIGH,
                category=DeliverableCategory.TESTING,
                dependencies=["E005", "E008", "E009"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Suite E2E cobrindo fluxos críticos."
                    ),
                    AcceptanceCriteria(
                        description="Testes de carga validando SLAs definidos."
                    ),
                    AcceptanceCriteria(
                        description="Scan OWASP ZAP sem vulnerabilidades críticas."
                    ),
                ],
                responsible_team="QA / DevOps",
                estimated_effort_hours=50.0,
            ),
        ]
    )

    # ===================================================================
    # FASE 5 — ESCALA E EXPANSÃO
    # ===================================================================

    deliverables.extend(
        [
            Deliverable(
                code="E018",
                title="Documentação técnica e de usuário",
                description=(
                    "Documentação completa: guia de instalação, manual do usuário, "
                    "documentação de API (OpenAPI), ADRs, runbooks operacionais "
                    "e guia de contribuição."
                ),
                phase=ProjectPhase.PHASE_5_SCALE,
                priority=DeliverablePriority.MEDIUM,
                category=DeliverableCategory.DOCUMENTATION,
                dependencies=["E008", "E009"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Manual do usuário completo em PT-BR."
                    ),
                    AcceptanceCriteria(
                        description="Documentação de API 100% sincronizada com código."
                    ),
                    AcceptanceCriteria(
                        description="Runbooks para operações críticas."
                    ),
                ],
                responsible_team="Todos",
                estimated_effort_hours=40.0,
            ),
            Deliverable(
                code="E019",
                title="Hardening de segurança e pentest",
                description=(
                    "Revisão completa de segurança: headers HTTP (CSP, HSTS), "
                    "rate limiting avançado, proteção contra CSRF/XSS/SQLi, "
                    "pentest externo e remediação de vulnerabilidades."
                ),
                phase=ProjectPhase.PHASE_5_SCALE,
                priority=DeliverablePriority.HIGH,
                category=DeliverableCategory.SECURITY,
                dependencies=["E002", "E017"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Headers de segurança configurados (CSP, HSTS, X-Frame-Options)."
                    ),
                    AcceptanceCriteria(
                        description="Pentest externo realizado sem vulnerabilidades críticas."
                    ),
                    AcceptanceCriteria(
                        description="Todas as vulnerabilidades encontradas remediadas."
                    ),
                ],
                responsible_team="Segurança / DevOps",
                estimated_effort_hours=45.0,
            ),
            Deliverable(
                code="E020",
                title="Deploy em produção e monitoramento",
                description=(
                    "Configuração de ambiente de produção com Docker/Kubernetes, "
                    "monitoramento com Prometheus + Grafana, alertas, backups "
                    "automatizados e plano de disaster recovery."
                ),
                phase=ProjectPhase.PHASE_5_SCALE,
                priority=DeliverablePriority.CRITICAL,
                category=DeliverableCategory.DEVOPS,
                dependencies=["E016", "E017", "E019"],
                acceptance_criteria=[
                    AcceptanceCriteria(
                        description="Ambiente de produção provisionado e funcional."
                    ),
                    AcceptanceCriteria(
                        description="Monitoramento com dashboards Grafana configurados."
                    ),
                    AcceptanceCriteria(
                        description="Backups automatizados com teste de restauração."
                    ),
                    AcceptanceCriteria(
                        description="Plano de disaster recovery documentado e testado."
                    ),
                ],
                responsible_team="DevOps",
                estimated_effort_hours=55.0,
            ),
        ]
    )

    return deliverables


# ---------------------------------------------------------------------------
# Serviço principal
# ---------------------------------------------------------------------------


class DeliverablesSummaryService:
    """Serviço para consulta e consolidação de entregáveis do projeto.

    Fornece métodos para listar, filtrar e gerar resumos dos entregáveis
    organizados por fase, prioridade e status.
    """

    def __init__(self, deliverables: Optional[list[Deliverable]] = None) -> None:
        """Inicializa o serviço com a lista de entregáveis.

        Args:
            deliverables: Lista customizada de entregáveis. Se None, utiliza
                         o catálogo padrão do projeto.
        """
        self._deliverables = deliverables or _build_default_deliverables()
        self._deliverables_map: dict[str, Deliverable] = {
            d.code: d for d in self._deliverables
        }

    @property
    def deliverables(self) -> list[Deliverable]:
        """Retorna a lista completa de entregáveis."""
        return list(self._deliverables)

    def get_deliverable_by_code(self, code: str) -> Optional[Deliverable]:
        """Busca um entregável pelo código.

        Args:
            code: Código do entregável (ex: 'E001').

        Returns:
            O entregável encontrado ou None.
        """
        return self._deliverables_map.get(code)

    def list_by_phase(self, phase: ProjectPhase) -> list[Deliverable]:
        """Lista entregáveis de uma fase específica.

        Args:
            phase: Fase do projeto.

        Returns:
            Lista de entregáveis da fase, ordenados por prioridade.
        """
        priority_order = {
            DeliverablePriority.CRITICAL: 0,
            DeliverablePriority.HIGH: 1,
            DeliverablePriority.MEDIUM: 2,
            DeliverablePriority.LOW: 3,
        }
        phase_deliverables = [d for d in self._deliverables if d.phase == phase]
        return sorted(phase_deliverables, key=lambda d: priority_order.get(d.priority, 99))

    def list_by_priority(self, priority: DeliverablePriority) -> list[Deliverable]:
        """Lista entregáveis por nível de prioridade.

        Args:
            priority: Nível de prioridade desejado.

        Returns:
            Lista de entregáveis com a prioridade especificada.
        """
        return [d for d in self._deliverables if d.priority == priority]

    def list_by_status(self, status: DeliverableStatus) -> list[Deliverable]:
        """Lista entregáveis por status.

        Args:
            status: Status desejado.

        Returns:
            Lista de entregáveis com o status especificado.
        """
        return [d for d in self._deliverables if d.status == status]

    def list_by_category(self, category: DeliverableCategory) -> list[Deliverable]:
        """Lista entregáveis por categoria funcional.

        Args:
            category: Categoria funcional desejada.

        Returns:
            Lista de entregáveis da categoria.
        """
        return [d for d in self._deliverables if d.category == category]

    def list_blocked(self) -> list[Deliverable]:
        """Lista todos os entregáveis bloqueados.

        Returns:
            Lista de entregáveis com status BLOCKED.
        """
        return self.list_by_status(DeliverableStatus.BLOCKED)

    def get_dependencies(self, code: str) -> list[Deliverable]:
        """Retorna os entregáveis dos quais o código informado depende.

        Args:
            code: Código do entregável.

        Returns:
            Lista de entregáveis que são dependências diretas.
        """
        deliverable = self.get_deliverable_by_code(code)
        if not deliverable:
            return []
        return [
            self._deliverables_map[dep_code]
            for dep_code in deliverable.dependencies
            if dep_code in self._deliverables_map
        ]

    def get_dependents(self, code: str) -> list[Deliverable]:
        """Retorna os entregáveis que dependem do código informado.

        Args:
            code: Código do entregável.

        Returns:
            Lista de entregáveis que possuem o código como dependência.
        """
        return [d for d in self._deliverables if code in d.dependencies]

    def get_phase_summary(self, phase: ProjectPhase) -> PhaseSummary:
        """Gera o resumo consolidado de uma fase.

        Args:
            phase: Fase do projeto.

        Returns:
            Resumo com contadores e métricas da fase.
        """
        phase_deliverables = self.list_by_phase(phase)
        total = len(phase_deliverables)

        completed = sum(
            1 for d in phase_deliverables if d.status == DeliverableStatus.COMPLETED
        )
        in_progress = sum(
            1
            for d in phase_deliverables
            if d.status in (DeliverableStatus.IN_PROGRESS, DeliverableStatus.IN_REVIEW)
        )
        blocked = sum(
            1 for d in phase_deliverables if d.status == DeliverableStatus.BLOCKED
        )
        not_started = sum(
            1 for d in phase_deliverables if d.status == DeliverableStatus.NOT_STARTED
        )

        completion_pct = round((completed / total) * 100, 2) if total > 0 else 0.0

        total_hours = sum(
            d.estimated_effort_hours
            for d in phase_deliverables
            if d.estimated_effort_hours is not None
        )

        return PhaseSummary(
            phase=phase,
            phase_display_name=PHASE_DISPLAY_NAMES.get(phase, phase.value),
            total_deliverables=total,
            completed=completed,
            in_progress=in_progress,
            blocked=blocked,
            not_started=not_started,
            completion_percentage=completion_pct,
            total_estimated_hours=total_hours,
            deliverables=phase_deliverables,
        )

    def get_project_summary(self) -> ProjectSummary:
        """Gera o resumo geral do projeto com todas as fases.

        Returns:
            Resumo completo do projeto com métricas consolidadas.
        """
        phases_summaries = [
            self.get_phase_summary(phase) for phase in ProjectPhase
        ]

        total = len(self._deliverables)
        completed = sum(ps.completed for ps in phases_summaries)
        overall_pct = round((completed / total) * 100, 2) if total > 0 else 0.0

        critical_path = self._compute_critical_path()

        return ProjectSummary(
            total_deliverables=total,
            overall_completion_percentage=overall_pct,
            phases=phases_summaries,
            critical_path=critical_path,
        )

    def _compute_critical_path(self) -> list[str]:
        """Calcula o caminho crítico baseado em dependências e prioridade.

        Identifica a cadeia mais longa de dependências entre entregáveis
        críticos, representando o caminho que determina a duração mínima
        do projeto.

        Returns:
            Lista ordenada de códigos de entregáveis no caminho crítico.
        """
        # Memoização para comprimento do caminho mais longo a partir de cada nó
        memo: dict[str, list[str]] = {}

        def _longest_path(code: str) -> list[str]:
            """Calcula recursivamente o caminho mais longo a partir de um nó."""
            if code in memo:
                return memo[code]

            deliverable = self._deliverables_map.get(code)
            if not deliverable:
                memo[code] = []
                return []

            dependents = self.get_dependents(code)
            if not dependents:
                memo[code] = [code]
                return [code]

            longest: list[str] = []
            for dep in dependents:
                path = _longest_path(dep.code)
                if len(path) > len(longest):
                    longest = path

            result = [code] + longest
            memo[code] = result
            return result

        # Encontrar nós raiz (sem dependências)
        roots = [d.code for d in self._deliverables if not d.dependencies]

        overall_longest: list[str] = []
        for root in roots:
            path = _longest_path(root)
            if len(path) > len(overall_longest):
                overall_longest = path

        return overall_longest

    def update_status(
        self, code: str, new_status: DeliverableStatus
    ) -> Optional[Deliverable]:
        """Atualiza o status de um entregável.

        Args:
            code: Código do entregável.
            new_status: Novo status a ser atribuído.

        Returns:
            O entregável atualizado ou None se não encontrado.
        """
        deliverable = self._deliverables_map.get(code)
        if not deliverable:
            return None

        deliverable.status = new_status
        deliverable.updated_at = datetime.utcnow()

        if new_status == DeliverableStatus.COMPLETED:
            deliverable.completed_at = datetime.utcnow()

        return deliverable

    def list_all_deliverables(self) -> list[Deliverable]:
        """Lista todos os entregáveis ordenados por fase e prioridade.

        Returns:
            Lista completa de entregáveis ordenada.
        """
        phase_order = {phase: idx for idx, phase in enumerate(ProjectPhase)}
        priority_order = {
            DeliverablePriority.CRITICAL: 0,
            DeliverablePriority.HIGH: 1,
            DeliverablePriority.MEDIUM: 2,
            DeliverablePriority.LOW: 3,
        }
        return sorted(
            self._deliverables,
            key=lambda d: (
                phase_order.get(d.phase, 99),
                priority_order.get(d.priority, 99),
            ),
        )

    def get_total_estimated_hours(self) -> float:
        """Calcula o total de horas estimadas para todo o projeto.

        Returns:
            Soma das horas estimadas de todos os entregáveis.
        """
        return sum(
            d.estimated_effort_hours
            for d in self._deliverables
            if d.estimated_effort_hours is not None
        )

    def to_markdown_report(self) -> str:
        """Gera um relatório em formato Markdown com todos os entregáveis.

        Returns:
            String com o relatório formatado em Markdown.
        """
        lines: list[str] = []
        lines.append("# Entregáveis — Automação Jurídica Assistida\n")
        lines.append(f"**Total de entregáveis:** {len(self._deliverables)}")
        lines.append(f"**Horas estimadas totais:** {self.get_total_estimated_hours()}h\n")

        for phase in ProjectPhase:
            summary = self.get_phase_summary(phase)
            lines.append(f"## {summary.phase_display_name}\n")
            lines.append(
                f"| Métrica | Valor |\n"
                f"|---------|-------|\n"
                f"| Total | {summary.total_deliverables} |\n"
                f"| Concluídos | {summary.completed} |\n"
                f"| Em andamento | {summary.in_progress} |\n"
                f"| Bloqueados | {summary.blocked} |\n"
                f"| Não iniciados | {summary.not_started} |\n"
                f"| Horas estimadas | {summary.total_estimated_hours}h |\n"
                f"| Conclusão | {summary.completion_percentage}% |\n"
            )

            for d in summary.deliverables:
                status_emoji = {
                    DeliverableStatus.NOT_STARTED: "⬜",
                    DeliverableStatus.IN_PROGRESS: "🔵",
                    DeliverableStatus.IN_REVIEW: "🟡",
                    DeliverableStatus.COMPLETED: "✅",
                    DeliverableStatus.BLOCKED: "🔴",
                    DeliverableStatus.CANCELLED: "⚫",
                }.get(d.status, "⬜")

                deps_str = ", ".join(d.dependencies) if d.dependencies else "Nenhuma"
                lines.append(
                    f"### {status_emoji} {d.code} — {d.title}\n"
                    f"- **Prioridade:** {d.priority.value}\n"
                    f"- **Categoria:** {d.category.value}\n"
                    f"- **Status:** {d.status.value}\n"
                    f"- **Dependências:** {deps_str}\n"
                    f"- **Esforço estimado:** {d.estimated_effort_hours or 'N/A'}h\n"
                    f"- **Equipe:** {d.responsible_team or 'N/A'}\n"
                    f"- **Descrição:** {d.description}\n"
                )

                if d.acceptance_criteria:
                    lines.append("**Critérios de aceitação:**\n")
                    for ac in d.acceptance_criteria:
                        check = "☑" if ac.is_met else "☐"
                        lines.append(f"  - {check} {ac.description}")
                    lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Factory / Singleton
# ---------------------------------------------------------------------------

_service_instance: Optional[DeliverablesSummaryService] = None


def get_deliverables_summary_service() -> DeliverablesSummaryService:
    """Retorna a instância singleton do serviço de entregáveis.

    Returns:
        Instância do DeliverablesSummaryService.
    """
    global _service_instance  # noqa: PLW0603
    if _service_instance is None:
        _service_instance = DeliverablesSummaryService()
    return _service_instance


def reset_deliverables_summary_service() -> None:
    """Reseta a instância singleton (útil para testes)."""
    global _service_instance  # noqa: PLW0603
    _service_instance = None
