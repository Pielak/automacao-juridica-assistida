"""Módulo backlog #7: Configurar stack do projeto.

Responsável por validar dependências instaladas, verificar versões mínimas
requeridas, checar compatibilidade entre componentes da stack e reportar
o estado geral de saúde da configuração do projeto.

Este módulo é utilizado tanto em tempo de inicialização (startup checks)
quanto sob demanda via endpoint de health/diagnóstico.

Exemplo de uso:
    from backend.src.modules.m07_stack_configuration import (
        validate_stack,
        get_stack_report,
        check_dependency,
    )

    report = validate_stack()
    if not report.all_valid:
        for issue in report.issues:
            print(f"[{issue.severity}] {issue.component}: {issue.message}")
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from backend.src.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes — Requisitos mínimos de versão da stack
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Nível de severidade de um problema encontrado na validação."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class DependencyRequirement:
    """Especificação de uma dependência obrigatória ou recomendada.

    Attributes:
        package_name: Nome do pacote conforme registrado no PyPI / importlib.metadata.
        import_name: Nome utilizado no import (pode diferir do package_name).
        min_version: Versão mínima aceitável (semver parcial, ex: '0.100').
        max_version: Versão máxima aceitável (opcional).
        required: Se True, a ausência é CRITICAL; se False, é WARNING.
        description: Descrição em PT-BR do papel da dependência.
    """

    package_name: str
    import_name: str
    min_version: str
    max_version: Optional[str] = None
    required: bool = True
    description: str = ""


# Mapeamento completo das dependências da stack backend
BACKEND_DEPENDENCIES: list[DependencyRequirement] = [
    # --- Framework principal ---
    DependencyRequirement(
        package_name="fastapi",
        import_name="fastapi",
        min_version="0.100",
        required=True,
        description="Framework web assíncrono — API REST com documentação OpenAPI automática.",
    ),
    DependencyRequirement(
        package_name="pydantic",
        import_name="pydantic",
        min_version="2.0",
        required=True,
        description="Serialização e validação de dados de alta performance.",
    ),
    DependencyRequirement(
        package_name="pydantic-settings",
        import_name="pydantic_settings",
        min_version="2.0",
        required=True,
        description="Carregamento de configurações via variáveis de ambiente.",
    ),
    DependencyRequirement(
        package_name="uvicorn",
        import_name="uvicorn",
        min_version="0.20",
        required=True,
        description="Servidor ASGI de produção para FastAPI.",
    ),
    # --- Banco de dados ---
    DependencyRequirement(
        package_name="SQLAlchemy",
        import_name="sqlalchemy",
        min_version="2.0",
        required=True,
        description="ORM assíncrono para PostgreSQL (Clean Architecture — adapter de persistência).",
    ),
    DependencyRequirement(
        package_name="asyncpg",
        import_name="asyncpg",
        min_version="0.27",
        required=True,
        description="Driver assíncrono nativo para PostgreSQL.",
    ),
    DependencyRequirement(
        package_name="alembic",
        import_name="alembic",
        min_version="1.10",
        required=True,
        description="Migrações de banco de dados.",
    ),
    # --- Autenticação e segurança ---
    DependencyRequirement(
        package_name="PyJWT",
        import_name="jwt",
        min_version="2.6",
        required=True,
        description="Autenticação JWT com suporte a RS256.",
    ),
    DependencyRequirement(
        package_name="passlib",
        import_name="passlib",
        min_version="1.7",
        required=True,
        description="Hashing seguro de senhas com bcrypt.",
    ),
    DependencyRequirement(
        package_name="pyotp",
        import_name="pyotp",
        min_version="2.8",
        required=False,
        description="MFA via TOTP (Google Authenticator / Authy).",
    ),
    # --- Processamento assíncrono ---
    DependencyRequirement(
        package_name="celery",
        import_name="celery",
        min_version="5.3",
        required=True,
        description="Processamento assíncrono de tarefas (análise de documentos, etc.).",
    ),
    # --- Integração LLM ---
    DependencyRequirement(
        package_name="anthropic",
        import_name="anthropic",
        min_version="0.18",
        required=True,
        description="SDK oficial para integração com Claude (Anthropic).",
    ),
    DependencyRequirement(
        package_name="httpx",
        import_name="httpx",
        min_version="0.24",
        required=True,
        description="Cliente HTTP assíncrono para chamadas externas.",
    ),
    DependencyRequirement(
        package_name="tenacity",
        import_name="tenacity",
        min_version="8.2",
        required=True,
        description="Retry e circuit breaker para chamadas à API Anthropic.",
    ),
    # --- Observabilidade e controle ---
    DependencyRequirement(
        package_name="structlog",
        import_name="structlog",
        min_version="23.1",
        required=True,
        description="Logs estruturados para rastreabilidade e auditoria.",
    ),
    DependencyRequirement(
        package_name="slowapi",
        import_name="slowapi",
        min_version="0.1.5",
        required=False,
        description="Rate limiting para proteção de endpoints.",
    ),
    # --- Upload ---
    DependencyRequirement(
        package_name="python-multipart",
        import_name="multipart",
        min_version="0.0.6",
        required=True,
        description="Suporte a upload de arquivos via multipart/form-data.",
    ),
]

# Versão mínima do Python exigida pela stack
MIN_PYTHON_VERSION = (3, 11)


# ---------------------------------------------------------------------------
# Modelos de resultado
# ---------------------------------------------------------------------------

@dataclass
class ValidationIssue:
    """Representa um problema encontrado durante a validação da stack.

    Attributes:
        component: Nome do componente ou pacote afetado.
        severity: Nível de severidade (critical, warning, info).
        message: Descrição do problema em PT-BR.
        installed_version: Versão encontrada (None se não instalado).
        required_version: Versão mínima exigida.
    """

    component: str
    severity: Severity
    message: str
    installed_version: Optional[str] = None
    required_version: Optional[str] = None


@dataclass
class StackReport:
    """Relatório completo da validação da stack.

    Attributes:
        all_valid: True se nenhuma issue CRITICAL foi encontrada.
        python_version: Versão do Python em execução.
        issues: Lista de problemas encontrados.
        dependencies_checked: Número total de dependências verificadas.
        dependencies_ok: Número de dependências válidas.
        settings_valid: True se as configurações do settings.py carregaram corretamente.
        details: Dicionário com detalhes adicionais por dependência.
    """

    all_valid: bool = True
    python_version: str = ""
    issues: list[ValidationIssue] = field(default_factory=list)
    dependencies_checked: int = 0
    dependencies_ok: int = 0
    settings_valid: bool = False
    details: dict[str, dict[str, Any]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Funções utilitárias de comparação de versão
# ---------------------------------------------------------------------------

def _parse_version_tuple(version_str: str) -> tuple[int, ...]:
    """Converte uma string de versão em tupla numérica para comparação.

    Lida com sufixos comuns como 'a', 'b', 'rc', 'dev', 'post' removendo-os
    antes da conversão.

    Args:
        version_str: String de versão (ex: '2.0.1', '0.100.0a1').

    Returns:
        Tupla de inteiros representando a versão.
    """
    # Remove sufixos de pré-release
    clean = version_str
    for sep in ("a", "b", "rc", "dev", "post", "+"):
        clean = clean.split(sep)[0]

    parts: list[int] = []
    for segment in clean.strip().split("."):
        segment = segment.strip()
        if segment.isdigit():
            parts.append(int(segment))
        else:
            # Tenta extrair dígitos iniciais
            digits = ""
            for ch in segment:
                if ch.isdigit():
                    digits += ch
                else:
                    break
            if digits:
                parts.append(int(digits))

    return tuple(parts) if parts else (0,)


def _version_gte(installed: str, minimum: str) -> bool:
    """Verifica se a versão instalada é >= a versão mínima.

    Args:
        installed: Versão instalada.
        minimum: Versão mínima requerida.

    Returns:
        True se installed >= minimum.
    """
    inst = _parse_version_tuple(installed)
    mini = _parse_version_tuple(minimum)

    # Normaliza comprimento para comparação justa
    max_len = max(len(inst), len(mini))
    inst_padded = inst + (0,) * (max_len - len(inst))
    mini_padded = mini + (0,) * (max_len - len(mini))

    return inst_padded >= mini_padded


def _version_lte(installed: str, maximum: str) -> bool:
    """Verifica se a versão instalada é <= a versão máxima.

    Args:
        installed: Versão instalada.
        maximum: Versão máxima permitida.

    Returns:
        True se installed <= maximum.
    """
    inst = _parse_version_tuple(installed)
    maxi = _parse_version_tuple(maximum)

    max_len = max(len(inst), len(maxi))
    inst_padded = inst + (0,) * (max_len - len(inst))
    maxi_padded = maxi + (0,) * (max_len - len(maxi))

    return inst_padded <= maxi_padded


# ---------------------------------------------------------------------------
# Funções de verificação individual
# ---------------------------------------------------------------------------

def check_python_version() -> ValidationIssue | None:
    """Verifica se a versão do Python atende ao requisito mínimo.

    Returns:
        ValidationIssue se a versão for insuficiente, None caso contrário.
    """
    current = sys.version_info[:2]
    if current < MIN_PYTHON_VERSION:
        return ValidationIssue(
            component="python",
            severity=Severity.CRITICAL,
            message=(
                f"Versão do Python insuficiente. "
                f"Encontrada: {current[0]}.{current[1]}, "
                f"mínima requerida: {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}."
            ),
            installed_version=f"{current[0]}.{current[1]}",
            required_version=f"{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}",
        )
    return None


def check_dependency(req: DependencyRequirement) -> tuple[bool, Optional[str], Optional[ValidationIssue]]:
    """Verifica se uma dependência está instalada e atende aos requisitos de versão.

    Args:
        req: Especificação da dependência a ser verificada.

    Returns:
        Tupla (is_valid, installed_version, issue).
        - is_valid: True se a dependência está OK.
        - installed_version: Versão encontrada ou None.
        - issue: ValidationIssue se houver problema, None caso contrário.
    """
    # 1. Verificar se o pacote pode ser importado
    try:
        importlib.import_module(req.import_name)
    except ImportError:
        severity = Severity.CRITICAL if req.required else Severity.WARNING
        return (
            False,
            None,
            ValidationIssue(
                component=req.package_name,
                severity=severity,
                message=(
                    f"Pacote '{req.package_name}' não encontrado. "
                    f"{req.description} "
                    f"Instale com: pip install {req.package_name}"
                ),
                installed_version=None,
                required_version=req.min_version,
            ),
        )

    # 2. Obter versão instalada
    installed_version: Optional[str] = None
    try:
        installed_version = importlib.metadata.version(req.package_name)
    except importlib.metadata.PackageNotFoundError:
        # Alguns pacotes têm nomes diferentes no metadata
        # Tenta variações comuns
        for alt_name in [
            req.package_name.lower(),
            req.package_name.replace("-", "_"),
            req.import_name,
        ]:
            try:
                installed_version = importlib.metadata.version(alt_name)
                break
            except importlib.metadata.PackageNotFoundError:
                continue

    if installed_version is None:
        return (
            True,
            None,
            ValidationIssue(
                component=req.package_name,
                severity=Severity.INFO,
                message=(
                    f"Pacote '{req.package_name}' importável, mas não foi possível "
                    f"determinar a versão instalada. Verificação de versão ignorada."
                ),
            ),
        )

    # 3. Verificar versão mínima
    if not _version_gte(installed_version, req.min_version):
        severity = Severity.CRITICAL if req.required else Severity.WARNING
        return (
            False,
            installed_version,
            ValidationIssue(
                component=req.package_name,
                severity=severity,
                message=(
                    f"Versão de '{req.package_name}' insuficiente. "
                    f"Instalada: {installed_version}, mínima: {req.min_version}. "
                    f"Atualize com: pip install '{req.package_name}>={req.min_version}'"
                ),
                installed_version=installed_version,
                required_version=req.min_version,
            ),
        )

    # 4. Verificar versão máxima (se definida)
    if req.max_version and not _version_lte(installed_version, req.max_version):
        return (
            False,
            installed_version,
            ValidationIssue(
                component=req.package_name,
                severity=Severity.WARNING,
                message=(
                    f"Versão de '{req.package_name}' acima do máximo testado. "
                    f"Instalada: {installed_version}, máxima: {req.max_version}. "
                    f"Podem ocorrer incompatibilidades."
                ),
                installed_version=installed_version,
                required_version=f"{req.min_version} - {req.max_version}",
            ),
        )

    return (True, installed_version, None)


def check_settings_loadable() -> tuple[bool, Optional[ValidationIssue]]:
    """Verifica se as configurações do projeto podem ser carregadas.

    Tenta invocar get_settings() e captura erros de validação do Pydantic
    ou variáveis de ambiente ausentes.

    Returns:
        Tupla (is_valid, issue).
    """
    try:
        settings = get_settings()
        # Verificação básica: o objeto settings deve existir
        if settings is None:
            return (
                False,
                ValidationIssue(
                    component="settings",
                    severity=Severity.CRITICAL,
                    message="get_settings() retornou None. Verifique o arquivo .env e as variáveis de ambiente.",
                ),
            )
        return (True, None)
    except Exception as exc:
        return (
            False,
            ValidationIssue(
                component="settings",
                severity=Severity.CRITICAL,
                message=(
                    f"Falha ao carregar configurações: {type(exc).__name__}: {exc}. "
                    f"Verifique o arquivo .env e as variáveis de ambiente obrigatórias."
                ),
            ),
        )


# ---------------------------------------------------------------------------
# Funções de compatibilidade entre componentes
# ---------------------------------------------------------------------------

def check_compatibility() -> list[ValidationIssue]:
    """Verifica compatibilidade conhecida entre componentes da stack.

    Checa combinações que podem causar problemas:
    - SQLAlchemy 2.x requer asyncpg para modo assíncrono
    - Pydantic v2 requer pydantic-settings separado
    - FastAPI >= 0.100 requer Pydantic v2

    Returns:
        Lista de issues de compatibilidade encontradas.
    """
    issues: list[ValidationIssue] = []

    # Verificar se SQLAlchemy 2.x está com asyncpg disponível
    sqlalchemy_available = False
    asyncpg_available = False

    try:
        import sqlalchemy  # noqa: F811
        sqlalchemy_available = True
    except ImportError:
        pass

    try:
        import asyncpg  # noqa: F811
        asyncpg_available = True
    except ImportError:
        pass

    if sqlalchemy_available and not asyncpg_available:
        issues.append(
            ValidationIssue(
                component="sqlalchemy+asyncpg",
                severity=Severity.CRITICAL,
                message=(
                    "SQLAlchemy está instalado mas asyncpg não foi encontrado. "
                    "O modo assíncrono com PostgreSQL requer asyncpg. "
                    "Instale com: pip install asyncpg"
                ),
            )
        )

    # Verificar compatibilidade FastAPI + Pydantic v2
    try:
        fastapi_version = importlib.metadata.version("fastapi")
        pydantic_version = importlib.metadata.version("pydantic")

        if _version_gte(fastapi_version, "0.100") and not _version_gte(pydantic_version, "2.0"):
            issues.append(
                ValidationIssue(
                    component="fastapi+pydantic",
                    severity=Severity.CRITICAL,
                    message=(
                        f"FastAPI {fastapi_version} requer Pydantic v2+, "
                        f"mas encontrada versão {pydantic_version}. "
                        f"Atualize com: pip install 'pydantic>=2.0'"
                    ),
                    installed_version=pydantic_version,
                    required_version="2.0",
                )
            )
    except importlib.metadata.PackageNotFoundError:
        pass  # Já reportado na verificação individual

    # Verificar se pydantic-settings está disponível (separado no Pydantic v2)
    try:
        pydantic_version = importlib.metadata.version("pydantic")
        if _version_gte(pydantic_version, "2.0"):
            try:
                importlib.import_module("pydantic_settings")
            except ImportError:
                issues.append(
                    ValidationIssue(
                        component="pydantic+pydantic-settings",
                        severity=Severity.CRITICAL,
                        message=(
                            "Pydantic v2 requer o pacote 'pydantic-settings' separado "
                            "para BaseSettings. Instale com: pip install pydantic-settings"
                        ),
                    )
                )
    except importlib.metadata.PackageNotFoundError:
        pass

    # Verificar se Celery tem broker configurável (Redis recomendado)
    try:
        importlib.import_module("celery")
        try:
            importlib.import_module("redis")
        except ImportError:
            issues.append(
                ValidationIssue(
                    component="celery+redis",
                    severity=Severity.WARNING,
                    message=(
                        "Celery está instalado mas o pacote 'redis' não foi encontrado. "
                        "Redis é o broker recomendado para Celery neste projeto. "
                        "Instale com: pip install redis"
                    ),
                )
            )
    except ImportError:
        pass

    return issues


# ---------------------------------------------------------------------------
# Função principal de validação
# ---------------------------------------------------------------------------

def validate_stack(
    dependencies: list[DependencyRequirement] | None = None,
    check_settings: bool = True,
) -> StackReport:
    """Executa validação completa da stack do projeto.

    Verifica versão do Python, todas as dependências configuradas,
    compatibilidade entre componentes e carregamento das configurações.

    Args:
        dependencies: Lista customizada de dependências a verificar.
            Se None, usa BACKEND_DEPENDENCIES.
        check_settings: Se True, tenta carregar settings via get_settings().

    Returns:
        StackReport com o resultado completo da validação.
    """
    if dependencies is None:
        dependencies = BACKEND_DEPENDENCIES

    report = StackReport(
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        dependencies_checked=len(dependencies),
    )

    # 1. Verificar versão do Python
    python_issue = check_python_version()
    if python_issue:
        report.issues.append(python_issue)
        report.all_valid = False
        logger.error(
            "Validação da stack: versão do Python insuficiente — %s",
            python_issue.message,
        )

    # 2. Verificar cada dependência
    ok_count = 0
    for req in dependencies:
        is_valid, installed_version, issue = check_dependency(req)

        report.details[req.package_name] = {
            "installed_version": installed_version,
            "min_version": req.min_version,
            "max_version": req.max_version,
            "required": req.required,
            "valid": is_valid,
            "description": req.description,
        }

        if is_valid:
            ok_count += 1
            if issue:  # INFO level (ex: versão não determinável)
                report.issues.append(issue)
        else:
            if issue:
                report.issues.append(issue)
                if issue.severity == Severity.CRITICAL:
                    report.all_valid = False
                    logger.error(
                        "Validação da stack: dependência crítica — %s",
                        issue.message,
                    )
                else:
                    logger.warning(
                        "Validação da stack: aviso — %s",
                        issue.message,
                    )

    report.dependencies_ok = ok_count

    # 3. Verificar compatibilidade entre componentes
    compat_issues = check_compatibility()
    for issue in compat_issues:
        report.issues.append(issue)
        if issue.severity == Severity.CRITICAL:
            report.all_valid = False
            logger.error(
                "Validação da stack: incompatibilidade — %s",
                issue.message,
            )

    # 4. Verificar carregamento das configurações
    if check_settings:
        settings_valid, settings_issue = check_settings_loadable()
        report.settings_valid = settings_valid
        if settings_issue:
            report.issues.append(settings_issue)
            if settings_issue.severity == Severity.CRITICAL:
                report.all_valid = False
                logger.error(
                    "Validação da stack: configurações — %s",
                    settings_issue.message,
                )
    else:
        report.settings_valid = True  # Não verificado, assume OK

    # Log resumo
    if report.all_valid:
        logger.info(
            "Validação da stack concluída com sucesso: %d/%d dependências OK, Python %s.",
            report.dependencies_ok,
            report.dependencies_checked,
            report.python_version,
        )
    else:
        critical_count = sum(
            1 for i in report.issues if i.severity == Severity.CRITICAL
        )
        logger.error(
            "Validação da stack falhou: %d problemas críticos encontrados, "
            "%d/%d dependências OK, Python %s.",
            critical_count,
            report.dependencies_ok,
            report.dependencies_checked,
            report.python_version,
        )

    return report


def get_stack_report() -> dict[str, Any]:
    """Gera relatório da stack em formato dicionário, adequado para serialização JSON.

    Útil para endpoints de health check e diagnóstico.

    Returns:
        Dicionário com o relatório completo da stack.
    """
    report = validate_stack()

    return {
        "all_valid": report.all_valid,
        "python_version": report.python_version,
        "dependencies_checked": report.dependencies_checked,
        "dependencies_ok": report.dependencies_ok,
        "settings_valid": report.settings_valid,
        "issues": [
            {
                "component": issue.component,
                "severity": issue.severity.value,
                "message": issue.message,
                "installed_version": issue.installed_version,
                "required_version": issue.required_version,
            }
            for issue in report.issues
        ],
        "details": report.details,
    }


def ensure_stack_ready() -> None:
    """Verifica a stack e levanta exceção se houver problemas críticos.

    Destinado para uso no startup da aplicação FastAPI.

    Raises:
        RuntimeError: Se alguma dependência crítica estiver ausente ou
            incompatível.
    """
    report = validate_stack()

    if not report.all_valid:
        critical_issues = [
            issue for issue in report.issues
            if issue.severity == Severity.CRITICAL
        ]
        messages = "\n".join(
            f"  - [{issue.component}] {issue.message}"
            for issue in critical_issues
        )
        raise RuntimeError(
            f"A stack do projeto possui {len(critical_issues)} problema(s) crítico(s) "
            f"que impedem a inicialização:\n{messages}\n\n"
            f"Corrija os problemas acima e tente novamente."
        )

    logger.info("Stack do projeto validada e pronta para uso.")
