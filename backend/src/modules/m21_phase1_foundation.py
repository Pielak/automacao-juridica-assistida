"""Módulo backlog #21: Artefatos técnicos fundamentais — Automação Jurídica Assistida.

Responsável por orquestrar e validar os artefatos fundamentais da Fase 1:
- Scaffold do projeto (estrutura de diretórios e módulos)
- Configuração base de CI/CD (validação de pipelines)
- Schema inicial do banco de dados (migrações Alembic)
- Autenticação base (JWT + RBAC foundation)

Este módulo atua como ponto de verificação central para garantir que todos
os componentes fundamentais estão corretamente configurados antes de
avançar para funcionalidades de domínio.

Exemplo de uso:
    from backend.src.modules.m21_phase1_foundation import (
        Phase1Foundation,
        validate_foundation,
        get_foundation_status,
        ScaffoldValidator,
        DatabaseSchemaValidator,
        AuthBaseValidator,
        CICDValidator,
    )

    foundation = Phase1Foundation()
    status = await foundation.validate_all()
    if not status.is_ready:
        for issue in status.issues:
            logger.warning(issue)
"""

from __future__ import annotations

import importlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

# Peers do projeto
from backend.src.modules.m06_data_model_engine_config import (
    EngineConfig,
    get_engine_config,
)
from backend.src.modules.m07_stack_configuration import (
    check_dependency,
    get_stack_report,
    validate_stack,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes e configurações da Fase 1
# ---------------------------------------------------------------------------

# Diretórios obrigatórios do scaffold
REQUIRED_DIRECTORIES: list[str] = [
    "backend/src",
    "backend/src/modules",
    "backend/src/infrastructure",
    "backend/src/infrastructure/database",
    "backend/src/infrastructure/auth",
    "backend/src/infrastructure/logging",
    "backend/src/domain",
    "backend/src/domain/entities",
    "backend/src/domain/ports",
    "backend/src/domain/services",
    "backend/src/application",
    "backend/src/application/use_cases",
    "backend/src/application/dtos",
    "backend/src/api",
    "backend/src/api/routers",
    "backend/src/api/middleware",
    "backend/src/api/dependencies",
    "backend/tests",
    "backend/tests/unit",
    "backend/tests/integration",
    "backend/alembic",
    "backend/alembic/versions",
    "frontend/src",
    "frontend/src/components",
    "frontend/src/pages",
    "frontend/src/hooks",
    "frontend/src/services",
    "frontend/src/types",
]

# Arquivos obrigatórios do scaffold
REQUIRED_FILES: list[str] = [
    "backend/src/__init__.py",
    "backend/src/modules/__init__.py",
    "backend/src/infrastructure/__init__.py",
    "backend/src/infrastructure/database/__init__.py",
    "backend/src/infrastructure/auth/__init__.py",
    "backend/src/domain/__init__.py",
    "backend/src/application/__init__.py",
    "backend/src/api/__init__.py",
    "backend/alembic/env.py",
    "backend/alembic.ini",
    "backend/pyproject.toml",
    "frontend/package.json",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
    ".env.example",
    "docker-compose.yml",
]

# Dependências Python obrigatórias para Fase 1
REQUIRED_PYTHON_DEPS: list[dict[str, str]] = [
    {"name": "fastapi", "min_version": "0.100.0"},
    {"name": "pydantic", "min_version": "2.0.0"},
    {"name": "sqlalchemy", "min_version": "2.0.0"},
    {"name": "alembic", "min_version": "1.12.0"},
    {"name": "asyncpg", "min_version": "0.28.0"},
    {"name": "python-jose", "min_version": "3.3.0"},
    {"name": "passlib", "min_version": "1.7.4"},
    {"name": "structlog", "min_version": "23.0.0"},
    {"name": "httpx", "min_version": "0.24.0"},
]

# Arquivos de CI/CD esperados
CICD_FILES: list[str] = [
    ".github/workflows/ci.yml",
    ".github/workflows/cd.yml",
    "Dockerfile",
    "docker-compose.yml",
    ".dockerignore",
]

# Tabelas obrigatórias do schema inicial
REQUIRED_DB_TABLES: list[str] = [
    "users",
    "roles",
    "user_roles",
    "sessions",
    "audit_logs",
]


# ---------------------------------------------------------------------------
# Enums e modelos de dados
# ---------------------------------------------------------------------------


class ValidationSeverity(str, Enum):
    """Severidade de um problema encontrado na validação."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ComponentStatus(str, Enum):
    """Status de um componente da fundação."""

    READY = "ready"
    PARTIAL = "partial"
    MISSING = "missing"
    ERROR = "error"


class ValidationIssue(BaseModel):
    """Representa um problema encontrado durante a validação da fundação."""

    component: str = Field(description="Componente afetado (scaffold, cicd, db, auth)")
    severity: ValidationSeverity = Field(description="Severidade do problema")
    message: str = Field(description="Descrição do problema em PT-BR")
    suggestion: Optional[str] = Field(
        default=None, description="Sugestão de correção em PT-BR"
    )
    path: Optional[str] = Field(
        default=None, description="Caminho do arquivo/diretório afetado"
    )


class ComponentReport(BaseModel):
    """Relatório de validação de um componente individual."""

    name: str = Field(description="Nome do componente")
    status: ComponentStatus = Field(description="Status atual do componente")
    issues: list[ValidationIssue] = Field(
        default_factory=list, description="Problemas encontrados"
    )
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora da verificação",
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Detalhes adicionais da verificação"
    )

    @property
    def has_errors(self) -> bool:
        """Verifica se há erros críticos no componente."""
        return any(
            issue.severity == ValidationSeverity.ERROR for issue in self.issues
        )

    @property
    def error_count(self) -> int:
        """Conta o número de erros críticos."""
        return sum(
            1 for issue in self.issues
            if issue.severity == ValidationSeverity.ERROR
        )

    @property
    def warning_count(self) -> int:
        """Conta o número de avisos."""
        return sum(
            1 for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        )


class FoundationStatus(BaseModel):
    """Status consolidado de toda a fundação da Fase 1."""

    is_ready: bool = Field(
        description="Indica se a fundação está pronta para avançar"
    )
    components: dict[str, ComponentReport] = Field(
        default_factory=dict, description="Relatórios por componente"
    )
    total_errors: int = Field(default=0, description="Total de erros encontrados")
    total_warnings: int = Field(default=0, description="Total de avisos encontrados")
    validated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora da validação completa",
    )
    stack_report: Optional[dict[str, Any]] = Field(
        default=None, description="Relatório da stack (m07)"
    )
    engine_config_valid: bool = Field(
        default=False, description="Configuração do engine de banco validada"
    )

    @property
    def issues(self) -> list[ValidationIssue]:
        """Retorna todos os problemas de todos os componentes."""
        all_issues: list[ValidationIssue] = []
        for report in self.components.values():
            all_issues.extend(report.issues)
        return all_issues

    @property
    def summary(self) -> str:
        """Resumo textual do status da fundação."""
        if self.is_ready:
            return (
                f"Fundação Fase 1 PRONTA — {len(self.components)} componentes "
                f"validados com {self.total_warnings} aviso(s)."
            )
        return (
            f"Fundação Fase 1 INCOMPLETA — {self.total_errors} erro(s) e "
            f"{self.total_warnings} aviso(s) em {len(self.components)} componentes."
        )


# ---------------------------------------------------------------------------
# Validadores individuais
# ---------------------------------------------------------------------------


class ScaffoldValidator:
    """Validador da estrutura de diretórios e arquivos do scaffold.

    Verifica se todos os diretórios e arquivos obrigatórios existem
    na raiz do projeto, garantindo que o scaffold foi corretamente
    gerado antes de prosseguir com o desenvolvimento.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Inicializa o validador de scaffold.

        Args:
            project_root: Caminho raiz do projeto. Se não informado,
                          tenta detectar automaticamente.
        """
        self.project_root = project_root or self._detect_project_root()

    def _detect_project_root(self) -> Path:
        """Detecta a raiz do projeto a partir do diretório atual.

        Percorre os diretórios pais procurando por indicadores de raiz
        do projeto (docker-compose.yml, pyproject.toml, .git).

        Returns:
            Caminho da raiz do projeto.
        """
        current = Path.cwd()
        root_indicators = ["docker-compose.yml", ".git", "pyproject.toml"]

        for parent in [current, *current.parents]:
            if any((parent / indicator).exists() for indicator in root_indicators):
                return parent

        logger.warning(
            "Não foi possível detectar a raiz do projeto. "
            "Usando diretório atual: %s",
            current,
        )
        return current

    def validate(self) -> ComponentReport:
        """Executa a validação completa do scaffold.

        Returns:
            Relatório com o status do scaffold e problemas encontrados.
        """
        issues: list[ValidationIssue] = []
        dirs_found = 0
        dirs_total = len(REQUIRED_DIRECTORIES)
        files_found = 0
        files_total = len(REQUIRED_FILES)

        # Validar diretórios obrigatórios
        for dir_path in REQUIRED_DIRECTORIES:
            full_path = self.project_root / dir_path
            if full_path.is_dir():
                dirs_found += 1
            else:
                issues.append(
                    ValidationIssue(
                        component="scaffold",
                        severity=ValidationSeverity.ERROR,
                        message=f"Diretório obrigatório ausente: {dir_path}",
                        suggestion=f"Crie o diretório com: mkdir -p {dir_path}",
                        path=dir_path,
                    )
                )

        # Validar arquivos obrigatórios
        for file_path in REQUIRED_FILES:
            full_path = self.project_root / file_path
            if full_path.is_file():
                files_found += 1
                # Verificar se o arquivo não está vazio (aviso)
                if full_path.stat().st_size == 0:
                    issues.append(
                        ValidationIssue(
                            component="scaffold",
                            severity=ValidationSeverity.WARNING,
                            message=f"Arquivo existe mas está vazio: {file_path}",
                            suggestion="Adicione o conteúdo necessário ao arquivo.",
                            path=file_path,
                        )
                    )
            else:
                issues.append(
                    ValidationIssue(
                        component="scaffold",
                        severity=ValidationSeverity.ERROR,
                        message=f"Arquivo obrigatório ausente: {file_path}",
                        suggestion=f"Crie o arquivo: touch {file_path}",
                        path=file_path,
                    )
                )

        # Verificar __init__.py em pacotes Python
        init_issues = self._check_init_files()
        issues.extend(init_issues)

        # Determinar status
        has_errors = any(
            i.severity == ValidationSeverity.ERROR for i in issues
        )
        if not has_errors:
            status = ComponentStatus.READY
        elif dirs_found > 0 or files_found > 0:
            status = ComponentStatus.PARTIAL
        else:
            status = ComponentStatus.MISSING

        return ComponentReport(
            name="scaffold",
            status=status,
            issues=issues,
            details={
                "project_root": str(self.project_root),
                "directories": {"found": dirs_found, "total": dirs_total},
                "files": {"found": files_found, "total": files_total},
            },
        )

    def _check_init_files(self) -> list[ValidationIssue]:
        """Verifica se pacotes Python possuem __init__.py.

        Returns:
            Lista de problemas encontrados.
        """
        issues: list[ValidationIssue] = []
        python_dirs = [
            d for d in REQUIRED_DIRECTORIES if d.startswith("backend/src")
        ]

        for dir_path in python_dirs:
            full_path = self.project_root / dir_path
            init_file = full_path / "__init__.py"
            if full_path.is_dir() and not init_file.exists():
                issues.append(
                    ValidationIssue(
                        component="scaffold",
                        severity=ValidationSeverity.WARNING,
                        message=(
                            f"Pacote Python sem __init__.py: {dir_path}"
                        ),
                        suggestion=f"Crie: touch {dir_path}/__init__.py",
                        path=f"{dir_path}/__init__.py",
                    )
                )

        return issues

    def create_scaffold(self, dry_run: bool = True) -> list[str]:
        """Cria a estrutura de diretórios e arquivos do scaffold.

        Args:
            dry_run: Se True, apenas lista o que seria criado sem executar.

        Returns:
            Lista de caminhos que foram (ou seriam) criados.
        """
        created: list[str] = []

        for dir_path in REQUIRED_DIRECTORIES:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                if not dry_run:
                    full_path.mkdir(parents=True, exist_ok=True)
                    logger.info("Diretório criado: %s", dir_path)
                created.append(f"[DIR] {dir_path}")

        for file_path in REQUIRED_FILES:
            full_path = self.project_root / file_path
            if not full_path.exists():
                if not dry_run:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.touch()
                    logger.info("Arquivo criado: %s", file_path)
                created.append(f"[FILE] {file_path}")

        # Garantir __init__.py em pacotes Python
        python_dirs = [
            d for d in REQUIRED_DIRECTORIES if d.startswith("backend/src")
        ]
        for dir_path in python_dirs:
            init_path = self.project_root / dir_path / "__init__.py"
            if not init_path.exists():
                if not dry_run:
                    init_path.parent.mkdir(parents=True, exist_ok=True)
                    init_path.touch()
                    logger.info("__init__.py criado: %s", init_path)
                created.append(f"[INIT] {dir_path}/__init__.py")

        return created


class CICDValidator:
    """Validador de configuração de CI/CD.

    Verifica a presença e estrutura básica dos arquivos de pipeline
    de integração e entrega contínua.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Inicializa o validador de CI/CD.

        Args:
            project_root: Caminho raiz do projeto.
        """
        self.project_root = project_root or Path.cwd()

    def validate(self) -> ComponentReport:
        """Executa a validação dos artefatos de CI/CD.

        Returns:
            Relatório com o status de CI/CD e problemas encontrados.
        """
        issues: list[ValidationIssue] = []
        files_found = 0

        for cicd_file in CICD_FILES:
            full_path = self.project_root / cicd_file
            if full_path.is_file():
                files_found += 1
                # Validação básica de conteúdo YAML para workflows
                if cicd_file.endswith(".yml") or cicd_file.endswith(".yaml"):
                    content = full_path.read_text(encoding="utf-8").strip()
                    if not content:
                        issues.append(
                            ValidationIssue(
                                component="cicd",
                                severity=ValidationSeverity.ERROR,
                                message=(
                                    f"Arquivo de CI/CD vazio: {cicd_file}"
                                ),
                                suggestion=(
                                    "Adicione a configuração do pipeline."
                                ),
                                path=cicd_file,
                            )
                        )
                    elif "name:" not in content and cicd_file.endswith(".yml"):
                        # Workflows GitHub Actions devem ter 'name:'
                        if ".github/workflows" in cicd_file:
                            issues.append(
                                ValidationIssue(
                                    component="cicd",
                                    severity=ValidationSeverity.WARNING,
                                    message=(
                                        f"Workflow sem campo 'name': {cicd_file}"
                                    ),
                                    suggestion=(
                                        "Adicione 'name:' ao workflow para "
                                        "identificação no GitHub Actions."
                                    ),
                                    path=cicd_file,
                                )
                            )
            else:
                issues.append(
                    ValidationIssue(
                        component="cicd",
                        severity=ValidationSeverity.WARNING,
                        message=f"Arquivo de CI/CD ausente: {cicd_file}",
                        suggestion=(
                            "Crie o arquivo de configuração de CI/CD. "
                            "Consulte a documentação do projeto."
                        ),
                        path=cicd_file,
                    )
                )

        # Verificar Dockerfile multi-stage
        dockerfile_path = self.project_root / "Dockerfile"
        if dockerfile_path.is_file():
            content = dockerfile_path.read_text(encoding="utf-8")
            if "FROM" not in content:
                issues.append(
                    ValidationIssue(
                        component="cicd",
                        severity=ValidationSeverity.ERROR,
                        message="Dockerfile sem instrução FROM.",
                        suggestion=(
                            "Adicione ao menos uma instrução FROM "
                            "com a imagem base Python 3.11+."
                        ),
                        path="Dockerfile",
                    )
                )

        # Determinar status
        has_errors = any(
            i.severity == ValidationSeverity.ERROR for i in issues
        )
        if files_found == len(CICD_FILES) and not has_errors:
            status = ComponentStatus.READY
        elif files_found > 0:
            status = ComponentStatus.PARTIAL
        else:
            status = ComponentStatus.MISSING

        return ComponentReport(
            name="cicd",
            status=status,
            issues=issues,
            details={
                "files_found": files_found,
                "files_expected": len(CICD_FILES),
            },
        )


class DatabaseSchemaValidator:
    """Validador do schema inicial do banco de dados.

    Verifica se as migrações Alembic estão configuradas e se as tabelas
    obrigatórias do schema inicial estão definidas.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Inicializa o validador de schema do banco.

        Args:
            project_root: Caminho raiz do projeto.
        """
        self.project_root = project_root or Path.cwd()

    def validate(self) -> ComponentReport:
        """Executa a validação do schema do banco de dados.

        Returns:
            Relatório com o status do schema e problemas encontrados.
        """
        issues: list[ValidationIssue] = []

        # Verificar configuração Alembic
        alembic_ini = self.project_root / "backend" / "alembic.ini"
        alembic_env = self.project_root / "backend" / "alembic" / "env.py"
        versions_dir = (
            self.project_root / "backend" / "alembic" / "versions"
        )

        if not alembic_ini.is_file():
            issues.append(
                ValidationIssue(
                    component="database_schema",
                    severity=ValidationSeverity.ERROR,
                    message="Arquivo alembic.ini não encontrado.",
                    suggestion=(
                        "Execute 'alembic init alembic' no diretório backend/."
                    ),
                    path="backend/alembic.ini",
                )
            )

        if not alembic_env.is_file():
            issues.append(
                ValidationIssue(
                    component="database_schema",
                    severity=ValidationSeverity.ERROR,
                    message="Arquivo alembic/env.py não encontrado.",
                    suggestion=(
                        "Configure o env.py do Alembic com o metadata "
                        "do SQLAlchemy."
                    ),
                    path="backend/alembic/env.py",
                )
            )

        if versions_dir.is_dir():
            migrations = list(versions_dir.glob("*.py"))
            if not migrations:
                issues.append(
                    ValidationIssue(
                        component="database_schema",
                        severity=ValidationSeverity.WARNING,
                        message=(
                            "Nenhuma migração encontrada no diretório "
                            "alembic/versions/."
                        ),
                        suggestion=(
                            "Crie a migração inicial com: "
                            "alembic revision --autogenerate -m 'initial_schema'"
                        ),
                        path="backend/alembic/versions/",
                    )
                )
        else:
            issues.append(
                ValidationIssue(
                    component="database_schema",
                    severity=ValidationSeverity.ERROR,
                    message="Diretório de migrações não encontrado.",
                    suggestion="Crie: mkdir -p backend/alembic/versions",
                    path="backend/alembic/versions/",
                )
            )

        # Verificar configuração do engine via m06
        engine_config_valid = self._validate_engine_config(issues)

        # Verificar modelos SQLAlchemy para tabelas obrigatórias
        models_found = self._check_model_definitions(issues)

        # Determinar status
        has_errors = any(
            i.severity == ValidationSeverity.ERROR for i in issues
        )
        if not has_errors and models_found == len(REQUIRED_DB_TABLES):
            status = ComponentStatus.READY
        elif not has_errors or models_found > 0:
            status = ComponentStatus.PARTIAL
        else:
            status = ComponentStatus.MISSING

        return ComponentReport(
            name="database_schema",
            status=status,
            issues=issues,
            details={
                "alembic_configured": alembic_ini.is_file(),
                "engine_config_valid": engine_config_valid,
                "required_tables": REQUIRED_DB_TABLES,
                "models_found": models_found,
                "models_expected": len(REQUIRED_DB_TABLES),
            },
        )

    def _validate_engine_config(self, issues: list[ValidationIssue]) -> bool:
        """Valida a configuração do engine de banco via módulo m06.

        Args:
            issues: Lista de problemas para adicionar se necessário.

        Returns:
            True se a configuração do engine é válida.
        """
        try:
            engine_config = get_engine_config()
            if engine_config is not None:
                return True
            issues.append(
                ValidationIssue(
                    component="database_schema",
                    severity=ValidationSeverity.WARNING,
                    message=(
                        "Configuração do engine retornou None. "
                        "Verifique as variáveis de ambiente do banco."
                    ),
                    suggestion=(
                        "Configure DATABASE_URL no .env com a string de "
                        "conexão PostgreSQL."
                    ),
                )
            )
            return False
        except Exception as exc:
            issues.append(
                ValidationIssue(
                    component="database_schema",
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"Erro ao validar configuração do engine: {exc}"
                    ),
                    suggestion=(
                        "Verifique se o módulo m06_data_model_engine_config "
                        "está corretamente configurado."
                    ),
                )
            )
            return False

    def _check_model_definitions(self, issues: list[ValidationIssue]) -> int:
        """Verifica se os modelos SQLAlchemy das tabelas obrigatórias existem.

        Args:
            issues: Lista de problemas para adicionar se necessário.

        Returns:
            Número de modelos encontrados.
        """
        models_dir = (
            self.project_root / "backend" / "src" / "domain" / "entities"
        )
        found = 0

        if not models_dir.is_dir():
            issues.append(
                ValidationIssue(
                    component="database_schema",
                    severity=ValidationSeverity.ERROR,
                    message="Diretório de entidades de domínio não encontrado.",
                    suggestion=(
                        "Crie: mkdir -p backend/src/domain/entities"
                    ),
                    path="backend/src/domain/entities/",
                )
            )
            return 0

        # Buscar definições de tabelas nos arquivos Python do diretório
        for py_file in models_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                for table_name in REQUIRED_DB_TABLES:
                    # Procurar por __tablename__ = "table_name" ou
                    # Table("table_name", ...)
                    if (
                        f'__tablename__ = "{table_name}"' in content
                        or f"__tablename__ = '{table_name}'" in content
                        or f'Table("{table_name}"' in content
                    ):
                        found += 1
            except Exception:
                logger.debug(
                    "Não foi possível ler o arquivo: %s", py_file
                )

        missing_tables = set(REQUIRED_DB_TABLES) - self._get_found_tables(
            models_dir
        )
        for table in missing_tables:
            issues.append(
                ValidationIssue(
                    component="database_schema",
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"Modelo para tabela obrigatória '{table}' "
                        f"não encontrado."
                    ),
                    suggestion=(
                        f"Crie o modelo SQLAlchemy para a tabela '{table}' "
                        f"em backend/src/domain/entities/."
                    ),
                )
            )

        return found

    def _get_found_tables(self, models_dir: Path) -> set[str]:
        """Retorna o conjunto de tabelas encontradas nos modelos.

        Args:
            models_dir: Diretório de entidades.

        Returns:
            Conjunto de nomes de tabelas encontradas.
        """
        found_tables: set[str] = set()

        for py_file in models_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                for table_name in REQUIRED_DB_TABLES:
                    if (
                        f'__tablename__ = "{table_name}"' in content
                        or f"__tablename__ = '{table_name}'" in content
                        or f'Table("{table_name}"' in content
                    ):
                        found_tables.add(table_name)
            except Exception:
                pass

        return found_tables


class AuthBaseValidator:
    """Validador da configuração base de autenticação.

    Verifica se os componentes fundamentais de autenticação estão
    configurados: JWT, hashing de senhas, RBAC e MFA.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Inicializa o validador de autenticação base.

        Args:
            project_root: Caminho raiz do projeto.
        """
        self.project_root = project_root or Path.cwd()

    def validate(self) -> ComponentReport:
        """Executa a validação da configuração de autenticação base.

        Returns:
            Relatório com o status da autenticação e problemas encontrados.
        """
        issues: list[ValidationIssue] = []

        # Verificar dependências de autenticação
        auth_deps = [
            ("python-jose", "Geração e validação de tokens JWT"),
            ("passlib", "Hashing seguro de senhas com bcrypt"),
            ("pyotp", "MFA via TOTP (Google Authenticator/Authy)"),
        ]

        deps_available = 0
        for dep_name, dep_purpose in auth_deps:
            try:
                dep_status = check_dependency(dep_name)
                if dep_status:
                    deps_available += 1
                else:
                    issues.append(
                        ValidationIssue(
                            component="auth_base",
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Dependência de autenticação não encontrada: "
                                f"{dep_name} ({dep_purpose})"
                            ),
                            suggestion=(
                                f"Instale com: pip install {dep_name}"
                            ),
                        )
                    )
            except Exception:
                issues.append(
                    ValidationIssue(
                        component="auth_base",
                        severity=ValidationSeverity.WARNING,
                        message=(
                            f"Não foi possível verificar dependência: "
                            f"{dep_name}"
                        ),
                        suggestion=(
                            f"Verifique manualmente: pip show {dep_name}"
                        ),
                    )
                )

        # Verificar estrutura de módulo de autenticação
        auth_module_path = (
            self.project_root / "backend" / "src" / "infrastructure" / "auth"
        )
        expected_auth_files = [
            "__init__.py",
            "jwt_handler.py",
            "password_handler.py",
            "rbac.py",
        ]

        auth_files_found = 0
        for auth_file in expected_auth_files:
            file_path = auth_module_path / auth_file
            if file_path.is_file():
                auth_files_found += 1
            else:
                severity = (
                    ValidationSeverity.WARNING
                    if auth_file == "__init__.py"
                    else ValidationSeverity.WARNING
                )
                issues.append(
                    ValidationIssue(
                        component="auth_base",
                        severity=severity,
                        message=(
                            f"Arquivo de autenticação ausente: "
                            f"infrastructure/auth/{auth_file}"
                        ),
                        suggestion=(
                            f"Crie o módulo {auth_file} com a implementação "
                            f"base de autenticação."
                        ),
                        path=f"backend/src/infrastructure/auth/{auth_file}",
                    )
                )

        # Verificar variáveis de ambiente de segurança
        env_issues = self._check_security_env_vars()
        issues.extend(env_issues)

        # Determinar status
        has_errors = any(
            i.severity == ValidationSeverity.ERROR for i in issues
        )
        if not has_errors and deps_available == len(auth_deps):
            status = ComponentStatus.READY
        elif deps_available > 0 or auth_files_found > 0:
            status = ComponentStatus.PARTIAL
        else:
            status = ComponentStatus.MISSING

        return ComponentReport(
            name="auth_base",
            status=status,
            issues=issues,
            details={
                "dependencies_available": deps_available,
                "dependencies_expected": len(auth_deps),
                "auth_files_found": auth_files_found,
                "auth_files_expected": len(expected_auth_files),
            },
        )

    def _check_security_env_vars(self) -> list[ValidationIssue]:
        """Verifica variáveis de ambiente de segurança.

        Returns:
            Lista de problemas encontrados.
        """
        issues: list[ValidationIssue] = []
        required_env_vars = [
            (
                "JWT_SECRET_KEY",
                "Chave secreta para assinatura de tokens JWT",
            ),
            (
                "JWT_ALGORITHM",
                "Algoritmo de assinatura JWT (recomendado: RS256)",
            ),
            (
                "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
                "Tempo de expiração do access token em minutos",
            ),
        ]

        for var_name, var_description in required_env_vars:
            value = os.environ.get(var_name)
            if not value:
                # Verificar no .env.example se está documentada
                env_example = self.project_root / ".env.example"
                documented = False
                if env_example.is_file():
                    content = env_example.read_text(encoding="utf-8")
                    if var_name in content:
                        documented = True

                severity = (
                    ValidationSeverity.INFO
                    if documented
                    else ValidationSeverity.WARNING
                )
                issues.append(
                    ValidationIssue(
                        component="auth_base",
                        severity=severity,
                        message=(
                            f"Variável de ambiente não definida: {var_name} "
                            f"— {var_description}"
                        ),
                        suggestion=(
                            f"Defina {var_name} no arquivo .env ou nas "
                            f"variáveis de ambiente do sistema."
                        ),
                    )
                )
            elif var_name == "JWT_SECRET_KEY" and len(value) < 32:
                issues.append(
                    ValidationIssue(
                        component="auth_base",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            "JWT_SECRET_KEY muito curta. Mínimo recomendado: "
                            "32 caracteres."
                        ),
                        suggestion=(
                            "Gere uma chave segura com: "
                            "python -c \"import secrets; "
                            "print(secrets.token_urlsafe(64))\""
                        ),
                    )
                )

        return issues


# ---------------------------------------------------------------------------
# Orquestrador principal — Phase1Foundation
# ---------------------------------------------------------------------------


class Phase1Foundation:
    """Orquestrador principal de validação da Fase 1.

    Coordena todos os validadores individuais (scaffold, CI/CD, database
    schema, autenticação base) e consolida os resultados em um relatório
    unificado.

    Também integra com os módulos peers (m06 e m07) para validação
    cruzada de stack e configuração de engine.
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Inicializa o orquestrador da Fase 1.

        Args:
            project_root: Caminho raiz do projeto.
        """
        self.project_root = project_root
        self.scaffold_validator = ScaffoldValidator(project_root)
        self.cicd_validator = CICDValidator(
            project_root or self.scaffold_validator.project_root
        )
        self.db_schema_validator = DatabaseSchemaValidator(
            project_root or self.scaffold_validator.project_root
        )
        self.auth_validator = AuthBaseValidator(
            project_root or self.scaffold_validator.project_root
        )

    async def validate_all(self) -> FoundationStatus:
        """Executa validação completa de todos os componentes da Fase 1.

        Returns:
            Status consolidado da fundação com relatórios de cada componente.
        """
        logger.info("Iniciando validação completa da Fase 1 — Fundação...")

        # Executar validações individuais
        scaffold_report = self.scaffold_validator.validate()
        cicd_report = self.cicd_validator.validate()
        db_report = self.db_schema_validator.validate()
        auth_report = self.auth_validator.validate()

        # Integrar com m07 — validação de stack
        stack_report_data: Optional[dict[str, Any]] = None
        try:
            stack_validation = validate_stack()
            stack_report_data = get_stack_report()
            if stack_validation and hasattr(stack_validation, "all_valid"):
                if not stack_validation.all_valid:
                    logger.warning(
                        "Validação de stack (m07) reportou problemas."
                    )
        except Exception as exc:
            logger.warning(
                "Não foi possível executar validação de stack (m07): %s", exc
            )

        # Integrar com m06 — configuração de engine
        engine_config_valid = False
        try:
            engine_config = get_engine_config()
            engine_config_valid = engine_config is not None
        except Exception as exc:
            logger.warning(
                "Não foi possível validar configuração de engine (m06): %s",
                exc,
            )

        # Consolidar resultados
        components = {
            "scaffold": scaffold_report,
            "cicd": cicd_report,
            "database_schema": db_report,
            "auth_base": auth_report,
        }

        total_errors = sum(r.error_count for r in components.values())
        total_warnings = sum(r.warning_count for r in components.values())

        # A fundação está pronta se não há erros críticos
        is_ready = total_errors == 0

        status = FoundationStatus(
            is_ready=is_ready,
            components=components,
            total_errors=total_errors,
            total_warnings=total_warnings,
            stack_report=stack_report_data,
            engine_config_valid=engine_config_valid,
        )

        logger.info(status.summary)

        return status

    def validate_scaffold_only(self) -> ComponentReport:
        """Valida apenas o scaffold do projeto.

        Returns:
            Relatório do scaffold.
        """
        return self.scaffold_validator.validate()

    def validate_cicd_only(self) -> ComponentReport:
        """Valida apenas a configuração de CI/CD.

        Returns:
            Relatório de CI/CD.
        """
        return self.cicd_validator.validate()

    def validate_database_only(self) -> ComponentReport:
        """Valida apenas o schema do banco de dados.

        Returns:
            Relatório do schema.
        """
        return self.db_schema_validator.validate()

    def validate_auth_only(self) -> ComponentReport:
        """Valida apenas a configuração de autenticação.

        Returns:
            Relatório de autenticação.
        """
        return self.auth_validator.validate()

    def create_scaffold(self, dry_run: bool = True) -> list[str]:
        """Cria a estrutura de scaffold do projeto.

        Args:
            dry_run: Se True, apenas lista o que seria criado.

        Returns:
            Lista de caminhos criados ou que seriam criados.
        """
        return self.scaffold_validator.create_scaffold(dry_run=dry_run)


# ---------------------------------------------------------------------------
# Funções de conveniência (API pública do módulo)
# ---------------------------------------------------------------------------


async def validate_foundation(
    project_root: Optional[Path] = None,
) -> FoundationStatus:
    """Valida todos os artefatos fundamentais da Fase 1.

    Função de conveniência que cria uma instância de Phase1Foundation
    e executa a validação completa.

    Args:
        project_root: Caminho raiz do projeto (opcional).

    Returns:
        Status consolidado da fundação.
    """
    foundation = Phase1Foundation(project_root=project_root)
    return await foundation.validate_all()


def get_foundation_status(
    project_root: Optional[Path] = None,
) -> dict[str, Any]:
    """Retorna um resumo rápido (síncrono) do status da fundação.

    Executa apenas verificações de sistema de arquivos (sem I/O de banco
    ou rede), adequado para health checks rápidos.

    Args:
        project_root: Caminho raiz do projeto (opcional).

    Returns:
        Dicionário com resumo do status de cada componente.
    """
    foundation = Phase1Foundation(project_root=project_root)

    scaffold = foundation.validate_scaffold_only()
    cicd = foundation.validate_cicd_only()
    db = foundation.validate_database_only()
    auth = foundation.validate_auth_only()

    components = {
        "scaffold": scaffold,
        "cicd": cicd,
        "database_schema": db,
        "auth_base": auth,
    }

    total_errors = sum(r.error_count for r in components.values())

    return {
        "is_ready": total_errors == 0,
        "total_errors": total_errors,
        "total_warnings": sum(r.warning_count for r in components.values()),
        "components": {
            name: {
                "status": report.status.value,
                "errors": report.error_count,
                "warnings": report.warning_count,
            }
            for name, report in components.items()
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_scaffold(
    project_root: Optional[Path] = None,
    dry_run: bool = True,
) -> list[str]:
    """Gera a estrutura de scaffold do projeto.

    Args:
        project_root: Caminho raiz do projeto (opcional).
        dry_run: Se True, apenas lista o que seria criado.

    Returns:
        Lista de caminhos criados ou que seriam criados.
    """
    foundation = Phase1Foundation(project_root=project_root)
    return foundation.create_scaffold(dry_run=dry_run)


# ---------------------------------------------------------------------------
# Exports públicos
# ---------------------------------------------------------------------------

__all__ = [
    # Classes principais
    "Phase1Foundation",
    "ScaffoldValidator",
    "CICDValidator",
    "DatabaseSchemaValidator",
    "AuthBaseValidator",
    # Modelos de dados
    "FoundationStatus",
    "ComponentReport",
    "ValidationIssue",
    "ValidationSeverity",
    "ComponentStatus",
    # Funções de conveniência
    "validate_foundation",
    "get_foundation_status",
    "generate_scaffold",
    # Constantes
    "REQUIRED_DIRECTORIES",
    "REQUIRED_FILES",
    "REQUIRED_DB_TABLES",
    "REQUIRED_PYTHON_DEPS",
    "CICD_FILES",
]
