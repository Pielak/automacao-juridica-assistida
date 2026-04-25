"""Módulo backlog #20: Artefatos Obrigatórios Pré-Desenvolvimento — Automação Jurídica Assistida.

Implementa checklist e validação de bloqueios para artefatos obrigatórios
que devem estar presentes antes do início da fase de desenvolvimento (Phase 0).

Artefatos verificados:
- Business Case validado (ROI, stakeholders, orçamento)
- Configuração de banco de dados (engine, schema, pool)
- Documentação de arquitetura (ADRs pendentes)
- Configurações de segurança (JWT, MFA, RBAC)
- Configurações de ambiente (variáveis, secrets)
- Dependências externas (API Anthropic, DataJud)
- Pipeline CI/CD configurado
- Testes mínimos definidos

Este módulo faz parte da camada de aplicação (use cases) e segue os
princípios de Clean Architecture.

Exemplo de uso:
    from backend.src.modules.m20_phase0_prerequisites import (
        Phase0PrerequisiteChecker,
        PrerequisiteStatus,
        check_all_prerequisites,
    )

    checker = Phase0PrerequisiteChecker()
    resultado = await checker.run_all_checks()
    if resultado.has_blockers:
        print("Bloqueios encontrados:", resultado.blockers)
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional

from pydantic import BaseModel, Field
import structlog

from backend.src.modules.m01_business_case_validation import (
    BusinessCaseValidator,
    BusinessCaseData,
    ValidationResult as BCValidationResult,
)
from backend.src.modules.m06_data_model_engine_config import (
    EngineConfig,
    get_engine_config,
    validate_database_schema,
)

# ---------------------------------------------------------------------------
# Logger estruturado
# ---------------------------------------------------------------------------
logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums e constantes
# ---------------------------------------------------------------------------
class PrerequisiteCategory(str, enum.Enum):
    """Categorias de pré-requisitos obrigatórios."""

    BUSINESS_CASE = "business_case"
    DATABASE = "database"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    ENVIRONMENT = "environment"
    EXTERNAL_DEPS = "external_dependencies"
    CI_CD = "ci_cd"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    COMPLIANCE = "compliance"


class CheckSeverity(str, enum.Enum):
    """Severidade de cada verificação.

    BLOCKER — impede início do desenvolvimento.
    WARNING — permite início, mas deve ser resolvido em breve.
    INFO — informativo, boas práticas recomendadas.
    """

    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


class CheckStatus(str, enum.Enum):
    """Status de uma verificação individual."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Modelos Pydantic — resultados de verificação
# ---------------------------------------------------------------------------
class PrerequisiteCheckResult(BaseModel):
    """Resultado de uma verificação individual de pré-requisito."""

    check_id: str = Field(..., description="Identificador único da verificação")
    name: str = Field(..., description="Nome descritivo da verificação")
    category: PrerequisiteCategory = Field(
        ..., description="Categoria do pré-requisito"
    )
    severity: CheckSeverity = Field(
        ..., description="Severidade caso a verificação falhe"
    )
    status: CheckStatus = Field(..., description="Status da verificação")
    message: str = Field(
        ..., description="Mensagem descritiva do resultado"
    )
    details: Optional[dict[str, Any]] = Field(
        default=None, description="Detalhes adicionais da verificação"
    )
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora da verificação",
    )
    resolution_hint: Optional[str] = Field(
        default=None,
        description="Dica de resolução caso a verificação falhe",
    )


class PrerequisiteStatus(BaseModel):
    """Status consolidado de todos os pré-requisitos Phase 0."""

    project_slug: str = Field(
        default="automacao-juridica-assistida",
        description="Slug do projeto",
    )
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data/hora da execução completa",
    )
    total_checks: int = Field(default=0, description="Total de verificações executadas")
    passed: int = Field(default=0, description="Verificações aprovadas")
    failed: int = Field(default=0, description="Verificações reprovadas")
    skipped: int = Field(default=0, description="Verificações ignoradas")
    errors: int = Field(default=0, description="Verificações com erro de execução")
    has_blockers: bool = Field(
        default=False,
        description="Indica se existem bloqueios que impedem o desenvolvimento",
    )
    blockers: list[PrerequisiteCheckResult] = Field(
        default_factory=list,
        description="Lista de bloqueios encontrados",
    )
    warnings: list[PrerequisiteCheckResult] = Field(
        default_factory=list,
        description="Lista de avisos encontrados",
    )
    all_results: list[PrerequisiteCheckResult] = Field(
        default_factory=list,
        description="Todos os resultados de verificação",
    )
    ready_for_development: bool = Field(
        default=False,
        description="Indica se o projeto está pronto para iniciar desenvolvimento",
    )
    summary: str = Field(
        default="",
        description="Resumo textual do status dos pré-requisitos",
    )


# ---------------------------------------------------------------------------
# Dataclass interna para registro de checks
# ---------------------------------------------------------------------------
@dataclass
class _CheckDefinition:
    """Definição interna de uma verificação a ser executada."""

    check_id: str
    name: str
    category: PrerequisiteCategory
    severity: CheckSeverity
    handler: Callable[..., Coroutine[Any, Any, PrerequisiteCheckResult]]
    resolution_hint: str = ""


# ---------------------------------------------------------------------------
# Classe principal — Phase0PrerequisiteChecker
# ---------------------------------------------------------------------------
class Phase0PrerequisiteChecker:
    """Verificador de pré-requisitos obrigatórios para Phase 0.

    Executa uma série de verificações configuráveis para garantir que todos
    os artefatos obrigatórios estejam presentes e válidos antes do início
    da fase de desenvolvimento.

    Attributes:
        _checks: Lista de definições de verificações registradas.
        _business_case_data: Dados do business case para validação (opcional).
        _engine_config: Configuração do engine de banco de dados (opcional).
    """

    def __init__(
        self,
        business_case_data: Optional[BusinessCaseData] = None,
        engine_config: Optional[EngineConfig] = None,
    ) -> None:
        """Inicializa o verificador de pré-requisitos.

        Args:
            business_case_data: Dados do business case para validação.
                Se None, a verificação de business case tentará carregar
                dados padrão ou falhará com orientação.
            engine_config: Configuração do engine de banco de dados.
                Se None, tentará obter via get_engine_config().
        """
        self._checks: list[_CheckDefinition] = []
        self._business_case_data = business_case_data
        self._engine_config = engine_config
        self._register_default_checks()

    # -------------------------------------------------------------------
    # Registro de verificações
    # -------------------------------------------------------------------
    def _register_default_checks(self) -> None:
        """Registra todas as verificações padrão do Phase 0."""
        self._checks = [
            # --- Business Case ---
            _CheckDefinition(
                check_id="BC-001",
                name="Business Case validado",
                category=PrerequisiteCategory.BUSINESS_CASE,
                severity=CheckSeverity.BLOCKER,
                handler=self._check_business_case_validated,
                resolution_hint=(
                    "Execute a validação do business case via módulo "
                    "m01_business_case_validation. Verifique ROI, "
                    "stakeholders e orçamento."
                ),
            ),
            _CheckDefinition(
                check_id="BC-002",
                name="ROI projetado acima do mínimo aceitável",
                category=PrerequisiteCategory.BUSINESS_CASE,
                severity=CheckSeverity.BLOCKER,
                handler=self._check_roi_minimum,
                resolution_hint=(
                    "O ROI projetado deve ser >= 1.5 (150%). "
                    "Revise as projeções financeiras do business case."
                ),
            ),
            _CheckDefinition(
                check_id="BC-003",
                name="Stakeholders definidos",
                category=PrerequisiteCategory.BUSINESS_CASE,
                severity=CheckSeverity.BLOCKER,
                handler=self._check_stakeholders_defined,
                resolution_hint=(
                    "Defina ao menos 1 stakeholder com papel de sponsor "
                    "e 1 stakeholder técnico no business case."
                ),
            ),
            # --- Database ---
            _CheckDefinition(
                check_id="DB-001",
                name="Engine de banco de dados configurado",
                category=PrerequisiteCategory.DATABASE,
                severity=CheckSeverity.BLOCKER,
                handler=self._check_database_engine_configured,
                resolution_hint=(
                    "Configure o engine via módulo "
                    "m06_data_model_engine_config. Verifique variáveis "
                    "DATABASE_URL e pool settings."
                ),
            ),
            _CheckDefinition(
                check_id="DB-002",
                name="Schema do banco de dados validado",
                category=PrerequisiteCategory.DATABASE,
                severity=CheckSeverity.WARNING,
                handler=self._check_database_schema_valid,
                resolution_hint=(
                    "Execute validate_database_schema() do módulo "
                    "m06_data_model_engine_config para verificar "
                    "integridade do schema."
                ),
            ),
            # --- Segurança ---
            _CheckDefinition(
                check_id="SEC-001",
                name="Configuração JWT definida",
                category=PrerequisiteCategory.SECURITY,
                severity=CheckSeverity.BLOCKER,
                handler=self._check_jwt_configuration,
                resolution_hint=(
                    "Defina as variáveis JWT_SECRET_KEY, JWT_ALGORITHM "
                    "(RS256 recomendado) e JWT_EXPIRATION_MINUTES."
                ),
            ),
            _CheckDefinition(
                check_id="SEC-002",
                name="Configuração MFA habilitada",
                category=PrerequisiteCategory.SECURITY,
                severity=CheckSeverity.WARNING,
                handler=self._check_mfa_configuration,
                resolution_hint=(
                    "Configure MFA via TOTP (pyotp). Variável "
                    "MFA_ENABLED deve estar definida."
                ),
            ),
            _CheckDefinition(
                check_id="SEC-003",
                name="Política RBAC definida",
                category=PrerequisiteCategory.SECURITY,
                severity=CheckSeverity.BLOCKER,
                handler=self._check_rbac_policy,
                resolution_hint=(
                    "Defina os papéis (roles) e permissões mínimas: "
                    "admin, advogado, analista, visualizador."
                ),
            ),
            # --- Arquitetura ---
            _CheckDefinition(
                check_id="ARCH-001",
                name="ADRs pendentes resolvidas",
                category=PrerequisiteCategory.ARCHITECTURE,
                severity=CheckSeverity.WARNING,
                handler=self._check_pending_adrs,
                resolution_hint=(
                    "Resolva ADRs pendentes: G002 (FAISS vs Milvus), "
                    "G005 (Design Tokens). Documente decisões."
                ),
            ),
            _CheckDefinition(
                check_id="ARCH-002",
                name="Módulos obrigatórios definidos",
                category=PrerequisiteCategory.ARCHITECTURE,
                severity=CheckSeverity.BLOCKER,
                handler=self._check_required_modules,
                resolution_hint=(
                    "Verifique que os módulos auth, users, documents, "
                    "analysis, chat e audit estão definidos."
                ),
            ),
            # --- Ambiente ---
            _CheckDefinition(
                check_id="ENV-001",
                name="Variáveis de ambiente obrigatórias",
                category=PrerequisiteCategory.ENVIRONMENT,
                severity=CheckSeverity.BLOCKER,
                handler=self._check_required_env_vars,
                resolution_hint=(
                    "Defina todas as variáveis obrigatórias no .env: "
                    "DATABASE_URL, JWT_SECRET_KEY, ANTHROPIC_API_KEY, "
                    "REDIS_URL, SECRET_KEY."
                ),
            ),
            # --- Dependências Externas ---
            _CheckDefinition(
                check_id="EXT-001",
                name="API Anthropic acessível",
                category=PrerequisiteCategory.EXTERNAL_DEPS,
                severity=CheckSeverity.WARNING,
                handler=self._check_anthropic_api_access,
                resolution_hint=(
                    "Verifique ANTHROPIC_API_KEY e conectividade "
                    "com api.anthropic.com. Use httpx para teste."
                ),
            ),
            _CheckDefinition(
                check_id="EXT-002",
                name="Acesso DataJud configurado",
                category=PrerequisiteCategory.EXTERNAL_DEPS,
                severity=CheckSeverity.WARNING,
                handler=self._check_datajud_access,
                resolution_hint=(
                    "Configure credenciais e URL base para API DataJud. "
                    "Verifique variável DATAJUD_API_URL."
                ),
            ),
            # --- CI/CD ---
            _CheckDefinition(
                check_id="CICD-001",
                name="Pipeline CI/CD configurado",
                category=PrerequisiteCategory.CI_CD,
                severity=CheckSeverity.WARNING,
                handler=self._check_cicd_pipeline,
                resolution_hint=(
                    "Configure pipeline CI/CD com etapas de lint, "
                    "testes, build e deploy. Arquivo de configuração "
                    "deve existir (.github/workflows ou equivalente)."
                ),
            ),
            # --- Testes ---
            _CheckDefinition(
                check_id="TEST-001",
                name="Estrutura de testes definida",
                category=PrerequisiteCategory.TESTING,
                severity=CheckSeverity.WARNING,
                handler=self._check_test_structure,
                resolution_hint=(
                    "Crie diretórios tests/unit, tests/integration e "
                    "tests/e2e. Configure pytest com conftest.py."
                ),
            ),
            # --- Documentação ---
            _CheckDefinition(
                check_id="DOC-001",
                name="Documentação mínima presente",
                category=PrerequisiteCategory.DOCUMENTATION,
                severity=CheckSeverity.INFO,
                handler=self._check_minimum_documentation,
                resolution_hint=(
                    "Garanta que README.md, CONTRIBUTING.md e "
                    "docs/architecture.md existam."
                ),
            ),
            # --- Compliance ---
            _CheckDefinition(
                check_id="COMP-001",
                name="Conformidade LGPD verificada",
                category=PrerequisiteCategory.COMPLIANCE,
                severity=CheckSeverity.BLOCKER,
                handler=self._check_lgpd_compliance,
                resolution_hint=(
                    "Verifique política de privacidade, consentimento "
                    "de dados, anonimização e direito ao esquecimento. "
                    "Documente no artefato de compliance."
                ),
            ),
            _CheckDefinition(
                check_id="COMP-002",
                name="Política de retenção de dados definida",
                category=PrerequisiteCategory.COMPLIANCE,
                severity=CheckSeverity.WARNING,
                handler=self._check_data_retention_policy,
                resolution_hint=(
                    "Defina política de retenção para logs, documentos "
                    "jurídicos e dados pessoais conforme LGPD."
                ),
            ),
        ]

    def register_check(
        self,
        check_id: str,
        name: str,
        category: PrerequisiteCategory,
        severity: CheckSeverity,
        handler: Callable[..., Coroutine[Any, Any, PrerequisiteCheckResult]],
        resolution_hint: str = "",
    ) -> None:
        """Registra uma verificação customizada adicional.

        Args:
            check_id: Identificador único da verificação.
            name: Nome descritivo.
            category: Categoria do pré-requisito.
            severity: Severidade caso falhe.
            handler: Coroutine que executa a verificação.
            resolution_hint: Dica de resolução.
        """
        self._checks.append(
            _CheckDefinition(
                check_id=check_id,
                name=name,
                category=category,
                severity=severity,
                handler=handler,
                resolution_hint=resolution_hint,
            )
        )
        logger.info(
            "Verificação customizada registrada",
            check_id=check_id,
            name=name,
        )

    # -------------------------------------------------------------------
    # Execução principal
    # -------------------------------------------------------------------
    async def run_all_checks(self) -> PrerequisiteStatus:
        """Executa todas as verificações registradas e retorna status consolidado.

        Returns:
            PrerequisiteStatus com resultado de todas as verificações.
        """
        logger.info(
            "Iniciando verificação de pré-requisitos Phase 0",
            total_checks=len(self._checks),
        )

        results: list[PrerequisiteCheckResult] = []

        for check_def in self._checks:
            try:
                result = await check_def.handler()
                if result.resolution_hint is None and check_def.resolution_hint:
                    result.resolution_hint = check_def.resolution_hint
                results.append(result)
            except Exception as exc:
                logger.error(
                    "Erro ao executar verificação",
                    check_id=check_def.check_id,
                    error=str(exc),
                )
                results.append(
                    PrerequisiteCheckResult(
                        check_id=check_def.check_id,
                        name=check_def.name,
                        category=check_def.category,
                        severity=check_def.severity,
                        status=CheckStatus.ERROR,
                        message=f"Erro ao executar verificação: {exc}",
                        resolution_hint=check_def.resolution_hint,
                    )
                )

        # Consolidar resultados
        status = self._consolidate_results(results)

        logger.info(
            "Verificação de pré-requisitos concluída",
            total=status.total_checks,
            passed=status.passed,
            failed=status.failed,
            blockers=len(status.blockers),
            ready=status.ready_for_development,
        )

        return status

    async def run_checks_by_category(
        self, category: PrerequisiteCategory
    ) -> PrerequisiteStatus:
        """Executa verificações filtradas por categoria.

        Args:
            category: Categoria de pré-requisitos a verificar.

        Returns:
            PrerequisiteStatus com resultados da categoria.
        """
        logger.info(
            "Executando verificações por categoria",
            category=category.value,
        )

        results: list[PrerequisiteCheckResult] = []

        for check_def in self._checks:
            if check_def.category != category:
                continue
            try:
                result = await check_def.handler()
                if result.resolution_hint is None and check_def.resolution_hint:
                    result.resolution_hint = check_def.resolution_hint
                results.append(result)
            except Exception as exc:
                results.append(
                    PrerequisiteCheckResult(
                        check_id=check_def.check_id,
                        name=check_def.name,
                        category=check_def.category,
                        severity=check_def.severity,
                        status=CheckStatus.ERROR,
                        message=f"Erro ao executar verificação: {exc}",
                        resolution_hint=check_def.resolution_hint,
                    )
                )

        return self._consolidate_results(results)

    # -------------------------------------------------------------------
    # Consolidação de resultados
    # -------------------------------------------------------------------
    def _consolidate_results(
        self, results: list[PrerequisiteCheckResult]
    ) -> PrerequisiteStatus:
        """Consolida resultados individuais em status geral.

        Args:
            results: Lista de resultados de verificações.

        Returns:
            PrerequisiteStatus consolidado.
        """
        passed = sum(1 for r in results if r.status == CheckStatus.PASSED)
        failed = sum(1 for r in results if r.status == CheckStatus.FAILED)
        skipped = sum(1 for r in results if r.status == CheckStatus.SKIPPED)
        errors = sum(1 for r in results if r.status == CheckStatus.ERROR)

        blockers = [
            r
            for r in results
            if r.severity == CheckSeverity.BLOCKER
            and r.status in (CheckStatus.FAILED, CheckStatus.ERROR)
        ]

        warnings = [
            r
            for r in results
            if r.severity == CheckSeverity.WARNING
            and r.status in (CheckStatus.FAILED, CheckStatus.ERROR)
        ]

        has_blockers = len(blockers) > 0
        ready = not has_blockers

        # Gerar resumo textual
        if ready and not warnings:
            summary = (
                "✅ Todos os pré-requisitos Phase 0 foram atendidos. "
                "O projeto está pronto para iniciar o desenvolvimento."
            )
        elif ready and warnings:
            summary = (
                f"⚠️ Projeto liberado para desenvolvimento com "
                f"{len(warnings)} aviso(s). Resolva-os em breve."
            )
        else:
            summary = (
                f"🚫 Desenvolvimento BLOQUEADO. {len(blockers)} bloqueio(s) "
                f"encontrado(s). Resolva antes de prosseguir."
            )

        return PrerequisiteStatus(
            checked_at=datetime.now(timezone.utc),
            total_checks=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            has_blockers=has_blockers,
            blockers=blockers,
            warnings=warnings,
            all_results=results,
            ready_for_development=ready,
            summary=summary,
        )

    # -------------------------------------------------------------------
    # Handlers de verificação — Business Case
    # -------------------------------------------------------------------
    async def _check_business_case_validated(self) -> PrerequisiteCheckResult:
        """Verifica se o business case foi validado com sucesso."""
        try:
            if self._business_case_data is None:
                return PrerequisiteCheckResult(
                    check_id="BC-001",
                    name="Business Case validado",
                    category=PrerequisiteCategory.BUSINESS_CASE,
                    severity=CheckSeverity.BLOCKER,
                    status=CheckStatus.FAILED,
                    message=(
                        "Dados do business case não fornecidos. "
                        "Forneça BusinessCaseData ao inicializar o checker."
                    ),
                )

            validator = BusinessCaseValidator()
            result: BCValidationResult = validator.validate(self._business_case_data)

            if result.is_valid:
                return PrerequisiteCheckResult(
                    check_id="BC-001",
                    name="Business Case validado",
                    category=PrerequisiteCategory.BUSINESS_CASE,
                    severity=CheckSeverity.BLOCKER,
                    status=CheckStatus.PASSED,
                    message="Business case validado com sucesso.",
                    details={"validation_result": result.dict() if hasattr(result, 'dict') else str(result)},
                )
            else:
                return PrerequisiteCheckResult(
                    check_id="BC-001",
                    name="Business Case validado",
                    category=PrerequisiteCategory.BUSINESS_CASE,
                    severity=CheckSeverity.BLOCKER,
                    status=CheckStatus.FAILED,
                    message=f"Business case inválido: {result.errors if hasattr(result, 'errors') else 'Verifique os dados'}",
                )
        except Exception as exc:
            return PrerequisiteCheckResult(
                check_id="BC-001",
                name="Business Case validado",
                category=PrerequisiteCategory.BUSINESS_CASE,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.ERROR,
                message=f"Erro ao validar business case: {exc}",
            )

    async def _check_roi_minimum(self) -> PrerequisiteCheckResult:
        """Verifica se o ROI projetado atinge o mínimo aceitável (150%)."""
        MIN_ROI = 1.5

        if self._business_case_data is None:
            return PrerequisiteCheckResult(
                check_id="BC-002",
                name="ROI projetado acima do mínimo aceitável",
                category=PrerequisiteCategory.BUSINESS_CASE,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.FAILED,
                message="Dados do business case não disponíveis para verificar ROI.",
            )

        try:
            roi = getattr(self._business_case_data, "projected_roi", None)
            if roi is None:
                return PrerequisiteCheckResult(
                    check_id="BC-002",
                    name="ROI projetado acima do mínimo aceitável",
                    category=PrerequisiteCategory.BUSINESS_CASE,
                    severity=CheckSeverity.BLOCKER,
                    status=CheckStatus.FAILED,
                    message="Campo projected_roi não encontrado no business case.",
                )

            if roi >= MIN_ROI:
                return PrerequisiteCheckResult(
                    check_id="BC-002",
                    name="ROI projetado acima do mínimo aceitável",
                    category=PrerequisiteCategory.BUSINESS_CASE,
                    severity=CheckSeverity.BLOCKER,
                    status=CheckStatus.PASSED,
                    message=f"ROI projetado ({roi:.1%}) atende o mínimo ({MIN_ROI:.0%}).",
                    details={"projected_roi": roi, "minimum_roi": MIN_ROI},
                )
            else:
                return PrerequisiteCheckResult(
                    check_id="BC-002",
                    name="ROI projetado acima do mínimo aceitável",
                    category=PrerequisiteCategory.BUSINESS_CASE,
                    severity=CheckSeverity.BLOCKER,
                    status=CheckStatus.FAILED,
                    message=f"ROI projetado ({roi:.1%}) abaixo do mínimo ({MIN_ROI:.0%}).",
                    details={"projected_roi": roi, "minimum_roi": MIN_ROI},
                )
        except Exception as exc:
            return PrerequisiteCheckResult(
                check_id="BC-002",
                name="ROI projetado acima do mínimo aceitável",
                category=PrerequisiteCategory.BUSINESS_CASE,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.ERROR,
                message=f"Erro ao verificar ROI: {exc}",
            )

    async def _check_stakeholders_defined(self) -> PrerequisiteCheckResult:
        """Verifica se stakeholders obrigatórios estão definidos."""
        if self._business_case_data is None:
            return PrerequisiteCheckResult(
                check_id="BC-003",
                name="Stakeholders definidos",
                category=PrerequisiteCategory.BUSINESS_CASE,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.FAILED,
                message="Dados do business case não disponíveis.",
            )

        try:
            stakeholders = getattr(self._business_case_data, "stakeholders", None)
            if not stakeholders or len(stakeholders) < 2:
                return PrerequisiteCheckResult(
                    check_id="BC-003",
                    name="Stakeholders definidos",
                    category=PrerequisiteCategory.BUSINESS_CASE,
                    severity=CheckSeverity.BLOCKER,
                    status=CheckStatus.FAILED,
                    message=(
                        "Mínimo de 2 stakeholders necessários "
                        "(sponsor + técnico)."
                    ),
                    details={"stakeholders_count": len(stakeholders) if stakeholders else 0},
                )

            return PrerequisiteCheckResult(
                check_id="BC-003",
                name="Stakeholders definidos",
                category=PrerequisiteCategory.BUSINESS_CASE,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.PASSED,
                message=f"{len(stakeholders)} stakeholder(s) definido(s).",
                details={"stakeholders_count": len(stakeholders)},
            )
        except Exception as exc:
            return PrerequisiteCheckResult(
                check_id="BC-003",
                name="Stakeholders definidos",
                category=PrerequisiteCategory.BUSINESS_CASE,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.ERROR,
                message=f"Erro ao verificar stakeholders: {exc}",
            )

    # -------------------------------------------------------------------
    # Handlers de verificação — Database
    # -------------------------------------------------------------------
    async def _check_database_engine_configured(self) -> PrerequisiteCheckResult:
        """Verifica se o engine de banco de dados está configurado."""
        try:
            config = self._engine_config or get_engine_config()

            if config is None:
                return PrerequisiteCheckResult(
                    check_id="DB-001",
                    name="Engine de banco de dados configurado",
                    category=PrerequisiteCategory.DATABASE,
                    severity=CheckSeverity.BLOCKER,
                    status=CheckStatus.FAILED,
                    message="Configuração do engine de banco não encontrada.",
                )

            return PrerequisiteCheckResult(
                check_id="DB-001",
                name="Engine de banco de dados configurado",
                category=PrerequisiteCategory.DATABASE,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.PASSED,
                message="Engine de banco de dados configurado com sucesso.",
                details={
                    "engine_type": getattr(config, "engine_type", "asyncpg"),
                    "pool_size": getattr(config, "pool_size", "N/A"),
                },
            )
        except Exception as exc:
            return PrerequisiteCheckResult(
                check_id="DB-001",
                name="Engine de banco de dados configurado",
                category=PrerequisiteCategory.DATABASE,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.ERROR,
                message=f"Erro ao verificar engine de banco: {exc}",
            )

    async def _check_database_schema_valid(self) -> PrerequisiteCheckResult:
        """Verifica se o schema do banco de dados é válido."""
        try:
            validation = validate_database_schema()

            is_valid = getattr(validation, "is_valid", None)
            if is_valid is None:
                # Se validate_database_schema retorna bool
                is_valid = bool(validation)

            if is_valid:
                return PrerequisiteCheckResult(
                    check_id="DB-002",
                    name="Schema do banco de dados validado",
                    category=PrerequisiteCategory.DATABASE,
                    severity=CheckSeverity.WARNING,
                    status=CheckStatus.PASSED,
                    message="Schema do banco de dados validado com sucesso.",
                )
            else:
                return PrerequisiteCheckResult(
                    check_id="DB-002",
                    name="Schema do banco de dados validado",
                    category=PrerequisiteCategory.DATABASE,
                    severity=CheckSeverity.WARNING,
                    status=CheckStatus.FAILED,
                    message="Schema do banco de dados apresenta inconsistências.",
                )
        except Exception as exc:
            return PrerequisiteCheckResult(
                check_id="DB-002",
                name="Schema do banco de dados validado",
                category=PrerequisiteCategory.DATABASE,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.ERROR,
                message=f"Erro ao validar schema: {exc}",
            )

    # -------------------------------------------------------------------
    # Handlers de verificação — Segurança
    # -------------------------------------------------------------------
    async def _check_jwt_configuration(self) -> PrerequisiteCheckResult:
        """Verifica se a configuração JWT está definida."""
        import os

        required_vars = ["JWT_SECRET_KEY", "JWT_ALGORITHM"]
        missing = [v for v in required_vars if not os.environ.get(v)]

        if missing:
            return PrerequisiteCheckResult(
                check_id="SEC-001",
                name="Configuração JWT definida",
                category=PrerequisiteCategory.SECURITY,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.FAILED,
                message=f"Variáveis JWT ausentes: {', '.join(missing)}",
                details={"missing_vars": missing},
            )

        algorithm = os.environ.get("JWT_ALGORITHM", "")
        if algorithm != "RS256":
            return PrerequisiteCheckResult(
                check_id="SEC-001",
                name="Configuração JWT definida",
                category=PrerequisiteCategory.SECURITY,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.PASSED,
                message=(
                    f"JWT configurado com algoritmo {algorithm}. "
                    f"Recomendado: RS256."
                ),
                details={"algorithm": algorithm, "recommended": "RS256"},
            )

        return PrerequisiteCheckResult(
            check_id="SEC-001",
            name="Configuração JWT definida",
            category=PrerequisiteCategory.SECURITY,
            severity=CheckSeverity.BLOCKER,
            status=CheckStatus.PASSED,
            message="Configuração JWT válida com RS256.",
        )

    async def _check_mfa_configuration(self) -> PrerequisiteCheckResult:
        """Verifica se MFA está configurado."""
        import os

        mfa_enabled = os.environ.get("MFA_ENABLED", "").lower()

        if mfa_enabled in ("true", "1", "yes"):
            return PrerequisiteCheckResult(
                check_id="SEC-002",
                name="Configuração MFA habilitada",
                category=PrerequisiteCategory.SECURITY,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.PASSED,
                message="MFA habilitado via TOTP.",
            )

        return PrerequisiteCheckResult(
            check_id="SEC-002",
            name="Configuração MFA habilitada",
            category=PrerequisiteCategory.SECURITY,
            severity=CheckSeverity.WARNING,
            status=CheckStatus.FAILED,
            message=(
                "MFA não está habilitado. Defina MFA_ENABLED=true "
                "para segurança adicional."
            ),
        )

    async def _check_rbac_policy(self) -> PrerequisiteCheckResult:
        """Verifica se a política RBAC está definida."""
        # Papéis mínimos obrigatórios para o sistema jurídico
        REQUIRED_ROLES = {"admin", "advogado", "analista", "visualizador"}

        import os

        roles_env = os.environ.get("RBAC_ROLES", "")

        if not roles_env:
            return PrerequisiteCheckResult(
                check_id="SEC-003",
                name="Política RBAC definida",
                category=PrerequisiteCategory.SECURITY,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.FAILED,
                message=(
                    "Variável RBAC_ROLES não definida. "
                    f"Papéis obrigatórios: {', '.join(sorted(REQUIRED_ROLES))}"
                ),
                details={"required_roles": sorted(REQUIRED_ROLES)},
            )

        defined_roles = {r.strip().lower() for r in roles_env.split(",") if r.strip()}
        missing_roles = REQUIRED_ROLES - defined_roles

        if missing_roles:
            return PrerequisiteCheckResult(
                check_id="SEC-003",
                name="Política RBAC definida",
                category=PrerequisiteCategory.SECURITY,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.FAILED,
                message=f"Papéis RBAC ausentes: {', '.join(sorted(missing_roles))}",
                details={
                    "defined_roles": sorted(defined_roles),
                    "missing_roles": sorted(missing_roles),
                },
            )

        return PrerequisiteCheckResult(
            check_id="SEC-003",
            name="Política RBAC definida",
            category=PrerequisiteCategory.SECURITY,
            severity=CheckSeverity.BLOCKER,
            status=CheckStatus.PASSED,
            message=f"Política RBAC definida com {len(defined_roles)} papéis.",
            details={"roles": sorted(defined_roles)},
        )

    # -------------------------------------------------------------------
    # Handlers de verificação — Arquitetura
    # -------------------------------------------------------------------
    async def _check_pending_adrs(self) -> PrerequisiteCheckResult:
        """Verifica ADRs (Architecture Decision Records) pendentes."""
        # ADRs conhecidas como pendentes conforme documentação do projeto
        PENDING_ADRS = [
            {"id": "G002", "title": "FAISS vs Milvus — índice vetorial para busca semântica"},
            {"id": "G005", "title": "Design Tokens — cores, tipografia, breakpoints"},
        ]

        import os

        resolved_adrs_env = os.environ.get("RESOLVED_ADRS", "")
        resolved_ids = {
            a.strip().upper()
            for a in resolved_adrs_env.split(",")
            if a.strip()
        }

        still_pending = [a for a in PENDING_ADRS if a["id"] not in resolved_ids]

        if still_pending:
            return PrerequisiteCheckResult(
                check_id="ARCH-001",
                name="ADRs pendentes resolvidas",
                category=PrerequisiteCategory.ARCHITECTURE,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.FAILED,
                message=(
                    f"{len(still_pending)} ADR(s) pendente(s): "
                    + "; ".join(f"{a['id']}: {a['title']}" for a in still_pending)
                ),
                details={"pending_adrs": still_pending},
            )

        return PrerequisiteCheckResult(
            check_id="ARCH-001",
            name="ADRs pendentes resolvidas",
            category=PrerequisiteCategory.ARCHITECTURE,
            severity=CheckSeverity.WARNING,
            status=CheckStatus.PASSED,
            message="Todas as ADRs pendentes foram resolvidas.",
        )

    async def _check_required_modules(self) -> PrerequisiteCheckResult:
        """Verifica se os módulos obrigatórios da arquitetura estão definidos."""
        REQUIRED_MODULES = [
            "auth",
            "users",
            "documents",
            "analysis",
            "chat",
            "audit",
        ]

        import os
        from pathlib import Path

        # Tentar localizar diretório de módulos
        base_paths = [
            Path("backend/src/modules"),
            Path("src/modules"),
            Path("modules"),
        ]

        modules_dir = None
        for bp in base_paths:
            if bp.exists():
                modules_dir = bp
                break

        if modules_dir is None:
            # Se não encontrar diretório, verificar via variável de ambiente
            defined_modules_env = os.environ.get("DEFINED_MODULES", "")
            if defined_modules_env:
                defined = {
                    m.strip().lower()
                    for m in defined_modules_env.split(",")
                    if m.strip()
                }
                missing = [m for m in REQUIRED_MODULES if m not in defined]
            else:
                missing = REQUIRED_MODULES
        else:
            # Verificar existência de arquivos/diretórios de módulos
            existing_files = {f.stem.lower() for f in modules_dir.iterdir()}
            missing = [
                m for m in REQUIRED_MODULES
                if not any(m in f for f in existing_files)
            ]

        if missing:
            return PrerequisiteCheckResult(
                check_id="ARCH-002",
                name="Módulos obrigatórios definidos",
                category=PrerequisiteCategory.ARCHITECTURE,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.FAILED,
                message=f"Módulos ausentes: {', '.join(missing)}",
                details={
                    "required": REQUIRED_MODULES,
                    "missing": missing,
                },
            )

        return PrerequisiteCheckResult(
            check_id="ARCH-002",
            name="Módulos obrigatórios definidos",
            category=PrerequisiteCategory.ARCHITECTURE,
            severity=CheckSeverity.BLOCKER,
            status=CheckStatus.PASSED,
            message="Todos os módulos obrigatórios estão definidos.",
            details={"modules": REQUIRED_MODULES},
        )

    # -------------------------------------------------------------------
    # Handlers de verificação — Ambiente
    # -------------------------------------------------------------------
    async def _check_required_env_vars(self) -> PrerequisiteCheckResult:
        """Verifica se todas as variáveis de ambiente obrigatórias estão definidas."""
        import os

        REQUIRED_ENV_VARS = [
            "DATABASE_URL",
            "JWT_SECRET_KEY",
            "ANTHROPIC_API_KEY",
            "REDIS_URL",
            "SECRET_KEY",
        ]

        missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]

        if missing:
            return PrerequisiteCheckResult(
                check_id="ENV-001",
                name="Variáveis de ambiente obrigatórias",
                category=PrerequisiteCategory.ENVIRONMENT,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.FAILED,
                message=f"Variáveis ausentes: {', '.join(missing)}",
                details={
                    "required": REQUIRED_ENV_VARS,
                    "missing": missing,
                },
            )

        return PrerequisiteCheckResult(
            check_id="ENV-001",
            name="Variáveis de ambiente obrigatórias",
            category=PrerequisiteCategory.ENVIRONMENT,
            severity=CheckSeverity.BLOCKER,
            status=CheckStatus.PASSED,
            message="Todas as variáveis de ambiente obrigatórias estão definidas.",
        )

    # -------------------------------------------------------------------
    # Handlers de verificação — Dependências Externas
    # -------------------------------------------------------------------
    async def _check_anthropic_api_access(self) -> PrerequisiteCheckResult:
        """Verifica se a API Anthropic está acessível."""
        import os

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        if not api_key:
            return PrerequisiteCheckResult(
                check_id="EXT-001",
                name="API Anthropic acessível",
                category=PrerequisiteCategory.EXTERNAL_DEPS,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.FAILED,
                message="ANTHROPIC_API_KEY não definida.",
            )

        # Tentativa de verificação de conectividade via httpx
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                )

                if response.status_code in (200, 401, 403):
                    # 200 = OK, 401/403 = chave inválida mas API acessível
                    if response.status_code == 200:
                        return PrerequisiteCheckResult(
                            check_id="EXT-001",
                            name="API Anthropic acessível",
                            category=PrerequisiteCategory.EXTERNAL_DEPS,
                            severity=CheckSeverity.WARNING,
                            status=CheckStatus.PASSED,
                            message="API Anthropic acessível e autenticada.",
                        )
                    else:
                        return PrerequisiteCheckResult(
                            check_id="EXT-001",
                            name="API Anthropic acessível",
                            category=PrerequisiteCategory.EXTERNAL_DEPS,
                            severity=CheckSeverity.WARNING,
                            status=CheckStatus.FAILED,
                            message=(
                                f"API Anthropic acessível, mas autenticação "
                                f"falhou (HTTP {response.status_code}). "
                                f"Verifique a chave API."
                            ),
                        )
                else:
                    return PrerequisiteCheckResult(
                        check_id="EXT-001",
                        name="API Anthropic acessível",
                        category=PrerequisiteCategory.EXTERNAL_DEPS,
                        severity=CheckSeverity.WARNING,
                        status=CheckStatus.FAILED,
                        message=f"API Anthropic retornou HTTP {response.status_code}.",
                    )
        except ImportError:
            return PrerequisiteCheckResult(
                check_id="EXT-001",
                name="API Anthropic acessível",
                category=PrerequisiteCategory.EXTERNAL_DEPS,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.SKIPPED,
                message="httpx não instalado. Verificação de conectividade ignorada.",
            )
        except Exception as exc:
            return PrerequisiteCheckResult(
                check_id="EXT-001",
                name="API Anthropic acessível",
                category=PrerequisiteCategory.EXTERNAL_DEPS,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.FAILED,
                message=f"Erro de conectividade com API Anthropic: {exc}",
            )

    async def _check_datajud_access(self) -> PrerequisiteCheckResult:
        """Verifica se o acesso ao DataJud está configurado."""
        import os

        datajud_url = os.environ.get("DATAJUD_API_URL", "")

        if not datajud_url:
            return PrerequisiteCheckResult(
                check_id="EXT-002",
                name="Acesso DataJud configurado",
                category=PrerequisiteCategory.EXTERNAL_DEPS,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.FAILED,
                message="DATAJUD_API_URL não definida.",
            )

        return PrerequisiteCheckResult(
            check_id="EXT-002",
            name="Acesso DataJud configurado",
            category=PrerequisiteCategory.EXTERNAL_DEPS,
            severity=CheckSeverity.WARNING,
            status=CheckStatus.PASSED,
            message=f"DataJud configurado: {datajud_url}",
            details={"url": datajud_url},
        )

    # -------------------------------------------------------------------
    # Handlers de verificação — CI/CD
    # -------------------------------------------------------------------
    async def _check_cicd_pipeline(self) -> PrerequisiteCheckResult:
        """Verifica se o pipeline CI/CD está configurado."""
        from pathlib import Path

        PIPELINE_PATHS = [
            Path(".github/workflows"),
            Path(".gitlab-ci.yml"),
            Path("Jenkinsfile"),
            Path(".circleci/config.yml"),
            Path("bitbucket-pipelines.yml"),
        ]

        found = []
        for p in PIPELINE_PATHS:
            if p.exists():
                found.append(str(p))

        if not found:
            return PrerequisiteCheckResult(
                check_id="CICD-001",
                name="Pipeline CI/CD configurado",
                category=PrerequisiteCategory.CI_CD,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.FAILED,
                message="Nenhuma configuração de pipeline CI/CD encontrada.",
                details={"searched_paths": [str(p) for p in PIPELINE_PATHS]},
            )

        return PrerequisiteCheckResult(
            check_id="CICD-001",
            name="Pipeline CI/CD configurado",
            category=PrerequisiteCategory.CI_CD,
            severity=CheckSeverity.WARNING,
            status=CheckStatus.PASSED,
            message=f"Pipeline CI/CD encontrado: {', '.join(found)}",
            details={"found_pipelines": found},
        )

    # -------------------------------------------------------------------
    # Handlers de verificação — Testes
    # -------------------------------------------------------------------
    async def _check_test_structure(self) -> PrerequisiteCheckResult:
        """Verifica se a estrutura de testes está definida."""
        from pathlib import Path

        REQUIRED_TEST_DIRS = [
            "tests",
        ]

        RECOMMENDED_SUBDIRS = [
            "tests/unit",
            "tests/integration",
        ]

        missing_required = [
            d for d in REQUIRED_TEST_DIRS if not Path(d).exists()
        ]

        if missing_required:
            return PrerequisiteCheckResult(
                check_id="TEST-001",
                name="Estrutura de testes definida",
                category=PrerequisiteCategory.TESTING,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.FAILED,
                message=f"Diretórios de teste ausentes: {', '.join(missing_required)}",
            )

        missing_recommended = [
            d for d in RECOMMENDED_SUBDIRS if not Path(d).exists()
        ]

        conftest_exists = Path("tests/conftest.py").exists()

        details = {
            "missing_recommended": missing_recommended,
            "conftest_exists": conftest_exists,
        }

        if missing_recommended or not conftest_exists:
            msg_parts = []
            if missing_recommended:
                msg_parts.append(
                    f"Subdiretórios recomendados ausentes: {', '.join(missing_recommended)}"
                )
            if not conftest_exists:
                msg_parts.append("conftest.py não encontrado em tests/")

            return PrerequisiteCheckResult(
                check_id="TEST-001",
                name="Estrutura de testes definida",
                category=PrerequisiteCategory.TESTING,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.PASSED,
                message=(
                    "Estrutura básica de testes existe. "
                    + "; ".join(msg_parts)
                ),
                details=details,
            )

        return PrerequisiteCheckResult(
            check_id="TEST-001",
            name="Estrutura de testes definida",
            category=PrerequisiteCategory.TESTING,
            severity=CheckSeverity.WARNING,
            status=CheckStatus.PASSED,
            message="Estrutura de testes completa.",
            details=details,
        )

    # -------------------------------------------------------------------
    # Handlers de verificação — Documentação
    # -------------------------------------------------------------------
    async def _check_minimum_documentation(self) -> PrerequisiteCheckResult:
        """Verifica se a documentação mínima está presente."""
        from pathlib import Path

        REQUIRED_DOCS = [
            "README.md",
        ]

        RECOMMENDED_DOCS = [
            "CONTRIBUTING.md",
            "docs/architecture.md",
            "CHANGELOG.md",
        ]

        missing_required = [d for d in REQUIRED_DOCS if not Path(d).exists()]
        missing_recommended = [d for d in RECOMMENDED_DOCS if not Path(d).exists()]

        if missing_required:
            return PrerequisiteCheckResult(
                check_id="DOC-001",
                name="Documentação mínima presente",
                category=PrerequisiteCategory.DOCUMENTATION,
                severity=CheckSeverity.INFO,
                status=CheckStatus.FAILED,
                message=f"Documentos obrigatórios ausentes: {', '.join(missing_required)}",
                details={
                    "missing_required": missing_required,
                    "missing_recommended": missing_recommended,
                },
            )

        msg = "Documentação mínima presente."
        if missing_recommended:
            msg += f" Recomendados ausentes: {', '.join(missing_recommended)}"

        return PrerequisiteCheckResult(
            check_id="DOC-001",
            name="Documentação mínima presente",
            category=PrerequisiteCategory.DOCUMENTATION,
            severity=CheckSeverity.INFO,
            status=CheckStatus.PASSED,
            message=msg,
            details={"missing_recommended": missing_recommended},
        )

    # -------------------------------------------------------------------
    # Handlers de verificação — Compliance
    # -------------------------------------------------------------------
    async def _check_lgpd_compliance(self) -> PrerequisiteCheckResult:
        """Verifica conformidade básica com LGPD."""
        import os

        # Verificações de compliance LGPD via variáveis de ambiente
        # ou existência de artefatos de compliance
        lgpd_checks = {
            "LGPD_PRIVACY_POLICY_DEFINED": "Política de privacidade definida",
            "LGPD_CONSENT_MECHANISM": "Mecanismo de consentimento implementado",
            "LGPD_DATA_ANONYMIZATION": "Anonimização de dados configurada",
            "LGPD_RIGHT_TO_ERASURE": "Direito ao esquecimento implementado",
        }

        missing = []
        for var, desc in lgpd_checks.items():
            val = os.environ.get(var, "").lower()
            if val not in ("true", "1", "yes"):
                missing.append(desc)

        if missing:
            return PrerequisiteCheckResult(
                check_id="COMP-001",
                name="Conformidade LGPD verificada",
                category=PrerequisiteCategory.COMPLIANCE,
                severity=CheckSeverity.BLOCKER,
                status=CheckStatus.FAILED,
                message=(
                    f"{len(missing)} requisito(s) LGPD pendente(s): "
                    + "; ".join(missing)
                ),
                details={
                    "pending_requirements": missing,
                    "total_requirements": len(lgpd_checks),
                },
            )

        return PrerequisiteCheckResult(
            check_id="COMP-001",
            name="Conformidade LGPD verificada",
            category=PrerequisiteCategory.COMPLIANCE,
            severity=CheckSeverity.BLOCKER,
            status=CheckStatus.PASSED,
            message="Todos os requisitos LGPD básicos estão atendidos.",
        )

    async def _check_data_retention_policy(self) -> PrerequisiteCheckResult:
        """Verifica se a política de retenção de dados está definida."""
        import os

        retention_policy = os.environ.get("DATA_RETENTION_POLICY_DEFINED", "").lower()

        if retention_policy not in ("true", "1", "yes"):
            return PrerequisiteCheckResult(
                check_id="COMP-002",
                name="Política de retenção de dados definida",
                category=PrerequisiteCategory.COMPLIANCE,
                severity=CheckSeverity.WARNING,
                status=CheckStatus.FAILED,
                message=(
                    "Política de retenção de dados não definida. "
                    "Defina períodos de retenção para logs, documentos "
                    "jurídicos e dados pessoais."
                ),
            )

        return PrerequisiteCheckResult(
            check_id="COMP-002",
            name="Política de retenção de dados definida",
            category=PrerequisiteCategory.COMPLIANCE,
            severity=CheckSeverity.WARNING,
            status=CheckStatus.PASSED,
            message="Política de retenção de dados definida.",
        )


# ---------------------------------------------------------------------------
# Funções utilitárias de conveniência
# ---------------------------------------------------------------------------
async def check_all_prerequisites(
    business_case_data: Optional[BusinessCaseData] = None,
    engine_config: Optional[EngineConfig] = None,
) -> PrerequisiteStatus:
    """Função de conveniência para executar todas as verificações Phase 0.

    Args:
        business_case_data: Dados do business case (opcional).
        engine_config: Configuração do engine de banco (opcional).

    Returns:
        PrerequisiteStatus com resultado consolidado.
    """
    checker = Phase0PrerequisiteChecker(
        business_case_data=business_case_data,
        engine_config=engine_config,
    )
    return await checker.run_all_checks()


async def check_prerequisites_by_category(
    category: PrerequisiteCategory,
    business_case_data: Optional[BusinessCaseData] = None,
    engine_config: Optional[EngineConfig] = None,
) -> PrerequisiteStatus:
    """Função de conveniência para verificar pré-requisitos por categoria.

    Args:
        category: Categoria de pré-requisitos a verificar.
        business_case_data: Dados do business case (opcional).
        engine_config: Configuração do engine de banco (opcional).

    Returns:
        PrerequisiteStatus com resultados da categoria.
    """
    checker = Phase0PrerequisiteChecker(
        business_case_data=business_case_data,
        engine_config=engine_config,
    )
    return await checker.run_checks_by_category(category)


def get_prerequisite_summary_text(status: PrerequisiteStatus) -> str:
    """Gera texto formatado com resumo dos pré-requisitos.

    Args:
        status: Status consolidado dos pré-requisitos.

    Returns:
        Texto formatado para exibição.
    """
    lines = [
        "=" * 60,
        "  RELATÓRIO DE PRÉ-REQUISITOS — PHASE 0",
        f"  Projeto: {status.project_slug}",
        f"  Data: {status.checked_at.strftime('%d/%m/%Y %H:%M:%S UTC')}",
        "=" * 60,
        "",
        f"  Total de verificações: {status.total_checks}",
        f"  ✅ Aprovadas: {status.passed}",
        f"  ❌ Reprovadas: {status.failed}",
        f"  ⏭️  Ignoradas: {status.skipped}",
        f"  ⚠️  Erros: {status.errors}",
        "",
    ]

    if status.blockers:
        lines.append("  🚫 BLOQUEIOS:")
        for b in status.blockers:
            lines.append(f"    [{b.check_id}] {b.name}")
            lines.append(f"      → {b.message}")
            if b.resolution_hint:
                lines.append(f"      💡 {b.resolution_hint}")
        lines.append("")

    if status.warnings:
        lines.append("  ⚠️  AVISOS:")
        for w in status.warnings:
            lines.append(f"    [{w.check_id}] {w.name}")
            lines.append(f"      → {w.message}")
            if w.resolution_hint:
                lines.append(f"      💡 {w.resolution_hint}")
        lines.append("")

    lines.append("-" * 60)
    lines.append(f"  {status.summary}")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Exports públicos
# ---------------------------------------------------------------------------
__all__ = [
    "Phase0PrerequisiteChecker",
    "PrerequisiteStatus",
    "PrerequisiteCheckResult",
    "PrerequisiteCategory",
    "CheckSeverity",
    "CheckStatus",
    "check_all_prerequisites",
    "check_prerequisites_by_category",
    "get_prerequisite_summary_text",
]
