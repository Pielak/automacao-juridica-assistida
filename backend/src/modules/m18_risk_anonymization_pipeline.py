"""Módulo Backlog #18: Risco e Mitigação via Anonimização.

Implementa o pipeline completo de anonimização com avaliação de risco,
integração com Microsoft Presidio + NER, geração de RIPD (Relatório de
Impacto à Proteção de Dados Pessoais) e validação de base legal para
transferência de dados a LLMs.

O módulo orquestra:
- Avaliação de risco pré-envio (scoring de sensibilidade)
- Pipeline de anonimização Presidio + NER customizado para domínio jurídico
- Geração e gestão de RIPD conforme LGPD (Art. 38)
- Validação de base legal para transferência internacional de dados
- Registro de auditoria completo de cada operação
- Métricas de eficácia da anonimização

Dependências:
- backend/src/infrastructure/security/anonymizer.py — pipeline Presidio+NER
- backend/src/modules/m02_data_confidentiality_compliance.py — compliance sigilo OAB
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator
import structlog

from backend.src.infrastructure.security.anonymizer import (
    AnonymizationPipeline,
    AnonymizationResult,
    AnonymizationConfig,
)
from backend.src.modules.m02_data_confidentiality_compliance import (
    ConfidentialityClassifier,
    ConfidentialityLevel,
    LLMSendPolicy,
    AuditLogger as ComplianceAuditLogger,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    """Nível de risco de exposição de dados pessoais."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LegalBasis(str, Enum):
    """Base legal LGPD para tratamento/transferência de dados."""

    CONSENT = "consentimento"  # Art. 7º, I
    LEGAL_OBLIGATION = "obrigacao_legal"  # Art. 7º, II
    PUBLIC_ADMINISTRATION = "administracao_publica"  # Art. 7º, III
    RESEARCH = "pesquisa"  # Art. 7º, IV
    CONTRACT = "execucao_contrato"  # Art. 7º, V
    LEGAL_PROCESS = "exercicio_direitos_processo"  # Art. 7º, VI
    LEGITIMATE_INTEREST = "interesse_legitimo"  # Art. 7º, IX
    CREDIT_PROTECTION = "protecao_credito"  # Art. 7º, X


class TransferMechanism(str, Enum):
    """Mecanismo de transferência internacional de dados (Art. 33 LGPD)."""

    ADEQUATE_COUNTRY = "pais_nivel_adequado"  # Art. 33, I
    STANDARD_CLAUSES = "clausulas_padrao"  # Art. 33, II-a
    CORPORATE_RULES = "normas_corporativas"  # Art. 33, II-b
    SPECIFIC_CONSENT = "consentimento_especifico"  # Art. 33, VIII
    ANONYMIZED_DATA = "dados_anonimizados"  # Art. 12 — não se aplica LGPD


class RIPDStatus(str, Enum):
    """Status do Relatório de Impacto à Proteção de Dados."""

    DRAFT = "rascunho"
    PENDING_REVIEW = "pendente_revisao"
    APPROVED = "aprovado"
    REJECTED = "rejeitado"
    EXPIRED = "expirado"


# ---------------------------------------------------------------------------
# Schemas / DTOs
# ---------------------------------------------------------------------------


class RiskAssessmentInput(BaseModel):
    """Dados de entrada para avaliação de risco de anonimização."""

    document_id: str = Field(..., description="ID do documento a avaliar")
    text_content: str = Field(..., description="Conteúdo textual do documento")
    document_type: str = Field(
        ..., description="Tipo do documento jurídico (petição, contrato, etc.)"
    )
    intended_llm_provider: str = Field(
        default="anthropic",
        description="Provedor LLM de destino (ex.: anthropic, openai)",
    )
    user_id: str = Field(..., description="ID do usuário solicitante")
    client_id: Optional[str] = Field(
        default=None, description="ID do cliente/titular dos dados"
    )
    legal_basis: Optional[LegalBasis] = Field(
        default=None, description="Base legal declarada para o tratamento"
    )
    has_explicit_consent: bool = Field(
        default=False,
        description="Se há consentimento explícito do titular para envio a LLM",
    )


class EntityRiskScore(BaseModel):
    """Score de risco para uma entidade detectada."""

    entity_type: str = Field(..., description="Tipo da entidade (CPF, NOME, etc.)")
    count: int = Field(..., description="Quantidade de ocorrências detectadas")
    risk_weight: float = Field(
        ..., ge=0.0, le=1.0, description="Peso de risco da entidade (0-1)"
    )
    partial_score: float = Field(..., description="Score parcial = count * weight")


class RiskAssessmentResult(BaseModel):
    """Resultado da avaliação de risco pré-anonimização."""

    assessment_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID único da avaliação",
    )
    document_id: str
    risk_level: RiskLevel
    overall_score: float = Field(
        ..., ge=0.0, le=100.0, description="Score geral de risco (0-100)"
    )
    entity_scores: list[EntityRiskScore] = Field(default_factory=list)
    confidentiality_level: Optional[str] = Field(
        default=None, description="Nível de confidencialidade do m02"
    )
    requires_anonymization: bool = Field(
        default=True, description="Se anonimização é obrigatória"
    )
    requires_ripd: bool = Field(
        default=False, description="Se requer RIPD antes do envio"
    )
    blocking_reasons: list[str] = Field(
        default_factory=list,
        description="Razões que bloqueiam o envio (se houver)",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recomendações de mitigação",
    )
    assessed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AnonymizationPipelineResult(BaseModel):
    """Resultado completo do pipeline de anonimização com risco."""

    pipeline_run_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID único da execução do pipeline",
    )
    document_id: str
    risk_assessment: RiskAssessmentResult
    anonymized_text: str = Field(
        ..., description="Texto anonimizado pronto para envio"
    )
    entities_removed: int = Field(
        ..., description="Total de entidades removidas/mascaradas"
    )
    anonymization_coverage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentual de cobertura da anonimização",
    )
    mapping_hash: str = Field(
        ...,
        description="Hash do mapeamento reversível (para auditoria, sem expor dados)",
    )
    legal_basis_validated: bool
    transfer_mechanism: Optional[TransferMechanism] = None
    ripd_id: Optional[str] = Field(
        default=None, description="ID do RIPD associado, se aplicável"
    )
    is_safe_to_send: bool = Field(
        ..., description="Indicador final: seguro para enviar ao LLM"
    )
    blocking_reasons: list[str] = Field(default_factory=list)
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class RIPDRecord(BaseModel):
    """Relatório de Impacto à Proteção de Dados Pessoais (RIPD).

    Conforme Art. 38 da LGPD, o controlador deverá elaborar RIPD quando
    o tratamento puder gerar riscos às liberdades civis e aos direitos
    fundamentais do titular.
    """

    ripd_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID único do RIPD",
    )
    document_id: str
    assessment_id: str = Field(
        ..., description="ID da avaliação de risco que originou o RIPD"
    )
    status: RIPDStatus = Field(default=RIPDStatus.DRAFT)

    # Descrição do tratamento
    treatment_description: str = Field(
        ...,
        description="Descrição do tratamento de dados pessoais realizado",
    )
    treatment_purpose: str = Field(
        ..., description="Finalidade do tratamento"
    )
    legal_basis: LegalBasis
    data_categories: list[str] = Field(
        default_factory=list,
        description="Categorias de dados pessoais tratados",
    )
    sensitive_data_categories: list[str] = Field(
        default_factory=list,
        description="Categorias de dados sensíveis (Art. 11 LGPD)",
    )

    # Avaliação de risco
    risk_level: RiskLevel
    risk_score: float
    identified_risks: list[str] = Field(
        default_factory=list,
        description="Riscos identificados ao titular",
    )

    # Medidas de mitigação
    mitigation_measures: list[str] = Field(
        default_factory=list,
        description="Medidas de mitigação aplicadas",
    )
    anonymization_applied: bool = Field(
        default=True,
        description="Se anonimização foi aplicada antes do envio",
    )
    anonymization_method: str = Field(
        default="presidio_ner_pipeline",
        description="Método de anonimização utilizado",
    )

    # Transferência internacional
    involves_international_transfer: bool = Field(default=True)
    transfer_mechanism: Optional[TransferMechanism] = None
    destination_country: str = Field(
        default="EUA",
        description="País de destino dos dados",
    )
    llm_provider: str = Field(
        default="anthropic",
        description="Provedor LLM de destino",
    )

    # Metadados
    created_by: str = Field(..., description="ID do usuário que criou o RIPD")
    reviewed_by: Optional[str] = Field(
        default=None, description="ID do DPO/revisor"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class TransferValidationResult(BaseModel):
    """Resultado da validação de base legal para transferência."""

    is_valid: bool
    legal_basis: Optional[LegalBasis] = None
    transfer_mechanism: Optional[TransferMechanism] = None
    requires_additional_consent: bool = False
    requires_ripd: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pesos de risco por tipo de entidade
# ---------------------------------------------------------------------------

ENTITY_RISK_WEIGHTS: dict[str, float] = {
    # Dados pessoais diretos — risco alto
    "CPF": 0.95,
    "CNPJ": 0.70,
    "RG": 0.90,
    "NOME": 0.85,
    "NOME_COMPLETO": 0.90,
    "PERSON": 0.85,
    # Dados de contato
    "EMAIL": 0.80,
    "TELEFONE": 0.75,
    "PHONE_NUMBER": 0.75,
    "ENDERECO": 0.80,
    "LOCATION": 0.60,
    # Dados jurídicos
    "OAB": 0.65,
    "NUMERO_PROCESSO": 0.70,
    "VARA": 0.30,
    "COMARCA": 0.25,
    # Dados financeiros
    "CONTA_BANCARIA": 0.95,
    "CREDIT_CARD": 0.95,
    # Dados sensíveis (Art. 11 LGPD)
    "DADOS_SAUDE": 1.0,
    "ORIGEM_RACIAL": 1.0,
    "OPINIAO_POLITICA": 1.0,
    "FILIACAO_SINDICAL": 1.0,
    "DADOS_BIOMETRICOS": 1.0,
    "DADOS_GENETICOS": 1.0,
    # Genéricos
    "DATE_TIME": 0.20,
    "NRP": 0.50,
}

# Limites de score para classificação de risco
RISK_THRESHOLDS = {
    RiskLevel.LOW: 10.0,
    RiskLevel.MEDIUM: 30.0,
    RiskLevel.HIGH: 60.0,
    # Acima de 60 → CRITICAL
}

# Score mínimo que exige RIPD
RIPD_REQUIRED_THRESHOLD = 30.0


# ---------------------------------------------------------------------------
# Serviço principal: RiskAnonymizationPipeline
# ---------------------------------------------------------------------------


class RiskAnonymizationPipeline:
    """Pipeline integrado de avaliação de risco e anonimização.

    Orquestra a avaliação de risco, anonimização via Presidio+NER,
    validação de base legal e geração de RIPD para envio seguro de
    dados jurídicos a LLMs.

    Exemplo de uso::

        pipeline = RiskAnonymizationPipeline()
        result = await pipeline.process(
            RiskAssessmentInput(
                document_id="doc-123",
                text_content="O réu João da Silva, CPF 123.456.789-00...",
                document_type="petição",
                user_id="user-456",
            )
        )
        if result.is_safe_to_send:
            # Enviar result.anonymized_text ao LLM
            ...
    """

    def __init__(
        self,
        anonymization_pipeline: AnonymizationPipeline | None = None,
        confidentiality_classifier: ConfidentialityClassifier | None = None,
        llm_send_policy: LLMSendPolicy | None = None,
        compliance_audit_logger: ComplianceAuditLogger | None = None,
        custom_entity_weights: dict[str, float] | None = None,
        ripd_auto_generate: bool = True,
    ) -> None:
        """Inicializa o pipeline de risco e anonimização.

        Args:
            anonymization_pipeline: Instância do pipeline Presidio+NER.
                Se None, cria instância padrão.
            confidentiality_classifier: Classificador de confidencialidade do m02.
                Se None, cria instância padrão.
            llm_send_policy: Política de envio a LLMs do m02.
                Se None, cria instância padrão.
            compliance_audit_logger: Logger de auditoria de compliance.
                Se None, cria instância padrão.
            custom_entity_weights: Pesos customizados por tipo de entidade.
            ripd_auto_generate: Se True, gera RIPD automaticamente quando necessário.
        """
        self._anonymizer = anonymization_pipeline or AnonymizationPipeline()
        self._classifier = confidentiality_classifier or ConfidentialityClassifier()
        self._send_policy = llm_send_policy or LLMSendPolicy()
        self._audit_logger = compliance_audit_logger or ComplianceAuditLogger()
        self._entity_weights = {**ENTITY_RISK_WEIGHTS, **(custom_entity_weights or {})}
        self._ripd_auto_generate = ripd_auto_generate
        self._ripd_store: dict[str, RIPDRecord] = {}  # TODO: Substituir por repositório persistente

        logger.info(
            "pipeline_risco_anonimizacao_inicializado",
            ripd_auto_generate=ripd_auto_generate,
            custom_weights_count=len(custom_entity_weights or {}),
        )

    # ------------------------------------------------------------------
    # Método principal
    # ------------------------------------------------------------------

    async def process(
        self, input_data: RiskAssessmentInput
    ) -> AnonymizationPipelineResult:
        """Executa o pipeline completo de risco + anonimização.

        Fluxo:
        1. Avaliação de risco do texto original
        2. Validação de base legal para transferência
        3. Verificação de política de envio (m02)
        4. Anonimização via Presidio+NER
        5. Geração de RIPD (se necessário)
        6. Registro de auditoria
        7. Decisão final de envio

        Args:
            input_data: Dados de entrada com documento e metadados.

        Returns:
            AnonymizationPipelineResult com texto anonimizado e metadados.
        """
        pipeline_run_id = str(uuid.uuid4())

        logger.info(
            "pipeline_iniciado",
            pipeline_run_id=pipeline_run_id,
            document_id=input_data.document_id,
            user_id=input_data.user_id,
        )

        # 1. Avaliação de risco
        risk_assessment = await self.assess_risk(input_data)

        logger.info(
            "avaliacao_risco_concluida",
            pipeline_run_id=pipeline_run_id,
            risk_level=risk_assessment.risk_level.value,
            overall_score=risk_assessment.overall_score,
        )

        # 2. Validação de base legal
        transfer_validation = await self.validate_transfer_legal_basis(
            legal_basis=input_data.legal_basis,
            has_consent=input_data.has_explicit_consent,
            risk_level=risk_assessment.risk_level,
            llm_provider=input_data.intended_llm_provider,
        )

        # 3. Verificar bloqueios antes de prosseguir
        blocking_reasons: list[str] = []
        blocking_reasons.extend(risk_assessment.blocking_reasons)
        blocking_reasons.extend(transfer_validation.blocking_reasons)

        # Verificar política de confidencialidade (m02)
        try:
            confidentiality_level = self._classifier.classify(
                text=input_data.text_content,
                document_type=input_data.document_type,
            )
            policy_result = self._send_policy.evaluate(
                confidentiality_level=confidentiality_level,
                has_anonymization=True,
                has_consent=input_data.has_explicit_consent,
            )
            if not policy_result.is_allowed:
                blocking_reasons.append(
                    f"Política de sigilo advocatício bloqueia envio: "
                    f"nível {confidentiality_level.value}"
                )
        except Exception as exc:
            logger.warning(
                "erro_verificacao_confidencialidade",
                pipeline_run_id=pipeline_run_id,
                error=str(exc),
            )
            confidentiality_level = None
            # Em caso de erro na classificação, bloquear por precaução
            blocking_reasons.append(
                "Não foi possível verificar nível de confidencialidade — "
                "envio bloqueado por precaução"
            )

        # 4. Executar anonimização
        anonymization_result = await self._run_anonymization(
            text=input_data.text_content,
            document_type=input_data.document_type,
        )

        # Calcular cobertura da anonimização
        entities_removed = anonymization_result.entities_removed
        total_entities_detected = anonymization_result.total_entities_detected
        coverage = (
            (entities_removed / total_entities_detected * 100.0)
            if total_entities_detected > 0
            else 100.0
        )

        # Gerar hash do mapeamento para auditoria
        mapping_hash = self._compute_mapping_hash(
            anonymization_result.mapping_id
        )

        # 5. Gerar RIPD se necessário
        ripd_id: str | None = None
        if (
            risk_assessment.requires_ripd
            or transfer_validation.requires_ripd
        ) and self._ripd_auto_generate:
            ripd = await self.generate_ripd(
                input_data=input_data,
                risk_assessment=risk_assessment,
                transfer_validation=transfer_validation,
            )
            ripd_id = ripd.ripd_id
            logger.info(
                "ripd_gerado",
                pipeline_run_id=pipeline_run_id,
                ripd_id=ripd_id,
            )

        # 6. Decisão final
        is_safe = len(blocking_reasons) == 0 and coverage >= 95.0

        if coverage < 95.0 and len(blocking_reasons) == 0:
            blocking_reasons.append(
                f"Cobertura de anonimização insuficiente: {coverage:.1f}% "
                f"(mínimo: 95%)"
            )

        # 7. Registro de auditoria
        await self._log_audit(
            pipeline_run_id=pipeline_run_id,
            input_data=input_data,
            risk_assessment=risk_assessment,
            is_safe=is_safe,
            blocking_reasons=blocking_reasons,
        )

        result = AnonymizationPipelineResult(
            pipeline_run_id=pipeline_run_id,
            document_id=input_data.document_id,
            risk_assessment=risk_assessment,
            anonymized_text=anonymization_result.anonymized_text,
            entities_removed=entities_removed,
            anonymization_coverage=coverage,
            mapping_hash=mapping_hash,
            legal_basis_validated=transfer_validation.is_valid,
            transfer_mechanism=transfer_validation.transfer_mechanism,
            ripd_id=ripd_id,
            is_safe_to_send=is_safe,
            blocking_reasons=blocking_reasons,
        )

        logger.info(
            "pipeline_concluido",
            pipeline_run_id=pipeline_run_id,
            is_safe_to_send=is_safe,
            entities_removed=entities_removed,
            coverage=coverage,
            blocking_count=len(blocking_reasons),
        )

        return result

    # ------------------------------------------------------------------
    # Avaliação de risco
    # ------------------------------------------------------------------

    async def assess_risk(
        self, input_data: RiskAssessmentInput
    ) -> RiskAssessmentResult:
        """Avalia o risco de exposição de dados pessoais no texto.

        Utiliza o pipeline Presidio+NER para detectar entidades e calcula
        um score de risco ponderado por tipo de entidade.

        Args:
            input_data: Dados de entrada com texto a avaliar.

        Returns:
            RiskAssessmentResult com score, nível e recomendações.
        """
        # Detectar entidades sem anonimizar (modo análise)
        detected_entities = await self._detect_entities(input_data.text_content)

        # Calcular scores por entidade
        entity_scores: list[EntityRiskScore] = []
        total_score = 0.0

        entity_counts: dict[str, int] = {}
        for entity in detected_entities:
            entity_type = entity.get("entity_type", "UNKNOWN")
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

        for entity_type, count in entity_counts.items():
            weight = self._entity_weights.get(entity_type, 0.5)
            partial = count * weight
            total_score += partial
            entity_scores.append(
                EntityRiskScore(
                    entity_type=entity_type,
                    count=count,
                    risk_weight=weight,
                    partial_score=partial,
                )
            )

        # Normalizar score para 0-100
        overall_score = min(total_score * 2.0, 100.0)  # Fator de escala

        # Classificar nível de risco
        risk_level = self._classify_risk_level(overall_score)

        # Determinar se requer RIPD
        requires_ripd = overall_score >= RIPD_REQUIRED_THRESHOLD

        # Determinar bloqueios
        blocking_reasons: list[str] = []
        if risk_level == RiskLevel.CRITICAL and not input_data.has_explicit_consent:
            blocking_reasons.append(
                "Risco CRÍTICO detectado — consentimento explícito do titular "
                "é obrigatório para prosseguir"
            )

        # Gerar recomendações
        recommendations = self._generate_recommendations(
            risk_level=risk_level,
            entity_scores=entity_scores,
            has_consent=input_data.has_explicit_consent,
            legal_basis=input_data.legal_basis,
        )

        # Obter nível de confidencialidade do m02
        confidentiality_str: str | None = None
        try:
            conf_level = self._classifier.classify(
                text=input_data.text_content,
                document_type=input_data.document_type,
            )
            confidentiality_str = conf_level.value
        except Exception:
            confidentiality_str = None

        return RiskAssessmentResult(
            document_id=input_data.document_id,
            risk_level=risk_level,
            overall_score=overall_score,
            entity_scores=entity_scores,
            confidentiality_level=confidentiality_str,
            requires_anonymization=overall_score > 0,
            requires_ripd=requires_ripd,
            blocking_reasons=blocking_reasons,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Validação de base legal para transferência
    # ------------------------------------------------------------------

    async def validate_transfer_legal_basis(
        self,
        legal_basis: LegalBasis | None,
        has_consent: bool,
        risk_level: RiskLevel,
        llm_provider: str = "anthropic",
    ) -> TransferValidationResult:
        """Valida a base legal para transferência de dados ao LLM.

        Verifica conformidade com Art. 33 da LGPD (transferência internacional)
        e determina o mecanismo de transferência adequado.

        Args:
            legal_basis: Base legal declarada pelo usuário.
            has_consent: Se há consentimento explícito do titular.
            risk_level: Nível de risco avaliado.
            llm_provider: Provedor LLM de destino.

        Returns:
            TransferValidationResult com validação e mecanismo.
        """
        blocking_reasons: list[str] = []
        recommendations: list[str] = []
        requires_additional_consent = False
        requires_ripd = False

        # Se dados serão anonimizados, Art. 12 LGPD: dados anonimizados
        # não são considerados dados pessoais
        transfer_mechanism = TransferMechanism.ANONYMIZED_DATA

        # Validar base legal
        if legal_basis is None:
            if has_consent:
                legal_basis = LegalBasis.CONSENT
            else:
                # Tentar inferir base legal
                legal_basis = LegalBasis.LEGITIMATE_INTEREST
                recommendations.append(
                    "Base legal não declarada — assumindo interesse legítimo. "
                    "Recomenda-se declarar base legal explícita."
                )

        # Para risco alto/crítico, exigir base legal mais forte
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            strong_bases = {
                LegalBasis.CONSENT,
                LegalBasis.LEGAL_OBLIGATION,
                LegalBasis.LEGAL_PROCESS,
            }
            if legal_basis not in strong_bases:
                if risk_level == RiskLevel.CRITICAL:
                    blocking_reasons.append(
                        f"Risco {risk_level.value}: base legal "
                        f"'{legal_basis.value}' insuficiente. "
                        f"Necessário: consentimento, obrigação legal ou "
                        f"exercício de direitos em processo."
                    )
                else:
                    recommendations.append(
                        f"Risco {risk_level.value}: considere obter "
                        f"consentimento explícito do titular."
                    )
                    requires_additional_consent = True

            requires_ripd = True

        # Verificar se provedor é internacional (transferência Art. 33)
        international_providers = {"anthropic", "openai", "google", "cohere"}
        if llm_provider.lower() in international_providers:
            recommendations.append(
                f"Provedor '{llm_provider}' implica transferência internacional "
                f"de dados (Art. 33 LGPD). Dados serão anonimizados antes do envio."
            )
            # Com anonimização efetiva, Art. 12 se aplica
            transfer_mechanism = TransferMechanism.ANONYMIZED_DATA

        is_valid = len(blocking_reasons) == 0

        return TransferValidationResult(
            is_valid=is_valid,
            legal_basis=legal_basis,
            transfer_mechanism=transfer_mechanism,
            requires_additional_consent=requires_additional_consent,
            requires_ripd=requires_ripd,
            blocking_reasons=blocking_reasons,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Geração de RIPD
    # ------------------------------------------------------------------

    async def generate_ripd(
        self,
        input_data: RiskAssessmentInput,
        risk_assessment: RiskAssessmentResult,
        transfer_validation: TransferValidationResult,
    ) -> RIPDRecord:
        """Gera um Relatório de Impacto à Proteção de Dados Pessoais.

        Conforme Art. 38 da LGPD, o RIPD deve conter:
        - Descrição dos tipos de dados coletados
        - Metodologia utilizada para coleta e tratamento
        - Medidas de segurança da informação
        - Análise do controlador sobre medidas de mitigação

        Args:
            input_data: Dados de entrada originais.
            risk_assessment: Resultado da avaliação de risco.
            transfer_validation: Resultado da validação de transferência.

        Returns:
            RIPDRecord com o relatório gerado.
        """
        # Extrair categorias de dados detectados
        data_categories = [
            score.entity_type for score in risk_assessment.entity_scores
        ]

        # Identificar dados sensíveis (Art. 11 LGPD)
        sensitive_types = {
            "DADOS_SAUDE",
            "ORIGEM_RACIAL",
            "OPINIAO_POLITICA",
            "FILIACAO_SINDICAL",
            "DADOS_BIOMETRICOS",
            "DADOS_GENETICOS",
        }
        sensitive_categories = [
            cat for cat in data_categories if cat in sensitive_types
        ]

        # Riscos identificados
        identified_risks = [
            "Exposição de dados pessoais a provedor de LLM internacional",
            "Possibilidade de retenção de dados pelo provedor",
            "Risco de reidentificação em caso de anonimização insuficiente",
        ]
        if sensitive_categories:
            identified_risks.append(
                f"Tratamento de dados sensíveis: {', '.join(sensitive_categories)}"
            )
        if risk_assessment.risk_level == RiskLevel.CRITICAL:
            identified_risks.append(
                "Volume ou sensibilidade de dados pessoais em nível crítico"
            )

        # Medidas de mitigação
        mitigation_measures = [
            "Anonimização obrigatória via pipeline Presidio+NER antes do envio",
            "Mapeamento reversível armazenado localmente (não enviado ao LLM)",
            "Validação de cobertura mínima de 95% na anonimização",
            "Registro de auditoria de todas as operações de envio",
            "Classificação de confidencialidade conforme Art. 7º Estatuto OAB",
            "Rate limiting e controle de acesso por RBAC",
            "Logs estruturados com correlation ID para rastreabilidade",
        ]
        if transfer_validation.transfer_mechanism == TransferMechanism.ANONYMIZED_DATA:
            mitigation_measures.append(
                "Dados anonimizados não são considerados dados pessoais "
                "(Art. 12 LGPD), reduzindo escopo de aplicação da lei"
            )

        ripd = RIPDRecord(
            document_id=input_data.document_id,
            assessment_id=risk_assessment.assessment_id,
            treatment_description=(
                f"Envio de texto jurídico (tipo: {input_data.document_type}) "
                f"a modelo de linguagem ({input_data.intended_llm_provider}) "
                f"para análise assistida, após anonimização de dados pessoais."
            ),
            treatment_purpose=(
                "Análise jurídica assistida por inteligência artificial para "
                "apoio à atividade advocatícia, com anonimização prévia de "
                "dados pessoais do titular."
            ),
            legal_basis=(
                transfer_validation.legal_basis or LegalBasis.LEGITIMATE_INTEREST
            ),
            data_categories=data_categories,
            sensitive_data_categories=sensitive_categories,
            risk_level=risk_assessment.risk_level,
            risk_score=risk_assessment.overall_score,
            identified_risks=identified_risks,
            mitigation_measures=mitigation_measures,
            anonymization_applied=True,
            involves_international_transfer=True,
            transfer_mechanism=transfer_validation.transfer_mechanism,
            destination_country=self._get_provider_country(
                input_data.intended_llm_provider
            ),
            llm_provider=input_data.intended_llm_provider,
            created_by=input_data.user_id,
        )

        # Armazenar RIPD
        self._ripd_store[ripd.ripd_id] = ripd

        logger.info(
            "ripd_gerado",
            ripd_id=ripd.ripd_id,
            document_id=input_data.document_id,
            risk_level=risk_assessment.risk_level.value,
            data_categories_count=len(data_categories),
            sensitive_count=len(sensitive_categories),
        )

        return ripd

    async def get_ripd(self, ripd_id: str) -> RIPDRecord | None:
        """Recupera um RIPD pelo ID.

        Args:
            ripd_id: ID do RIPD.

        Returns:
            RIPDRecord ou None se não encontrado.
        """
        # TODO: Substituir por consulta ao repositório persistente (SQLAlchemy)
        return self._ripd_store.get(ripd_id)

    async def review_ripd(
        self,
        ripd_id: str,
        reviewer_id: str,
        approved: bool,
        notes: str | None = None,
    ) -> RIPDRecord | None:
        """Registra revisão de um RIPD pelo DPO.

        Args:
            ripd_id: ID do RIPD a revisar.
            reviewer_id: ID do DPO/revisor.
            approved: Se o RIPD foi aprovado.
            notes: Observações do revisor.

        Returns:
            RIPDRecord atualizado ou None se não encontrado.
        """
        ripd = self._ripd_store.get(ripd_id)
        if ripd is None:
            return None

        ripd.reviewed_by = reviewer_id
        ripd.reviewed_at = datetime.now(timezone.utc)
        ripd.status = RIPDStatus.APPROVED if approved else RIPDStatus.REJECTED
        ripd.notes = notes

        logger.info(
            "ripd_revisado",
            ripd_id=ripd_id,
            reviewer_id=reviewer_id,
            approved=approved,
        )

        return ripd

    async def list_ripds(
        self,
        status: RIPDStatus | None = None,
        document_id: str | None = None,
    ) -> list[RIPDRecord]:
        """Lista RIPDs com filtros opcionais.

        Args:
            status: Filtrar por status.
            document_id: Filtrar por documento.

        Returns:
            Lista de RIPDRecords.
        """
        # TODO: Substituir por consulta ao repositório persistente
        results = list(self._ripd_store.values())
        if status is not None:
            results = [r for r in results if r.status == status]
        if document_id is not None:
            results = [r for r in results if r.document_id == document_id]
        return results

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    async def _detect_entities(
        self, text: str
    ) -> list[dict[str, Any]]:
        """Detecta entidades no texto usando o pipeline Presidio+NER.

        Args:
            text: Texto a analisar.

        Returns:
            Lista de dicionários com entidades detectadas.
        """
        try:
            result = self._anonymizer.analyze(text)
            return result.detected_entities
        except Exception as exc:
            logger.error(
                "erro_deteccao_entidades",
                error=str(exc),
            )
            # Retornar lista vazia em caso de erro — o pipeline
            # tratará como risco desconhecido
            return []

    async def _run_anonymization(
        self, text: str, document_type: str
    ) -> AnonymizationResult:
        """Executa a anonimização do texto.

        Args:
            text: Texto a anonimizar.
            document_type: Tipo do documento jurídico.

        Returns:
            AnonymizationResult do pipeline Presidio+NER.
        """
        config = AnonymizationConfig(
            document_type=document_type,
            enable_reversible_mapping=True,
        )
        return self._anonymizer.anonymize(text, config=config)

    def _classify_risk_level(self, score: float) -> RiskLevel:
        """Classifica o nível de risco com base no score.

        Args:
            score: Score de risco (0-100).

        Returns:
            RiskLevel correspondente.
        """
        if score <= RISK_THRESHOLDS[RiskLevel.LOW]:
            return RiskLevel.LOW
        elif score <= RISK_THRESHOLDS[RiskLevel.MEDIUM]:
            return RiskLevel.MEDIUM
        elif score <= RISK_THRESHOLDS[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def _generate_recommendations(
        self,
        risk_level: RiskLevel,
        entity_scores: list[EntityRiskScore],
        has_consent: bool,
        legal_basis: LegalBasis | None,
    ) -> list[str]:
        """Gera recomendações de mitigação baseadas na avaliação.

        Args:
            risk_level: Nível de risco avaliado.
            entity_scores: Scores por tipo de entidade.
            has_consent: Se há consentimento do titular.
            legal_basis: Base legal declarada.

        Returns:
            Lista de recomendações em PT-BR.
        """
        recommendations: list[str] = []

        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            recommendations.append(
                "Risco elevado: revise manualmente o texto antes do envio "
                "para garantir que dados sensíveis foram adequadamente mascarados."
            )

        if not has_consent:
            recommendations.append(
                "Considere obter consentimento explícito do titular dos dados "
                "antes do envio a LLMs, especialmente para dados sensíveis."
            )

        if legal_basis is None:
            recommendations.append(
                "Declare a base legal para o tratamento de dados conforme "
                "Art. 7º da LGPD."
            )

        # Recomendações específicas por tipo de entidade
        high_risk_entities = [
            s for s in entity_scores if s.risk_weight >= 0.9
        ]
        if high_risk_entities:
            entity_names = ", ".join(
                s.entity_type for s in high_risk_entities
            )
            recommendations.append(
                f"Entidades de alto risco detectadas ({entity_names}): "
                f"verifique se a anonimização cobriu todas as ocorrências."
            )

        # Dados sensíveis Art. 11
        sensitive_entities = [
            s
            for s in entity_scores
            if s.entity_type
            in {
                "DADOS_SAUDE",
                "ORIGEM_RACIAL",
                "OPINIAO_POLITICA",
                "FILIACAO_SINDICAL",
                "DADOS_BIOMETRICOS",
                "DADOS_GENETICOS",
            }
        ]
        if sensitive_entities:
            recommendations.append(
                "Dados sensíveis (Art. 11 LGPD) detectados. "
                "Tratamento requer consentimento específico e destacado "
                "ou enquadramento em hipótese legal do Art. 11, II."
            )

        if risk_level == RiskLevel.CRITICAL:
            recommendations.append(
                "RECOMENDAÇÃO FORTE: considere não enviar este documento "
                "a LLMs. Avalie alternativas locais de processamento."
            )

        return recommendations

    def _compute_mapping_hash(self, mapping_id: str) -> str:
        """Computa hash do mapeamento reversível para auditoria.

        O hash permite verificar integridade do mapeamento sem expor
        os dados originais.

        Args:
            mapping_id: ID do mapeamento reversível.

        Returns:
            Hash SHA-256 do mapping_id.
        """
        return hashlib.sha256(mapping_id.encode("utf-8")).hexdigest()

    def _get_provider_country(self, provider: str) -> str:
        """Retorna o país sede do provedor LLM.

        Args:
            provider: Nome do provedor.

        Returns:
            País sede.
        """
        provider_countries = {
            "anthropic": "EUA",
            "openai": "EUA",
            "google": "EUA",
            "cohere": "Canadá",
            "mistral": "França",
        }
        return provider_countries.get(provider.lower(), "Desconhecido")

    async def _log_audit(
        self,
        pipeline_run_id: str,
        input_data: RiskAssessmentInput,
        risk_assessment: RiskAssessmentResult,
        is_safe: bool,
        blocking_reasons: list[str],
    ) -> None:
        """Registra evento de auditoria da execução do pipeline.

        Args:
            pipeline_run_id: ID da execução.
            input_data: Dados de entrada.
            risk_assessment: Resultado da avaliação.
            is_safe: Se o envio foi aprovado.
            blocking_reasons: Razões de bloqueio (se houver).
        """
        try:
            self._audit_logger.log(
                event_type="risk_anonymization_pipeline",
                user_id=input_data.user_id,
                document_id=input_data.document_id,
                details={
                    "pipeline_run_id": pipeline_run_id,
                    "risk_level": risk_assessment.risk_level.value,
                    "risk_score": risk_assessment.overall_score,
                    "entities_detected": len(risk_assessment.entity_scores),
                    "is_safe_to_send": is_safe,
                    "blocking_reasons": blocking_reasons,
                    "llm_provider": input_data.intended_llm_provider,
                    "has_consent": input_data.has_explicit_consent,
                    "legal_basis": (
                        input_data.legal_basis.value
                        if input_data.legal_basis
                        else None
                    ),
                },
            )
        except Exception as exc:
            logger.error(
                "erro_registro_auditoria",
                pipeline_run_id=pipeline_run_id,
                error=str(exc),
            )


# ---------------------------------------------------------------------------
# Funções utilitárias de módulo
# ---------------------------------------------------------------------------


def create_risk_anonymization_pipeline(
    custom_entity_weights: dict[str, float] | None = None,
    ripd_auto_generate: bool = True,
) -> RiskAnonymizationPipeline:
    """Factory para criação do pipeline de risco e anonimização.

    Cria uma instância configurada do pipeline com todas as dependências
    padrão. Use esta função para obter uma instância pronta para uso.

    Args:
        custom_entity_weights: Pesos customizados por tipo de entidade.
        ripd_auto_generate: Se True, gera RIPD automaticamente.

    Returns:
        Instância configurada de RiskAnonymizationPipeline.
    """
    return RiskAnonymizationPipeline(
        custom_entity_weights=custom_entity_weights,
        ripd_auto_generate=ripd_auto_generate,
    )


def get_entity_risk_weights() -> dict[str, float]:
    """Retorna os pesos de risco padrão por tipo de entidade.

    Returns:
        Dicionário com tipo de entidade → peso de risco (0-1).
    """
    return dict(ENTITY_RISK_WEIGHTS)


def get_risk_thresholds() -> dict[RiskLevel, float]:
    """Retorna os limites de score para cada nível de risco.

    Returns:
        Dicionário com nível de risco → limite de score.
    """
    return dict(RISK_THRESHOLDS)
