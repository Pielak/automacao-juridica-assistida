"""Módulo backlog #13: Configuração de Performance Testing — Automação Jurídica Assistida.

Define configurações, cenários de carga e perfis de teste de performance
utilizando Locust (Python) e k6 (JavaScript/Go). Este módulo centraliza:

- Perfis de carga (smoke, load, stress, spike, soak)
- Cenários de teste por endpoint/funcionalidade
- Thresholds de aceitação baseados nas metas do módulo m04
- Configuração de usuários virtuais e ramp-up
- Geração de arquivos de configuração para Locust e k6
- Utilitários para execução e relatórios de testes

Dependências:
    - backend/src/modules/m04_performance_targets (metas de performance/SLA)
    - locust (framework de teste de carga em Python)
    - structlog (logs estruturados)

Exemplo de uso::

    from backend.src.modules.m13_performance_testing_config import (
        LoadTestProfile,
        PerformanceTestConfig,
        LocustScenarioBuilder,
        K6ConfigGenerator,
    )

    config = PerformanceTestConfig.from_profile(LoadTestProfile.LOAD)
    locust_builder = LocustScenarioBuilder(config)
    k6_generator = K6ConfigGenerator(config)
"""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

from backend.src.modules.m04_performance_targets import (
    PERFORMANCE_TARGETS,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constantes globais
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://localhost:8000"
"""URL base padrão para execução local dos testes de performance."""

DEFAULT_API_PREFIX = "/api/v1"
"""Prefixo padrão da API REST."""

OUTPUT_DIR = Path("tests/performance")
"""Diretório padrão para geração de artefatos de teste de performance."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class LoadTestProfile(str, Enum):
    """Perfis de teste de carga disponíveis.

    Cada perfil define uma estratégia diferente de simulação de carga,
    adequada a diferentes fases de validação de performance.
    """

    SMOKE = "smoke"
    """Teste de fumaça — poucos usuários, validação básica de funcionamento."""

    LOAD = "load"
    """Teste de carga — carga normal esperada em produção."""

    STRESS = "stress"
    """Teste de estresse — carga acima do esperado para encontrar limites."""

    SPIKE = "spike"
    """Teste de pico — aumento súbito e breve de carga."""

    SOAK = "soak"
    """Teste de resistência — carga moderada por período prolongado."""


class EndpointCategory(str, Enum):
    """Categorias de endpoints para agrupamento de cenários."""

    AUTH = "auth"
    DOCUMENTS = "documents"
    ANALYSIS = "analysis"
    CHAT = "chat"
    USERS = "users"
    AUDIT = "audit"
    HEALTH = "health"


# ---------------------------------------------------------------------------
# Dataclasses de configuração
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RampUpConfig:
    """Configuração de ramp-up/ramp-down de usuários virtuais.

    Attributes:
        stages: Lista de estágios no formato (duração_segundos, usuarios_alvo).
    """

    stages: list[tuple[int, int]] = field(default_factory=list)

    def to_k6_stages(self) -> list[dict[str, str]]:
        """Converte estágios para formato k6.

        Returns:
            Lista de dicionários com 'duration' e 'target' para k6.
        """
        return [
            {"duration": f"{duration}s", "target": str(target)}
            for duration, target in self.stages
        ]

    def to_locust_shape(self) -> list[dict[str, int]]:
        """Converte estágios para formato Locust LoadTestShape.

        Returns:
            Lista de dicionários com 'duration', 'users' e 'spawn_rate'.
        """
        result: list[dict[str, int]] = []
        cumulative_time = 0
        prev_users = 0
        for duration, target in self.stages:
            cumulative_time += duration
            spawn_rate = max(1, abs(target - prev_users) // max(1, duration // 10))
            result.append(
                {
                    "duration": cumulative_time,
                    "users": target,
                    "spawn_rate": spawn_rate,
                }
            )
            prev_users = target
        return result


@dataclass(frozen=True)
class EndpointScenario:
    """Cenário de teste para um endpoint específico.

    Attributes:
        name: Nome descritivo do cenário.
        method: Método HTTP (GET, POST, PUT, DELETE, PATCH).
        path: Caminho relativo do endpoint (sem base URL).
        category: Categoria funcional do endpoint.
        weight: Peso relativo na distribuição de requisições (1-100).
        expected_status: Código HTTP esperado de sucesso.
        max_latency_p95_ms: Latência máxima aceitável no percentil 95 (ms).
        max_latency_p99_ms: Latência máxima aceitável no percentil 99 (ms).
        requires_auth: Se o endpoint requer autenticação JWT.
        payload_template: Template de payload para métodos com body (opcional).
        tags: Tags adicionais para filtragem e agrupamento.
    """

    name: str
    method: str
    path: str
    category: EndpointCategory
    weight: int = 10
    expected_status: int = 200
    max_latency_p95_ms: int = 500
    max_latency_p99_ms: int = 1000
    requires_auth: bool = True
    payload_template: dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ThresholdConfig:
    """Configuração de thresholds de aceitação para testes de performance.

    Attributes:
        http_req_duration_p95_ms: Latência máxima p95 global (ms).
        http_req_duration_p99_ms: Latência máxima p99 global (ms).
        http_req_failed_rate: Taxa máxima de falhas HTTP (0.0 a 1.0).
        http_req_duration_avg_ms: Latência média máxima global (ms).
        iteration_duration_p95_ms: Duração máxima p95 de iteração completa (ms).
        checks_rate: Taxa mínima de checks passando (0.0 a 1.0).
    """

    http_req_duration_p95_ms: int = 500
    http_req_duration_p99_ms: int = 1500
    http_req_failed_rate: float = 0.01
    http_req_duration_avg_ms: int = 300
    iteration_duration_p95_ms: int = 5000
    checks_rate: float = 0.99

    def to_k6_thresholds(self) -> dict[str, list[str]]:
        """Converte thresholds para formato k6.

        Returns:
            Dicionário de thresholds no formato esperado pelo k6.
        """
        return {
            "http_req_duration": [
                f"p(95)<{self.http_req_duration_p95_ms}",
                f"p(99)<{self.http_req_duration_p99_ms}",
                f"avg<{self.http_req_duration_avg_ms}",
            ],
            "http_req_failed": [
                f"rate<{self.http_req_failed_rate}",
            ],
            "iteration_duration": [
                f"p(95)<{self.iteration_duration_p95_ms}",
            ],
            "checks": [
                f"rate>{self.checks_rate}",
            ],
        }


# ---------------------------------------------------------------------------
# Perfis de carga pré-definidos
# ---------------------------------------------------------------------------

# Mapeamento de perfis para configurações de ramp-up
_PROFILE_RAMP_CONFIGS: dict[LoadTestProfile, RampUpConfig] = {
    LoadTestProfile.SMOKE: RampUpConfig(
        stages=[
            (10, 1),   # Ramp-up: 1 usuário em 10s
            (30, 3),   # Sustenta 3 usuários por 30s
            (10, 0),   # Ramp-down
        ]
    ),
    LoadTestProfile.LOAD: RampUpConfig(
        stages=[
            (60, 10),   # Ramp-up: 10 usuários em 1min
            (120, 50),  # Ramp-up: 50 usuários em 2min
            (300, 50),  # Sustenta 50 usuários por 5min
            (60, 0),    # Ramp-down
        ]
    ),
    LoadTestProfile.STRESS: RampUpConfig(
        stages=[
            (60, 50),    # Ramp-up: 50 usuários em 1min
            (120, 100),  # Ramp-up: 100 usuários em 2min
            (180, 200),  # Ramp-up: 200 usuários em 3min
            (300, 200),  # Sustenta 200 usuários por 5min
            (60, 0),     # Ramp-down
        ]
    ),
    LoadTestProfile.SPIKE: RampUpConfig(
        stages=[
            (30, 10),    # Carga base: 10 usuários
            (10, 150),   # Spike: 150 usuários em 10s
            (60, 150),   # Sustenta spike por 1min
            (10, 10),    # Volta à base
            (60, 10),    # Estabiliza
            (10, 0),     # Ramp-down
        ]
    ),
    LoadTestProfile.SOAK: RampUpConfig(
        stages=[
            (120, 30),    # Ramp-up: 30 usuários em 2min
            (3600, 30),   # Sustenta 30 usuários por 1h
            (120, 0),     # Ramp-down
        ]
    ),
}

# Thresholds por perfil
_PROFILE_THRESHOLDS: dict[LoadTestProfile, ThresholdConfig] = {
    LoadTestProfile.SMOKE: ThresholdConfig(
        http_req_duration_p95_ms=300,
        http_req_duration_p99_ms=800,
        http_req_failed_rate=0.0,
        http_req_duration_avg_ms=200,
        checks_rate=1.0,
    ),
    LoadTestProfile.LOAD: ThresholdConfig(
        http_req_duration_p95_ms=500,
        http_req_duration_p99_ms=1500,
        http_req_failed_rate=0.01,
        http_req_duration_avg_ms=300,
        checks_rate=0.99,
    ),
    LoadTestProfile.STRESS: ThresholdConfig(
        http_req_duration_p95_ms=1000,
        http_req_duration_p99_ms=3000,
        http_req_failed_rate=0.05,
        http_req_duration_avg_ms=500,
        checks_rate=0.95,
    ),
    LoadTestProfile.SPIKE: ThresholdConfig(
        http_req_duration_p95_ms=2000,
        http_req_duration_p99_ms=5000,
        http_req_failed_rate=0.10,
        http_req_duration_avg_ms=800,
        checks_rate=0.90,
    ),
    LoadTestProfile.SOAK: ThresholdConfig(
        http_req_duration_p95_ms=500,
        http_req_duration_p99_ms=1500,
        http_req_failed_rate=0.01,
        http_req_duration_avg_ms=300,
        checks_rate=0.99,
    ),
}


# ---------------------------------------------------------------------------
# Cenários de endpoint padrão
# ---------------------------------------------------------------------------

DEFAULT_SCENARIOS: list[EndpointScenario] = [
    # --- Health ---
    EndpointScenario(
        name="health_check",
        method="GET",
        path=f"{DEFAULT_API_PREFIX}/health",
        category=EndpointCategory.HEALTH,
        weight=5,
        expected_status=200,
        max_latency_p95_ms=100,
        max_latency_p99_ms=200,
        requires_auth=False,
        tags=["critical", "monitoring"],
    ),
    # --- Auth ---
    EndpointScenario(
        name="auth_login",
        method="POST",
        path=f"{DEFAULT_API_PREFIX}/auth/login",
        category=EndpointCategory.AUTH,
        weight=15,
        expected_status=200,
        max_latency_p95_ms=300,
        max_latency_p99_ms=800,
        requires_auth=False,
        payload_template={
            "email": "usuario_teste_{{user_id}}@teste.com.br",
            "password": "SenhaSegura123!",
        },
        tags=["auth", "critical"],
    ),
    EndpointScenario(
        name="auth_refresh_token",
        method="POST",
        path=f"{DEFAULT_API_PREFIX}/auth/refresh",
        category=EndpointCategory.AUTH,
        weight=5,
        expected_status=200,
        max_latency_p95_ms=200,
        max_latency_p99_ms=500,
        requires_auth=True,
        tags=["auth"],
    ),
    # --- Documentos ---
    EndpointScenario(
        name="documents_list",
        method="GET",
        path=f"{DEFAULT_API_PREFIX}/documents",
        category=EndpointCategory.DOCUMENTS,
        weight=20,
        expected_status=200,
        max_latency_p95_ms=500,
        max_latency_p99_ms=1200,
        requires_auth=True,
        tags=["documents", "read"],
    ),
    EndpointScenario(
        name="documents_get_by_id",
        method="GET",
        path=f"{DEFAULT_API_PREFIX}/documents/{{document_id}}",
        category=EndpointCategory.DOCUMENTS,
        weight=15,
        expected_status=200,
        max_latency_p95_ms=400,
        max_latency_p99_ms=1000,
        requires_auth=True,
        tags=["documents", "read"],
    ),
    EndpointScenario(
        name="documents_upload",
        method="POST",
        path=f"{DEFAULT_API_PREFIX}/documents/upload",
        category=EndpointCategory.DOCUMENTS,
        weight=10,
        expected_status=201,
        max_latency_p95_ms=2000,
        max_latency_p99_ms=5000,
        requires_auth=True,
        tags=["documents", "write", "upload"],
    ),
    # --- Análise IA ---
    EndpointScenario(
        name="analysis_request",
        method="POST",
        path=f"{DEFAULT_API_PREFIX}/analysis",
        category=EndpointCategory.ANALYSIS,
        weight=10,
        expected_status=202,
        max_latency_p95_ms=3000,
        max_latency_p99_ms=8000,
        requires_auth=True,
        payload_template={
            "document_id": "{{document_id}}",
            "analysis_type": "summary",
        },
        tags=["analysis", "ia", "async"],
    ),
    EndpointScenario(
        name="analysis_status",
        method="GET",
        path=f"{DEFAULT_API_PREFIX}/analysis/{{analysis_id}}/status",
        category=EndpointCategory.ANALYSIS,
        weight=10,
        expected_status=200,
        max_latency_p95_ms=300,
        max_latency_p99_ms=800,
        requires_auth=True,
        tags=["analysis", "read"],
    ),
    # --- Chat ---
    EndpointScenario(
        name="chat_send_message",
        method="POST",
        path=f"{DEFAULT_API_PREFIX}/chat/messages",
        category=EndpointCategory.CHAT,
        weight=5,
        expected_status=200,
        max_latency_p95_ms=5000,
        max_latency_p99_ms=10000,
        requires_auth=True,
        payload_template={
            "session_id": "{{session_id}}",
            "message": "Qual o prazo para recurso de apelação?",
        },
        tags=["chat", "ia", "streaming"],
    ),
    # --- Usuários ---
    EndpointScenario(
        name="users_me",
        method="GET",
        path=f"{DEFAULT_API_PREFIX}/users/me",
        category=EndpointCategory.USERS,
        weight=5,
        expected_status=200,
        max_latency_p95_ms=200,
        max_latency_p99_ms=500,
        requires_auth=True,
        tags=["users", "read"],
    ),
]


# ---------------------------------------------------------------------------
# Classe principal de configuração
# ---------------------------------------------------------------------------


@dataclass
class PerformanceTestConfig:
    """Configuração completa para execução de testes de performance.

    Centraliza todas as definições necessárias para gerar artefatos
    de teste tanto para Locust quanto para k6.

    Attributes:
        profile: Perfil de carga selecionado.
        base_url: URL base do servidor alvo.
        api_prefix: Prefixo da API REST.
        ramp_up: Configuração de ramp-up/ramp-down.
        thresholds: Thresholds de aceitação.
        scenarios: Lista de cenários de endpoint.
        tags_filter: Filtro opcional por tags (executa apenas cenários com essas tags).
        auth_token_env_var: Nome da variável de ambiente com token JWT para testes.
    """

    profile: LoadTestProfile
    base_url: str = DEFAULT_BASE_URL
    api_prefix: str = DEFAULT_API_PREFIX
    ramp_up: RampUpConfig = field(default_factory=RampUpConfig)
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    scenarios: list[EndpointScenario] = field(default_factory=list)
    tags_filter: list[str] = field(default_factory=list)
    auth_token_env_var: str = "PERF_TEST_AUTH_TOKEN"

    @classmethod
    def from_profile(
        cls,
        profile: LoadTestProfile,
        *,
        base_url: str = DEFAULT_BASE_URL,
        scenarios: list[EndpointScenario] | None = None,
        tags_filter: list[str] | None = None,
    ) -> PerformanceTestConfig:
        """Cria configuração a partir de um perfil pré-definido.

        Args:
            profile: Perfil de carga desejado.
            base_url: URL base do servidor alvo.
            scenarios: Cenários customizados (usa DEFAULT_SCENARIOS se None).
            tags_filter: Filtro opcional por tags.

        Returns:
            Instância configurada de PerformanceTestConfig.
        """
        selected_scenarios = scenarios if scenarios is not None else DEFAULT_SCENARIOS

        if tags_filter:
            selected_scenarios = [
                s for s in selected_scenarios
                if any(tag in s.tags for tag in tags_filter)
            ]

        config = cls(
            profile=profile,
            base_url=base_url,
            ramp_up=_PROFILE_RAMP_CONFIGS[profile],
            thresholds=_PROFILE_THRESHOLDS[profile],
            scenarios=selected_scenarios,
            tags_filter=tags_filter or [],
        )

        logger.info(
            "Configuração de teste de performance criada",
            profile=profile.value,
            base_url=base_url,
            total_scenarios=len(selected_scenarios),
            tags_filter=tags_filter,
        )

        return config

    def get_total_duration_seconds(self) -> int:
        """Calcula a duração total estimada do teste em segundos.

        Returns:
            Duração total em segundos.
        """
        return sum(duration for duration, _ in self.ramp_up.stages)

    def get_max_virtual_users(self) -> int:
        """Retorna o número máximo de usuários virtuais no teste.

        Returns:
            Número máximo de VUs.
        """
        if not self.ramp_up.stages:
            return 0
        return max(target for _, target in self.ramp_up.stages)

    def get_scenarios_by_category(
        self, category: EndpointCategory
    ) -> list[EndpointScenario]:
        """Filtra cenários por categoria.

        Args:
            category: Categoria de endpoint desejada.

        Returns:
            Lista de cenários da categoria especificada.
        """
        return [s for s in self.scenarios if s.category == category]

    def validate_against_targets(self) -> list[str]:
        """Valida thresholds contra as metas definidas em m04_performance_targets.

        Compara os thresholds configurados com as metas de performance
        do módulo m04 e retorna avisos caso os thresholds sejam mais
        permissivos que as metas.

        Returns:
            Lista de avisos de validação (vazia se tudo OK).
        """
        warnings: list[str] = []

        # TODO: Implementar validação cruzada detalhada com PERFORMANCE_TARGETS
        # quando a estrutura exata de PERFORMANCE_TARGETS estiver disponível.
        # Por ora, fazemos validação básica de existência.
        try:
            if PERFORMANCE_TARGETS is not None:
                logger.info(
                    "Validação cruzada com metas de performance m04 disponível",
                    profile=self.profile.value,
                )
            # TODO: Iterar sobre metas específicas de PERFORMANCE_TARGETS
            # e comparar com self.thresholds para gerar avisos.
        except (AttributeError, TypeError) as exc:
            warnings.append(
                f"Não foi possível validar contra metas m04: {exc}"
            )
            logger.warning(
                "Falha na validação cruzada com m04_performance_targets",
                error=str(exc),
            )

        return warnings


# ---------------------------------------------------------------------------
# Gerador de configuração Locust
# ---------------------------------------------------------------------------


class LocustScenarioBuilder:
    """Gera arquivos de configuração e cenários para o Locust.

    Produz um locustfile.py completo com tasks ponderadas,
    LoadTestShape customizado e configurações de autenticação.
    """

    def __init__(self, config: PerformanceTestConfig) -> None:
        """Inicializa o builder com a configuração de teste.

        Args:
            config: Configuração completa de teste de performance.
        """
        self._config = config

    def generate_locustfile(self) -> str:
        """Gera o conteúdo completo do locustfile.py.

        Returns:
            Conteúdo do arquivo locustfile.py como string.
        """
        header = self._generate_header()
        shape_class = self._generate_shape_class()
        user_class = self._generate_user_class()
        tasks = self._generate_tasks()

        return f"{header}\n\n{shape_class}\n\n{tasks}\n\n{user_class}"

    def _generate_header(self) -> str:
        """Gera imports e cabeçalho do locustfile."""
        return textwrap.dedent(f'''\
            """Locustfile gerado automaticamente — Automação Jurídica Assistida.

            Perfil: {self._config.profile.value}
            Duração estimada: {self._config.get_total_duration_seconds()}s
            Máx. usuários virtuais: {self._config.get_max_virtual_users()}
            """

            import os

            from locust import HttpUser, LoadTestShape, between, task
        ''')

    def _generate_shape_class(self) -> str:
        """Gera a classe LoadTestShape com os estágios configurados."""
        stages_repr = repr(self._config.ramp_up.to_locust_shape())

        return textwrap.dedent(f'''\
            class CustomLoadShape(LoadTestShape):
                """Shape de carga customizado — perfil {self._config.profile.value}."""

                stages = {stages_repr}

                def tick(self):
                    """Retorna configuração do estágio atual."""
                    run_time = self.get_run_time()
                    for stage in self.stages:
                        if run_time < stage["duration"]:
                            return (stage["users"], stage["spawn_rate"])
                    return None
        ''')

    def _generate_user_class(self) -> str:
        """Gera a classe HttpUser principal."""
        token_var = self._config.auth_token_env_var

        return textwrap.dedent(f'''\
            class JuridicoUser(HttpUser):
                """Usuário virtual simulando operações jurídicas."""

                host = "{self._config.base_url}"
                wait_time = between(1, 3)

                def on_start(self):
                    """Configuração inicial — autenticação."""
                    token = os.environ.get("{token_var}", "")
                    if token:
                        self.client.headers["Authorization"] = f"Bearer {{token}}"
        ''')

    def _generate_tasks(self) -> str:
        """Gera métodos de task para cada cenário."""
        task_methods: list[str] = []

        for scenario in self._config.scenarios:
            method_name = f"task_{scenario.name}"
            http_method = scenario.method.lower()
            weight = scenario.weight

            if scenario.payload_template and http_method in ("post", "put", "patch"):
                payload_repr = repr(scenario.payload_template)
                body = textwrap.dedent(f'''\
                    @task({weight})
                    def {method_name}(self):
                        """Cenário: {scenario.name} [{scenario.method} {scenario.path}]."""
                        self.client.{http_method}(
                            "{scenario.path}",
                            json={payload_repr},
                            name="{scenario.name}",
                        )
                ''')
            else:
                body = textwrap.dedent(f'''\
                    @task({weight})
                    def {method_name}(self):
                        """Cenário: {scenario.name} [{scenario.method} {scenario.path}]."""
                        self.client.{http_method}(
                            "{scenario.path}",
                            name="{scenario.name}",
                        )
                ''')

            task_methods.append(body)

        return "\n".join(task_methods)

    def write_locustfile(self, output_dir: Path | None = None) -> Path:
        """Escreve o locustfile.py no diretório especificado.

        Args:
            output_dir: Diretório de saída (usa OUTPUT_DIR se None).

        Returns:
            Caminho do arquivo gerado.
        """
        target_dir = output_dir or OUTPUT_DIR / "locust"
        target_dir.mkdir(parents=True, exist_ok=True)

        filepath = target_dir / f"locustfile_{self._config.profile.value}.py"
        content = self.generate_locustfile()
        filepath.write_text(content, encoding="utf-8")

        logger.info(
            "Locustfile gerado com sucesso",
            filepath=str(filepath),
            profile=self._config.profile.value,
            scenarios=len(self._config.scenarios),
        )

        return filepath


# ---------------------------------------------------------------------------
# Gerador de configuração k6
# ---------------------------------------------------------------------------


class K6ConfigGenerator:
    """Gera arquivos de configuração e scripts para o k6.

    Produz scripts JavaScript compatíveis com k6, incluindo
    cenários, thresholds e configurações de execução.
    """

    def __init__(self, config: PerformanceTestConfig) -> None:
        """Inicializa o gerador com a configuração de teste.

        Args:
            config: Configuração completa de teste de performance.
        """
        self._config = config

    def generate_k6_script(self) -> str:
        """Gera o conteúdo completo do script k6 em JavaScript.

        Returns:
            Conteúdo do script k6 como string.
        """
        options = self._generate_options()
        setup_fn = self._generate_setup()
        default_fn = self._generate_default_function()

        return textwrap.dedent(f'''\
            // Script k6 gerado automaticamente — Automação Jurídica Assistida
            // Perfil: {self._config.profile.value}
            // Duração estimada: {self._config.get_total_duration_seconds()}s
            // Máx. usuários virtuais: {self._config.get_max_virtual_users()}

            import http from 'k6/http';
            import {{ check, sleep }} from 'k6';
            import {{ Rate, Trend }} from 'k6/metrics';

            // Métricas customizadas
            const errorRate = new Rate('errors');
            const authLatency = new Trend('auth_latency', true);
            const documentLatency = new Trend('document_latency', true);
            const analysisLatency = new Trend('analysis_latency', true);

            const BASE_URL = __ENV.BASE_URL || '{self._config.base_url}';
            const AUTH_TOKEN = __ENV.{self._config.auth_token_env_var} || '';

            {options}

            {setup_fn}

            {default_fn}
        ''')

    def _generate_options(self) -> str:
        """Gera o bloco de opções do k6."""
        stages = json.dumps(self._config.ramp_up.to_k6_stages(), indent=4)
        thresholds = json.dumps(
            self._config.thresholds.to_k6_thresholds(), indent=4
        )

        return textwrap.dedent(f'''\
            export const options = {{
                stages: {stages},
                thresholds: {thresholds},
                insecureSkipTLSVerify: true,
                noConnectionReuse: false,
                userAgent: 'k6-perf-test/automacao-juridica',
            }};
        ''')

    def _generate_setup(self) -> str:
        """Gera a função setup do k6."""
        return textwrap.dedent('''\
            export function setup() {
                // Validação de conectividade antes do teste
                const healthRes = http.get(`${BASE_URL}/api/v1/health`);
                if (healthRes.status !== 200) {
                    throw new Error(
                        `Servidor não está saudável. Status: ${healthRes.status}`
                    );
                }
                console.log('Servidor validado — iniciando teste de performance.');
                return { authToken: AUTH_TOKEN };
            }
        ''')

    def _generate_default_function(self) -> str:
        """Gera a função default com os cenários de teste."""
        scenario_blocks: list[str] = []

        for scenario in self._config.scenarios:
            block = self._generate_scenario_block(scenario)
            scenario_blocks.append(block)

        scenarios_code = "\n\n".join(scenario_blocks)

        return textwrap.dedent(f'''\
            export default function(data) {{
                const headers = {{
                    'Content-Type': 'application/json',
                }};

                if (data.authToken) {{
                    headers['Authorization'] = `Bearer ${{data.authToken}}`;
                }}

                {scenarios_code}

                sleep(Math.random() * 2 + 1);
            }}
        ''')

    def _generate_scenario_block(self, scenario: EndpointScenario) -> str:
        """Gera bloco de código k6 para um cenário específico.

        Args:
            scenario: Cenário de endpoint.

        Returns:
            Bloco de código JavaScript para o cenário.
        """
        url = f"${{BASE_URL}}{scenario.path}"
        method = scenario.method.lower()

        if method == "get":
            request_line = f"const res_{scenario.name} = http.get(`{url}`, {{ headers, tags: {{ name: '{scenario.name}' }} }});"
        elif method in ("post", "put", "patch"):
            payload = json.dumps(scenario.payload_template or {})
            request_line = (
                f"const res_{scenario.name} = http.{method}("
                f"`{url}`, JSON.stringify({payload}), "
                f"{{ headers, tags: {{ name: '{scenario.name}' }} }});"
            )
        else:
            request_line = f"const res_{scenario.name} = http.del(`{url}`, null, {{ headers, tags: {{ name: '{scenario.name}' }} }});"

        return textwrap.dedent(f'''\
            // Cenário: {scenario.name}
            {request_line}
            check(res_{scenario.name}, {{
                '{scenario.name} — status {scenario.expected_status}': (r) => r.status === {scenario.expected_status},
                '{scenario.name} — latência p95 < {scenario.max_latency_p95_ms}ms': (r) => r.timings.duration < {scenario.max_latency_p95_ms},
            }});
            errorRate.add(res_{scenario.name}.status !== {scenario.expected_status});
        ''')

    def generate_k6_options_json(self) -> str:
        """Gera arquivo JSON de opções separado para k6.

        Returns:
            Conteúdo JSON com opções de execução.
        """
        options = {
            "stages": self._config.ramp_up.to_k6_stages(),
            "thresholds": self._config.thresholds.to_k6_thresholds(),
            "insecureSkipTLSVerify": True,
            "userAgent": "k6-perf-test/automacao-juridica",
            "summaryTrendStats": [
                "avg", "min", "med", "max", "p(90)", "p(95)", "p(99)",
            ],
        }
        return json.dumps(options, indent=2, ensure_ascii=False)

    def write_k6_script(self, output_dir: Path | None = None) -> Path:
        """Escreve o script k6 no diretório especificado.

        Args:
            output_dir: Diretório de saída (usa OUTPUT_DIR se None).

        Returns:
            Caminho do arquivo gerado.
        """
        target_dir = output_dir or OUTPUT_DIR / "k6"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Script principal
        script_path = target_dir / f"test_{self._config.profile.value}.js"
        script_content = self.generate_k6_script()
        script_path.write_text(script_content, encoding="utf-8")

        # Arquivo de opções JSON
        options_path = target_dir / f"options_{self._config.profile.value}.json"
        options_content = self.generate_k6_options_json()
        options_path.write_text(options_content, encoding="utf-8")

        logger.info(
            "Scripts k6 gerados com sucesso",
            script_path=str(script_path),
            options_path=str(options_path),
            profile=self._config.profile.value,
            scenarios=len(self._config.scenarios),
        )

        return script_path


# ---------------------------------------------------------------------------
# Utilitários de execução
# ---------------------------------------------------------------------------


def generate_all_profiles(
    base_url: str = DEFAULT_BASE_URL,
    output_dir: Path | None = None,
) -> dict[str, list[Path]]:
    """Gera artefatos de teste para todos os perfis de carga.

    Cria locustfiles e scripts k6 para cada perfil disponível
    (smoke, load, stress, spike, soak).

    Args:
        base_url: URL base do servidor alvo.
        output_dir: Diretório base de saída.

    Returns:
        Dicionário mapeando nome do perfil para lista de arquivos gerados.
    """
    generated: dict[str, list[Path]] = {}

    for profile in LoadTestProfile:
        config = PerformanceTestConfig.from_profile(
            profile, base_url=base_url
        )

        locust_builder = LocustScenarioBuilder(config)
        k6_generator = K6ConfigGenerator(config)

        locust_path = locust_builder.write_locustfile(
            output_dir / "locust" if output_dir else None
        )
        k6_path = k6_generator.write_k6_script(
            output_dir / "k6" if output_dir else None
        )

        generated[profile.value] = [locust_path, k6_path]

        logger.info(
            "Artefatos de teste gerados para perfil",
            profile=profile.value,
            files=[str(locust_path), str(k6_path)],
        )

    return generated


def get_run_command_locust(profile: LoadTestProfile) -> str:
    """Retorna o comando para executar o Locust com o perfil especificado.

    Args:
        profile: Perfil de carga.

    Returns:
        Comando de terminal para execução.
    """
    locustfile = f"tests/performance/locust/locustfile_{profile.value}.py"
    return (
        f"locust -f {locustfile} "
        f"--headless "
        f"--html=tests/performance/reports/locust_{profile.value}.html"
    )


def get_run_command_k6(profile: LoadTestProfile) -> str:
    """Retorna o comando para executar o k6 com o perfil especificado.

    Args:
        profile: Perfil de carga.

    Returns:
        Comando de terminal para execução.
    """
    script = f"tests/performance/k6/test_{profile.value}.js"
    return (
        f"k6 run {script} "
        f"--out json=tests/performance/reports/k6_{profile.value}.json "
        f"--summary-export=tests/performance/reports/k6_{profile.value}_summary.json"
    )


# ---------------------------------------------------------------------------
# Ponto de entrada para geração via CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    target_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    print(f"Gerando artefatos de teste de performance para: {target_url}")
    results = generate_all_profiles(base_url=target_url, output_dir=out_dir)

    print("\n=== Artefatos gerados ===")
    for profile_name, files in results.items():
        print(f"\nPerfil: {profile_name}")
        for f in files:
            print(f"  → {f}")

    print("\n=== Comandos de execução ===")
    for profile in LoadTestProfile:
        print(f"\n--- {profile.value.upper()} ---")
        print(f"  Locust: {get_run_command_locust(profile)}")
        print(f"  k6:     {get_run_command_k6(profile)}")
