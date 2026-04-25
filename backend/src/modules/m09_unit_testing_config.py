"""Módulo backlog #9: Configuração de Unit Testing.

Este módulo centraliza a configuração de testes unitários do projeto
Automação Jurídica Assistida, incluindo:

- Fixtures reutilizáveis para pytest (app, client, banco de dados, autenticação)
- Configuração de cobertura de código (mínimo 80%)
- Helpers e factories para criação de objetos de teste
- Configuração de mocks para serviços externos (Anthropic, DataJud)

Uso:
    Este módulo é importado automaticamente pelo conftest.py na raiz de testes.
    As fixtures ficam disponíveis para todos os módulos de teste.

Exemplo:
    from modules.m09_unit_testing_config import (
        get_test_settings,
        create_test_user_data,
        MockAnthropicClient,
    )
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Constantes de configuração de testes
# ---------------------------------------------------------------------------

MIN_COVERAGE_PERCENT: int = 80
"""Percentual mínimo de cobertura de código exigido pelo projeto."""

TEST_DATABASE_URL: str = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_automacao_juridica",
)
"""URL de conexão com o banco de dados de testes."""

TEST_SECRET_KEY: str = "chave-secreta-apenas-para-testes-nao-usar-em-producao"
"""Chave secreta usada exclusivamente em ambiente de testes."""

TEST_JWT_ALGORITHM: str = "HS256"
"""Algoritmo JWT simplificado para testes (produção usa RS256)."""

TEST_JWT_EXPIRATION_MINUTES: int = 30
"""Tempo de expiração do token JWT em testes."""


# ---------------------------------------------------------------------------
# Configurações de teste (Settings override)
# ---------------------------------------------------------------------------

@dataclass
class TestSettings:
    """Configurações específicas para o ambiente de testes.

    Substitui as configurações de produção durante a execução dos testes,
    garantindo isolamento e previsibilidade.
    """

    database_url: str = TEST_DATABASE_URL
    secret_key: str = TEST_SECRET_KEY
    jwt_algorithm: str = TEST_JWT_ALGORITHM
    jwt_expiration_minutes: int = TEST_JWT_EXPIRATION_MINUTES
    debug: bool = True
    testing: bool = True
    anthropic_api_key: str = "sk-ant-test-fake-key-para-testes"
    anthropic_model: str = "claude-3-haiku-20240307"
    redis_url: str = "redis://localhost:6379/15"
    celery_broker_url: str = "redis://localhost:6379/14"
    celery_result_backend: str = "redis://localhost:6379/14"
    rate_limit_enabled: bool = False
    mfa_enabled: bool = False
    upload_max_size_mb: int = 10
    allowed_file_types: list[str] = field(
        default_factory=lambda: [".pdf", ".docx", ".txt", ".odt"]
    )
    cors_origins: list[str] = field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )
    log_level: str = "DEBUG"


def get_test_settings() -> TestSettings:
    """Retorna instância das configurações de teste.

    Returns:
        TestSettings: Objeto com todas as configurações para ambiente de testes.
    """
    return TestSettings()


# ---------------------------------------------------------------------------
# Factories — criação de dados de teste
# ---------------------------------------------------------------------------

def create_test_user_data(
    *,
    email: str | None = None,
    nome: str = "Usuário de Teste",
    role: str = "advogado",
    is_active: bool = True,
    oab_number: str | None = None,
) -> dict[str, Any]:
    """Cria dicionário com dados de um usuário para testes.

    Args:
        email: E-mail do usuário. Se não informado, gera um aleatório.
        nome: Nome completo do usuário.
        role: Papel do usuário no sistema (advogado, admin, estagiario).
        is_active: Se o usuário está ativo.
        oab_number: Número da OAB (opcional).

    Returns:
        Dicionário com os dados do usuário prontos para uso em testes.
    """
    unique_id = uuid.uuid4().hex[:8]
    return {
        "id": str(uuid.uuid4()),
        "email": email or f"teste_{unique_id}@automacaojuridica.com.br",
        "nome": nome,
        "senha": "SenhaForte@123",
        "role": role,
        "is_active": is_active,
        "oab_number": oab_number or f"SP{unique_id[:6].upper()}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def create_test_document_data(
    *,
    titulo: str = "Petição Inicial de Teste",
    tipo: str = "peticao_inicial",
    owner_id: str | None = None,
    status: str = "rascunho",
    conteudo: str | None = None,
) -> dict[str, Any]:
    """Cria dicionário com dados de um documento jurídico para testes.

    Args:
        titulo: Título do documento.
        tipo: Tipo do documento (peticao_inicial, contestacao, recurso, etc.).
        owner_id: ID do proprietário. Se não informado, gera um UUID.
        status: Status do documento no ciclo de vida.
        conteudo: Conteúdo textual do documento.

    Returns:
        Dicionário com os dados do documento prontos para uso em testes.
    """
    return {
        "id": str(uuid.uuid4()),
        "titulo": titulo,
        "tipo": tipo,
        "owner_id": owner_id or str(uuid.uuid4()),
        "status": status,
        "conteudo": conteudo or f"Conteúdo de teste para {titulo}.",
        "arquivo_nome": f"{titulo.lower().replace(' ', '_')}.pdf",
        "arquivo_tamanho_bytes": 1024 * 50,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def create_test_analysis_data(
    *,
    document_id: str | None = None,
    tipo_analise: str = "revisao_completa",
    status: str = "pendente",
) -> dict[str, Any]:
    """Cria dicionário com dados de uma análise de IA para testes.

    Args:
        document_id: ID do documento associado.
        tipo_analise: Tipo de análise solicitada.
        status: Status da análise (pendente, processando, concluida, erro).

    Returns:
        Dicionário com os dados da análise prontos para uso em testes.
    """
    return {
        "id": str(uuid.uuid4()),
        "document_id": document_id or str(uuid.uuid4()),
        "tipo_analise": tipo_analise,
        "status": status,
        "resultado": None if status == "pendente" else {
            "resumo": "Análise de teste concluída com sucesso.",
            "pontos_atencao": ["Ponto 1 de atenção", "Ponto 2 de atenção"],
            "sugestoes": ["Sugestão de melhoria 1"],
            "score_qualidade": 85,
        },
        "tokens_utilizados": 0 if status == "pendente" else 1500,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None if status == "pendente" else datetime.now(timezone.utc).isoformat(),
    }


def create_test_jwt_payload(
    *,
    user_id: str | None = None,
    email: str = "teste@automacaojuridica.com.br",
    role: str = "advogado",
    expires_delta_minutes: int = TEST_JWT_EXPIRATION_MINUTES,
) -> dict[str, Any]:
    """Cria payload JWT para testes de autenticação.

    Args:
        user_id: ID do usuário. Se não informado, gera um UUID.
        email: E-mail do usuário.
        role: Papel do usuário.
        expires_delta_minutes: Minutos até expiração do token.

    Returns:
        Dicionário com o payload JWT para testes.
    """
    now = datetime.now(timezone.utc)
    return {
        "sub": user_id or str(uuid.uuid4()),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_delta_minutes)).timestamp()),
        "jti": str(uuid.uuid4()),
    }


# ---------------------------------------------------------------------------
# Mocks — serviços externos
# ---------------------------------------------------------------------------

class MockAnthropicClient:
    """Mock do cliente Anthropic para testes sem chamadas reais à API.

    Simula respostas do Claude para testes de integração com IA,
    evitando custos e dependência de rede.
    """

    def __init__(
        self,
        *,
        default_response: str = "Resposta simulada do Claude para testes.",
        should_fail: bool = False,
        failure_message: str = "Erro simulado na API Anthropic.",
    ) -> None:
        """Inicializa o mock do cliente Anthropic.

        Args:
            default_response: Texto padrão retornado nas respostas.
            should_fail: Se True, simula falha na API.
            failure_message: Mensagem de erro quando should_fail=True.
        """
        self.default_response = default_response
        self.should_fail = should_fail
        self.failure_message = failure_message
        self.call_history: list[dict[str, Any]] = []
        self.messages = self._create_messages_mock()

    def _create_messages_mock(self) -> MagicMock:
        """Cria mock do endpoint messages.create."""
        messages_mock = MagicMock()
        messages_mock.create = AsyncMock(side_effect=self._handle_create)
        return messages_mock

    async def _handle_create(self, **kwargs: Any) -> MagicMock:
        """Manipula chamadas ao messages.create.

        Args:
            **kwargs: Argumentos da chamada (model, messages, max_tokens, etc.).

        Returns:
            Mock da resposta do Claude.

        Raises:
            Exception: Se should_fail=True, simula erro da API.
        """
        self.call_history.append({
            "method": "messages.create",
            "kwargs": kwargs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        if self.should_fail:
            raise Exception(self.failure_message)

        response = MagicMock()
        response.id = f"msg_{uuid.uuid4().hex[:24]}"
        response.type = "message"
        response.role = "assistant"
        response.model = kwargs.get("model", "claude-3-haiku-20240307")

        content_block = MagicMock()
        content_block.type = "text"
        content_block.text = self.default_response
        response.content = [content_block]

        response.stop_reason = "end_turn"
        usage = MagicMock()
        usage.input_tokens = 100
        usage.output_tokens = 250
        response.usage = usage

        return response

    def reset(self) -> None:
        """Reseta o histórico de chamadas do mock."""
        self.call_history.clear()

    @property
    def call_count(self) -> int:
        """Retorna o número de chamadas realizadas ao mock."""
        return len(self.call_history)


class MockCeleryTask:
    """Mock de task Celery para testes sem broker real.

    Permite testar lógica de tarefas assíncronas de forma síncrona.
    """

    def __init__(self, task_name: str = "mock_task") -> None:
        """Inicializa o mock da task Celery.

        Args:
            task_name: Nome identificador da task.
        """
        self.task_name = task_name
        self.call_history: list[dict[str, Any]] = []
        self._result: Any = None

    def delay(self, *args: Any, **kwargs: Any) -> MagicMock:
        """Simula chamada .delay() de uma task Celery.

        Returns:
            Mock do AsyncResult com task_id.
        """
        task_id = str(uuid.uuid4())
        self.call_history.append({
            "task_id": task_id,
            "args": args,
            "kwargs": kwargs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = MagicMock()
        result.id = task_id
        result.status = "PENDING"
        result.get = MagicMock(return_value=self._result)
        return result

    def apply_async(self, args: tuple = (), kwargs: dict | None = None, **options: Any) -> MagicMock:
        """Simula chamada .apply_async() de uma task Celery.

        Returns:
            Mock do AsyncResult com task_id.
        """
        return self.delay(*args, **(kwargs or {}))

    def set_result(self, result: Any) -> None:
        """Define o resultado que será retornado pelo mock.

        Args:
            result: Valor a ser retornado por .get().
        """
        self._result = result


class MockRedisClient:
    """Mock do cliente Redis para testes sem servidor Redis real.

    Implementa operações básicas de get/set/delete em memória.
    """

    def __init__(self) -> None:
        """Inicializa o mock do Redis com store em memória."""
        self._store: dict[str, Any] = {}
        self._expiry: dict[str, datetime] = {}

    async def get(self, key: str) -> Any | None:
        """Obtém valor pela chave.

        Args:
            key: Chave de busca.

        Returns:
            Valor armazenado ou None se não encontrado/expirado.
        """
        if key in self._expiry:
            if datetime.now(timezone.utc) > self._expiry[key]:
                del self._store[key]
                del self._expiry[key]
                return None
        return self._store.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ex: int | None = None,
    ) -> bool:
        """Armazena valor com chave e TTL opcional.

        Args:
            key: Chave de armazenamento.
            value: Valor a armazenar.
            ex: Tempo de expiração em segundos (opcional).

        Returns:
            True se armazenado com sucesso.
        """
        self._store[key] = value
        if ex is not None:
            self._expiry[key] = datetime.now(timezone.utc) + timedelta(seconds=ex)
        return True

    async def delete(self, key: str) -> int:
        """Remove valor pela chave.

        Args:
            key: Chave a remover.

        Returns:
            1 se removido, 0 se não encontrado.
        """
        if key in self._store:
            del self._store[key]
            self._expiry.pop(key, None)
            return 1
        return 0

    async def exists(self, key: str) -> bool:
        """Verifica se chave existe e não está expirada.

        Args:
            key: Chave a verificar.

        Returns:
            True se a chave existe e é válida.
        """
        value = await self.get(key)
        return value is not None

    def flush(self) -> None:
        """Limpa todo o store em memória."""
        self._store.clear()
        self._expiry.clear()


# ---------------------------------------------------------------------------
# Helpers para fixtures pytest
# ---------------------------------------------------------------------------

def get_event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    """Retorna a política de event loop para testes assíncronos.

    Compatível com pytest-asyncio.

    Returns:
        Política de event loop padrão.
    """
    return asyncio.DefaultEventLoopPolicy()


def build_auth_headers(
    token: str = "fake-jwt-token-para-testes",
    token_type: str = "Bearer",
) -> dict[str, str]:
    """Constrói headers de autenticação para requisições de teste.

    Args:
        token: Token JWT (pode ser fake para testes unitários).
        token_type: Tipo do token (padrão: Bearer).

    Returns:
        Dicionário com header Authorization.
    """
    return {
        "Authorization": f"{token_type} {token}",
        "Content-Type": "application/json",
    }


def assert_response_structure(
    response_data: dict[str, Any],
    required_fields: list[str],
    *,
    context: str = "",
) -> None:
    """Valida que a resposta contém todos os campos obrigatórios.

    Args:
        response_data: Dados da resposta a validar.
        required_fields: Lista de campos que devem estar presentes.
        context: Contexto adicional para mensagem de erro.

    Raises:
        AssertionError: Se algum campo obrigatório estiver ausente.
    """
    missing = [f for f in required_fields if f not in response_data]
    if missing:
        ctx = f" ({context})" if context else ""
        raise AssertionError(
            f"Campos obrigatórios ausentes na resposta{ctx}: {missing}. "
            f"Campos presentes: {list(response_data.keys())}"
        )


def assert_error_response(
    response_data: dict[str, Any],
    *,
    expected_status: int | None = None,
    expected_detail_contains: str | None = None,
) -> None:
    """Valida estrutura de resposta de erro da API.

    Args:
        response_data: Dados da resposta de erro.
        expected_status: Código de status HTTP esperado (opcional).
        expected_detail_contains: Substring esperada no campo 'detail' (opcional).

    Raises:
        AssertionError: Se a resposta não corresponder ao esperado.
    """
    assert "detail" in response_data, (
        f"Resposta de erro deve conter campo 'detail'. Recebido: {response_data}"
    )

    if expected_detail_contains is not None:
        detail = str(response_data["detail"])
        assert expected_detail_contains.lower() in detail.lower(), (
            f"Campo 'detail' deveria conter '{expected_detail_contains}', "
            f"mas contém: '{detail}'"
        )


# ---------------------------------------------------------------------------
# Gerador de configuração pytest (pytest.ini / pyproject.toml section)
# ---------------------------------------------------------------------------

PYTEST_INI_CONTENT: str = """
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
    "--tb=short",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html:htmlcov",
    "--cov-fail-under=80",
    "-v",
]
markers = [
    "unit: Testes unitários (rápidos, sem I/O externo)",
    "integration: Testes de integração (podem usar banco/redis)",
    "slow: Testes lentos (timeout estendido)",
    "auth: Testes relacionados a autenticação e autorização",
    "documents: Testes do módulo de documentos",
    "analysis: Testes do módulo de análise com IA",
    "chat: Testes do módulo de chat com IA",
    "audit: Testes do módulo de auditoria",
]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning:passlib.*",
    "ignore::UserWarning:sqlalchemy.*",
]
log_cli = true
log_cli_level = "INFO"
"""

COVERAGE_CONFIG_CONTENT: str = """
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*",
    "*/migrations/*",
    "*/alembic/*",
    "src/modules/m09_unit_testing_config.py",
]
branch = true
parallel = true

[tool.coverage.report]
fail_under = 80
show_missing = true
skip_covered = false
precision = 2
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
    "pass",
    "\\.\\.\\.",
    "# TODO:",
]

[tool.coverage.html]
directory = "htmlcov"
title = "Automação Jurídica Assistida — Cobertura de Testes"
"""


def get_pytest_config() -> str:
    """Retorna a configuração pytest para inclusão no pyproject.toml.

    Returns:
        String com a seção [tool.pytest.ini_options] formatada.
    """
    return PYTEST_INI_CONTENT.strip()


def get_coverage_config() -> str:
    """Retorna a configuração de cobertura para inclusão no pyproject.toml.

    Returns:
        String com as seções [tool.coverage.*] formatadas.
    """
    return COVERAGE_CONFIG_CONTENT.strip()


# ---------------------------------------------------------------------------
# Gerador de conftest.py base
# ---------------------------------------------------------------------------

CONFTEST_TEMPLATE: str = '''
"""Configuração global de fixtures para testes — conftest.py.

Gerado automaticamente pelo módulo m09_unit_testing_config.
Personalize conforme necessidade do projeto.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

# TODO: Descomentar quando os módulos de app e banco estiverem implementados
# from httpx import ASGITransport, AsyncClient
# from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
# from src.main import create_app
# from src.infrastructure.database import Base, get_db_session

from src.modules.m09_unit_testing_config import (
    MockAnthropicClient,
    MockCeleryTask,
    MockRedisClient,
    build_auth_headers,
    create_test_user_data,
    get_test_settings,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Cria event loop para toda a sessão de testes."""
    policy = asyncio.DefaultEventLoopPolicy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Retorna configurações de teste para toda a sessão."""
    return get_test_settings()


@pytest.fixture
def mock_anthropic_client() -> MockAnthropicClient:
    """Fixture que fornece mock do cliente Anthropic."""
    client = MockAnthropicClient()
    yield client
    client.reset()


@pytest.fixture
def mock_anthropic_client_failing() -> MockAnthropicClient:
    """Fixture que fornece mock do cliente Anthropic que simula falhas."""
    client = MockAnthropicClient(should_fail=True)
    yield client
    client.reset()


@pytest.fixture
def mock_celery_task() -> MockCeleryTask:
    """Fixture que fornece mock de task Celery."""
    return MockCeleryTask()


@pytest.fixture
def mock_redis() -> MockRedisClient:
    """Fixture que fornece mock do Redis."""
    client = MockRedisClient()
    yield client
    client.flush()


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Fixture que fornece dados de usuário de teste."""
    return create_test_user_data()


@pytest.fixture
def admin_user_data() -> dict[str, Any]:
    """Fixture que fornece dados de usuário administrador de teste."""
    return create_test_user_data(
        email="admin@automacaojuridica.com.br",
        nome="Administrador de Teste",
        role="admin",
    )


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Fixture que fornece headers de autenticação para testes."""
    return build_auth_headers()


# TODO: Descomentar e ajustar quando a aplicação FastAPI estiver implementada
# @pytest_asyncio.fixture
# async def async_client(test_settings) -> AsyncGenerator[AsyncClient, None]:
#     """Fixture que fornece cliente HTTP assíncrono para testes de API."""
#     app = create_app(settings=test_settings)
#     transport = ASGITransport(app=app)
#     async with AsyncClient(transport=transport, base_url="http://test") as client:
#         yield client

# TODO: Descomentar quando o banco de dados estiver configurado
# @pytest_asyncio.fixture
# async def db_session(test_settings) -> AsyncGenerator[AsyncSession, None]:
#     """Fixture que fornece sessão de banco de dados isolada por teste."""
#     engine = create_async_engine(test_settings.database_url, echo=False)
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     session_factory = async_sessionmaker(engine, expire_on_commit=False)
#     async with session_factory() as session:
#         yield session
#         await session.rollback()
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.drop_all)
#     await engine.dispose()
'''


def get_conftest_template() -> str:
    """Retorna o template do conftest.py para a raiz de testes.

    Returns:
        String com o conteúdo completo do conftest.py.
    """
    return CONFTEST_TEMPLATE.strip()


# ---------------------------------------------------------------------------
# Utilitário para gerar estrutura de diretórios de testes
# ---------------------------------------------------------------------------

TEST_DIRECTORY_STRUCTURE: dict[str, list[str]] = {
    "tests/": ["__init__.py", "conftest.py"],
    "tests/unit/": ["__init__.py", "conftest.py"],
    "tests/unit/auth/": ["__init__.py", "test_auth_service.py"],
    "tests/unit/users/": ["__init__.py", "test_user_service.py"],
    "tests/unit/documents/": ["__init__.py", "test_document_service.py"],
    "tests/unit/analysis/": ["__init__.py", "test_analysis_service.py"],
    "tests/unit/chat/": ["__init__.py", "test_chat_service.py"],
    "tests/unit/audit/": ["__init__.py", "test_audit_service.py"],
    "tests/integration/": ["__init__.py", "conftest.py"],
    "tests/integration/api/": ["__init__.py"],
    "tests/integration/database/": ["__init__.py"],
}


def get_test_directory_structure() -> dict[str, list[str]]:
    """Retorna a estrutura de diretórios recomendada para testes.

    Returns:
        Dicionário mapeando diretórios para lista de arquivos.
    """
    return TEST_DIRECTORY_STRUCTURE.copy()


# ---------------------------------------------------------------------------
# Ponto de entrada para geração de configuração via CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("Automação Jurídica Assistida — Configuração de Testes")
    print("=" * 70)
    print()
    print("--- Configuração pytest (adicionar ao pyproject.toml) ---")
    print(get_pytest_config())
    print()
    print("--- Configuração coverage (adicionar ao pyproject.toml) ---")
    print(get_coverage_config())
    print()
    print("--- Estrutura de diretórios recomendada ---")
    for directory, files in get_test_directory_structure().items():
        for f in files:
            print(f"  {directory}{f}")
    print()
    print(f"Cobertura mínima exigida: {MIN_COVERAGE_PERCENT}%")
    print("Geração concluída com sucesso.")
