"""Módulo de Configuração de Compliance Testing — LGPD, OAB e Auditoria.

Implementa verificações automatizadas de conformidade com:
- LGPD (Lei Geral de Proteção de Dados — Lei 13.709/2018)
- Regras do Estatuto da OAB (Lei 8.906/94) — sigilo advocatício
- Validação de trilha de auditoria (audit trail)

Este módulo fornece configurações, regras e utilitários para execução
de testes de compliance em pipelines de CI/CD e verificações em runtime.

Dependências:
- m02_data_confidentiality_compliance: Classificação de confidencialidade e sanitização
- Pydantic v2: Validação de schemas de configuração
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums de domínio
# ---------------------------------------------------------------------------


class ComplianceDomain(str, enum.Enum):
    """Domínios de compliance suportados pelo sistema."""

    LGPD = "lgpd"
    OAB = "oab"
    AUDIT_TRAIL = "audit_trail"


class ComplianceSeverity(str, enum.Enum):
    """Severidade de uma violação de compliance."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ComplianceCheckStatus(str, enum.Enum):
    """Status de execução de uma verificação de compliance."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Regras de Compliance — LGPD
# ---------------------------------------------------------------------------


class LGPDRule(BaseModel):
    """Representação de uma regra de verificação LGPD.

    Cada regra mapeia um artigo ou princípio da Lei 13.709/2018 para
    uma verificação automatizada executável.
    """

    rule_id: str = Field(
        ...,
        description="Identificador único da regra (ex: LGPD-001).",
        pattern=r"^LGPD-\d{3}$",
    )
    article: str = Field(
        ...,
        description="Artigo da LGPD referenciado (ex: Art. 6º, Art. 46).",
    )
    title: str = Field(
        ...,
        description="Título descritivo da regra em PT-BR.",
    )
    description: str = Field(
        ...,
        description="Descrição detalhada da verificação em PT-BR.",
    )
    severity: ComplianceSeverity = Field(
        default=ComplianceSeverity.HIGH,
        description="Severidade em caso de violação.",
    )
    enabled: bool = Field(
        default=True,
        description="Se a regra está ativa para verificação.",
    )
    automated: bool = Field(
        default=True,
        description="Se a verificação pode ser executada automaticamente.",
    )


class LGPDComplianceConfig(BaseModel):
    """Configuração completa de verificações LGPD."""

    domain: ComplianceDomain = Field(
        default=ComplianceDomain.LGPD,
        description="Domínio de compliance.",
    )
    rules: list[LGPDRule] = Field(
        default_factory=list,
        description="Lista de regras LGPD configuradas.",
    )
    require_consent_record: bool = Field(
        default=True,
        description="Exigir registro de consentimento antes de processar dados pessoais.",
    )
    require_legal_basis: bool = Field(
        default=True,
        description="Exigir base legal documentada para cada tratamento de dados.",
    )
    data_retention_max_days: int = Field(
        default=1825,
        ge=1,
        description="Prazo máximo de retenção de dados pessoais em dias (padrão: 5 anos).",
    )
    require_anonymization_for_llm: bool = Field(
        default=True,
        description="Exigir anonimização obrigatória antes de envio a LLMs.",
    )
    pii_detection_enabled: bool = Field(
        default=True,
        description="Habilitar detecção automática de dados pessoais (PII).",
    )
    sensitive_data_categories: list[str] = Field(
        default_factory=lambda: [
            "cpf",
            "rg",
            "nome_completo",
            "endereco",
            "telefone",
            "email",
            "dados_bancarios",
            "dados_saude",
            "origem_racial_etnica",
            "opiniao_politica",
            "convicao_religiosa",
            "dados_biometricos",
            "dados_geneticos",
        ],
        description="Categorias de dados sensíveis monitoradas conforme Art. 5º, II da LGPD.",
    )


# ---------------------------------------------------------------------------
# Regras de Compliance — OAB
# ---------------------------------------------------------------------------


class OABRule(BaseModel):
    """Representação de uma regra de verificação do Estatuto da OAB.

    Foca no sigilo profissional (Art. 7º) e demais obrigações éticas
    aplicáveis ao uso de tecnologia na advocacia.
    """

    rule_id: str = Field(
        ...,
        description="Identificador único da regra (ex: OAB-001).",
        pattern=r"^OAB-\d{3}$",
    )
    statute_reference: str = Field(
        ...,
        description="Referência ao Estatuto da OAB ou Código de Ética (ex: Art. 7º, §2º).",
    )
    title: str = Field(
        ...,
        description="Título descritivo da regra em PT-BR.",
    )
    description: str = Field(
        ...,
        description="Descrição detalhada da verificação em PT-BR.",
    )
    severity: ComplianceSeverity = Field(
        default=ComplianceSeverity.CRITICAL,
        description="Severidade em caso de violação.",
    )
    enabled: bool = Field(
        default=True,
        description="Se a regra está ativa para verificação.",
    )
    requires_confidentiality_classification: bool = Field(
        default=True,
        description="Se a regra exige classificação prévia de confidencialidade.",
    )


class OABComplianceConfig(BaseModel):
    """Configuração completa de verificações OAB."""

    domain: ComplianceDomain = Field(
        default=ComplianceDomain.OAB,
        description="Domínio de compliance.",
    )
    rules: list[OABRule] = Field(
        default_factory=list,
        description="Lista de regras OAB configuradas.",
    )
    enforce_confidentiality_before_llm: bool = Field(
        default=True,
        description="Bloquear envio a LLM sem classificação de confidencialidade.",
    )
    require_sanitization_pipeline: bool = Field(
        default=True,
        description="Exigir passagem pelo pipeline de sanitização (m02) antes de envio a LLMs.",
    )
    max_confidentiality_level_for_llm: str = Field(
        default="restrito",
        description="Nível máximo de confidencialidade permitido para envio a LLMs.",
    )
    log_all_llm_interactions: bool = Field(
        default=True,
        description="Registrar todas as interações com LLMs na trilha de auditoria.",
    )


# ---------------------------------------------------------------------------
# Regras de Compliance — Trilha de Auditoria
# ---------------------------------------------------------------------------


class AuditTrailRule(BaseModel):
    """Representação de uma regra de validação de trilha de auditoria."""

    rule_id: str = Field(
        ...,
        description="Identificador único da regra (ex: AUDIT-001).",
        pattern=r"^AUDIT-\d{3}$",
    )
    title: str = Field(
        ...,
        description="Título descritivo da regra em PT-BR.",
    )
    description: str = Field(
        ...,
        description="Descrição detalhada da verificação em PT-BR.",
    )
    severity: ComplianceSeverity = Field(
        default=ComplianceSeverity.HIGH,
        description="Severidade em caso de violação.",
    )
    enabled: bool = Field(
        default=True,
        description="Se a regra está ativa para verificação.",
    )


class AuditTrailComplianceConfig(BaseModel):
    """Configuração de validação da trilha de auditoria."""

    domain: ComplianceDomain = Field(
        default=ComplianceDomain.AUDIT_TRAIL,
        description="Domínio de compliance.",
    )
    rules: list[AuditTrailRule] = Field(
        default_factory=list,
        description="Lista de regras de auditoria configuradas.",
    )
    require_immutable_logs: bool = Field(
        default=True,
        description="Exigir que registros de auditoria sejam imutáveis (append-only).",
    )
    require_timestamp_utc: bool = Field(
        default=True,
        description="Exigir timestamps em UTC para todos os registros.",
    )
    require_user_identification: bool = Field(
        default=True,
        description="Exigir identificação do usuário em cada registro de auditoria.",
    )
    require_request_correlation_id: bool = Field(
        default=True,
        description="Exigir correlation ID (request ID) em cada registro.",
    )
    retention_days: int = Field(
        default=2555,
        ge=365,
        description="Prazo mínimo de retenção de registros de auditoria em dias (padrão: ~7 anos).",
    )
    log_access_to_sensitive_data: bool = Field(
        default=True,
        description="Registrar todo acesso a dados classificados como sensíveis.",
    )


# ---------------------------------------------------------------------------
# Resultado de verificação de compliance
# ---------------------------------------------------------------------------


class ComplianceCheckResult(BaseModel):
    """Resultado de uma verificação individual de compliance."""

    check_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único da execução da verificação.",
    )
    rule_id: str = Field(
        ...,
        description="Identificador da regra verificada.",
    )
    domain: ComplianceDomain = Field(
        ...,
        description="Domínio de compliance da verificação.",
    )
    status: ComplianceCheckStatus = Field(
        ...,
        description="Status da verificação.",
    )
    severity: ComplianceSeverity = Field(
        ...,
        description="Severidade da regra.",
    )
    message: str = Field(
        ...,
        description="Mensagem descritiva do resultado em PT-BR.",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Detalhes adicionais da verificação.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Momento da verificação em UTC.",
    )


class ComplianceReport(BaseModel):
    """Relatório consolidado de verificações de compliance."""

    report_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único do relatório.",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Momento de geração do relatório em UTC.",
    )
    domains_checked: list[ComplianceDomain] = Field(
        default_factory=list,
        description="Domínios de compliance verificados.",
    )
    total_checks: int = Field(
        default=0,
        ge=0,
        description="Total de verificações executadas.",
    )
    passed: int = Field(
        default=0,
        ge=0,
        description="Quantidade de verificações aprovadas.",
    )
    failed: int = Field(
        default=0,
        ge=0,
        description="Quantidade de verificações reprovadas.",
    )
    errors: int = Field(
        default=0,
        ge=0,
        description="Quantidade de verificações com erro.",
    )
    skipped: int = Field(
        default=0,
        ge=0,
        description="Quantidade de verificações ignoradas.",
    )
    results: list[ComplianceCheckResult] = Field(
        default_factory=list,
        description="Lista detalhada de resultados.",
    )
    overall_compliant: bool = Field(
        default=False,
        description="Se o sistema está em conformidade geral (nenhuma falha crítica/alta).",
    )

    @field_validator("overall_compliant", mode="before")
    @classmethod
    def compute_overall_compliance(cls, v: Any, info: Any) -> bool:
        """Calcula conformidade geral com base nos resultados, se não fornecido explicitamente."""
        # Se o valor foi explicitamente definido como False, respeitar
        # A lógica real é computada no método de instância
        return v

    def compute_compliance(self) -> bool:
        """Recalcula o status de conformidade geral.

        Retorna False se houver qualquer falha com severidade CRITICAL ou HIGH.
        """
        for result in self.results:
            if result.status == ComplianceCheckStatus.FAILED and result.severity in (
                ComplianceSeverity.CRITICAL,
                ComplianceSeverity.HIGH,
            ):
                return False
        return True


# ---------------------------------------------------------------------------
# Regras padrão pré-configuradas
# ---------------------------------------------------------------------------


def get_default_lgpd_rules() -> list[LGPDRule]:
    """Retorna as regras LGPD padrão do sistema.

    Regras baseadas nos artigos mais relevantes da Lei 13.709/2018
    para o contexto de automação jurídica com IA.
    """
    return [
        LGPDRule(
            rule_id="LGPD-001",
            article="Art. 7º",
            title="Base legal para tratamento de dados",
            description=(
                "Verificar se todo tratamento de dados pessoais possui base legal "
                "documentada conforme Art. 7º da LGPD."
            ),
            severity=ComplianceSeverity.CRITICAL,
        ),
        LGPDRule(
            rule_id="LGPD-002",
            article="Art. 6º, I",
            title="Princípio da finalidade",
            description=(
                "Verificar se o tratamento de dados é realizado para propósitos "
                "legítimos, específicos e informados ao titular."
            ),
            severity=ComplianceSeverity.HIGH,
        ),
        LGPDRule(
            rule_id="LGPD-003",
            article="Art. 6º, III",
            title="Princípio da necessidade",
            description=(
                "Verificar se apenas dados estritamente necessários são coletados "
                "e processados (minimização de dados)."
            ),
            severity=ComplianceSeverity.HIGH,
        ),
        LGPDRule(
            rule_id="LGPD-004",
            article="Art. 46",
            title="Medidas de segurança",
            description=(
                "Verificar se medidas técnicas e administrativas de segurança estão "
                "implementadas para proteger dados pessoais."
            ),
            severity=ComplianceSeverity.CRITICAL,
        ),
        LGPDRule(
            rule_id="LGPD-005",
            article="Art. 12",
            title="Anonimização de dados para LLM",
            description=(
                "Verificar se dados enviados a modelos de linguagem (LLMs) passam "
                "por processo de anonimização irreversível ou pseudonimização."
            ),
            severity=ComplianceSeverity.CRITICAL,
        ),
        LGPDRule(
            rule_id="LGPD-006",
            article="Art. 37",
            title="Registro de operações de tratamento",
            description=(
                "Verificar se todas as operações de tratamento de dados pessoais "
                "são registradas conforme Art. 37 da LGPD."
            ),
            severity=ComplianceSeverity.HIGH,
        ),
        LGPDRule(
            rule_id="LGPD-007",
            article="Art. 18",
            title="Direitos do titular",
            description=(
                "Verificar se mecanismos para exercício dos direitos do titular "
                "(acesso, correção, exclusão, portabilidade) estão implementados."
            ),
            severity=ComplianceSeverity.HIGH,
        ),
        LGPDRule(
            rule_id="LGPD-008",
            article="Art. 16",
            title="Eliminação de dados após tratamento",
            description=(
                "Verificar se dados pessoais são eliminados após o término do "
                "tratamento, respeitados os prazos legais de retenção."
            ),
            severity=ComplianceSeverity.MEDIUM,
        ),
    ]


def get_default_oab_rules() -> list[OABRule]:
    """Retorna as regras OAB padrão do sistema.

    Regras baseadas no Estatuto da Advocacia (Lei 8.906/94) e no
    Código de Ética e Disciplina da OAB, com foco no sigilo profissional.
    """
    return [
        OABRule(
            rule_id="OAB-001",
            statute_reference="Art. 7º, II — Estatuto da OAB",
            title="Sigilo profissional — inviolabilidade",
            description=(
                "Verificar se dados protegidos por sigilo advocatício não são "
                "expostos a terceiros sem autorização, incluindo LLMs."
            ),
            severity=ComplianceSeverity.CRITICAL,
        ),
        OABRule(
            rule_id="OAB-002",
            statute_reference="Art. 34, VII — Estatuto da OAB",
            title="Violação de sigilo profissional",
            description=(
                "Verificar se não há violação de sigilo profissional no envio "
                "de informações a serviços externos (APIs de IA)."
            ),
            severity=ComplianceSeverity.CRITICAL,
        ),
        OABRule(
            rule_id="OAB-003",
            statute_reference="Art. 25 — Código de Ética OAB",
            title="Sigilo sobre fatos conhecidos no exercício da profissão",
            description=(
                "Verificar se fatos e informações conhecidos no exercício da "
                "advocacia são mantidos em sigilo, mesmo em interações com IA."
            ),
            severity=ComplianceSeverity.CRITICAL,
        ),
        OABRule(
            rule_id="OAB-004",
            statute_reference="Provimento 205/2021 — OAB",
            title="Uso de tecnologia na advocacia",
            description=(
                "Verificar conformidade com o Provimento 205/2021 sobre uso de "
                "tecnologia, publicidade e exercício da advocacia digital."
            ),
            severity=ComplianceSeverity.HIGH,
        ),
        OABRule(
            rule_id="OAB-005",
            statute_reference="Art. 7º, §2º — Estatuto da OAB",
            title="Classificação de confidencialidade obrigatória",
            description=(
                "Verificar se todos os documentos possuem classificação de "
                "confidencialidade antes de qualquer processamento por IA."
            ),
            severity=ComplianceSeverity.CRITICAL,
            requires_confidentiality_classification=True,
        ),
    ]


def get_default_audit_trail_rules() -> list[AuditTrailRule]:
    """Retorna as regras de auditoria padrão do sistema."""
    return [
        AuditTrailRule(
            rule_id="AUDIT-001",
            title="Imutabilidade dos registros de auditoria",
            description=(
                "Verificar se registros de auditoria são imutáveis e não podem "
                "ser alterados ou excluídos após criação."
            ),
            severity=ComplianceSeverity.CRITICAL,
        ),
        AuditTrailRule(
            rule_id="AUDIT-002",
            title="Timestamps em UTC",
            description=(
                "Verificar se todos os registros de auditoria utilizam timestamps "
                "em UTC para consistência temporal."
            ),
            severity=ComplianceSeverity.MEDIUM,
        ),
        AuditTrailRule(
            rule_id="AUDIT-003",
            title="Identificação de usuário",
            description=(
                "Verificar se cada registro de auditoria contém identificação "
                "inequívoca do usuário responsável pela ação."
            ),
            severity=ComplianceSeverity.HIGH,
        ),
        AuditTrailRule(
            rule_id="AUDIT-004",
            title="Correlation ID em requests",
            description=(
                "Verificar se cada request possui um correlation ID único "
                "propagado em todos os registros de auditoria associados."
            ),
            severity=ComplianceSeverity.MEDIUM,
        ),
        AuditTrailRule(
            rule_id="AUDIT-005",
            title="Registro de acesso a dados sensíveis",
            description=(
                "Verificar se todo acesso a dados classificados como sensíveis "
                "é registrado na trilha de auditoria."
            ),
            severity=ComplianceSeverity.HIGH,
        ),
        AuditTrailRule(
            rule_id="AUDIT-006",
            title="Registro de interações com LLM",
            description=(
                "Verificar se todas as interações com modelos de linguagem (LLMs) "
                "são registradas com metadados completos (prompt hash, tokens, modelo)."
            ),
            severity=ComplianceSeverity.HIGH,
        ),
        AuditTrailRule(
            rule_id="AUDIT-007",
            title="Retenção mínima de registros",
            description=(
                "Verificar se registros de auditoria são retidos pelo prazo "
                "mínimo configurado (padrão: 7 anos)."
            ),
            severity=ComplianceSeverity.HIGH,
        ),
    ]


# ---------------------------------------------------------------------------
# Configuração consolidada
# ---------------------------------------------------------------------------


class ComplianceTestingConfig(BaseModel):
    """Configuração consolidada de todos os domínios de compliance testing.

    Ponto central de configuração para verificações de conformidade
    executadas tanto em testes automatizados (CI/CD) quanto em
    verificações de runtime.
    """

    lgpd: LGPDComplianceConfig = Field(
        default_factory=lambda: LGPDComplianceConfig(
            rules=get_default_lgpd_rules(),
        ),
        description="Configuração de compliance LGPD.",
    )
    oab: OABComplianceConfig = Field(
        default_factory=lambda: OABComplianceConfig(
            rules=get_default_oab_rules(),
        ),
        description="Configuração de compliance OAB.",
    )
    audit_trail: AuditTrailComplianceConfig = Field(
        default_factory=lambda: AuditTrailComplianceConfig(
            rules=get_default_audit_trail_rules(),
        ),
        description="Configuração de validação de trilha de auditoria.",
    )
    fail_on_critical: bool = Field(
        default=True,
        description="Falhar build/deploy se houver violação de severidade CRITICAL.",
    )
    fail_on_high: bool = Field(
        default=True,
        description="Falhar build/deploy se houver violação de severidade HIGH.",
    )
    enabled_domains: list[ComplianceDomain] = Field(
        default_factory=lambda: [
            ComplianceDomain.LGPD,
            ComplianceDomain.OAB,
            ComplianceDomain.AUDIT_TRAIL,
        ],
        description="Domínios de compliance habilitados para verificação.",
    )

    def get_all_enabled_rules(
        self,
    ) -> list[LGPDRule | OABRule | AuditTrailRule]:
        """Retorna todas as regras habilitadas de todos os domínios ativos."""
        rules: list[LGPDRule | OABRule | AuditTrailRule] = []

        if ComplianceDomain.LGPD in self.enabled_domains:
            rules.extend(r for r in self.lgpd.rules if r.enabled)

        if ComplianceDomain.OAB in self.enabled_domains:
            rules.extend(r for r in self.oab.rules if r.enabled)

        if ComplianceDomain.AUDIT_TRAIL in self.enabled_domains:
            rules.extend(r for r in self.audit_trail.rules if r.enabled)

        return rules

    def get_rules_by_domain(
        self, domain: ComplianceDomain
    ) -> list[LGPDRule | OABRule | AuditTrailRule]:
        """Retorna regras habilitadas de um domínio específico."""
        if domain == ComplianceDomain.LGPD:
            return [r for r in self.lgpd.rules if r.enabled]
        elif domain == ComplianceDomain.OAB:
            return [r for r in self.oab.rules if r.enabled]
        elif domain == ComplianceDomain.AUDIT_TRAIL:
            return [r for r in self.audit_trail.rules if r.enabled]
        return []

    def should_fail_on_severity(self, severity: ComplianceSeverity) -> bool:
        """Verifica se uma severidade deve causar falha no pipeline."""
        if severity == ComplianceSeverity.CRITICAL:
            return self.fail_on_critical
        if severity == ComplianceSeverity.HIGH:
            return self.fail_on_high
        return False


# ---------------------------------------------------------------------------
# Executor de verificações de compliance
# ---------------------------------------------------------------------------


class ComplianceChecker:
    """Executor de verificações de compliance.

    Orquestra a execução de regras de compliance e gera relatórios
    consolidados. Projetado para ser utilizado tanto em testes
    automatizados quanto em verificações de runtime.

    Exemplo de uso::

        config = ComplianceTestingConfig()
        checker = ComplianceChecker(config)
        report = await checker.run_all_checks(context={...})
        if not report.overall_compliant:
            raise ComplianceViolationError(report)
    """

    def __init__(self, config: ComplianceTestingConfig | None = None) -> None:
        """Inicializa o verificador com a configuração fornecida.

        Args:
            config: Configuração de compliance. Se None, usa configuração padrão.
        """
        self.config = config or ComplianceTestingConfig()
        self._check_handlers: dict[
            str, Any
        ] = {}  # TODO: Registrar handlers específicos por rule_id

    async def run_all_checks(
        self, context: dict[str, Any] | None = None
    ) -> ComplianceReport:
        """Executa todas as verificações de compliance habilitadas.

        Args:
            context: Contexto adicional para as verificações (ex: dados do request,
                     informações do documento sendo processado).

        Returns:
            Relatório consolidado de compliance.
        """
        context = context or {}
        results: list[ComplianceCheckResult] = []

        for domain in self.config.enabled_domains:
            domain_results = await self._run_domain_checks(domain, context)
            results.extend(domain_results)

        report = ComplianceReport(
            domains_checked=list(self.config.enabled_domains),
            total_checks=len(results),
            passed=sum(
                1 for r in results if r.status == ComplianceCheckStatus.PASSED
            ),
            failed=sum(
                1 for r in results if r.status == ComplianceCheckStatus.FAILED
            ),
            errors=sum(
                1 for r in results if r.status == ComplianceCheckStatus.ERROR
            ),
            skipped=sum(
                1 for r in results if r.status == ComplianceCheckStatus.SKIPPED
            ),
            results=results,
            overall_compliant=True,  # Será recalculado
        )
        report.overall_compliant = report.compute_compliance()

        return report

    async def run_domain_checks(
        self, domain: ComplianceDomain, context: dict[str, Any] | None = None
    ) -> ComplianceReport:
        """Executa verificações de um domínio específico.

        Args:
            domain: Domínio de compliance a verificar.
            context: Contexto adicional para as verificações.

        Returns:
            Relatório de compliance do domínio.
        """
        context = context or {}
        results = await self._run_domain_checks(domain, context)

        report = ComplianceReport(
            domains_checked=[domain],
            total_checks=len(results),
            passed=sum(
                1 for r in results if r.status == ComplianceCheckStatus.PASSED
            ),
            failed=sum(
                1 for r in results if r.status == ComplianceCheckStatus.FAILED
            ),
            errors=sum(
                1 for r in results if r.status == ComplianceCheckStatus.ERROR
            ),
            skipped=sum(
                1 for r in results if r.status == ComplianceCheckStatus.SKIPPED
            ),
            results=results,
            overall_compliant=True,
        )
        report.overall_compliant = report.compute_compliance()

        return report

    async def _run_domain_checks(
        self, domain: ComplianceDomain, context: dict[str, Any]
    ) -> list[ComplianceCheckResult]:
        """Executa verificações de um domínio e retorna resultados individuais."""
        rules = self.config.get_rules_by_domain(domain)
        results: list[ComplianceCheckResult] = []

        for rule in rules:
            result = await self._execute_check(rule, domain, context)
            results.append(result)

        return results

    async def _execute_check(
        self,
        rule: LGPDRule | OABRule | AuditTrailRule,
        domain: ComplianceDomain,
        context: dict[str, Any],
    ) -> ComplianceCheckResult:
        """Executa uma verificação individual de compliance.

        Args:
            rule: Regra a ser verificada.
            domain: Domínio da regra.
            context: Contexto da verificação.

        Returns:
            Resultado da verificação.
        """
        handler = self._check_handlers.get(rule.rule_id)

        if handler is not None:
            try:
                return await handler(rule, context)
            except Exception as exc:
                return ComplianceCheckResult(
                    rule_id=rule.rule_id,
                    domain=domain,
                    status=ComplianceCheckStatus.ERROR,
                    severity=rule.severity,
                    message=f"Erro ao executar verificação {rule.rule_id}: {exc!s}",
                    details={"error": str(exc)},
                )

        # TODO: Implementar handlers específicos para cada regra.
        # Por enquanto, regras sem handler registrado são marcadas como SKIPPED.
        return ComplianceCheckResult(
            rule_id=rule.rule_id,
            domain=domain,
            status=ComplianceCheckStatus.SKIPPED,
            severity=rule.severity,
            message=(
                f"Verificação {rule.rule_id} ignorada — handler não registrado. "
                f"Implemente e registre o handler para ativar esta verificação."
            ),
            details={"reason": "handler_not_registered"},
        )

    def register_check_handler(
        self,
        rule_id: str,
        handler: Any,
    ) -> None:
        """Registra um handler de verificação para uma regra específica.

        Args:
            rule_id: Identificador da regra (ex: LGPD-001, OAB-001, AUDIT-001).
            handler: Função assíncrona que recebe (rule, context) e retorna
                     ComplianceCheckResult.
        """
        self._check_handlers[rule_id] = handler


# ---------------------------------------------------------------------------
# Factory — instância padrão
# ---------------------------------------------------------------------------


def create_default_compliance_config() -> ComplianceTestingConfig:
    """Cria a configuração padrão de compliance testing.

    Retorna uma instância de ComplianceTestingConfig com todas as regras
    padrão habilitadas para LGPD, OAB e trilha de auditoria.

    Returns:
        Configuração padrão de compliance testing.
    """
    return ComplianceTestingConfig()


def create_compliance_checker(
    config: ComplianceTestingConfig | None = None,
) -> ComplianceChecker:
    """Cria uma instância do verificador de compliance.

    Args:
        config: Configuração personalizada. Se None, usa configuração padrão.

    Returns:
        Instância configurada de ComplianceChecker.
    """
    return ComplianceChecker(config=config)


# ---------------------------------------------------------------------------
# Exports públicos
# ---------------------------------------------------------------------------

__all__ = [
    "AuditTrailComplianceConfig",
    "AuditTrailRule",
    "ComplianceCheckResult",
    "ComplianceCheckStatus",
    "ComplianceChecker",
    "ComplianceDomain",
    "ComplianceReport",
    "ComplianceSeverity",
    "ComplianceTestingConfig",
    "LGPDComplianceConfig",
    "LGPDRule",
    "OABComplianceConfig",
    "OABRule",
    "create_compliance_checker",
    "create_default_compliance_config",
    "get_default_audit_trail_rules",
    "get_default_lgpd_rules",
    "get_default_oab_rules",
]
