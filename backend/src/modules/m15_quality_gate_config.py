"""Módulo backlog #15: Configuração de Quality Gate.

Define thresholds de qualidade para cobertura de testes, lint, segurança
e performance. Utilizado pela pipeline CI/CD e por verificações locais
para garantir que o código atende aos padrões mínimos de qualidade
do projeto Automação Jurídica Assistida.

Os quality gates são organizados em categorias:
- Cobertura de testes (unitários, integração, e2e)
- Lint e formatação (ruff, mypy, eslint)
- Segurança (bandit, safety, trivy, dependabot)
- Performance (tempo de resposta, throughput, bundle size)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GateCategory(str, enum.Enum):
    """Categorias de quality gate suportadas."""

    COVERAGE = "coverage"
    LINT = "lint"
    SECURITY = "security"
    PERFORMANCE = "performance"


class GateSeverity(str, enum.Enum):
    """Severidade de uma violação de quality gate.

    - BLOCKER: impede merge/deploy.
    - WARNING: gera alerta mas não bloqueia.
    - INFO: apenas informativo nos relatórios.
    """

    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


class GateStatus(str, enum.Enum):
    """Status resultante da avaliação de um quality gate."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Schemas Pydantic — configuração e resultado
# ---------------------------------------------------------------------------


class ThresholdConfig(BaseModel):
    """Configuração de um threshold individual de quality gate."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Nome identificador do threshold (ex: 'cobertura_unitaria').",
    )
    category: GateCategory = Field(
        ...,
        description="Categoria do quality gate.",
    )
    metric: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="Nome da métrica avaliada (ex: 'line_coverage_percent').",
    )
    operator: str = Field(
        default=">=",
        description="Operador de comparação: '>=', '<=', '==', '>', '<'.",
    )
    threshold_value: float = Field(
        ...,
        description="Valor numérico do threshold.",
    )
    severity: GateSeverity = Field(
        default=GateSeverity.BLOCKER,
        description="Severidade caso o threshold seja violado.",
    )
    enabled: bool = Field(
        default=True,
        description="Se o threshold está ativo.",
    )
    description_pt: str = Field(
        default="",
        description="Descrição em PT-BR para relatórios e logs.",
    )

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        """Valida que o operador é suportado."""
        allowed = {">=", "<=", "==", ">", "<"}
        if value not in allowed:
            msg = (
                f"Operador '{value}' não suportado. "
                f"Operadores válidos: {', '.join(sorted(allowed))}."
            )
            raise ValueError(msg)
        return value


class GateEvaluationResult(BaseModel):
    """Resultado da avaliação de um único threshold."""

    threshold_name: str = Field(..., description="Nome do threshold avaliado.")
    category: GateCategory
    status: GateStatus
    severity: GateSeverity
    expected_value: float = Field(..., description="Valor esperado (threshold).")
    actual_value: float = Field(..., description="Valor real medido.")
    operator: str
    message: str = Field(default="", description="Mensagem descritiva em PT-BR.")


class QualityGateReport(BaseModel):
    """Relatório consolidado de quality gate."""

    overall_status: GateStatus = Field(
        ...,
        description="Status geral: 'failed' se qualquer blocker falhar.",
    )
    total_checks: int = Field(default=0, description="Total de verificações executadas.")
    passed: int = Field(default=0, description="Quantidade aprovada.")
    failed: int = Field(default=0, description="Quantidade reprovada.")
    skipped: int = Field(default=0, description="Quantidade ignorada.")
    results: list[GateEvaluationResult] = Field(
        default_factory=list,
        description="Lista detalhada de resultados.",
    )
    blockers_failed: int = Field(
        default=0,
        description="Quantidade de blockers que falharam.",
    )


# ---------------------------------------------------------------------------
# Thresholds padrão do projeto
# ---------------------------------------------------------------------------


def _build_default_thresholds() -> list[ThresholdConfig]:
    """Constrói a lista de thresholds padrão do projeto.

    Returns:
        Lista de ThresholdConfig com os valores padrão aprovados
        pela equipe de arquitetura.
    """
    return [
        # ---- Cobertura de testes ----
        ThresholdConfig(
            name="cobertura_unitaria_linhas",
            category=GateCategory.COVERAGE,
            metric="unit_line_coverage_percent",
            operator=">=",
            threshold_value=80.0,
            severity=GateSeverity.BLOCKER,
            description_pt="Cobertura mínima de linhas por testes unitários: 80%.",
        ),
        ThresholdConfig(
            name="cobertura_unitaria_branches",
            category=GateCategory.COVERAGE,
            metric="unit_branch_coverage_percent",
            operator=">=",
            threshold_value=70.0,
            severity=GateSeverity.BLOCKER,
            description_pt="Cobertura mínima de branches por testes unitários: 70%.",
        ),
        ThresholdConfig(
            name="cobertura_integracao",
            category=GateCategory.COVERAGE,
            metric="integration_line_coverage_percent",
            operator=">=",
            threshold_value=60.0,
            severity=GateSeverity.WARNING,
            description_pt="Cobertura mínima de linhas por testes de integração: 60%.",
        ),
        ThresholdConfig(
            name="cobertura_global",
            category=GateCategory.COVERAGE,
            metric="total_line_coverage_percent",
            operator=">=",
            threshold_value=85.0,
            severity=GateSeverity.BLOCKER,
            description_pt="Cobertura global mínima de linhas: 85%.",
        ),
        # ---- Lint e tipagem ----
        ThresholdConfig(
            name="lint_ruff_erros",
            category=GateCategory.LINT,
            metric="ruff_error_count",
            operator="==",
            threshold_value=0.0,
            severity=GateSeverity.BLOCKER,
            description_pt="Nenhum erro de lint (ruff) permitido.",
        ),
        ThresholdConfig(
            name="lint_ruff_warnings",
            category=GateCategory.LINT,
            metric="ruff_warning_count",
            operator="<=",
            threshold_value=10.0,
            severity=GateSeverity.WARNING,
            description_pt="Máximo de 10 warnings de lint (ruff) permitidos.",
        ),
        ThresholdConfig(
            name="mypy_erros",
            category=GateCategory.LINT,
            metric="mypy_error_count",
            operator="==",
            threshold_value=0.0,
            severity=GateSeverity.BLOCKER,
            description_pt="Nenhum erro de tipagem (mypy) permitido.",
        ),
        ThresholdConfig(
            name="eslint_erros_frontend",
            category=GateCategory.LINT,
            metric="eslint_error_count",
            operator="==",
            threshold_value=0.0,
            severity=GateSeverity.BLOCKER,
            description_pt="Nenhum erro de ESLint no frontend permitido.",
        ),
        ThresholdConfig(
            name="eslint_warnings_frontend",
            category=GateCategory.LINT,
            metric="eslint_warning_count",
            operator="<=",
            threshold_value=15.0,
            severity=GateSeverity.WARNING,
            description_pt="Máximo de 15 warnings de ESLint no frontend.",
        ),
        # ---- Segurança ----
        ThresholdConfig(
            name="bandit_high_severity",
            category=GateCategory.SECURITY,
            metric="bandit_high_count",
            operator="==",
            threshold_value=0.0,
            severity=GateSeverity.BLOCKER,
            description_pt="Nenhuma vulnerabilidade de alta severidade (bandit) permitida.",
        ),
        ThresholdConfig(
            name="bandit_medium_severity",
            category=GateCategory.SECURITY,
            metric="bandit_medium_count",
            operator="<=",
            threshold_value=3.0,
            severity=GateSeverity.WARNING,
            description_pt="Máximo de 3 achados de média severidade (bandit).",
        ),
        ThresholdConfig(
            name="safety_vulnerabilities",
            category=GateCategory.SECURITY,
            metric="safety_vuln_count",
            operator="==",
            threshold_value=0.0,
            severity=GateSeverity.BLOCKER,
            description_pt="Nenhuma vulnerabilidade conhecida em dependências (safety).",
        ),
        ThresholdConfig(
            name="trivy_critical",
            category=GateCategory.SECURITY,
            metric="trivy_critical_count",
            operator="==",
            threshold_value=0.0,
            severity=GateSeverity.BLOCKER,
            description_pt="Nenhuma vulnerabilidade crítica em imagens Docker (trivy).",
        ),
        ThresholdConfig(
            name="trivy_high",
            category=GateCategory.SECURITY,
            metric="trivy_high_count",
            operator="==",
            threshold_value=0.0,
            severity=GateSeverity.BLOCKER,
            description_pt="Nenhuma vulnerabilidade alta em imagens Docker (trivy).",
        ),
        ThresholdConfig(
            name="secrets_detectados",
            category=GateCategory.SECURITY,
            metric="secret_scan_findings",
            operator="==",
            threshold_value=0.0,
            severity=GateSeverity.BLOCKER,
            description_pt="Nenhum segredo/credencial detectado no código-fonte.",
        ),
        # ---- Performance ----
        ThresholdConfig(
            name="api_p95_response_ms",
            category=GateCategory.PERFORMANCE,
            metric="api_p95_latency_ms",
            operator="<=",
            threshold_value=500.0,
            severity=GateSeverity.WARNING,
            description_pt="Latência P95 da API deve ser ≤ 500ms.",
        ),
        ThresholdConfig(
            name="api_p99_response_ms",
            category=GateCategory.PERFORMANCE,
            metric="api_p99_latency_ms",
            operator="<=",
            threshold_value=1000.0,
            severity=GateSeverity.BLOCKER,
            description_pt="Latência P99 da API deve ser ≤ 1000ms.",
        ),
        ThresholdConfig(
            name="frontend_bundle_size_kb",
            category=GateCategory.PERFORMANCE,
            metric="frontend_bundle_size_kb",
            operator="<=",
            threshold_value=500.0,
            severity=GateSeverity.WARNING,
            description_pt="Tamanho do bundle principal do frontend deve ser ≤ 500KB (gzipped).",
        ),
        ThresholdConfig(
            name="frontend_lcp_ms",
            category=GateCategory.PERFORMANCE,
            metric="largest_contentful_paint_ms",
            operator="<=",
            threshold_value=2500.0,
            severity=GateSeverity.WARNING,
            description_pt="Largest Contentful Paint deve ser ≤ 2500ms.",
        ),
        ThresholdConfig(
            name="db_query_slow_count",
            category=GateCategory.PERFORMANCE,
            metric="slow_query_count",
            operator="==",
            threshold_value=0.0,
            severity=GateSeverity.WARNING,
            description_pt="Nenhuma query lenta (> 1s) detectada nos testes de carga.",
        ),
    ]


# Instância singleton dos thresholds padrão
DEFAULT_THRESHOLDS: list[ThresholdConfig] = _build_default_thresholds()


# ---------------------------------------------------------------------------
# Dataclass auxiliar para contexto de avaliação
# ---------------------------------------------------------------------------


@dataclass
class MetricsSnapshot:
    """Snapshot de métricas coletadas para avaliação de quality gate.

    Armazena pares métrica→valor coletados das diversas ferramentas
    (pytest-cov, ruff, mypy, bandit, etc.).
    """

    values: dict[str, float] = field(default_factory=dict)

    def set_metric(self, metric_name: str, value: float) -> None:
        """Define o valor de uma métrica."""
        self.values[metric_name] = value

    def get_metric(self, metric_name: str) -> float | None:
        """Retorna o valor de uma métrica ou None se não coletada."""
        return self.values.get(metric_name)


# ---------------------------------------------------------------------------
# Motor de avaliação
# ---------------------------------------------------------------------------

_OPERATOR_MAP: dict[str, Any] = {
    ">=": lambda actual, expected: actual >= expected,
    "<=": lambda actual, expected: actual <= expected,
    "==": lambda actual, expected: actual == expected,  # noqa: E731
    ">": lambda actual, expected: actual > expected,
    "<": lambda actual, expected: actual < expected,
}


def evaluate_threshold(
    threshold: ThresholdConfig,
    snapshot: MetricsSnapshot,
) -> GateEvaluationResult:
    """Avalia um único threshold contra o snapshot de métricas.

    Args:
        threshold: Configuração do threshold a ser avaliado.
        snapshot: Snapshot contendo os valores reais das métricas.

    Returns:
        Resultado da avaliação com status, valores e mensagem.
    """
    if not threshold.enabled:
        return GateEvaluationResult(
            threshold_name=threshold.name,
            category=threshold.category,
            status=GateStatus.SKIPPED,
            severity=threshold.severity,
            expected_value=threshold.threshold_value,
            actual_value=0.0,
            operator=threshold.operator,
            message=f"Threshold '{threshold.name}' está desabilitado.",
        )

    actual = snapshot.get_metric(threshold.metric)
    if actual is None:
        return GateEvaluationResult(
            threshold_name=threshold.name,
            category=threshold.category,
            status=GateStatus.SKIPPED,
            severity=threshold.severity,
            expected_value=threshold.threshold_value,
            actual_value=0.0,
            operator=threshold.operator,
            message=(
                f"Métrica '{threshold.metric}' não encontrada no snapshot. "
                f"Verificação ignorada."
            ),
        )

    comparator = _OPERATOR_MAP.get(threshold.operator)
    if comparator is None:
        # Não deveria acontecer após validação Pydantic, mas defensivo
        return GateEvaluationResult(
            threshold_name=threshold.name,
            category=threshold.category,
            status=GateStatus.FAILED,
            severity=GateSeverity.BLOCKER,
            expected_value=threshold.threshold_value,
            actual_value=actual,
            operator=threshold.operator,
            message=f"Operador '{threshold.operator}' não reconhecido.",
        )

    passed = comparator(actual, threshold.threshold_value)
    status = GateStatus.PASSED if passed else GateStatus.FAILED

    if passed:
        message = (
            f"✅ {threshold.description_pt or threshold.name} — "
            f"Valor: {actual} {threshold.operator} {threshold.threshold_value}."
        )
    else:
        message = (
            f"❌ {threshold.description_pt or threshold.name} — "
            f"Valor atual: {actual}, esperado: {threshold.operator} {threshold.threshold_value}."
        )

    return GateEvaluationResult(
        threshold_name=threshold.name,
        category=threshold.category,
        status=status,
        severity=threshold.severity,
        expected_value=threshold.threshold_value,
        actual_value=actual,
        operator=threshold.operator,
        message=message,
    )


def evaluate_quality_gate(
    snapshot: MetricsSnapshot,
    thresholds: list[ThresholdConfig] | None = None,
) -> QualityGateReport:
    """Avalia todos os thresholds de quality gate contra as métricas coletadas.

    Args:
        snapshot: Snapshot com os valores reais das métricas.
        thresholds: Lista de thresholds a avaliar. Se None, usa os padrão.

    Returns:
        Relatório consolidado com status geral e detalhamento.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    results: list[GateEvaluationResult] = []
    passed_count = 0
    failed_count = 0
    skipped_count = 0
    blockers_failed_count = 0

    for threshold in thresholds:
        result = evaluate_threshold(threshold, snapshot)
        results.append(result)

        if result.status == GateStatus.PASSED:
            passed_count += 1
        elif result.status == GateStatus.FAILED:
            failed_count += 1
            if result.severity == GateSeverity.BLOCKER:
                blockers_failed_count += 1
        else:
            skipped_count += 1

    # Status geral: falha se qualquer BLOCKER falhou
    overall = GateStatus.PASSED if blockers_failed_count == 0 else GateStatus.FAILED

    return QualityGateReport(
        overall_status=overall,
        total_checks=len(results),
        passed=passed_count,
        failed=failed_count,
        skipped=skipped_count,
        results=results,
        blockers_failed=blockers_failed_count,
    )


# ---------------------------------------------------------------------------
# Utilitários de consulta
# ---------------------------------------------------------------------------


def get_thresholds_by_category(
    category: GateCategory,
    thresholds: list[ThresholdConfig] | None = None,
) -> list[ThresholdConfig]:
    """Filtra thresholds por categoria.

    Args:
        category: Categoria desejada.
        thresholds: Lista de thresholds. Se None, usa os padrão.

    Returns:
        Lista filtrada de thresholds.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS
    return [t for t in thresholds if t.category == category]


def get_blocker_thresholds(
    thresholds: list[ThresholdConfig] | None = None,
) -> list[ThresholdConfig]:
    """Retorna apenas os thresholds com severidade BLOCKER.

    Args:
        thresholds: Lista de thresholds. Se None, usa os padrão.

    Returns:
        Lista de thresholds bloqueantes.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS
    return [t for t in thresholds if t.severity == GateSeverity.BLOCKER]


def format_report_summary(report: QualityGateReport) -> str:
    """Formata um resumo textual do relatório de quality gate.

    Args:
        report: Relatório gerado por evaluate_quality_gate.

    Returns:
        String formatada com resumo em PT-BR.
    """
    status_emoji = "✅" if report.overall_status == GateStatus.PASSED else "❌"
    status_text = "APROVADO" if report.overall_status == GateStatus.PASSED else "REPROVADO"

    lines = [
        f"{status_emoji} Quality Gate: {status_text}",
        f"   Total de verificações: {report.total_checks}",
        f"   Aprovadas: {report.passed}",
        f"   Reprovadas: {report.failed} (blockers: {report.blockers_failed})",
        f"   Ignoradas: {report.skipped}",
        "",
    ]

    # Detalhar falhas
    failed_results = [r for r in report.results if r.status == GateStatus.FAILED]
    if failed_results:
        lines.append("Detalhamento das falhas:")
        for r in failed_results:
            severity_label = r.severity.value.upper()
            lines.append(f"   [{severity_label}] {r.message}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Ponto de entrada para execução direta (diagnóstico)
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    # Exemplo de uso para diagnóstico local
    print("=" * 60)
    print("Quality Gate — Thresholds configurados")
    print("=" * 60)
    for _t in DEFAULT_THRESHOLDS:
        status_icon = "🟢" if _t.enabled else "⚪"
        print(
            f"  {status_icon} [{_t.category.value:>12}] {_t.name}: "
            f"{_t.metric} {_t.operator} {_t.threshold_value} "
            f"({_t.severity.value})"
        )
    print(f"\nTotal: {len(DEFAULT_THRESHOLDS)} thresholds configurados.")
    print(
        f"Blockers: {len(get_blocker_thresholds())} | "
        f"Cobertura: {len(get_thresholds_by_category(GateCategory.COVERAGE))} | "
        f"Lint: {len(get_thresholds_by_category(GateCategory.LINT))} | "
        f"Segurança: {len(get_thresholds_by_category(GateCategory.SECURITY))} | "
        f"Performance: {len(get_thresholds_by_category(GateCategory.PERFORMANCE))}"
    )
