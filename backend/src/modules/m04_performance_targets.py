"""Módulo backlog #4: Metas de Performance — Automação Jurídica Assistida.

Define metas de performance, SLA (Service Level Agreement), RTO (Recovery Time
Objective), RPO (Recovery Point Objective), limites de latência por endpoint,
dimensionamento de usuários concorrentes e thresholds de alerta.

Este módulo centraliza todas as constantes e classes de configuração relacionadas
a requisitos não-funcionais de performance, servindo como referência única para:
- Monitoramento e alertas (Prometheus/Grafana)
- Testes de carga (Locust/k6)
- Validação de SLA em middleware
- Planejamento de capacidade

Exemplo de uso:
    from backend.src.modules.m04_performance_targets import (
        get_performance_targets,
        PerformanceTargets,
        EndpointLatencyTarget,
        SLADefinition,
        CapacityPlan,
    )

    targets = get_performance_targets()
    print(targets.sla.availability_percent)  # 99.5
    print(targets.get_latency_target("/api/v1/auth/login"))  # EndpointLatencyTarget
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerações
# ---------------------------------------------------------------------------


class LatencyTier(str, Enum):
    """Classificação de tiers de latência para endpoints.

    Cada tier representa uma faixa aceitável de tempo de resposta,
    permitindo categorizar endpoints por criticidade e complexidade.
    """

    CRITICAL = "critical"
    """Endpoints críticos — autenticação, health check. Latência máxima muito baixa."""

    STANDARD = "standard"
    """Endpoints padrão — CRUD, listagens paginadas. Latência moderada."""

    INTENSIVE = "intensive"
    """Endpoints intensivos — análise de documentos, chamadas LLM. Latência elevada permitida."""

    BACKGROUND = "background"
    """Tarefas em background — processamento assíncrono via Celery. Sem limite de latência HTTP."""


class AlertSeverity(str, Enum):
    """Severidade de alertas de performance."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Modelos de Latência por Endpoint
# ---------------------------------------------------------------------------


class EndpointLatencyTarget(BaseModel):
    """Meta de latência para um endpoint ou grupo de endpoints.

    Attributes:
        path_pattern: Padrão de caminho do endpoint (suporta wildcards simples).
        tier: Classificação do tier de latência.
        p50_ms: Latência alvo no percentil 50 (mediana), em milissegundos.
        p95_ms: Latência alvo no percentil 95, em milissegundos.
        p99_ms: Latência alvo no percentil 99, em milissegundos.
        max_ms: Latência máxima absoluta antes de timeout, em milissegundos.
        description: Descrição legível da meta.
    """

    path_pattern: str = Field(
        ...,
        description="Padrão de caminho do endpoint (ex: /api/v1/auth/*)",
    )
    tier: LatencyTier = Field(
        ...,
        description="Tier de classificação de latência",
    )
    p50_ms: int = Field(
        ...,
        gt=0,
        description="Meta de latência no percentil 50 (mediana) em ms",
    )
    p95_ms: int = Field(
        ...,
        gt=0,
        description="Meta de latência no percentil 95 em ms",
    )
    p99_ms: int = Field(
        ...,
        gt=0,
        description="Meta de latência no percentil 99 em ms",
    )
    max_ms: int = Field(
        ...,
        gt=0,
        description="Latência máxima absoluta (timeout) em ms",
    )
    description: str = Field(
        default="",
        description="Descrição legível da meta de latência",
    )


# ---------------------------------------------------------------------------
# SLA
# ---------------------------------------------------------------------------


class SLADefinition(BaseModel):
    """Definição de SLA (Service Level Agreement) da aplicação.

    Attributes:
        availability_percent: Percentual de disponibilidade alvo (ex: 99.5).
        max_downtime_monthly_minutes: Tempo máximo de indisponibilidade mensal em minutos.
        max_error_rate_percent: Taxa máxima de erros 5xx permitida.
        max_response_time_p95_ms: Tempo de resposta máximo no P95 global.
        measurement_window_days: Janela de medição do SLA em dias.
    """

    availability_percent: float = Field(
        default=99.5,
        ge=90.0,
        le=100.0,
        description="Percentual de disponibilidade alvo do serviço",
    )
    max_downtime_monthly_minutes: float = Field(
        default=216.0,
        ge=0,
        description="Tempo máximo de indisponibilidade mensal permitido (minutos). 99.5% ≈ 216 min/mês",
    )
    max_error_rate_percent: float = Field(
        default=0.5,
        ge=0,
        le=100.0,
        description="Taxa máxima de erros HTTP 5xx permitida (%)",
    )
    max_response_time_p95_ms: int = Field(
        default=2000,
        gt=0,
        description="Tempo de resposta máximo global no percentil 95 (ms)",
    )
    measurement_window_days: int = Field(
        default=30,
        gt=0,
        description="Janela de medição do SLA em dias",
    )


# ---------------------------------------------------------------------------
# RTO / RPO
# ---------------------------------------------------------------------------


class DisasterRecoveryTargets(BaseModel):
    """Metas de recuperação de desastres.

    Attributes:
        rto_minutes: Recovery Time Objective — tempo máximo para restaurar o serviço.
        rpo_minutes: Recovery Point Objective — perda máxima de dados aceitável.
        backup_frequency_hours: Frequência de backups automáticos em horas.
        backup_retention_days: Retenção de backups em dias.
        failover_type: Tipo de failover (manual, semi-automático, automático).
        test_frequency_days: Frequência de testes de DR em dias.
    """

    rto_minutes: int = Field(
        default=60,
        gt=0,
        description="Recovery Time Objective — tempo máximo para restaurar o serviço (minutos)",
    )
    rpo_minutes: int = Field(
        default=15,
        gt=0,
        description="Recovery Point Objective — perda máxima de dados aceitável (minutos)",
    )
    backup_frequency_hours: int = Field(
        default=1,
        gt=0,
        description="Frequência de backups automáticos (horas)",
    )
    backup_retention_days: int = Field(
        default=90,
        gt=0,
        description="Período de retenção de backups (dias)",
    )
    failover_type: str = Field(
        default="semi-automático",
        description="Tipo de failover: manual, semi-automático ou automático",
    )
    test_frequency_days: int = Field(
        default=90,
        gt=0,
        description="Frequência de testes de recuperação de desastres (dias)",
    )


# ---------------------------------------------------------------------------
# Dimensionamento de Usuários
# ---------------------------------------------------------------------------


class CapacityPlan(BaseModel):
    """Plano de capacidade e dimensionamento de usuários.

    Attributes:
        max_concurrent_users: Número máximo de usuários simultâneos suportados.
        max_registered_users: Número máximo de usuários registrados na plataforma.
        max_requests_per_second: Throughput máximo global em requisições por segundo.
        max_requests_per_user_per_minute: Rate limit por usuário autenticado.
        max_file_upload_size_mb: Tamanho máximo de upload de arquivo em MB.
        max_document_pages: Número máximo de páginas por documento para análise.
        max_concurrent_llm_requests: Máximo de chamadas simultâneas à API LLM (Anthropic).
        max_celery_workers: Número máximo de workers Celery para processamento assíncrono.
        db_connection_pool_size: Tamanho do pool de conexões do banco de dados.
        db_connection_pool_max_overflow: Overflow máximo do pool de conexões.
        redis_max_connections: Número máximo de conexões Redis.
    """

    max_concurrent_users: int = Field(
        default=200,
        gt=0,
        description="Número máximo de usuários simultâneos suportados",
    )
    max_registered_users: int = Field(
        default=5000,
        gt=0,
        description="Número máximo de usuários registrados na plataforma",
    )
    max_requests_per_second: int = Field(
        default=500,
        gt=0,
        description="Throughput máximo global (req/s)",
    )
    max_requests_per_user_per_minute: int = Field(
        default=60,
        gt=0,
        description="Rate limit por usuário autenticado (req/min)",
    )
    max_file_upload_size_mb: int = Field(
        default=50,
        gt=0,
        description="Tamanho máximo de upload de arquivo (MB)",
    )
    max_document_pages: int = Field(
        default=500,
        gt=0,
        description="Número máximo de páginas por documento para análise",
    )
    max_concurrent_llm_requests: int = Field(
        default=10,
        gt=0,
        description="Máximo de chamadas simultâneas à API LLM (Anthropic)",
    )
    max_celery_workers: int = Field(
        default=8,
        gt=0,
        description="Número máximo de workers Celery",
    )
    db_connection_pool_size: int = Field(
        default=20,
        gt=0,
        description="Tamanho do pool de conexões PostgreSQL",
    )
    db_connection_pool_max_overflow: int = Field(
        default=10,
        ge=0,
        description="Overflow máximo do pool de conexões PostgreSQL",
    )
    redis_max_connections: int = Field(
        default=50,
        gt=0,
        description="Número máximo de conexões Redis",
    )


# ---------------------------------------------------------------------------
# Thresholds de Alerta
# ---------------------------------------------------------------------------


class AlertThreshold(BaseModel):
    """Threshold individual para disparo de alerta de performance.

    Attributes:
        metric_name: Nome da métrica monitorada.
        warning_value: Valor que dispara alerta de warning.
        critical_value: Valor que dispara alerta crítico.
        unit: Unidade de medida (ms, %, count, MB, etc.).
        description: Descrição legível do threshold.
    """

    metric_name: str = Field(
        ...,
        description="Nome da métrica monitorada",
    )
    warning_value: float = Field(
        ...,
        description="Valor que dispara alerta de warning",
    )
    critical_value: float = Field(
        ...,
        description="Valor que dispara alerta crítico",
    )
    unit: str = Field(
        default="ms",
        description="Unidade de medida (ms, %, count, MB)",
    )
    description: str = Field(
        default="",
        description="Descrição legível do threshold de alerta",
    )


# ---------------------------------------------------------------------------
# Modelo Agregador Principal
# ---------------------------------------------------------------------------


class PerformanceTargets(BaseModel):
    """Modelo agregador de todas as metas de performance da aplicação.

    Centraliza SLA, DR, latência por endpoint, capacidade e alertas
    em uma única estrutura validada e tipada.

    Attributes:
        sla: Definição de SLA do serviço.
        disaster_recovery: Metas de RTO/RPO e recuperação.
        capacity: Plano de capacidade e dimensionamento.
        endpoint_latencies: Lista de metas de latência por endpoint.
        alert_thresholds: Lista de thresholds de alerta.
    """

    sla: SLADefinition = Field(
        default_factory=SLADefinition,
        description="Definição de SLA do serviço",
    )
    disaster_recovery: DisasterRecoveryTargets = Field(
        default_factory=DisasterRecoveryTargets,
        description="Metas de RTO/RPO e recuperação de desastres",
    )
    capacity: CapacityPlan = Field(
        default_factory=CapacityPlan,
        description="Plano de capacidade e dimensionamento de usuários",
    )
    endpoint_latencies: list[EndpointLatencyTarget] = Field(
        default_factory=list,
        description="Metas de latência por endpoint ou grupo de endpoints",
    )
    alert_thresholds: list[AlertThreshold] = Field(
        default_factory=list,
        description="Thresholds de alerta de performance",
    )

    def get_latency_target(
        self, path: str
    ) -> Optional[EndpointLatencyTarget]:
        """Busca a meta de latência mais específica para um caminho de endpoint.

        Realiza correspondência por prefixo, retornando a meta cujo
        path_pattern mais se aproxima do caminho fornecido.

        Args:
            path: Caminho do endpoint (ex: /api/v1/auth/login).

        Returns:
            EndpointLatencyTarget correspondente ou None se não encontrado.
        """
        best_match: Optional[EndpointLatencyTarget] = None
        best_match_length = 0

        for target in self.endpoint_latencies:
            pattern = target.path_pattern.rstrip("*").rstrip("/")
            if path.startswith(pattern) and len(pattern) > best_match_length:
                best_match = target
                best_match_length = len(pattern)

        return best_match

    def get_alert_threshold(
        self, metric_name: str
    ) -> Optional[AlertThreshold]:
        """Busca o threshold de alerta para uma métrica específica.

        Args:
            metric_name: Nome da métrica.

        Returns:
            AlertThreshold correspondente ou None se não encontrado.
        """
        for threshold in self.alert_thresholds:
            if threshold.metric_name == metric_name:
                return threshold
        return None

    def check_latency_compliance(
        self, path: str, actual_p95_ms: float
    ) -> tuple[bool, Optional[AlertSeverity], str]:
        """Verifica se a latência P95 de um endpoint está em conformidade.

        Args:
            path: Caminho do endpoint.
            actual_p95_ms: Latência P95 real medida em milissegundos.

        Returns:
            Tupla com (está_conforme, severidade_alerta, mensagem).
        """
        target = self.get_latency_target(path)
        if target is None:
            return (
                True,
                None,
                f"Nenhuma meta de latência definida para {path}",
            )

        if actual_p95_ms <= target.p95_ms:
            return (
                True,
                None,
                f"Latência P95 de {path} ({actual_p95_ms}ms) dentro da meta ({target.p95_ms}ms)",
            )

        if actual_p95_ms <= target.p99_ms:
            return (
                False,
                AlertSeverity.WARNING,
                f"Latência P95 de {path} ({actual_p95_ms}ms) excede meta P95 ({target.p95_ms}ms) "
                f"mas está abaixo do P99 ({target.p99_ms}ms)",
            )

        if actual_p95_ms <= target.max_ms:
            return (
                False,
                AlertSeverity.CRITICAL,
                f"Latência P95 de {path} ({actual_p95_ms}ms) excede meta P99 ({target.p99_ms}ms)",
            )

        return (
            False,
            AlertSeverity.CRITICAL,
            f"Latência P95 de {path} ({actual_p95_ms}ms) excede limite máximo ({target.max_ms}ms) — possível timeout",
        )


# ---------------------------------------------------------------------------
# Metas padrão da aplicação
# ---------------------------------------------------------------------------


def _build_default_endpoint_latencies() -> list[EndpointLatencyTarget]:
    """Constrói a lista padrão de metas de latência por endpoint.

    Returns:
        Lista de EndpointLatencyTarget com metas para todos os módulos.
    """
    return [
        # --- Autenticação (crítico) ---
        EndpointLatencyTarget(
            path_pattern="/api/v1/auth/login",
            tier=LatencyTier.CRITICAL,
            p50_ms=150,
            p95_ms=400,
            p99_ms=800,
            max_ms=2000,
            description="Login de usuário — inclui verificação de senha bcrypt e geração JWT",
        ),
        EndpointLatencyTarget(
            path_pattern="/api/v1/auth/refresh",
            tier=LatencyTier.CRITICAL,
            p50_ms=50,
            p95_ms=150,
            p99_ms=300,
            max_ms=1000,
            description="Refresh de token JWT",
        ),
        EndpointLatencyTarget(
            path_pattern="/api/v1/auth/mfa",
            tier=LatencyTier.CRITICAL,
            p50_ms=100,
            p95_ms=300,
            p99_ms=600,
            max_ms=1500,
            description="Verificação MFA (TOTP)",
        ),
        # --- Health check ---
        EndpointLatencyTarget(
            path_pattern="/api/v1/health",
            tier=LatencyTier.CRITICAL,
            p50_ms=10,
            p95_ms=50,
            p99_ms=100,
            max_ms=500,
            description="Health check — deve ser extremamente rápido",
        ),
        # --- Usuários (padrão) ---
        EndpointLatencyTarget(
            path_pattern="/api/v1/users",
            tier=LatencyTier.STANDARD,
            p50_ms=100,
            p95_ms=300,
            p99_ms=600,
            max_ms=2000,
            description="CRUD de usuários e perfis RBAC",
        ),
        # --- Documentos (padrão) ---
        EndpointLatencyTarget(
            path_pattern="/api/v1/documents",
            tier=LatencyTier.STANDARD,
            p50_ms=150,
            p95_ms=500,
            p99_ms=1000,
            max_ms=3000,
            description="Listagem e metadados de documentos jurídicos",
        ),
        EndpointLatencyTarget(
            path_pattern="/api/v1/documents/upload",
            tier=LatencyTier.INTENSIVE,
            p50_ms=500,
            p95_ms=2000,
            p99_ms=5000,
            max_ms=30000,
            description="Upload de documentos — depende do tamanho do arquivo e varredura",
        ),
        # --- Análise com LLM (intensivo) ---
        EndpointLatencyTarget(
            path_pattern="/api/v1/analysis",
            tier=LatencyTier.INTENSIVE,
            p50_ms=3000,
            p95_ms=10000,
            p99_ms=20000,
            max_ms=60000,
            description="Análise de documentos via LLM Anthropic — latência alta esperada",
        ),
        # --- Chat com assistente (intensivo) ---
        EndpointLatencyTarget(
            path_pattern="/api/v1/chat",
            tier=LatencyTier.INTENSIVE,
            p50_ms=2000,
            p95_ms=8000,
            p99_ms=15000,
            max_ms=45000,
            description="Chat interativo com assistente jurídico (streaming recomendado)",
        ),
        # --- Auditoria (padrão) ---
        EndpointLatencyTarget(
            path_pattern="/api/v1/audit",
            tier=LatencyTier.STANDARD,
            p50_ms=100,
            p95_ms=400,
            p99_ms=800,
            max_ms=2000,
            description="Consulta de logs de auditoria",
        ),
        # --- DataJud (intensivo — API externa) ---
        EndpointLatencyTarget(
            path_pattern="/api/v1/datajud",
            tier=LatencyTier.INTENSIVE,
            p50_ms=1000,
            p95_ms=5000,
            p99_ms=10000,
            max_ms=30000,
            description="Consulta à API DataJud — latência depende do serviço externo",
        ),
    ]


def _build_default_alert_thresholds() -> list[AlertThreshold]:
    """Constrói a lista padrão de thresholds de alerta.

    Returns:
        Lista de AlertThreshold para métricas críticas do sistema.
    """
    return [
        AlertThreshold(
            metric_name="cpu_usage_percent",
            warning_value=70.0,
            critical_value=90.0,
            unit="%",
            description="Uso de CPU do servidor de aplicação",
        ),
        AlertThreshold(
            metric_name="memory_usage_percent",
            warning_value=75.0,
            critical_value=90.0,
            unit="%",
            description="Uso de memória RAM do servidor",
        ),
        AlertThreshold(
            metric_name="disk_usage_percent",
            warning_value=80.0,
            critical_value=95.0,
            unit="%",
            description="Uso de disco (armazenamento de documentos)",
        ),
        AlertThreshold(
            metric_name="db_connection_pool_usage_percent",
            warning_value=70.0,
            critical_value=90.0,
            unit="%",
            description="Utilização do pool de conexões PostgreSQL",
        ),
        AlertThreshold(
            metric_name="http_error_rate_5xx_percent",
            warning_value=0.5,
            critical_value=2.0,
            unit="%",
            description="Taxa de erros HTTP 5xx",
        ),
        AlertThreshold(
            metric_name="http_response_time_p95_ms",
            warning_value=2000.0,
            critical_value=5000.0,
            unit="ms",
            description="Tempo de resposta HTTP global no percentil 95",
        ),
        AlertThreshold(
            metric_name="celery_queue_length",
            warning_value=100.0,
            critical_value=500.0,
            unit="count",
            description="Tamanho da fila de tarefas Celery pendentes",
        ),
        AlertThreshold(
            metric_name="celery_task_failure_rate_percent",
            warning_value=5.0,
            critical_value=15.0,
            unit="%",
            description="Taxa de falha de tarefas Celery",
        ),
        AlertThreshold(
            metric_name="llm_api_latency_p95_ms",
            warning_value=10000.0,
            critical_value=25000.0,
            unit="ms",
            description="Latência P95 de chamadas à API Anthropic (LLM)",
        ),
        AlertThreshold(
            metric_name="llm_api_error_rate_percent",
            warning_value=5.0,
            critical_value=20.0,
            unit="%",
            description="Taxa de erro de chamadas à API Anthropic",
        ),
        AlertThreshold(
            metric_name="redis_memory_usage_mb",
            warning_value=256.0,
            critical_value=450.0,
            unit="MB",
            description="Uso de memória do Redis (cache e sessões)",
        ),
        AlertThreshold(
            metric_name="active_websocket_connections",
            warning_value=150.0,
            critical_value=190.0,
            unit="count",
            description="Número de conexões WebSocket ativas (chat)",
        ),
    ]


def _build_default_targets() -> PerformanceTargets:
    """Constrói a instância padrão de PerformanceTargets com todos os valores recomendados.

    Returns:
        PerformanceTargets com metas padrão para a Automação Jurídica Assistida.
    """
    return PerformanceTargets(
        sla=SLADefinition(
            availability_percent=99.5,
            max_downtime_monthly_minutes=216.0,
            max_error_rate_percent=0.5,
            max_response_time_p95_ms=2000,
            measurement_window_days=30,
        ),
        disaster_recovery=DisasterRecoveryTargets(
            rto_minutes=60,
            rpo_minutes=15,
            backup_frequency_hours=1,
            backup_retention_days=90,
            failover_type="semi-automático",
            test_frequency_days=90,
        ),
        capacity=CapacityPlan(
            max_concurrent_users=200,
            max_registered_users=5000,
            max_requests_per_second=500,
            max_requests_per_user_per_minute=60,
            max_file_upload_size_mb=50,
            max_document_pages=500,
            max_concurrent_llm_requests=10,
            max_celery_workers=8,
            db_connection_pool_size=20,
            db_connection_pool_max_overflow=10,
            redis_max_connections=50,
        ),
        endpoint_latencies=_build_default_endpoint_latencies(),
        alert_thresholds=_build_default_alert_thresholds(),
    )


# ---------------------------------------------------------------------------
# Singleton com cache
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_performance_targets() -> PerformanceTargets:
    """Retorna a instância singleton de PerformanceTargets.

    Utiliza lru_cache para garantir que a instância seja criada apenas uma vez.
    Para sobrescrever valores em testes, utilize `get_performance_targets.cache_clear()`
    e recrie com valores customizados.

    Returns:
        PerformanceTargets com todas as metas de performance da aplicação.

    Exemplo:
        >>> targets = get_performance_targets()
        >>> targets.sla.availability_percent
        99.5
        >>> targets.capacity.max_concurrent_users
        200
    """
    # TODO: Futuramente, carregar overrides a partir de settings.py ou variáveis
    # de ambiente para permitir ajustes por ambiente (dev/staging/prod).
    # Exemplo: settings = get_settings(); usar settings.PERFORMANCE_* se disponíveis.
    return _build_default_targets()


# ---------------------------------------------------------------------------
# Utilitários para integração com middleware e monitoramento
# ---------------------------------------------------------------------------


def get_rate_limit_for_user() -> str:
    """Retorna a string de rate limit formatada para uso com slowapi.

    Returns:
        String no formato "N/minute" compatível com slowapi.

    Exemplo:
        >>> get_rate_limit_for_user()
        '60/minute'
    """
    targets = get_performance_targets()
    return f"{targets.capacity.max_requests_per_user_per_minute}/minute"


def get_max_upload_size_bytes() -> int:
    """Retorna o tamanho máximo de upload em bytes.

    Returns:
        Tamanho máximo em bytes.

    Exemplo:
        >>> get_max_upload_size_bytes()
        52428800
    """
    targets = get_performance_targets()
    return targets.capacity.max_file_upload_size_mb * 1024 * 1024


def get_db_pool_config() -> dict[str, int]:
    """Retorna configuração do pool de conexões para SQLAlchemy.

    Returns:
        Dicionário com pool_size e max_overflow.

    Exemplo:
        >>> get_db_pool_config()
        {'pool_size': 20, 'max_overflow': 10}
    """
    targets = get_performance_targets()
    return {
        "pool_size": targets.capacity.db_connection_pool_size,
        "max_overflow": targets.capacity.db_connection_pool_max_overflow,
    }


def is_endpoint_intensive(path: str) -> bool:
    """Verifica se um endpoint é classificado como intensivo.

    Endpoints intensivos podem ter tratamento diferenciado (timeout estendido,
    processamento assíncrono, streaming).

    Args:
        path: Caminho do endpoint.

    Returns:
        True se o endpoint é intensivo ou background.
    """
    targets = get_performance_targets()
    target = targets.get_latency_target(path)
    if target is None:
        return False
    return target.tier in (LatencyTier.INTENSIVE, LatencyTier.BACKGROUND)


def get_timeout_for_endpoint(path: str) -> float:
    """Retorna o timeout em segundos para um endpoint específico.

    Útil para configurar timeouts de httpx, Celery tasks ou middleware.

    Args:
        path: Caminho do endpoint.

    Returns:
        Timeout em segundos. Retorna 30.0 como padrão se não houver meta definida.
    """
    targets = get_performance_targets()
    target = targets.get_latency_target(path)
    if target is None:
        return 30.0
    return target.max_ms / 1000.0
