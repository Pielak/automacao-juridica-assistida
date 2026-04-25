"""Módulo backlog #3: Definição de MVP e User Stories — Automação Jurídica Assistida.

Este módulo fornece templates, validação MoSCoW, critérios de aceite e
estruturas de dados para definição de MVP e user stories no contexto
de automação jurídica. Permite criar, validar e gerenciar user stories
com priorização MoSCoW, critérios de aceite estruturados e rastreabilidade
de requisitos.

Exemplo de uso:
    from backend.src.modules.m03_mvp_user_stories_definition import (
        UserStoryService,
        MoscowPriority,
        UserStory,
        AcceptanceCriterion,
        MVPDefinition,
    )

    service = UserStoryService()
    story = service.create_user_story(
        title="Login com MFA",
        persona="Advogado",
        action="realizar login com autenticação multifator",
        benefit="garantir segurança no acesso ao sistema",
        priority=MoscowPriority.MUST_HAVE,
    )
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------


class MoscowPriority(str, Enum):
    """Prioridades MoSCoW para classificação de user stories.

    - MUST_HAVE: Requisito obrigatório para o MVP.
    - SHOULD_HAVE: Importante, mas o MVP funciona sem ele.
    - COULD_HAVE: Desejável se houver tempo/recurso.
    - WONT_HAVE: Fora do escopo atual, registrado para futuro.
    """

    MUST_HAVE = "must_have"
    SHOULD_HAVE = "should_have"
    COULD_HAVE = "could_have"
    WONT_HAVE = "wont_have"


class StoryStatus(str, Enum):
    """Status do ciclo de vida de uma user story."""

    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class StorySize(str, Enum):
    """Tamanho relativo (T-shirt sizing) para estimativa de esforço."""

    XS = "xs"
    S = "s"
    M = "m"
    L = "l"
    XL = "xl"


class PersonaType(str, Enum):
    """Personas pré-definidas do domínio jurídico."""

    ADVOGADO = "advogado"
    ESTAGIARIO = "estagiario"
    GESTOR_ESCRITORIO = "gestor_escritorio"
    CLIENTE = "cliente"
    ADMINISTRADOR = "administrador"
    ANALISTA_JURIDICO = "analista_juridico"
    CUSTOM = "custom"


class EpicCategory(str, Enum):
    """Categorias de épicos para agrupamento de user stories."""

    AUTENTICACAO = "autenticacao"
    GESTAO_DOCUMENTOS = "gestao_documentos"
    ANALISE_IA = "analise_ia"
    CHAT_ASSISTIDO = "chat_assistido"
    AUDITORIA = "auditoria"
    DATAJUD_INTEGRACAO = "datajud_integracao"
    BUSCA_SEMANTICA = "busca_semantica"
    RELATORIOS = "relatorios"
    ADMINISTRACAO = "administracao"
    ONBOARDING = "onboarding"


# ---------------------------------------------------------------------------
# Modelos de dados (Pydantic v2)
# ---------------------------------------------------------------------------


class AcceptanceCriterion(BaseModel):
    """Critério de aceite individual no formato Given-When-Then.

    Cada critério de aceite descreve um cenário específico que deve ser
    satisfeito para que a user story seja considerada completa.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único do critério de aceite.",
    )
    given: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Pré-condição do cenário (Dado que...).",
    )
    when: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Ação executada (Quando...).",
    )
    then: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Resultado esperado (Então...).",
    )
    is_automated: bool = Field(
        default=False,
        description="Indica se o critério possui teste automatizado.",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Observações adicionais sobre o critério.",
    )

    def to_gherkin(self) -> str:
        """Retorna o critério formatado em sintaxe Gherkin (PT-BR).

        Returns:
            String formatada no padrão Gherkin.
        """
        lines = [
            f"Dado que {self.given}",
            f"Quando {self.when}",
            f"Então {self.then}",
        ]
        return "\n".join(lines)


class TechnicalNote(BaseModel):
    """Nota técnica associada a uma user story."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único da nota técnica.",
    )
    category: str = Field(
        ...,
        description="Categoria da nota (ex: segurança, performance, integração).",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Descrição detalhada da nota técnica.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de criação da nota.",
    )


class DependencyLink(BaseModel):
    """Representação de dependência entre user stories."""

    target_story_id: str = Field(
        ...,
        description="ID da user story da qual esta depende.",
    )
    dependency_type: str = Field(
        default="blocks",
        description="Tipo de dependência: blocks, requires, relates_to.",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Descrição da relação de dependência.",
    )

    @field_validator("dependency_type")
    @classmethod
    def validate_dependency_type(cls, v: str) -> str:
        """Valida o tipo de dependência."""
        allowed = {"blocks", "requires", "relates_to"}
        if v not in allowed:
            raise ValueError(
                f"Tipo de dependência inválido: '{v}'. "
                f"Valores permitidos: {', '.join(sorted(allowed))}."
            )
        return v


class UserStory(BaseModel):
    """Modelo completo de uma User Story para o domínio jurídico.

    Segue o formato padrão:
        "Como [persona], eu quero [ação] para que [benefício]."

    Inclui priorização MoSCoW, critérios de aceite estruturados,
    notas técnicas e rastreabilidade de dependências.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único da user story.",
    )
    code: Optional[str] = Field(
        default=None,
        description="Código legível da story (ex: US-001).",
    )
    title: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Título conciso da user story.",
    )
    persona: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Persona que se beneficia (ex: Advogado, Estagiário).",
    )
    persona_type: PersonaType = Field(
        default=PersonaType.CUSTOM,
        description="Tipo de persona pré-definida.",
    )
    action: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Ação que a persona deseja realizar.",
    )
    benefit: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Benefício esperado pela persona.",
    )
    priority: MoscowPriority = Field(
        ...,
        description="Prioridade MoSCoW da user story.",
    )
    status: StoryStatus = Field(
        default=StoryStatus.DRAFT,
        description="Status atual da user story.",
    )
    size: Optional[StorySize] = Field(
        default=None,
        description="Estimativa de tamanho (T-shirt sizing).",
    )
    story_points: Optional[int] = Field(
        default=None,
        ge=1,
        le=21,
        description="Story points (Fibonacci: 1, 2, 3, 5, 8, 13, 21).",
    )
    epic: Optional[EpicCategory] = Field(
        default=None,
        description="Épico ao qual a story pertence.",
    )
    sprint: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Sprint em que a story está planejada.",
    )
    acceptance_criteria: list[AcceptanceCriterion] = Field(
        default_factory=list,
        description="Lista de critérios de aceite.",
    )
    technical_notes: list[TechnicalNote] = Field(
        default_factory=list,
        description="Notas técnicas relevantes.",
    )
    dependencies: list[DependencyLink] = Field(
        default_factory=list,
        description="Dependências com outras user stories.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags para categorização livre.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de criação.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data da última atualização.",
    )
    created_by: Optional[str] = Field(
        default=None,
        description="ID do usuário que criou a story.",
    )

    @field_validator("story_points")
    @classmethod
    def validate_fibonacci(cls, v: Optional[int]) -> Optional[int]:
        """Valida que story points seguem a sequência de Fibonacci."""
        if v is not None:
            fibonacci_values = {1, 2, 3, 5, 8, 13, 21}
            if v not in fibonacci_values:
                raise ValueError(
                    f"Story points deve ser um valor Fibonacci: "
                    f"{sorted(fibonacci_values)}. Valor recebido: {v}."
                )
        return v

    @model_validator(mode="after")
    def validate_ready_status_requires_criteria(self) -> "UserStory":
        """Valida que stories com status 'ready' possuem critérios de aceite."""
        if self.status == StoryStatus.READY and not self.acceptance_criteria:
            raise ValueError(
                "Uma user story com status 'ready' deve possuir ao menos "
                "um critério de aceite definido."
            )
        return self

    def format_story(self) -> str:
        """Formata a user story no padrão canônico.

        Returns:
            String formatada: "Como [persona], eu quero [ação] para que [benefício]."
        """
        return (
            f"Como {self.persona}, eu quero {self.action} "
            f"para que {self.benefit}."
        )

    def is_mvp(self) -> bool:
        """Verifica se a story faz parte do MVP (MUST_HAVE).

        Returns:
            True se a prioridade for MUST_HAVE.
        """
        return self.priority == MoscowPriority.MUST_HAVE

    def completeness_score(self) -> float:
        """Calcula um score de completude da user story (0.0 a 1.0).

        Critérios avaliados:
        - Tem critérios de aceite (peso 0.3)
        - Tem estimativa de tamanho (peso 0.15)
        - Tem story points (peso 0.15)
        - Tem épico definido (peso 0.1)
        - Tem notas técnicas (peso 0.1)
        - Tem sprint definida (peso 0.1)
        - Tem código definido (peso 0.1)

        Returns:
            Score de completude entre 0.0 e 1.0.
        """
        score = 0.0
        if self.acceptance_criteria:
            score += 0.3
        if self.size is not None:
            score += 0.15
        if self.story_points is not None:
            score += 0.15
        if self.epic is not None:
            score += 0.1
        if self.technical_notes:
            score += 0.1
        if self.sprint is not None:
            score += 0.1
        if self.code is not None:
            score += 0.1
        return round(score, 2)


class MVPDefinition(BaseModel):
    """Definição do MVP (Minimum Viable Product) do projeto.

    Agrupa user stories priorizadas, define objetivos, restrições
    e métricas de sucesso para o MVP.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único da definição de MVP.",
    )
    name: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Nome do MVP (ex: 'MVP v1 — Automação Jurídica').",
    )
    description: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="Descrição detalhada do escopo e objetivos do MVP.",
    )
    version: str = Field(
        default="1.0.0",
        description="Versão do MVP.",
    )
    target_date: Optional[datetime] = Field(
        default=None,
        description="Data alvo para entrega do MVP.",
    )
    stories: list[UserStory] = Field(
        default_factory=list,
        description="User stories que compõem o MVP.",
    )
    success_metrics: list[str] = Field(
        default_factory=list,
        description="Métricas de sucesso do MVP.",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Restrições e premissas do MVP.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de criação da definição.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data da última atualização.",
    )

    def get_must_have_stories(self) -> list[UserStory]:
        """Retorna apenas as stories classificadas como MUST_HAVE.

        Returns:
            Lista de user stories obrigatórias para o MVP.
        """
        return [s for s in self.stories if s.priority == MoscowPriority.MUST_HAVE]

    def get_should_have_stories(self) -> list[UserStory]:
        """Retorna stories classificadas como SHOULD_HAVE.

        Returns:
            Lista de user stories importantes mas não obrigatórias.
        """
        return [s for s in self.stories if s.priority == MoscowPriority.SHOULD_HAVE]

    def get_could_have_stories(self) -> list[UserStory]:
        """Retorna stories classificadas como COULD_HAVE.

        Returns:
            Lista de user stories desejáveis.
        """
        return [s for s in self.stories if s.priority == MoscowPriority.COULD_HAVE]

    def get_wont_have_stories(self) -> list[UserStory]:
        """Retorna stories classificadas como WONT_HAVE.

        Returns:
            Lista de user stories fora do escopo atual.
        """
        return [s for s in self.stories if s.priority == MoscowPriority.WONT_HAVE]

    def moscow_summary(self) -> dict[str, int]:
        """Retorna resumo quantitativo da distribuição MoSCoW.

        Returns:
            Dicionário com contagem por prioridade.
        """
        return {
            MoscowPriority.MUST_HAVE.value: len(self.get_must_have_stories()),
            MoscowPriority.SHOULD_HAVE.value: len(self.get_should_have_stories()),
            MoscowPriority.COULD_HAVE.value: len(self.get_could_have_stories()),
            MoscowPriority.WONT_HAVE.value: len(self.get_wont_have_stories()),
            "total": len(self.stories),
        }

    def stories_by_epic(self) -> dict[str, list[UserStory]]:
        """Agrupa stories por épico.

        Returns:
            Dicionário com épico como chave e lista de stories como valor.
        """
        grouped: dict[str, list[UserStory]] = {}
        for story in self.stories:
            epic_key = story.epic.value if story.epic else "sem_epico"
            if epic_key not in grouped:
                grouped[epic_key] = []
            grouped[epic_key].append(story)
        return grouped

    def overall_completeness(self) -> float:
        """Calcula a completude média de todas as stories do MVP.

        Returns:
            Score médio de completude (0.0 a 1.0).
        """
        if not self.stories:
            return 0.0
        total = sum(s.completeness_score() for s in self.stories)
        return round(total / len(self.stories), 2)

    def validate_mvp_readiness(self) -> list[str]:
        """Valida se o MVP está pronto para desenvolvimento.

        Verifica critérios mínimos de qualidade e completude.

        Returns:
            Lista de problemas encontrados. Lista vazia = MVP pronto.
        """
        issues: list[str] = []

        must_haves = self.get_must_have_stories()
        if not must_haves:
            issues.append(
                "O MVP não possui nenhuma user story classificada como MUST_HAVE."
            )

        for story in must_haves:
            if not story.acceptance_criteria:
                issues.append(
                    f"Story '{story.title}' (MUST_HAVE) não possui "
                    f"critérios de aceite definidos."
                )
            if story.size is None and story.story_points is None:
                issues.append(
                    f"Story '{story.title}' (MUST_HAVE) não possui "
                    f"estimativa de esforço (tamanho ou story points)."
                )
            if story.epic is None:
                issues.append(
                    f"Story '{story.title}' (MUST_HAVE) não está "
                    f"associada a nenhum épico."
                )

        if not self.success_metrics:
            issues.append(
                "O MVP não possui métricas de sucesso definidas."
            )

        if self.target_date is None:
            issues.append(
                "O MVP não possui data alvo de entrega definida."
            )

        return issues


# ---------------------------------------------------------------------------
# Templates de User Stories para o domínio jurídico
# ---------------------------------------------------------------------------


def get_authentication_story_templates() -> list[dict[str, Any]]:
    """Retorna templates de user stories para o épico de autenticação.

    Returns:
        Lista de dicionários com dados para criação de user stories.
    """
    return [
        {
            "title": "Login com credenciais",
            "persona": "Advogado",
            "persona_type": PersonaType.ADVOGADO,
            "action": "realizar login com e-mail e senha",
            "benefit": "eu possa acessar o sistema de forma segura",
            "priority": MoscowPriority.MUST_HAVE,
            "epic": EpicCategory.AUTENTICACAO,
            "acceptance_criteria": [
                AcceptanceCriterion(
                    given="o advogado possui uma conta ativa no sistema",
                    when="ele informa e-mail e senha válidos na tela de login",
                    then="ele é redirecionado para o dashboard principal com sessão autenticada",
                ),
                AcceptanceCriterion(
                    given="o advogado informa credenciais inválidas",
                    when="ele tenta realizar login",
                    then="uma mensagem de erro genérica é exibida sem revelar qual campo está incorreto",
                ),
            ],
            "technical_notes": [
                TechnicalNote(
                    category="segurança",
                    description="Implementar JWT com RS256, refresh tokens e rate limiting de tentativas de login (máximo 5 por minuto por IP).",
                ),
            ],
        },
        {
            "title": "Autenticação multifator (MFA)",
            "persona": "Advogado",
            "persona_type": PersonaType.ADVOGADO,
            "action": "configurar e utilizar autenticação multifator via TOTP",
            "benefit": "eu tenha uma camada adicional de segurança na minha conta",
            "priority": MoscowPriority.MUST_HAVE,
            "epic": EpicCategory.AUTENTICACAO,
            "acceptance_criteria": [
                AcceptanceCriterion(
                    given="o advogado está logado e deseja ativar MFA",
                    when="ele acessa as configurações de segurança e escaneia o QR code com um app autenticador",
                    then="o MFA é ativado e um código de backup é gerado para recuperação",
                ),
                AcceptanceCriterion(
                    given="o advogado possui MFA ativo",
                    when="ele realiza login com credenciais válidas",
                    then="o sistema solicita o código TOTP antes de conceder acesso",
                ),
            ],
            "technical_notes": [
                TechnicalNote(
                    category="segurança",
                    description="Utilizar pyotp para geração e validação de TOTP. Armazenar secret criptografado. Gerar 10 códigos de backup com hash bcrypt.",
                ),
            ],
        },
        {
            "title": "Logout e gestão de sessão",
            "persona": "Advogado",
            "persona_type": PersonaType.ADVOGADO,
            "action": "encerrar minha sessão de forma segura",
            "benefit": "ninguém possa acessar minha conta após eu sair",
            "priority": MoscowPriority.MUST_HAVE,
            "epic": EpicCategory.AUTENTICACAO,
            "acceptance_criteria": [
                AcceptanceCriterion(
                    given="o advogado está autenticado no sistema",
                    when="ele clica no botão de logout",
                    then="a sessão é invalidada, tokens são revogados e ele é redirecionado para a tela de login",
                ),
            ],
        },
    ]


def get_document_management_story_templates() -> list[dict[str, Any]]:
    """Retorna templates de user stories para o épico de gestão de documentos.

    Returns:
        Lista de dicionários com dados para criação de user stories.
    """
    return [
        {
            "title": "Upload de documento jurídico",
            "persona": "Advogado",
            "persona_type": PersonaType.ADVOGADO,
            "action": "fazer upload de documentos jurídicos (PDF, DOCX)",
            "benefit": "eu possa armazená-los de forma organizada e segura no sistema",
            "priority": MoscowPriority.MUST_HAVE,
            "epic": EpicCategory.GESTAO_DOCUMENTOS,
            "acceptance_criteria": [
                AcceptanceCriterion(
                    given="o advogado está na tela de upload de documentos",
                    when="ele seleciona um arquivo PDF de até 50MB e confirma o upload",
                    then="o documento é armazenado com sucesso e aparece na lista de documentos com metadados extraídos",
                ),
                AcceptanceCriterion(
                    given="o advogado tenta fazer upload de um arquivo com formato não suportado",
                    when="ele seleciona um arquivo .exe",
                    then="o sistema rejeita o upload com mensagem clara sobre formatos aceitos",
                ),
                AcceptanceCriterion(
                    given="o advogado tenta fazer upload de um arquivo maior que o limite",
                    when="ele seleciona um arquivo de 100MB",
                    then="o sistema informa o limite máximo de tamanho permitido",
                ),
            ],
            "technical_notes": [
                TechnicalNote(
                    category="segurança",
                    description="Validar tipo MIME real do arquivo (não apenas extensão). Executar varredura antivírus. Limitar tamanho a 50MB. Armazenar com nome randomizado.",
                ),
                TechnicalNote(
                    category="integração",
                    description="Utilizar react-dropzone no frontend com validação client-side. Processar extração de texto via Celery worker assíncrono.",
                ),
            ],
        },
        {
            "title": "Listagem e busca de documentos",
            "persona": "Advogado",
            "persona_type": PersonaType.ADVOGADO,
            "action": "listar, filtrar e buscar documentos por título, tipo ou data",
            "benefit": "eu encontre rapidamente o documento que preciso",
            "priority": MoscowPriority.MUST_HAVE,
            "epic": EpicCategory.GESTAO_DOCUMENTOS,
            "acceptance_criteria": [
                AcceptanceCriterion(
                    given="o advogado possui documentos cadastrados",
                    when="ele acessa a tela de documentos",
                    then="uma lista paginada é exibida com título, tipo, data de upload e status",
                ),
                AcceptanceCriterion(
                    given="o advogado deseja encontrar um documento específico",
                    when="ele digita um termo no campo de busca",
                    then="a lista é filtrada em tempo real mostrando apenas documentos relevantes",
                ),
            ],
        },
    ]


def get_ai_analysis_story_templates() -> list[dict[str, Any]]:
    """Retorna templates de user stories para o épico de análise com IA.

    Returns:
        Lista de dicionários com dados para criação de user stories.
    """
    return [
        {
            "title": "Análise de documento com IA",
            "persona": "Advogado",
            "persona_type": PersonaType.ADVOGADO,
            "action": "solicitar análise de um documento jurídico pela IA (Claude)",
            "benefit": "eu obtenha um resumo, pontos-chave e riscos identificados automaticamente",
            "priority": MoscowPriority.MUST_HAVE,
            "epic": EpicCategory.ANALISE_IA,
            "acceptance_criteria": [
                AcceptanceCriterion(
                    given="o advogado possui um documento já carregado no sistema",
                    when="ele solicita a análise do documento pela IA",
                    then="o sistema processa o documento e exibe resumo, pontos-chave e riscos identificados em até 60 segundos",
                ),
                AcceptanceCriterion(
                    given="a API da Anthropic está indisponível",
                    when="o advogado solicita análise",
                    then="o sistema informa que o serviço está temporariamente indisponível e oferece opção de notificação quando disponível",
                ),
            ],
            "technical_notes": [
                TechnicalNote(
                    category="integração",
                    description="Utilizar SDK oficial anthropic com httpx assíncrono. Implementar retry com tenacity (3 tentativas, backoff exponencial). Processar via Celery para não bloquear request.",
                ),
                TechnicalNote(
                    category="performance",
                    description="Cache de análises já realizadas. Timeout de 120s para chamada à API. Circuit breaker após 5 falhas consecutivas.",
                ),
            ],
        },
        {
            "title": "Chat assistido com contexto de documento",
            "persona": "Advogado",
            "persona_type": PersonaType.ADVOGADO,
            "action": "conversar com a IA sobre um documento específico fazendo perguntas",
            "benefit": "eu possa esclarecer dúvidas e obter insights adicionais sobre o conteúdo",
            "priority": MoscowPriority.SHOULD_HAVE,
            "epic": EpicCategory.CHAT_ASSISTIDO,
            "acceptance_criteria": [
                AcceptanceCriterion(
                    given="o advogado está visualizando a análise de um documento",
                    when="ele abre o chat e faz uma pergunta sobre o documento",
                    then="a IA responde considerando o contexto completo do documento e do histórico da conversa",
                ),
            ],
        },
    ]


def get_audit_story_templates() -> list[dict[str, Any]]:
    """Retorna templates de user stories para o épico de auditoria.

    Returns:
        Lista de dicionários com dados para criação de user stories.
    """
    return [
        {
            "title": "Log de auditoria de ações",
            "persona": "Gestor do Escritório",
            "persona_type": PersonaType.GESTOR_ESCRITORIO,
            "action": "visualizar logs de auditoria de todas as ações realizadas no sistema",
            "benefit": "eu possa rastrear quem fez o quê e quando para fins de compliance",
            "priority": MoscowPriority.MUST_HAVE,
            "epic": EpicCategory.AUDITORIA,
            "acceptance_criteria": [
                AcceptanceCriterion(
                    given="o gestor possui permissão de administrador",
                    when="ele acessa a tela de auditoria",
                    then="uma lista paginada de eventos é exibida com usuário, ação, recurso, timestamp e IP",
                ),
                AcceptanceCriterion(
                    given="o gestor deseja investigar ações de um usuário específico",
                    when="ele filtra por nome de usuário e período",
                    then="apenas os eventos correspondentes são exibidos",
                ),
            ],
            "technical_notes": [
                TechnicalNote(
                    category="compliance",
                    description="Logs de auditoria devem ser imutáveis (append-only). Retenção mínima de 5 anos conforme regulamentações jurídicas. Utilizar structlog para logs estruturados.",
                ),
            ],
        },
    ]


def get_datajud_story_templates() -> list[dict[str, Any]]:
    """Retorna templates de user stories para integração com DataJud.

    Returns:
        Lista de dicionários com dados para criação de user stories.
    """
    return [
        {
            "title": "Consulta de processos no DataJud",
            "persona": "Advogado",
            "persona_type": PersonaType.ADVOGADO,
            "action": "consultar processos judiciais no DataJud pelo número do processo",
            "benefit": "eu possa acompanhar andamentos processuais de forma integrada",
            "priority": MoscowPriority.SHOULD_HAVE,
            "epic": EpicCategory.DATAJUD_INTEGRACAO,
            "acceptance_criteria": [
                AcceptanceCriterion(
                    given="o advogado possui o número de um processo judicial",
                    when="ele informa o número na tela de consulta DataJud",
                    then="o sistema exibe os dados do processo incluindo partes, movimentações e status atual",
                ),
            ],
            "technical_notes": [
                TechnicalNote(
                    category="integração",
                    description="Implementar state machine para ciclo de vida de documentos DataJud usando python-statemachine. Cache de consultas por 1 hora.",
                ),
            ],
        },
    ]


def get_all_story_templates() -> list[dict[str, Any]]:
    """Retorna todos os templates de user stories disponíveis.

    Returns:
        Lista consolidada de todos os templates de user stories.
    """
    templates: list[dict[str, Any]] = []
    templates.extend(get_authentication_story_templates())
    templates.extend(get_document_management_story_templates())
    templates.extend(get_ai_analysis_story_templates())
    templates.extend(get_audit_story_templates())
    templates.extend(get_datajud_story_templates())
    return templates


# ---------------------------------------------------------------------------
# Serviço de User Stories
# ---------------------------------------------------------------------------


class UserStoryService:
    """Serviço para criação, validação e gerenciamento de user stories.

    Fornece operações CRUD em memória para user stories e definições de MVP.
    Em produção, este serviço deve ser integrado com a camada de persistência
    (repositório) via injeção de dependência.
    """

    def __init__(self) -> None:
        """Inicializa o serviço com armazenamento em memória."""
        self._stories: dict[str, UserStory] = {}
        self._mvp_definitions: dict[str, MVPDefinition] = {}
        self._story_counter: int = 0

    def _generate_code(self) -> str:
        """Gera código sequencial para user stories.

        Returns:
            Código no formato US-XXX.
        """
        self._story_counter += 1
        return f"US-{self._story_counter:03d}"

    def create_user_story(
        self,
        title: str,
        persona: str,
        action: str,
        benefit: str,
        priority: MoscowPriority,
        persona_type: PersonaType = PersonaType.CUSTOM,
        epic: Optional[EpicCategory] = None,
        size: Optional[StorySize] = None,
        story_points: Optional[int] = None,
        acceptance_criteria: Optional[list[AcceptanceCriterion]] = None,
        technical_notes: Optional[list[TechnicalNote]] = None,
        tags: Optional[list[str]] = None,
        created_by: Optional[str] = None,
    ) -> UserStory:
        """Cria uma nova user story.

        Args:
            title: Título conciso da story.
            persona: Nome da persona.
            action: Ação desejada pela persona.
            benefit: Benefício esperado.
            priority: Prioridade MoSCoW.
            persona_type: Tipo de persona pré-definida.
            epic: Épico ao qual pertence.
            size: Estimativa de tamanho.
            story_points: Story points (Fibonacci).
            acceptance_criteria: Critérios de aceite.
            technical_notes: Notas técnicas.
            tags: Tags de categorização.
            created_by: ID do criador.

        Returns:
            UserStory criada e armazenada.
        """
        story = UserStory(
            code=self._generate_code(),
            title=title,
            persona=persona,
            persona_type=persona_type,
            action=action,
            benefit=benefit,
            priority=priority,
            epic=epic,
            size=size,
            story_points=story_points,
            acceptance_criteria=acceptance_criteria or [],
            technical_notes=technical_notes or [],
            tags=tags or [],
            created_by=created_by,
        )
        self._stories[story.id] = story
        return story

    def get_story(self, story_id: str) -> Optional[UserStory]:
        """Busca uma user story pelo ID.

        Args:
            story_id: Identificador da story.

        Returns:
            UserStory encontrada ou None.
        """
        return self._stories.get(story_id)

    def get_story_by_code(self, code: str) -> Optional[UserStory]:
        """Busca uma user story pelo código (ex: US-001).

        Args:
            code: Código da story.

        Returns:
            UserStory encontrada ou None.
        """
        for story in self._stories.values():
            if story.code == code:
                return story
        return None

    def list_stories(
        self,
        priority: Optional[MoscowPriority] = None,
        status: Optional[StoryStatus] = None,
        epic: Optional[EpicCategory] = None,
    ) -> list[UserStory]:
        """Lista user stories com filtros opcionais.

        Args:
            priority: Filtrar por prioridade MoSCoW.
            status: Filtrar por status.
            epic: Filtrar por épico.

        Returns:
            Lista de user stories que atendem aos filtros.
        """
        stories = list(self._stories.values())

        if priority is not None:
            stories = [s for s in stories if s.priority == priority]
        if status is not None:
            stories = [s for s in stories if s.status == status]
        if epic is not None:
            stories = [s for s in stories if s.epic == epic]

        return stories

    def update_story_status(
        self, story_id: str, new_status: StoryStatus
    ) -> Optional[UserStory]:
        """Atualiza o status de uma user story.

        Args:
            story_id: Identificador da story.
            new_status: Novo status.

        Returns:
            UserStory atualizada ou None se não encontrada.
        """
        story = self._stories.get(story_id)
        if story is None:
            return None

        # Validação: não pode ir para READY sem critérios de aceite
        if new_status == StoryStatus.READY and not story.acceptance_criteria:
            raise ValueError(
                f"Não é possível marcar a story '{story.title}' como READY "
                f"sem critérios de aceite definidos."
            )

        story.status = new_status
        story.updated_at = datetime.now(timezone.utc)
        return story

    def update_story_priority(
        self, story_id: str, new_priority: MoscowPriority
    ) -> Optional[UserStory]:
        """Atualiza a prioridade MoSCoW de uma user story.

        Args:
            story_id: Identificador da story.
            new_priority: Nova prioridade.

        Returns:
            UserStory atualizada ou None se não encontrada.
        """
        story = self._stories.get(story_id)
        if story is None:
            return None

        story.priority = new_priority
        story.updated_at = datetime.now(timezone.utc)
        return story

    def add_acceptance_criterion(
        self, story_id: str, criterion: AcceptanceCriterion
    ) -> Optional[UserStory]:
        """Adiciona um critério de aceite a uma user story.

        Args:
            story_id: Identificador da story.
            criterion: Critério de aceite a adicionar.

        Returns:
            UserStory atualizada ou None se não encontrada.
        """
        story = self._stories.get(story_id)
        if story is None:
            return None

        story.acceptance_criteria.append(criterion)
        story.updated_at = datetime.now(timezone.utc)
        return story

    def add_technical_note(
        self, story_id: str, note: TechnicalNote
    ) -> Optional[UserStory]:
        """Adiciona uma nota técnica a uma user story.

        Args:
            story_id: Identificador da story.
            note: Nota técnica a adicionar.

        Returns:
            UserStory atualizada ou None se não encontrada.
        """
        story = self._stories.get(story_id)
        if story is None:
            return None

        story.technical_notes.append(note)
        story.updated_at = datetime.now(timezone.utc)
        return story

    def add_dependency(
        self, story_id: str, dependency: DependencyLink
    ) -> Optional[UserStory]:
        """Adiciona uma dependência a uma user story.

        Args:
            story_id: Identificador da story.
            dependency: Link de dependência.

        Returns:
            UserStory atualizada ou None se não encontrada.
        """
        story = self._stories.get(story_id)
        if story is None:
            return None

        # Validar que a story alvo existe
        if dependency.target_story_id not in self._stories:
            raise ValueError(
                f"Story alvo '{dependency.target_story_id}' não encontrada. "
                f"Não é possível criar dependência para story inexistente."
            )

        # Validar auto-referência
        if dependency.target_story_id == story_id:
            raise ValueError(
                "Uma user story não pode depender de si mesma."
            )

        story.dependencies.append(dependency)
        story.updated_at = datetime.now(timezone.utc)
        return story

    def delete_story(self, story_id: str) -> bool:
        """Remove uma user story.

        Args:
            story_id: Identificador da story.

        Returns:
            True se removida, False se não encontrada.
        """
        if story_id in self._stories:
            del self._stories[story_id]
            return True
        return False

    # -----------------------------------------------------------------------
    # Operações de MVP
    # -----------------------------------------------------------------------

    def create_mvp_definition(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        target_date: Optional[datetime] = None,
        success_metrics: Optional[list[str]] = None,
        constraints: Optional[list[str]] = None,
    ) -> MVPDefinition:
        """Cria uma nova definição de MVP.

        Args:
            name: Nome do MVP.
            description: Descrição detalhada.
            version: Versão do MVP.
            target_date: Data alvo de entrega.
            success_metrics: Métricas de sucesso.
            constraints: Restrições e premissas.

        Returns:
            MVPDefinition criada.
        """
        mvp = MVPDefinition(
            name=name,
            description=description,
            version=version,
            target_date=target_date,
            success_metrics=success_metrics or [],
            constraints=constraints or [],
        )
        self._mvp_definitions[mvp.id] = mvp
        return mvp

    def add_story_to_mvp(
        self, mvp_id: str, story_id: str
    ) -> Optional[MVPDefinition]:
        """Adiciona uma user story a uma definição de MVP.

        Args:
            mvp_id: Identificador do MVP.
            story_id: Identificador da story.

        Returns:
            MVPDefinition atualizada ou None se MVP/story não encontrada.
        """
        mvp = self._mvp_definitions.get(mvp_id)
        if mvp is None:
            return None

        story = self._stories.get(story_id)
        if story is None:
            raise ValueError(
                f"User story '{story_id}' não encontrada."
            )

        # Verificar duplicata
        existing_ids = {s.id for s in mvp.stories}
        if story.id in existing_ids:
            raise ValueError(
                f"User story '{story.title}' já está incluída neste MVP."
            )

        mvp.stories.append(story)
        mvp.updated_at = datetime.now(timezone.utc)
        return mvp

    def get_mvp_definition(self, mvp_id: str) -> Optional[MVPDefinition]:
        """Busca uma definição de MVP pelo ID.

        Args:
            mvp_id: Identificador do MVP.

        Returns:
            MVPDefinition encontrada ou None.
        """
        return self._mvp_definitions.get(mvp_id)

    def validate_mvp(self, mvp_id: str) -> list[str]:
        """Valida se um MVP está pronto para desenvolvimento.

        Args:
            mvp_id: Identificador do MVP.

        Returns:
            Lista de problemas encontrados. Lista vazia = MVP pronto.

        Raises:
            ValueError: Se o MVP não for encontrado.
        """
        mvp = self._mvp_definitions.get(mvp_id)
        if mvp is None:
            raise ValueError(f"MVP '{mvp_id}' não encontrado.")
        return mvp.validate_mvp_readiness()

    # -----------------------------------------------------------------------
    # Operações de templates
    # -----------------------------------------------------------------------

    def load_templates(
        self, templates: Optional[list[dict[str, Any]]] = None
    ) -> list[UserStory]:
        """Carrega user stories a partir de templates.

        Se nenhum template for fornecido, carrega todos os templates
        pré-definidos do domínio jurídico.

        Args:
            templates: Lista de dicionários com dados de stories.
                       Se None, usa get_all_story_templates().

        Returns:
            Lista de UserStory criadas a partir dos templates.
        """
        if templates is None:
            templates = get_all_story_templates()

        created_stories: list[UserStory] = []
        for template in templates:
            story = self.create_user_story(
                title=template["title"],
                persona=template["persona"],
                persona_type=template.get("persona_type", PersonaType.CUSTOM),
                action=template["action"],
                benefit=template["benefit"],
                priority=template["priority"],
                epic=template.get("epic"),
                acceptance_criteria=template.get("acceptance_criteria", []),
                technical_notes=template.get("technical_notes", []),
                tags=template.get("tags", []),
            )
            created_stories.append(story)

        return created_stories

    # -----------------------------------------------------------------------
    # Relatórios e métricas
    # -----------------------------------------------------------------------

    def backlog_summary(self) -> dict[str, Any]:
        """Gera resumo do backlog de user stories.

        Returns:
            Dicionário com métricas do backlog.
        """
        stories = list(self._stories.values())
        total = len(stories)

        priority_counts = {
            p.value: len([s for s in stories if s.priority == p])
            for p in MoscowPriority
        }

        status_counts = {
            s.value: len([st for st in stories if st.status == s])
            for s in StoryStatus
        }

        epic_counts: dict[str, int] = {}
        for story in stories:
            epic_key = story.epic.value if story.epic else "sem_epico"
            epic_counts[epic_key] = epic_counts.get(epic_key, 0) + 1

        stories_with_criteria = len(
            [s for s in stories if s.acceptance_criteria]
        )
        stories_with_estimates = len(
            [s for s in stories if s.size is not None or s.story_points is not None]
        )

        avg_completeness = (
            round(sum(s.completeness_score() for s in stories) / total, 2)
            if total > 0
            else 0.0
        )

        return {
            "total_stories": total,
            "por_prioridade": priority_counts,
            "por_status": status_counts,
            "por_epico": epic_counts,
            "stories_com_criterios_aceite": stories_with_criteria,
            "stories_com_estimativa": stories_with_estimates,
            "completude_media": avg_completeness,
            "percentual_mvp": (
                round(
                    priority_counts.get(MoscowPriority.MUST_HAVE.value, 0)
                    / total
                    * 100,
                    1,
                )
                if total > 0
                else 0.0
            ),
        }

    def detect_circular_dependencies(self) -> list[list[str]]:
        """Detecta dependências circulares entre user stories.

        Utiliza DFS para encontrar ciclos no grafo de dependências.

        Returns:
            Lista de ciclos encontrados (cada ciclo é uma lista de IDs).
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def _dfs(node_id: str) -> None:
            """Busca em profundidade para detecção de ciclos."""
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            story = self._stories.get(node_id)
            if story:
                for dep in story.dependencies:
                    target = dep.target_story_id
                    if target not in visited:
                        _dfs(target)
                    elif target in rec_stack:
                        # Ciclo encontrado
                        cycle_start = path.index(target)
                        cycle = path[cycle_start:] + [target]
                        cycles.append(cycle)

            path.pop()
            rec_stack.discard(node_id)

        for story_id in self._stories:
            if story_id not in visited:
                _dfs(story_id)

        return cycles
