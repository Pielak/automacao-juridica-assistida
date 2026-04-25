"""Módulo backlog #11: Configuração de E2E Testing.

Configuração centralizada para testes end-to-end utilizando Playwright,
incluindo definição de cenários críticos, fixtures, helpers e configurações
de ambiente para execução dos testes E2E do sistema de Automação Jurídica Assistida.

Este módulo fornece:
- Configurações de ambiente para testes E2E
- Definição de cenários críticos de teste
- Fixtures e helpers reutilizáveis
- Utilitários para setup/teardown de dados de teste
- Integração com o backend FastAPI para testes contra servidor real
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums e constantes
# ---------------------------------------------------------------------------

class BrowserType(str, Enum):
    """Tipos de navegador suportados para testes E2E."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class TestEnvironment(str, Enum):
    """Ambientes de execução dos testes E2E."""

    LOCAL = "local"
    CI = "ci"
    STAGING = "staging"


class TestPriority(str, Enum):
    """Prioridade dos cenários de teste."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Timeouts padrão (em milissegundos)
DEFAULT_TIMEOUT_MS = 30_000
NAVIGATION_TIMEOUT_MS = 60_000
ACTION_TIMEOUT_MS = 15_000
ASSERTION_TIMEOUT_MS = 10_000

# Dimensões de viewport padrão
DEFAULT_VIEWPORT = {"width": 1280, "height": 720}
MOBILE_VIEWPORT = {"width": 375, "height": 812}
TABLET_VIEWPORT = {"width": 768, "height": 1024}


# ---------------------------------------------------------------------------
# Configuração principal de E2E
# ---------------------------------------------------------------------------

@dataclass
class E2ETestConfig:
    """Configuração centralizada para execução de testes E2E.

    Agrupa todas as configurações necessárias para executar os testes
    end-to-end, incluindo URLs, credenciais de teste, timeouts e
    opções de navegador.

    Attributes:
        base_url: URL base do frontend para testes.
        api_base_url: URL base da API backend.
        environment: Ambiente de execução (local, ci, staging).
        browsers: Lista de navegadores para execução.
        headless: Se True, executa navegadores sem interface gráfica.
        slow_mo: Atraso entre ações (ms) para depuração visual.
        default_timeout: Timeout padrão para operações (ms).
        navigation_timeout: Timeout para navegação de páginas (ms).
        retries: Número de tentativas em caso de falha.
        workers: Número de workers paralelos.
        video_on_failure: Se True, grava vídeo em caso de falha.
        screenshot_on_failure: Se True, captura screenshot em caso de falha.
        trace_on_failure: Se True, grava trace do Playwright em caso de falha.
        output_dir: Diretório para artefatos de teste.
    """

    base_url: str = "http://localhost:5173"
    api_base_url: str = "http://localhost:8000"
    environment: TestEnvironment = TestEnvironment.LOCAL
    browsers: list[BrowserType] = field(
        default_factory=lambda: [BrowserType.CHROMIUM]
    )
    headless: bool = True
    slow_mo: int = 0
    default_timeout: int = DEFAULT_TIMEOUT_MS
    navigation_timeout: int = NAVIGATION_TIMEOUT_MS
    retries: int = 0
    workers: int = 1
    video_on_failure: bool = True
    screenshot_on_failure: bool = True
    trace_on_failure: bool = True
    output_dir: str = "test-results/e2e"

    @classmethod
    def from_env(cls) -> E2ETestConfig:
        """Cria configuração a partir de variáveis de ambiente.

        Variáveis de ambiente suportadas:
            E2E_BASE_URL: URL base do frontend.
            E2E_API_BASE_URL: URL base da API.
            E2E_ENVIRONMENT: Ambiente (local, ci, staging).
            E2E_HEADLESS: Modo headless (true/false).
            E2E_SLOW_MO: Atraso entre ações em ms.
            E2E_RETRIES: Número de retentativas.
            E2E_WORKERS: Número de workers paralelos.
            E2E_BROWSERS: Navegadores separados por vírgula.

        Returns:
            Instância de E2ETestConfig configurada.
        """
        env = os.environ.get("E2E_ENVIRONMENT", "local")
        headless_raw = os.environ.get("E2E_HEADLESS", "true")
        browsers_raw = os.environ.get("E2E_BROWSERS", "chromium")

        browsers = [
            BrowserType(b.strip())
            for b in browsers_raw.split(",")
            if b.strip() in BrowserType.__members__.values()
            or b.strip() in [e.value for e in BrowserType]
        ]
        if not browsers:
            browsers = [BrowserType.CHROMIUM]

        return cls(
            base_url=os.environ.get("E2E_BASE_URL", "http://localhost:5173"),
            api_base_url=os.environ.get(
                "E2E_API_BASE_URL", "http://localhost:8000"
            ),
            environment=TestEnvironment(env),
            browsers=browsers,
            headless=headless_raw.lower() in ("true", "1", "yes"),
            slow_mo=int(os.environ.get("E2E_SLOW_MO", "0")),
            retries=int(os.environ.get("E2E_RETRIES", "0")),
            workers=int(os.environ.get("E2E_WORKERS", "1")),
        )

    def get_ci_overrides(self) -> dict[str, Any]:
        """Retorna overrides específicos para ambiente de CI.

        Returns:
            Dicionário com configurações otimizadas para CI.
        """
        return {
            "headless": True,
            "retries": 2,
            "workers": 2,
            "video_on_failure": True,
            "screenshot_on_failure": True,
            "trace_on_failure": True,
            "slow_mo": 0,
        }

    def apply_ci_overrides(self) -> None:
        """Aplica overrides de CI se o ambiente for CI."""
        if self.environment == TestEnvironment.CI:
            overrides = self.get_ci_overrides()
            for key, value in overrides.items():
                setattr(self, key, value)


# ---------------------------------------------------------------------------
# Credenciais de teste
# ---------------------------------------------------------------------------

@dataclass
class TestUser:
    """Representa um usuário de teste para cenários E2E.

    Attributes:
        email: Email do usuário de teste.
        password: Senha do usuário de teste.
        role: Papel/perfil RBAC do usuário.
        display_name: Nome de exibição.
        mfa_enabled: Se o usuário possui MFA habilitado.
        mfa_secret: Segredo TOTP para MFA (se habilitado).
    """

    email: str
    password: str
    role: str
    display_name: str
    mfa_enabled: bool = False
    mfa_secret: str | None = None


@dataclass
class TestCredentials:
    """Conjunto de credenciais de teste para diferentes perfis.

    Fornece usuários pré-configurados para cada perfil RBAC
    do sistema, permitindo testar fluxos com diferentes níveis
    de permissão.
    """

    admin: TestUser = field(default_factory=lambda: TestUser(
        email=os.environ.get("E2E_ADMIN_EMAIL", "admin.teste@automacaojuridica.com.br"),
        password=os.environ.get("E2E_ADMIN_PASSWORD", "TestAdmin@2024!"),
        role="admin",
        display_name="Administrador de Teste",
    ))
    lawyer: TestUser = field(default_factory=lambda: TestUser(
        email=os.environ.get("E2E_LAWYER_EMAIL", "advogado.teste@automacaojuridica.com.br"),
        password=os.environ.get("E2E_LAWYER_PASSWORD", "TestLawyer@2024!"),
        role="lawyer",
        display_name="Advogado de Teste",
    ))
    analyst: TestUser = field(default_factory=lambda: TestUser(
        email=os.environ.get("E2E_ANALYST_EMAIL", "analista.teste@automacaojuridica.com.br"),
        password=os.environ.get("E2E_ANALYST_PASSWORD", "TestAnalyst@2024!"),
        role="analyst",
        display_name="Analista de Teste",
    ))
    viewer: TestUser = field(default_factory=lambda: TestUser(
        email=os.environ.get("E2E_VIEWER_EMAIL", "visualizador.teste@automacaojuridica.com.br"),
        password=os.environ.get("E2E_VIEWER_PASSWORD", "TestViewer@2024!"),
        role="viewer",
        display_name="Visualizador de Teste",
    ))

    def get_user_by_role(self, role: str) -> TestUser:
        """Retorna o usuário de teste correspondente ao perfil informado.

        Args:
            role: Nome do perfil RBAC.

        Returns:
            Instância de TestUser para o perfil.

        Raises:
            ValueError: Se o perfil não for reconhecido.
        """
        role_map = {
            "admin": self.admin,
            "lawyer": self.lawyer,
            "analyst": self.analyst,
            "viewer": self.viewer,
        }
        user = role_map.get(role)
        if user is None:
            raise ValueError(
                f"Perfil de teste '{role}' não reconhecido. "
                f"Perfis disponíveis: {list(role_map.keys())}"
            )
        return user


# ---------------------------------------------------------------------------
# Definição de cenários críticos de teste
# ---------------------------------------------------------------------------

@dataclass
class E2ETestScenario:
    """Representa um cenário de teste E2E.

    Attributes:
        id: Identificador único do cenário.
        name: Nome descritivo do cenário.
        description: Descrição detalhada do que é testado.
        priority: Prioridade do cenário.
        module: Módulo funcional relacionado.
        tags: Tags para filtragem de cenários.
        required_role: Perfil RBAC necessário para execução.
        steps: Lista de passos do cenário (descrição textual).
        preconditions: Pré-condições necessárias.
        expected_result: Resultado esperado ao final.
    """

    id: str
    name: str
    description: str
    priority: TestPriority
    module: str
    tags: list[str] = field(default_factory=list)
    required_role: str = "lawyer"
    steps: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    expected_result: str = ""


def get_critical_test_scenarios() -> list[E2ETestScenario]:
    """Retorna a lista de cenários críticos de teste E2E.

    Estes cenários cobrem os fluxos mais importantes do sistema
    e devem ser executados em toda pipeline de CI/CD.

    Returns:
        Lista de cenários E2E críticos ordenados por prioridade.
    """
    scenarios = [
        # ---------------------------------------------------------------
        # Módulo: Autenticação (auth)
        # ---------------------------------------------------------------
        E2ETestScenario(
            id="E2E-AUTH-001",
            name="Login com credenciais válidas",
            description="Verifica que um usuário consegue realizar login com email e senha válidos e é redirecionado ao dashboard.",
            priority=TestPriority.CRITICAL,
            module="auth",
            tags=["auth", "login", "smoke"],
            required_role="lawyer",
            preconditions=[
                "Usuário de teste cadastrado no sistema",
                "Servidor backend em execução",
            ],
            steps=[
                "Acessar a página de login",
                "Preencher o campo de email com credenciais válidas",
                "Preencher o campo de senha",
                "Clicar no botão 'Entrar'",
                "Aguardar redirecionamento ao dashboard",
            ],
            expected_result="Usuário autenticado e redirecionado ao dashboard com token JWT válido.",
        ),
        E2ETestScenario(
            id="E2E-AUTH-002",
            name="Login com credenciais inválidas",
            description="Verifica que o sistema exibe mensagem de erro adequada ao tentar login com credenciais inválidas.",
            priority=TestPriority.CRITICAL,
            module="auth",
            tags=["auth", "login", "negative"],
            required_role="lawyer",
            preconditions=["Servidor backend em execução"],
            steps=[
                "Acessar a página de login",
                "Preencher email com valor inválido",
                "Preencher senha incorreta",
                "Clicar no botão 'Entrar'",
                "Verificar mensagem de erro exibida",
            ],
            expected_result="Mensagem de erro 'Credenciais inválidas' exibida. Usuário permanece na tela de login.",
        ),
        E2ETestScenario(
            id="E2E-AUTH-003",
            name="Login com MFA (TOTP)",
            description="Verifica o fluxo completo de login com autenticação multifator via TOTP.",
            priority=TestPriority.CRITICAL,
            module="auth",
            tags=["auth", "login", "mfa", "totp"],
            required_role="admin",
            preconditions=[
                "Usuário com MFA habilitado",
                "Segredo TOTP disponível para geração de código",
            ],
            steps=[
                "Acessar a página de login",
                "Preencher credenciais válidas",
                "Clicar no botão 'Entrar'",
                "Aguardar tela de verificação MFA",
                "Gerar código TOTP a partir do segredo",
                "Preencher código TOTP",
                "Confirmar verificação",
            ],
            expected_result="Usuário autenticado com MFA e redirecionado ao dashboard.",
        ),
        E2ETestScenario(
            id="E2E-AUTH-004",
            name="Logout e invalidação de sessão",
            description="Verifica que o logout invalida a sessão e impede acesso a rotas protegidas.",
            priority=TestPriority.HIGH,
            module="auth",
            tags=["auth", "logout", "session"],
            required_role="lawyer",
            preconditions=["Usuário autenticado no sistema"],
            steps=[
                "Realizar login com credenciais válidas",
                "Verificar acesso ao dashboard",
                "Clicar no botão de logout",
                "Verificar redirecionamento à tela de login",
                "Tentar acessar rota protegida diretamente",
                "Verificar redirecionamento à tela de login",
            ],
            expected_result="Sessão invalidada. Acesso a rotas protegidas bloqueado após logout.",
        ),
        E2ETestScenario(
            id="E2E-AUTH-005",
            name="Proteção de rotas — acesso não autenticado",
            description="Verifica que rotas protegidas redirecionam usuários não autenticados para login.",
            priority=TestPriority.CRITICAL,
            module="auth",
            tags=["auth", "guards", "security"],
            required_role="lawyer",
            preconditions=["Nenhum token JWT armazenado"],
            steps=[
                "Acessar diretamente URL protegida (ex: /dashboard)",
                "Verificar redirecionamento para /login",
                "Acessar diretamente URL de documentos (ex: /documentos)",
                "Verificar redirecionamento para /login",
            ],
            expected_result="Todas as rotas protegidas redirecionam para /login quando não autenticado.",
        ),

        # ---------------------------------------------------------------
        # Módulo: Documentos (documents)
        # ---------------------------------------------------------------
        E2ETestScenario(
            id="E2E-DOC-001",
            name="Upload de documento jurídico",
            description="Verifica o fluxo completo de upload de um documento jurídico (PDF) com validação de tipo e tamanho.",
            priority=TestPriority.CRITICAL,
            module="documents",
            tags=["documents", "upload", "smoke"],
            required_role="lawyer",
            preconditions=[
                "Usuário autenticado com perfil advogado",
                "Arquivo PDF de teste disponível (< 10MB)",
            ],
            steps=[
                "Navegar até a seção de documentos",
                "Clicar no botão 'Novo Documento' ou área de upload",
                "Selecionar arquivo PDF válido via drag-and-drop ou seletor",
                "Preencher metadados obrigatórios (título, tipo, área jurídica)",
                "Confirmar upload",
                "Aguardar processamento",
                "Verificar documento listado com status correto",
            ],
            expected_result="Documento enviado com sucesso, listado na tabela com status 'Processado'.",
        ),
        E2ETestScenario(
            id="E2E-DOC-002",
            name="Rejeição de arquivo inválido no upload",
            description="Verifica que o sistema rejeita arquivos com tipo ou tamanho inválido durante upload.",
            priority=TestPriority.HIGH,
            module="documents",
            tags=["documents", "upload", "validation", "negative"],
            required_role="lawyer",
            preconditions=["Usuário autenticado"],
            steps=[
                "Navegar até a seção de documentos",
                "Tentar upload de arquivo .exe",
                "Verificar mensagem de erro de tipo inválido",
                "Tentar upload de arquivo PDF > limite de tamanho",
                "Verificar mensagem de erro de tamanho excedido",
            ],
            expected_result="Sistema rejeita arquivos inválidos com mensagens claras de erro.",
        ),
        E2ETestScenario(
            id="E2E-DOC-003",
            name="Listagem e busca de documentos",
            description="Verifica a listagem paginada de documentos e funcionalidade de busca/filtro.",
            priority=TestPriority.HIGH,
            module="documents",
            tags=["documents", "list", "search"],
            required_role="lawyer",
            preconditions=[
                "Usuário autenticado",
                "Ao menos 5 documentos cadastrados",
            ],
            steps=[
                "Navegar até a seção de documentos",
                "Verificar listagem paginada",
                "Utilizar campo de busca com termo conhecido",
                "Verificar resultados filtrados",
                "Aplicar filtro por tipo de documento",
                "Verificar resultados filtrados por tipo",
                "Limpar filtros e verificar listagem completa",
            ],
            expected_result="Documentos listados corretamente com paginação, busca e filtros funcionais.",
        ),

        # ---------------------------------------------------------------
        # Módulo: Análise com IA (analysis)
        # ---------------------------------------------------------------
        E2ETestScenario(
            id="E2E-AI-001",
            name="Análise de documento com IA (Anthropic Claude)",
            description="Verifica o fluxo completo de solicitação de análise de documento jurídico via IA.",
            priority=TestPriority.CRITICAL,
            module="analysis",
            tags=["analysis", "ia", "anthropic", "smoke"],
            required_role="lawyer",
            preconditions=[
                "Usuário autenticado",
                "Documento já enviado e processado",
                "Integração com Anthropic configurada (ou mock ativo)",
            ],
            steps=[
                "Navegar até o documento processado",
                "Clicar em 'Analisar com IA'",
                "Selecionar tipo de análise desejada",
                "Confirmar solicitação de análise",
                "Aguardar processamento (indicador de progresso)",
                "Verificar resultado da análise exibido",
                "Verificar estrutura do resultado (resumo, pontos-chave, riscos)",
            ],
            expected_result="Análise concluída com resultado estruturado exibido na interface.",
        ),

        # ---------------------------------------------------------------
        # Módulo: Chat com IA (chat)
        # ---------------------------------------------------------------
        E2ETestScenario(
            id="E2E-CHAT-001",
            name="Interação via chat com IA sobre documento",
            description="Verifica o fluxo de chat contextual com IA sobre um documento jurídico.",
            priority=TestPriority.HIGH,
            module="chat",
            tags=["chat", "ia", "anthropic"],
            required_role="lawyer",
            preconditions=[
                "Usuário autenticado",
                "Documento analisado disponível",
                "Integração com Anthropic configurada (ou mock ativo)",
            ],
            steps=[
                "Navegar até o documento analisado",
                "Abrir painel de chat",
                "Digitar pergunta sobre o documento",
                "Enviar mensagem",
                "Aguardar resposta da IA",
                "Verificar resposta contextualizada exibida",
                "Enviar pergunta de acompanhamento",
                "Verificar manutenção do contexto da conversa",
            ],
            expected_result="Chat funcional com respostas contextualizadas ao documento.",
        ),

        # ---------------------------------------------------------------
        # Módulo: RBAC e Permissões
        # ---------------------------------------------------------------
        E2ETestScenario(
            id="E2E-RBAC-001",
            name="Controle de acesso por perfil — visualizador",
            description="Verifica que o perfil visualizador não consegue realizar ações de escrita.",
            priority=TestPriority.CRITICAL,
            module="auth",
            tags=["rbac", "permissions", "security"],
            required_role="viewer",
            preconditions=["Usuário com perfil visualizador autenticado"],
            steps=[
                "Realizar login como visualizador",
                "Navegar até a seção de documentos",
                "Verificar que botão 'Novo Documento' está oculto ou desabilitado",
                "Tentar acessar rota de upload diretamente via URL",
                "Verificar bloqueio de acesso ou redirecionamento",
                "Verificar que ações de edição/exclusão não estão disponíveis",
            ],
            expected_result="Visualizador pode apenas consultar. Ações de escrita bloqueadas.",
        ),

        # ---------------------------------------------------------------
        # Módulo: Responsividade
        # ---------------------------------------------------------------
        E2ETestScenario(
            id="E2E-RESP-001",
            name="Responsividade — fluxo de login em mobile",
            description="Verifica que o fluxo de login funciona corretamente em viewport mobile.",
            priority=TestPriority.HIGH,
            module="ui",
            tags=["responsiveness", "mobile", "login"],
            required_role="lawyer",
            preconditions=["Viewport configurado para 375x812 (iPhone)"],
            steps=[
                "Configurar viewport mobile (375x812)",
                "Acessar página de login",
                "Verificar layout responsivo (sem overflow horizontal)",
                "Preencher credenciais",
                "Realizar login",
                "Verificar dashboard em layout mobile",
                "Verificar menu hambúrguer funcional",
            ],
            expected_result="Fluxo de login e dashboard funcionais em viewport mobile.",
        ),

        # ---------------------------------------------------------------
        # Módulo: Auditoria (audit)
        # ---------------------------------------------------------------
        E2ETestScenario(
            id="E2E-AUDIT-001",
            name="Registro de ações no log de auditoria",
            description="Verifica que ações críticas são registradas no log de auditoria.",
            priority=TestPriority.HIGH,
            module="audit",
            tags=["audit", "compliance", "lgpd"],
            required_role="admin",
            preconditions=["Usuário admin autenticado"],
            steps=[
                "Realizar login como admin",
                "Executar ação auditável (ex: upload de documento)",
                "Navegar até seção de auditoria",
                "Verificar registro da ação no log",
                "Verificar detalhes do registro (usuário, timestamp, ação, IP)",
            ],
            expected_result="Ação registrada no log de auditoria com todos os metadados.",
        ),
    ]

    return sorted(scenarios, key=lambda s: list(TestPriority).index(s.priority))


def get_scenarios_by_module(module: str) -> list[E2ETestScenario]:
    """Filtra cenários de teste por módulo funcional.

    Args:
        module: Nome do módulo (auth, documents, analysis, chat, audit, ui).

    Returns:
        Lista de cenários do módulo especificado.
    """
    return [
        s for s in get_critical_test_scenarios()
        if s.module == module
    ]


def get_scenarios_by_priority(priority: TestPriority) -> list[E2ETestScenario]:
    """Filtra cenários de teste por prioridade.

    Args:
        priority: Nível de prioridade desejado.

    Returns:
        Lista de cenários com a prioridade especificada.
    """
    return [
        s for s in get_critical_test_scenarios()
        if s.priority == priority
    ]


def get_scenarios_by_tag(tag: str) -> list[E2ETestScenario]:
    """Filtra cenários de teste por tag.

    Args:
        tag: Tag para filtragem.

    Returns:
        Lista de cenários que possuem a tag especificada.
    """
    return [
        s for s in get_critical_test_scenarios()
        if tag in s.tags
    ]


def get_smoke_scenarios() -> list[E2ETestScenario]:
    """Retorna cenários de smoke test (tag 'smoke').

    Smoke tests são o subconjunto mínimo de testes que devem
    passar para considerar um deploy viável.

    Returns:
        Lista de cenários de smoke test.
    """
    return get_scenarios_by_tag("smoke")


# ---------------------------------------------------------------------------
# Configuração de rotas/páginas para testes
# ---------------------------------------------------------------------------

@dataclass
class PageRoutes:
    """Mapeamento de rotas da aplicação para uso nos testes E2E.

    Centraliza as URLs das páginas para evitar strings mágicas
    espalhadas nos testes.
    """

    login: str = "/login"
    dashboard: str = "/dashboard"
    documents: str = "/documentos"
    document_upload: str = "/documentos/novo"
    document_detail: str = "/documentos/{id}"
    analysis: str = "/analises"
    analysis_detail: str = "/analises/{id}"
    chat: str = "/chat"
    chat_session: str = "/chat/{id}"
    audit_log: str = "/admin/auditoria"
    users: str = "/admin/usuarios"
    profile: str = "/perfil"
    settings: str = "/configuracoes"

    def document_detail_url(self, doc_id: str) -> str:
        """Gera URL de detalhe de documento.

        Args:
            doc_id: ID do documento.

        Returns:
            URL formatada.
        """
        return self.document_detail.format(id=doc_id)

    def analysis_detail_url(self, analysis_id: str) -> str:
        """Gera URL de detalhe de análise.

        Args:
            analysis_id: ID da análise.

        Returns:
            URL formatada.
        """
        return self.analysis_detail.format(id=analysis_id)

    def chat_session_url(self, session_id: str) -> str:
        """Gera URL de sessão de chat.

        Args:
            session_id: ID da sessão de chat.

        Returns:
            URL formatada.
        """
        return self.chat_session.format(id=session_id)


# ---------------------------------------------------------------------------
# Seletores de UI para testes
# ---------------------------------------------------------------------------

@dataclass
class UISelectors:
    """Seletores de elementos da UI para uso nos testes E2E.

    Utiliza atributos data-testid como estratégia principal de seleção,
    garantindo estabilidade dos testes independente de mudanças visuais.

    Convenção: data-testid="{modulo}-{elemento}-{acao}"
    """

    # Autenticação
    login_email_input: str = "[data-testid='auth-email-input']"
    login_password_input: str = "[data-testid='auth-password-input']"
    login_submit_button: str = "[data-testid='auth-login-button']"
    login_error_message: str = "[data-testid='auth-error-message']"
    mfa_code_input: str = "[data-testid='auth-mfa-code-input']"
    mfa_submit_button: str = "[data-testid='auth-mfa-submit-button']"
    logout_button: str = "[data-testid='auth-logout-button']"

    # Navegação
    nav_sidebar: str = "[data-testid='nav-sidebar']"
    nav_hamburger: str = "[data-testid='nav-hamburger-menu']"
    nav_dashboard_link: str = "[data-testid='nav-dashboard-link']"
    nav_documents_link: str = "[data-testid='nav-documents-link']"
    nav_analysis_link: str = "[data-testid='nav-analysis-link']"
    nav_chat_link: str = "[data-testid='nav-chat-link']"
    nav_audit_link: str = "[data-testid='nav-audit-link']"
    nav_profile_link: str = "[data-testid='nav-profile-link']"

    # Documentos
    doc_upload_button: str = "[data-testid='doc-upload-button']"
    doc_dropzone: str = "[data-testid='doc-dropzone']"
    doc_title_input: str = "[data-testid='doc-title-input']"
    doc_type_select: str = "[data-testid='doc-type-select']"
    doc_area_select: str = "[data-testid='doc-area-select']"
    doc_submit_button: str = "[data-testid='doc-submit-button']"
    doc_list_table: str = "[data-testid='doc-list-table']"
    doc_search_input: str = "[data-testid='doc-search-input']"
    doc_filter_type: str = "[data-testid='doc-filter-type']"
    doc_upload_error: str = "[data-testid='doc-upload-error']"

    # Análise IA
    analysis_trigger_button: str = "[data-testid='analysis-trigger-button']"
    analysis_type_select: str = "[data-testid='analysis-type-select']"
    analysis_confirm_button: str = "[data-testid='analysis-confirm-button']"
    analysis_progress: str = "[data-testid='analysis-progress']"
    analysis_result: str = "[data-testid='analysis-result']"
    analysis_summary: str = "[data-testid='analysis-summary']"

    # Chat
    chat_panel: str = "[data-testid='chat-panel']"
    chat_input: str = "[data-testid='chat-message-input']"
    chat_send_button: str = "[data-testid='chat-send-button']"
    chat_message_list: str = "[data-testid='chat-message-list']"
    chat_ai_response: str = "[data-testid='chat-ai-response']"

    # Auditoria
    audit_log_table: str = "[data-testid='audit-log-table']"
    audit_log_entry: str = "[data-testid='audit-log-entry']"

    # Geral
    loading_spinner: str = "[data-testid='loading-spinner']"
    toast_success: str = "[data-testid='toast-success']"
    toast_error: str = "[data-testid='toast-error']"
    pagination_next: str = "[data-testid='pagination-next']"
    pagination_prev: str = "[data-testid='pagination-prev']"


# ---------------------------------------------------------------------------
# Gerador de configuração Playwright (playwright.config.ts)
# ---------------------------------------------------------------------------

def generate_playwright_config(config: E2ETestConfig | None = None) -> str:
    """Gera o conteúdo do arquivo playwright.config.ts.

    Produz uma configuração TypeScript válida para o Playwright
    baseada nas configurações E2E fornecidas.

    Args:
        config: Configuração E2E. Se None, usa configuração padrão.

    Returns:
        Conteúdo do arquivo playwright.config.ts como string.
    """
    if config is None:
        config = E2ETestConfig.from_env()

    projects = ""
    for browser in config.browsers:
        projects += f"""
    {{
      name: '{browser.value}',
      use: {{ ...devices['Desktop Chrome'] }},
    }},"""

    return f"""// playwright.config.ts
// Gerado automaticamente por m11_e2e_testing_config.py
// NÃO EDITE MANUALMENTE — regenere via script de configuração.

import {{ defineConfig, devices }} from '@playwright/test';

export default defineConfig({{
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? {config.retries or 2} : {config.retries},
  workers: process.env.CI ? {config.workers} : undefined,
  reporter: [
    ['html', {{ outputFolder: '{config.output_dir}/html-report' }}],
    ['json', {{ outputFile: '{config.output_dir}/results.json' }}],
    ['list'],
  ],
  use: {{
    baseURL: process.env.E2E_BASE_URL || '{config.base_url}',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: {ACTION_TIMEOUT_MS},
    navigationTimeout: {NAVIGATION_TIMEOUT_MS},
  }},
  projects: [{projects}
    {{
      name: 'mobile-chrome',
      use: {{ ...devices['Pixel 5'] }},
    }},
  ],
  webServer: {{
    command: 'npm run dev',
    url: '{config.base_url}',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  }},
}});
"""


# ---------------------------------------------------------------------------
# Gerador de fixture base para Playwright (Python - pytest-playwright)
# ---------------------------------------------------------------------------

def generate_conftest_content(config: E2ETestConfig | None = None) -> str:
    """Gera o conteúdo do arquivo conftest.py para testes E2E com pytest-playwright.

    Produz fixtures reutilizáveis para autenticação, navegação
    e setup de dados de teste.

    Args:
        config: Configuração E2E. Se None, usa configuração padrão.

    Returns:
        Conteúdo do arquivo conftest.py como string.
    """
    if config is None:
        config = E2ETestConfig.from_env()

    return f'''"""Fixtures compartilhadas para testes E2E com Playwright.

Gerado automaticamente por m11_e2e_testing_config.py.
"""

import pytest
from playwright.sync_api import Page, BrowserContext, expect


BASE_URL = "{config.base_url}"
API_BASE_URL = "{config.api_base_url}"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configurações adicionais do contexto do navegador."""
    return {{
        **browser_context_args,
        "viewport": {DEFAULT_VIEWPORT},
        "ignore_https_errors": True,
    }}


@pytest.fixture
def authenticated_page(page: Page) -> Page:
    """Fixture que fornece uma página já autenticada.

    Realiza login com o usuário advogado de teste e retorna
    a página pronta para interação.
    """
    page.goto(f"{{BASE_URL}}/login")
    page.fill("[data-testid=\'auth-email-input\']", "advogado.teste@automacaojuridica.com.br")
    page.fill("[data-testid=\'auth-password-input\']", "TestLawyer@2024!")
    page.click("[data-testid=\'auth-login-button\']")
    page.wait_for_url(f"{{BASE_URL}}/dashboard", timeout={config.navigation_timeout})
    return page


@pytest.fixture
def admin_page(page: Page) -> Page:
    """Fixture que fornece uma página autenticada como admin."""
    page.goto(f"{{BASE_URL}}/login")
    page.fill("[data-testid=\'auth-email-input\']", "admin.teste@automacaojuridica.com.br")
    page.fill("[data-testid=\'auth-password-input\']", "TestAdmin@2024!")
    page.click("[data-testid=\'auth-login-button\']")
    # TODO: Implementar fluxo MFA para admin se necessário
    page.wait_for_url(f"{{BASE_URL}}/dashboard", timeout={config.navigation_timeout})
    return page


@pytest.fixture
def viewer_page(page: Page) -> Page:
    """Fixture que fornece uma página autenticada como visualizador."""
    page.goto(f"{{BASE_URL}}/login")
    page.fill("[data-testid=\'auth-email-input\']", "visualizador.teste@automacaojuridica.com.br")
    page.fill("[data-testid=\'auth-password-input\']", "TestViewer@2024!")
    page.click("[data-testid=\'auth-login-button\']")
    page.wait_for_url(f"{{BASE_URL}}/dashboard", timeout={config.navigation_timeout})
    return page
'''


# ---------------------------------------------------------------------------
# Utilitários de setup de dados de teste
# ---------------------------------------------------------------------------

@dataclass
class TestDataConfig:
    """Configuração de dados de teste para cenários E2E.

    Define os dados necessários para popular o ambiente de teste
    antes da execução dos cenários E2E.

    Attributes:
        seed_users: Se True, cria usuários de teste no banco.
        seed_documents: Se True, cria documentos de teste.
        seed_analyses: Se True, cria análises de teste.
        cleanup_after: Se True, remove dados de teste após execução.
        test_pdf_path: Caminho para arquivo PDF de teste.
    """

    seed_users: bool = True
    seed_documents: bool = True
    seed_analyses: bool = False
    cleanup_after: bool = True
    test_pdf_path: str = "tests/fixtures/documento_teste.pdf"


async def setup_test_data(
    api_base_url: str,
    data_config: TestDataConfig | None = None,
) -> dict[str, Any]:
    """Configura dados de teste no backend via API.

    Cria usuários, documentos e outros dados necessários para
    a execução dos testes E2E.

    Args:
        api_base_url: URL base da API backend.
        data_config: Configuração de dados de teste.

    Returns:
        Dicionário com IDs e referências dos dados criados.

    Note:
        Esta função requer que o backend esteja em execução
        e que exista um endpoint de seed de dados de teste
        (disponível apenas em ambiente de teste).
    """
    # TODO: Implementar chamadas HTTP ao backend para seed de dados.
    # Requer endpoint POST /api/v1/test/seed no backend (apenas em env=test).
    # Usar httpx para chamadas assíncronas.
    #
    # Exemplo de implementação:
    # async with httpx.AsyncClient(base_url=api_base_url) as client:
    #     if data_config.seed_users:
    #         response = await client.post("/api/v1/test/seed/users")
    #         users = response.json()
    #     if data_config.seed_documents:
    #         response = await client.post("/api/v1/test/seed/documents")
    #         documents = response.json()

    if data_config is None:
        data_config = TestDataConfig()

    created_data: dict[str, Any] = {
        "users": [],
        "documents": [],
        "analyses": [],
    }

    return created_data


async def teardown_test_data(
    api_base_url: str,
    created_data: dict[str, Any],
) -> None:
    """Remove dados de teste criados durante a execução.

    Args:
        api_base_url: URL base da API backend.
        created_data: Dicionário com referências dos dados a remover.
    """
    # TODO: Implementar chamadas HTTP ao backend para limpeza.
    # Requer endpoint DELETE /api/v1/test/cleanup no backend (apenas em env=test).
    pass


# ---------------------------------------------------------------------------
# Relatório de cobertura de cenários
# ---------------------------------------------------------------------------

def generate_scenario_report() -> str:
    """Gera relatório textual dos cenários E2E configurados.

    Útil para documentação e revisão dos cenários de teste
    com a equipe jurídica e de QA.

    Returns:
        Relatório formatado em texto.
    """
    scenarios = get_critical_test_scenarios()
    lines = [
        "=" * 80,
        "RELATÓRIO DE CENÁRIOS E2E — Automação Jurídica Assistida",
        "=" * 80,
        f"Total de cenários: {len(scenarios)}",
        f"Críticos: {len([s for s in scenarios if s.priority == TestPriority.CRITICAL])}",
        f"Alta prioridade: {len([s for s in scenarios if s.priority == TestPriority.HIGH])}",
        f"Média prioridade: {len([s for s in scenarios if s.priority == TestPriority.MEDIUM])}",
        f"Baixa prioridade: {len([s for s in scenarios if s.priority == TestPriority.LOW])}",
        "",
        "Módulos cobertos:",
    ]

    modules = set(s.module for s in scenarios)
    for module in sorted(modules):
        module_scenarios = get_scenarios_by_module(module)
        lines.append(f"  - {module}: {len(module_scenarios)} cenário(s)")

    lines.append("")
    lines.append("-" * 80)

    for scenario in scenarios:
        lines.extend([
            f"\n[{scenario.priority.value.upper()}] {scenario.id}: {scenario.name}",
            f"  Módulo: {scenario.module}",
            f"  Perfil: {scenario.required_role}",
            f"  Tags: {', '.join(scenario.tags)}",
            f"  Descrição: {scenario.description}",
            f"  Resultado esperado: {scenario.expected_result}",
        ])

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Instâncias padrão (singleton-like para uso direto)
# ---------------------------------------------------------------------------

# Configuração padrão carregada de variáveis de ambiente
default_config = E2ETestConfig.from_env()

# Credenciais de teste
default_credentials = TestCredentials()

# Rotas da aplicação
default_routes = PageRoutes()

# Seletores de UI
default_selectors = UISelectors()


# ---------------------------------------------------------------------------
# Ponto de entrada para geração de arquivos de configuração
# ---------------------------------------------------------------------------

def main() -> None:
    """Ponto de entrada para geração de arquivos de configuração E2E.

    Gera os seguintes arquivos:
    - playwright.config.ts (configuração do Playwright)
    - e2e/conftest.py (fixtures pytest-playwright)
    - Relatório de cenários (stdout)
    """
    import sys

    config = E2ETestConfig.from_env()
    config.apply_ci_overrides()

    if "--report" in sys.argv:
        print(generate_scenario_report())
        return

    if "--playwright-config" in sys.argv:
        playwright_config = generate_playwright_config(config)
        output_path = "frontend/playwright.config.ts"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(playwright_config)
        print(f"Arquivo gerado: {output_path}")
        return

    if "--conftest" in sys.argv:
        conftest = generate_conftest_content(config)
        output_path = "tests/e2e/conftest.py"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(conftest)
        print(f"Arquivo gerado: {output_path}")
        return

    # Sem argumentos: exibe ajuda
    print("Uso: python -m src.modules.m11_e2e_testing_config [opção]")
    print("")
    print("Opções:")
    print("  --report              Exibe relatório de cenários E2E")
    print("  --playwright-config   Gera frontend/playwright.config.ts")
    print("  --conftest            Gera tests/e2e/conftest.py")
    print("")
    print("Variáveis de ambiente:")
    print("  E2E_BASE_URL          URL base do frontend (padrão: http://localhost:5173)")
    print("  E2E_API_BASE_URL      URL base da API (padrão: http://localhost:8000)")
    print("  E2E_ENVIRONMENT       Ambiente: local, ci, staging (padrão: local)")
    print("  E2E_HEADLESS          Modo headless: true/false (padrão: true)")
    print("  E2E_BROWSERS          Navegadores: chromium,firefox,webkit (padrão: chromium)")
    print("  E2E_RETRIES           Retentativas em falha (padrão: 0)")
    print("  E2E_WORKERS           Workers paralelos (padrão: 1)")


if __name__ == "__main__":
    main()
