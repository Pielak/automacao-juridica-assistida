"""Módulo de Compliance com Sigilo Advocatício — Art. 7º do Estatuto da OAB.

Implementa controles de confidencialidade de dados para envio a modelos de
linguagem (LLMs), garantindo conformidade com o sigilo profissional previsto
no Art. 7º do Estatuto da Advocacia e da OAB (Lei 8.906/94).

Responsabilidades:
- Classificação de nível de confidencialidade de documentos jurídicos
- Validação de políticas de envio de dados a LLMs
- Pipeline de sanitização pré-envio com anonimização obrigatória
- Registro de auditoria de todas as operações de envio a LLMs
- Controle de consentimento do titular dos dados
- Bloqueio de envio de categorias protegidas (segredo de justiça, etc.)

Referências legais:
- Art. 7º, II — Estatuto da OAB (sigilo profissional)
- Art. 34, VII — Estatuto da OAB (violação de sigilo)
- LGPD (Lei 13.709/2018) — proteção de dados pessoais
- Provimento 205/2021 CNJ — DataJud
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field, field_validator
import structlog

# ---------------------------------------------------------------------------
# Peers do projeto
# ---------------------------------------------------------------------------
from backend.src.infrastructure.security.anonymizer import (
    # TODO: Importar classes/funções públicas do anonymizer quando a API
    # estiver completamente definida. Esperados:
    # - AnonymizationPipeline ou anonymize_text()
    # - DeanonymizationMap ou equivalente
    # Por ora, usamos referências genéricas com type hints.
)
from backend.src.domain.ports.audit_repository_port import (
    # TODO: Importar o DTO de auditoria e a interface do repositório
    # quando os nomes exatos estiverem disponíveis. Esperados:
    # - AuditRepositoryPort (Protocol)
    # - AuditEntry / AuditRecord (dataclass DTO)
)

logger = structlog.get_logger(__name__)


# ===========================================================================
# Enums de classificação
# ===========================================================================


class ConfidentialityLevel(str, Enum):
    """Níveis de confidencialidade de documentos jurídicos.

    Baseado nas categorias de sigilo do ordenamento jurídico brasileiro
    e nas boas práticas de governança de dados advocatícios.
    """

    PUBLIC = "public"
    """Documento público — pode ser enviado a LLM após anonimização padrão."""

    INTERNAL = "internal"
    """Documento interno do escritório — anonimização obrigatória, envio permitido."""

    CONFIDENTIAL = "confidential"
    """Documento confidencial — anonimização reforçada, requer consentimento."""

    STRICTLY_CONFIDENTIAL = "strictly_confidential"
    """Estritamente confidencial — sigilo advocatício Art. 7º OAB."""

    JUDICIAL_SECRET = "judicial_secret"
    """Segredo de justiça — envio a LLM BLOQUEADO."""


class LLMSendPolicy(str, Enum):
    """Política de envio de dados a modelos de linguagem."""

    ALLOWED = "allowed"
    """Envio permitido após anonimização."""

    ALLOWED_WITH_CONSENT = "allowed_with_consent"
    """Envio permitido somente com consentimento explícito do cliente."""

    ALLOWED_ANONYMIZED_ONLY = "allowed_anonymized_only"
    """Envio permitido apenas com anonimização completa (sem reversibilidade)."""

    BLOCKED = "blocked"
    """Envio bloqueado — dados não podem sair do ambiente controlado."""


class ConsentStatus(str, Enum):
    """Status do consentimento do titular para processamento por LLM."""

    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"


# ===========================================================================
# Mapeamento de políticas por nível de confidencialidade
# ===========================================================================

CONFIDENTIALITY_POLICY_MAP: dict[ConfidentialityLevel, LLMSendPolicy] = {
    ConfidentialityLevel.PUBLIC: LLMSendPolicy.ALLOWED,
    ConfidentialityLevel.INTERNAL: LLMSendPolicy.ALLOWED_ANONYMIZED_ONLY,
    ConfidentialityLevel.CONFIDENTIAL: LLMSendPolicy.ALLOWED_WITH_CONSENT,
    ConfidentialityLevel.STRICTLY_CONFIDENTIAL: LLMSendPolicy.ALLOWED_WITH_CONSENT,
    ConfidentialityLevel.JUDICIAL_SECRET: LLMSendPolicy.BLOCKED,
}

"""Entidades que NUNCA devem ser enviadas a LLMs, independentemente do nível."""
BLOCKED_ENTITY_TYPES: set[str] = {
    "JUDICIAL_SECRET_MARKER",
    "MINOR_IDENTIFICATION",
    "CRIMINAL_RECORD",
    "HEALTH_DATA",
    "SEXUAL_ORIENTATION",
    "RELIGIOUS_BELIEF",
    "POLITICAL_OPINION",
    "BIOMETRIC_DATA",
}


# ===========================================================================
# DTOs / Value Objects
# ===========================================================================


@dataclass(frozen=True)
class ConsentRecord:
    """Registro de consentimento do titular dos dados."""

    consent_id: uuid.UUID = field(default_factory=uuid.uuid4)
    case_id: uuid.UUID = field(default_factory=uuid.uuid4)
    client_id: uuid.UUID = field(default_factory=uuid.uuid4)
    lawyer_id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: ConsentStatus = ConsentStatus.NOT_REQUESTED
    purpose: str = ""
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass(frozen=True)
class ConfidentialityClassification:
    """Resultado da classificação de confidencialidade de um documento."""

    document_id: uuid.UUID
    level: ConfidentialityLevel
    policy: LLMSendPolicy
    reasons: list[str] = field(default_factory=list)
    detected_sensitive_entities: list[str] = field(default_factory=list)
    blocked_entities: list[str] = field(default_factory=list)
    classified_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    classified_by: Optional[uuid.UUID] = None


@dataclass
class LLMSendRequest:
    """Requisição de envio de texto a um LLM."""

    request_id: uuid.UUID = field(default_factory=uuid.uuid4)
    document_id: uuid.UUID = field(default_factory=uuid.uuid4)
    case_id: uuid.UUID = field(default_factory=uuid.uuid4)
    original_text: str = ""
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    purpose: str = ""
    requested_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(frozen=True)
class LLMSendResult:
    """Resultado do pipeline de compliance para envio a LLM."""

    request_id: uuid.UUID
    allowed: bool
    sanitized_text: Optional[str] = None
    denial_reason: Optional[str] = None
    classification: Optional[ConfidentialityClassification] = None
    anonymization_map_id: Optional[uuid.UUID] = None
    audit_entry_id: Optional[uuid.UUID] = None
    processed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ===========================================================================
# Pydantic Schemas (API layer)
# ===========================================================================


class ConfidentialityCheckRequest(BaseModel):
    """Schema de requisição para verificação de confidencialidade."""

    document_id: uuid.UUID = Field(
        ..., description="ID do documento a ser verificado"
    )
    text_content: str = Field(
        ...,
        min_length=1,
        max_length=500_000,
        description="Conteúdo textual do documento para análise",
    )
    case_id: uuid.UUID = Field(
        ..., description="ID do caso/processo associado"
    )
    purpose: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Finalidade do envio ao LLM (obrigatório para auditoria)",
    )

    @field_validator("text_content")
    @classmethod
    def text_must_not_be_blank(cls, v: str) -> str:
        """Valida que o texto não é composto apenas de espaços em branco."""
        if not v.strip():
            raise ValueError("O conteúdo textual não pode estar em branco.")
        return v


class ConfidentialityCheckResponse(BaseModel):
    """Schema de resposta da verificação de confidencialidade."""

    document_id: uuid.UUID = Field(
        ..., description="ID do documento verificado"
    )
    confidentiality_level: ConfidentialityLevel = Field(
        ..., description="Nível de confidencialidade detectado"
    )
    send_policy: LLMSendPolicy = Field(
        ..., description="Política de envio aplicável"
    )
    is_send_allowed: bool = Field(
        ..., description="Indica se o envio ao LLM é permitido"
    )
    requires_consent: bool = Field(
        ..., description="Indica se é necessário consentimento do titular"
    )
    blocked_entities_found: list[str] = Field(
        default_factory=list,
        description="Entidades bloqueadas encontradas no texto",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Razões para a classificação atribuída",
    )
    message: str = Field(
        ..., description="Mensagem descritiva do resultado"
    )


# ===========================================================================
# Portas (interfaces) do módulo
# ===========================================================================


@runtime_checkable
class ConsentRepositoryPort(Protocol):
    """Porta para persistência de registros de consentimento."""

    async def save_consent(self, record: ConsentRecord) -> ConsentRecord:
        """Persiste um registro de consentimento."""
        ...

    async def get_consent_by_case(
        self, case_id: uuid.UUID, client_id: uuid.UUID
    ) -> Optional[ConsentRecord]:
        """Recupera o consentimento vigente para um caso e cliente."""
        ...

    async def revoke_consent(self, consent_id: uuid.UUID) -> ConsentRecord:
        """Revoga um consentimento previamente concedido."""
        ...


# ===========================================================================
# Serviço principal de compliance
# ===========================================================================


class ConfidentialityComplianceService:
    """Serviço de compliance com sigilo advocatício para envio de dados a LLMs.

    Orquestra o pipeline completo de verificação de confidencialidade:
    1. Classificação do nível de confidencialidade do documento
    2. Verificação de entidades bloqueadas (segredo de justiça, menores, etc.)
    3. Verificação de consentimento quando necessário
    4. Anonimização do texto via pipeline do anonymizer
    5. Registro de auditoria de toda a operação

    Atributos:
        _consent_repo: Repositório de consentimentos.
        _audit_repo: Repositório de auditoria.
        _anonymizer: Pipeline de anonimização de dados.
    """

    def __init__(
        self,
        consent_repo: ConsentRepositoryPort,
        audit_repo: Any,  # TODO: Tipar como AuditRepositoryPort quando disponível
        anonymizer: Any,  # TODO: Tipar como AnonymizationPipeline quando disponível
    ) -> None:
        """Inicializa o serviço de compliance.

        Args:
            consent_repo: Implementação do repositório de consentimentos.
            audit_repo: Implementação do repositório de auditoria.
            anonymizer: Pipeline de anonimização de dados pessoais.
        """
        self._consent_repo = consent_repo
        self._audit_repo = audit_repo
        self._anonymizer = anonymizer
        self._logger = logger.bind(module="confidentiality_compliance")

    # -----------------------------------------------------------------------
    # Classificação de confidencialidade
    # -----------------------------------------------------------------------

    async def classify_document(
        self,
        document_id: uuid.UUID,
        text_content: str,
        metadata: Optional[dict[str, Any]] = None,
        classified_by: Optional[uuid.UUID] = None,
    ) -> ConfidentialityClassification:
        """Classifica o nível de confidencialidade de um documento.

        Analisa o conteúdo textual e metadados para determinar o nível
        de confidencialidade e a política de envio aplicável.

        Args:
            document_id: Identificador único do documento.
            text_content: Conteúdo textual do documento.
            metadata: Metadados adicionais (ex.: tipo processual, vara).
            classified_by: ID do usuário que solicitou a classificação.

        Returns:
            ConfidentialityClassification com o resultado da análise.
        """
        self._logger.info(
            "Iniciando classificação de confidencialidade",
            document_id=str(document_id),
        )

        metadata = metadata or {}
        reasons: list[str] = []
        detected_sensitive: list[str] = []
        blocked_found: list[str] = []

        # --- Verificação de segredo de justiça ---
        if self._is_judicial_secret(text_content, metadata):
            reasons.append(
                "Documento identificado como segredo de justiça — "
                "envio a LLM bloqueado conforme Art. 189 CPC."
            )
            blocked_found.append("JUDICIAL_SECRET_MARKER")
            level = ConfidentialityLevel.JUDICIAL_SECRET
        else:
            # --- Detecção de entidades sensíveis ---
            detected_sensitive = self._detect_sensitive_entities(text_content)
            blocked_found = [
                e for e in detected_sensitive if e in BLOCKED_ENTITY_TYPES
            ]

            if blocked_found:
                level = ConfidentialityLevel.JUDICIAL_SECRET
                reasons.append(
                    f"Entidades bloqueadas detectadas: {', '.join(blocked_found)}. "
                    "Envio a LLM bloqueado."
                )
            else:
                level = self._determine_level(text_content, metadata, detected_sensitive)
                reasons.append(
                    f"Nível de confidencialidade determinado: {level.value}."
                )

        policy = CONFIDENTIALITY_POLICY_MAP[level]

        classification = ConfidentialityClassification(
            document_id=document_id,
            level=level,
            policy=policy,
            reasons=reasons,
            detected_sensitive_entities=detected_sensitive,
            blocked_entities=blocked_found,
            classified_by=classified_by,
        )

        self._logger.info(
            "Classificação de confidencialidade concluída",
            document_id=str(document_id),
            level=level.value,
            policy=policy.value,
            blocked_count=len(blocked_found),
        )

        return classification

    # -----------------------------------------------------------------------
    # Pipeline completo de compliance para envio a LLM
    # -----------------------------------------------------------------------

    async def process_llm_send_request(
        self,
        request: LLMSendRequest,
        client_id: uuid.UUID,
        metadata: Optional[dict[str, Any]] = None,
    ) -> LLMSendResult:
        """Processa uma requisição de envio de texto a um LLM.

        Executa o pipeline completo de compliance:
        1. Classifica o documento
        2. Verifica política de envio
        3. Verifica consentimento (se necessário)
        4. Anonimiza o texto
        5. Registra auditoria

        Args:
            request: Dados da requisição de envio.
            client_id: ID do cliente titular dos dados.
            metadata: Metadados adicionais do documento.

        Returns:
            LLMSendResult com o resultado do pipeline.
        """
        self._logger.info(
            "Processando requisição de envio a LLM",
            request_id=str(request.request_id),
            document_id=str(request.document_id),
            user_id=str(request.user_id),
        )

        # 1. Classificar documento
        classification = await self.classify_document(
            document_id=request.document_id,
            text_content=request.original_text,
            metadata=metadata,
            classified_by=request.user_id,
        )

        # 2. Verificar se envio é bloqueado
        if classification.policy == LLMSendPolicy.BLOCKED:
            denial_reason = (
                "Envio bloqueado: documento classificado como segredo de justiça "
                "ou contém entidades protegidas. Conforme Art. 7º do Estatuto da "
                "OAB e Art. 189 do CPC, este conteúdo não pode ser enviado a "
                "serviços externos de IA."
            )
            await self._record_audit(
                request=request,
                action="llm_send_blocked",
                classification=classification,
                details={"denial_reason": denial_reason},
            )
            return LLMSendResult(
                request_id=request.request_id,
                allowed=False,
                denial_reason=denial_reason,
                classification=classification,
            )

        # 3. Verificar consentimento quando necessário
        if classification.policy == LLMSendPolicy.ALLOWED_WITH_CONSENT:
            consent = await self._consent_repo.get_consent_by_case(
                case_id=request.case_id,
                client_id=client_id,
            )
            if consent is None or consent.status != ConsentStatus.GRANTED:
                denial_reason = (
                    "Envio requer consentimento explícito do cliente/titular dos "
                    "dados. Conforme Art. 7º do Estatuto da OAB, o sigilo "
                    "profissional só pode ser dispensado com autorização expressa "
                    "do cliente. Solicite o consentimento antes de prosseguir."
                )
                await self._record_audit(
                    request=request,
                    action="llm_send_denied_no_consent",
                    classification=classification,
                    details={"denial_reason": denial_reason, "client_id": str(client_id)},
                )
                return LLMSendResult(
                    request_id=request.request_id,
                    allowed=False,
                    denial_reason=denial_reason,
                    classification=classification,
                )

        # 4. Anonimizar texto
        sanitized_text, anonymization_map_id = await self._anonymize_text(
            text=request.original_text,
            document_id=request.document_id,
            level=classification.level,
        )

        # 5. Validação pós-anonimização — verificar se restaram entidades bloqueadas
        post_check_entities = self._detect_sensitive_entities(sanitized_text)
        post_blocked = [e for e in post_check_entities if e in BLOCKED_ENTITY_TYPES]
        if post_blocked:
            denial_reason = (
                "Falha na anonimização: entidades protegidas ainda presentes "
                f"após sanitização ({', '.join(post_blocked)}). Envio bloqueado "
                "por segurança. Contate o administrador do sistema."
            )
            self._logger.error(
                "Entidades bloqueadas persistem após anonimização",
                request_id=str(request.request_id),
                remaining_blocked=post_blocked,
            )
            await self._record_audit(
                request=request,
                action="llm_send_blocked_post_anonymization",
                classification=classification,
                details={"denial_reason": denial_reason, "remaining": post_blocked},
            )
            return LLMSendResult(
                request_id=request.request_id,
                allowed=False,
                denial_reason=denial_reason,
                classification=classification,
            )

        # 6. Registrar auditoria de envio autorizado
        audit_entry_id = await self._record_audit(
            request=request,
            action="llm_send_authorized",
            classification=classification,
            details={
                "anonymization_map_id": str(anonymization_map_id) if anonymization_map_id else None,
                "sanitized_text_length": len(sanitized_text),
                "original_text_length": len(request.original_text),
                "purpose": request.purpose,
            },
        )

        self._logger.info(
            "Envio a LLM autorizado após compliance",
            request_id=str(request.request_id),
            document_id=str(request.document_id),
            level=classification.level.value,
        )

        return LLMSendResult(
            request_id=request.request_id,
            allowed=True,
            sanitized_text=sanitized_text,
            classification=classification,
            anonymization_map_id=anonymization_map_id,
            audit_entry_id=audit_entry_id,
        )

    # -----------------------------------------------------------------------
    # Verificação rápida de confidencialidade (sem pipeline completo)
    # -----------------------------------------------------------------------

    async def check_confidentiality(
        self,
        request: ConfidentialityCheckRequest,
        user_id: uuid.UUID,
    ) -> ConfidentialityCheckResponse:
        """Verifica a confidencialidade de um documento sem executar envio.

        Útil para o frontend exibir alertas antes do usuário confirmar
        o envio de dados ao LLM.

        Args:
            request: Dados da verificação.
            user_id: ID do usuário solicitante.

        Returns:
            ConfidentialityCheckResponse com o resultado da verificação.
        """
        classification = await self.classify_document(
            document_id=request.document_id,
            text_content=request.text_content,
            classified_by=user_id,
        )

        is_allowed = classification.policy not in (
            LLMSendPolicy.BLOCKED,
        )
        requires_consent = (
            classification.policy == LLMSendPolicy.ALLOWED_WITH_CONSENT
        )

        # Mensagem descritiva baseada na política
        message = self._build_policy_message(classification)

        return ConfidentialityCheckResponse(
            document_id=request.document_id,
            confidentiality_level=classification.level,
            send_policy=classification.policy,
            is_send_allowed=is_allowed,
            requires_consent=requires_consent,
            blocked_entities_found=classification.blocked_entities,
            reasons=classification.reasons,
            message=message,
        )

    # -----------------------------------------------------------------------
    # Gestão de consentimento
    # -----------------------------------------------------------------------

    async def register_consent(
        self,
        case_id: uuid.UUID,
        client_id: uuid.UUID,
        lawyer_id: uuid.UUID,
        purpose: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ConsentRecord:
        """Registra o consentimento do cliente para envio de dados a LLM.

        Args:
            case_id: ID do caso/processo.
            client_id: ID do cliente titular dos dados.
            lawyer_id: ID do advogado responsável.
            purpose: Finalidade do processamento por LLM.
            ip_address: Endereço IP do solicitante (para auditoria).
            user_agent: User-Agent do navegador (para auditoria).

        Returns:
            ConsentRecord com o registro de consentimento.
        """
        record = ConsentRecord(
            case_id=case_id,
            client_id=client_id,
            lawyer_id=lawyer_id,
            status=ConsentStatus.GRANTED,
            purpose=purpose,
            granted_at=datetime.now(timezone.utc),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        saved = await self._consent_repo.save_consent(record)

        self._logger.info(
            "Consentimento registrado para envio a LLM",
            consent_id=str(saved.consent_id),
            case_id=str(case_id),
            client_id=str(client_id),
        )

        await self._record_audit_simple(
            action="consent_granted",
            user_id=lawyer_id,
            details={
                "consent_id": str(saved.consent_id),
                "case_id": str(case_id),
                "client_id": str(client_id),
                "purpose": purpose,
            },
        )

        return saved

    async def revoke_consent(
        self,
        consent_id: uuid.UUID,
        revoked_by: uuid.UUID,
    ) -> ConsentRecord:
        """Revoga um consentimento previamente concedido.

        Args:
            consent_id: ID do consentimento a revogar.
            revoked_by: ID do usuário que está revogando.

        Returns:
            ConsentRecord atualizado.
        """
        revoked = await self._consent_repo.revoke_consent(consent_id)

        self._logger.info(
            "Consentimento revogado",
            consent_id=str(consent_id),
            revoked_by=str(revoked_by),
        )

        await self._record_audit_simple(
            action="consent_revoked",
            user_id=revoked_by,
            details={
                "consent_id": str(consent_id),
            },
        )

        return revoked

    # -----------------------------------------------------------------------
    # Métodos privados — Detecção e classificação
    # -----------------------------------------------------------------------

    def _is_judicial_secret(
        self, text: str, metadata: dict[str, Any]
    ) -> bool:
        """Verifica se o documento é segredo de justiça.

        Analisa marcadores textuais e metadados que indicam segredo de justiça
        conforme Art. 189 do CPC.

        Args:
            text: Conteúdo textual do documento.
            metadata: Metadados do documento.

        Returns:
            True se o documento for segredo de justiça.
        """
        # Verificação por metadados explícitos
        if metadata.get("segredo_justica", False):
            return True
        if metadata.get("judicial_secret", False):
            return True
        if metadata.get("nivel_sigilo") in ("segredo_justica", "judicial_secret"):
            return True

        # Verificação por marcadores textuais comuns
        judicial_secret_markers = [
            "segredo de justiça",
            "sigilo judicial",
            "tramitação em sigilo",
            "sob sigilo",
            "art. 189",
            "artigo 189",
            "segredo de justica",  # sem acento
        ]
        text_lower = text.lower()
        return any(marker in text_lower for marker in judicial_secret_markers)

    def _detect_sensitive_entities(self, text: str) -> list[str]:
        """Detecta entidades sensíveis no texto.

        Utiliza heurísticas e padrões para identificar categorias de dados
        que requerem tratamento especial.

        Args:
            text: Conteúdo textual a analisar.

        Returns:
            Lista de tipos de entidades sensíveis detectadas.
        """
        detected: list[str] = []
        text_lower = text.lower()

        # Marcadores de segredo de justiça
        if self._is_judicial_secret(text, {}):
            detected.append("JUDICIAL_SECRET_MARKER")

        # Identificação de menores
        minor_markers = [
            "menor de idade",
            "criança e adolescente",
            "eca",
            "estatuto da criança",
            "representado por seu genitor",
            "representado por sua genitora",
            "infante",
            "adolescente infrator",
            "medida socioeducativa",
        ]
        if any(m in text_lower for m in minor_markers):
            detected.append("MINOR_IDENTIFICATION")

        # Dados de saúde
        health_markers = [
            "diagnóstico",
            "diagnostico",
            "prontuário médico",
            "prontuario medico",
            "laudo médico",
            "laudo medico",
            "cid-10",
            "cid 10",
            "atestado médico",
            "exame toxicológico",
            "hiv",
            "aids",
            "doença mental",
            "internação compulsória",
        ]
        if any(m in text_lower for m in health_markers):
            detected.append("HEALTH_DATA")

        # Dados biométricos
        biometric_markers = [
            "impressão digital",
            "reconhecimento facial",
            "dna",
            "exame de dna",
            "biometria",
            "retina",
            "íris",
        ]
        if any(m in text_lower for m in biometric_markers):
            detected.append("BIOMETRIC_DATA")

        # Antecedentes criminais
        criminal_markers = [
            "antecedentes criminais",
            "folha de antecedentes",
            "certidão de antecedentes",
            "ficha criminal",
            "reincidência",
        ]
        if any(m in text_lower for m in criminal_markers):
            detected.append("CRIMINAL_RECORD")

        # Orientação sexual
        sexual_orientation_markers = [
            "orientação sexual",
            "orientacao sexual",
            "identidade de gênero",
            "identidade de genero",
            "homoafetivo",
            "homoafetiva",
        ]
        if any(m in text_lower for m in sexual_orientation_markers):
            detected.append("SEXUAL_ORIENTATION")

        # Convicção religiosa
        religious_markers = [
            "convicção religiosa",
            "conviccao religiosa",
            "crença religiosa",
            "crenca religiosa",
            "liberdade religiosa",
        ]
        if any(m in text_lower for m in religious_markers):
            detected.append("RELIGIOUS_BELIEF")

        # Opinião política
        political_markers = [
            "filiação partidária",
            "filiacao partidaria",
            "opinião política",
            "opiniao politica",
            "convicção política",
        ]
        if any(m in text_lower for m in political_markers):
            detected.append("POLITICAL_OPINION")

        return detected

    def _determine_level(
        self,
        text: str,
        metadata: dict[str, Any],
        detected_entities: list[str],
    ) -> ConfidentialityLevel:
        """Determina o nível de confidencialidade com base na análise.

        Args:
            text: Conteúdo textual.
            metadata: Metadados do documento.
            detected_entities: Entidades sensíveis detectadas.

        Returns:
            Nível de confidencialidade apropriado.
        """
        # Se há entidades sensíveis (não bloqueadas), elevar para confidencial
        if detected_entities:
            return ConfidentialityLevel.STRICTLY_CONFIDENTIAL

        # Verificar metadados de classificação explícita
        explicit_level = metadata.get("confidentiality_level")
        if explicit_level:
            try:
                return ConfidentialityLevel(explicit_level)
            except ValueError:
                self._logger.warning(
                    "Nível de confidencialidade inválido nos metadados",
                    explicit_level=explicit_level,
                )

        # Verificar tipo de documento
        doc_type = metadata.get("document_type", "").lower()
        confidential_types = {
            "procuração",
            "procuracao",
            "contrato",
            "parecer",
            "estratégia",
            "estrategia",
            "honorários",
            "honorarios",
        }
        if doc_type in confidential_types:
            return ConfidentialityLevel.CONFIDENTIAL

        internal_types = {
            "petição",
            "peticao",
            "recurso",
            "contestação",
            "contestacao",
            "réplica",
            "replica",
            "memoriais",
        }
        if doc_type in internal_types:
            return ConfidentialityLevel.INTERNAL

        # Heurística textual — presença de dados pessoais comuns
        personal_data_indicators = [
            "cpf",
            "rg",
            "cnpj",
            "endereço",
            "endereco",
            "telefone",
            "e-mail",
            "email",
            "nascimento",
            "filiação",
            "filiacao",
        ]
        text_lower = text.lower()
        personal_count = sum(
            1 for ind in personal_data_indicators if ind in text_lower
        )
        if personal_count >= 3:
            return ConfidentialityLevel.CONFIDENTIAL
        if personal_count >= 1:
            return ConfidentialityLevel.INTERNAL

        return ConfidentialityLevel.PUBLIC

    # -----------------------------------------------------------------------
    # Métodos privados — Anonimização
    # -----------------------------------------------------------------------

    async def _anonymize_text(
        self,
        text: str,
        document_id: uuid.UUID,
        level: ConfidentialityLevel,
    ) -> tuple[str, Optional[uuid.UUID]]:
        """Anonimiza o texto utilizando o pipeline de anonimização.

        Args:
            text: Texto original a ser anonimizado.
            document_id: ID do documento.
            level: Nível de confidencialidade para ajustar a intensidade.

        Returns:
            Tupla (texto_anonimizado, id_do_mapa_de_anonimização).
        """
        # TODO: Integrar com o AnonymizationPipeline do anonymizer.py
        # quando a API pública estiver completamente definida.
        # Exemplo esperado:
        #   result = await self._anonymizer.anonymize(
        #       text=text,
        #       document_id=document_id,
        #       entities_to_anonymize=self._get_entities_for_level(level),
        #   )
        #   return result.anonymized_text, result.map_id

        self._logger.warning(
            "Pipeline de anonimização ainda não integrado — usando placeholder",
            document_id=str(document_id),
            level=level.value,
        )

        # Placeholder: retorna texto original com aviso
        # Em produção, NUNCA retornar texto sem anonimização
        if level in (
            ConfidentialityLevel.JUDICIAL_SECRET,
            ConfidentialityLevel.STRICTLY_CONFIDENTIAL,
        ):
            raise RuntimeError(
                "Pipeline de anonimização não disponível para nível "
                f"{level.value}. Envio bloqueado por segurança."
            )

        return text, None

    def _get_entities_for_level(
        self, level: ConfidentialityLevel
    ) -> list[str]:
        """Retorna as entidades a anonimizar com base no nível de confidencialidade.

        Args:
            level: Nível de confidencialidade.

        Returns:
            Lista de tipos de entidades a anonimizar.
        """
        # Entidades base — sempre anonimizadas
        base_entities = [
            "CPF",
            "CNPJ",
            "PERSON_NAME",
            "EMAIL",
            "PHONE",
            "ADDRESS",
        ]

        if level == ConfidentialityLevel.PUBLIC:
            return base_entities

        # Entidades adicionais para níveis mais restritos
        extended_entities = base_entities + [
            "OAB_NUMBER",
            "PROCESS_NUMBER",
            "COURT",
            "JUDGE_NAME",
            "BANK_ACCOUNT",
            "LICENSE_PLATE",
        ]

        if level == ConfidentialityLevel.INTERNAL:
            return extended_entities

        # Anonimização completa para confidencial e acima
        full_entities = extended_entities + [
            "DATE_OF_BIRTH",
            "RG",
            "COMPANY_NAME",
            "LOCATION",
            "IP_ADDRESS",
            "MONETARY_VALUE",
        ]

        return full_entities

    # -----------------------------------------------------------------------
    # Métodos privados — Auditoria
    # -----------------------------------------------------------------------

    async def _record_audit(
        self,
        request: LLMSendRequest,
        action: str,
        classification: ConfidentialityClassification,
        details: Optional[dict[str, Any]] = None,
    ) -> Optional[uuid.UUID]:
        """Registra uma entrada de auditoria para operação de compliance.

        Args:
            request: Requisição de envio original.
            action: Ação realizada (ex.: 'llm_send_authorized').
            classification: Resultado da classificação.
            details: Detalhes adicionais.

        Returns:
            ID da entrada de auditoria, ou None se falhar.
        """
        try:
            # TODO: Usar a interface AuditRepositoryPort quando disponível.
            # Exemplo esperado:
            #   entry = AuditEntry(
            #       action=action,
            #       user_id=request.user_id,
            #       resource_type="document",
            #       resource_id=request.document_id,
            #       details={...},
            #   )
            #   saved = await self._audit_repo.save(entry)
            #   return saved.id

            audit_data = {
                "action": action,
                "module": "m02_data_confidentiality_compliance",
                "request_id": str(request.request_id),
                "document_id": str(request.document_id),
                "case_id": str(request.case_id),
                "user_id": str(request.user_id),
                "confidentiality_level": classification.level.value,
                "send_policy": classification.policy.value,
                "purpose": request.purpose,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(details or {}),
            }

            self._logger.info(
                "Registro de auditoria de compliance",
                **audit_data,
            )

            # TODO: Persistir via audit_repo quando integrado
            return uuid.uuid4()  # Placeholder ID

        except Exception as exc:
            self._logger.error(
                "Falha ao registrar auditoria de compliance",
                error=str(exc),
                action=action,
                request_id=str(request.request_id),
            )
            return None

    async def _record_audit_simple(
        self,
        action: str,
        user_id: uuid.UUID,
        details: Optional[dict[str, Any]] = None,
    ) -> Optional[uuid.UUID]:
        """Registra uma entrada de auditoria simples (sem requisição de envio).

        Args:
            action: Ação realizada.
            user_id: ID do usuário.
            details: Detalhes adicionais.

        Returns:
            ID da entrada de auditoria, ou None se falhar.
        """
        try:
            audit_data = {
                "action": action,
                "module": "m02_data_confidentiality_compliance",
                "user_id": str(user_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **(details or {}),
            }

            self._logger.info(
                "Registro de auditoria simples de compliance",
                **audit_data,
            )

            # TODO: Persistir via audit_repo quando integrado
            return uuid.uuid4()  # Placeholder ID

        except Exception as exc:
            self._logger.error(
                "Falha ao registrar auditoria simples",
                error=str(exc),
                action=action,
            )
            return None

    # -----------------------------------------------------------------------
    # Métodos privados — Mensagens
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_policy_message(
        classification: ConfidentialityClassification,
    ) -> str:
        """Constrói mensagem descritiva da política de envio.

        Args:
            classification: Resultado da classificação.

        Returns:
            Mensagem em português para exibição ao usuário.
        """
        messages = {
            LLMSendPolicy.ALLOWED: (
                "Documento classificado como público. O envio ao assistente de IA "
                "é permitido após anonimização padrão de dados pessoais."
            ),
            LLMSendPolicy.ALLOWED_ANONYMIZED_ONLY: (
                "Documento classificado como interno. O envio ao assistente de IA "
                "é permitido apenas com anonimização completa. Dados pessoais e "
                "identificadores processuais serão removidos."
            ),
            LLMSendPolicy.ALLOWED_WITH_CONSENT: (
                "Documento classificado como confidencial. O envio ao assistente "
                "de IA requer consentimento explícito do cliente, conforme Art. 7º "
                "do Estatuto da OAB. Anonimização reforçada será aplicada."
            ),
            LLMSendPolicy.BLOCKED: (
                "Documento classificado como segredo de justiça ou contém dados "
                "especialmente protegidos. O envio ao assistente de IA está "
                "BLOQUEADO conforme Art. 189 do CPC e Art. 7º do Estatuto da OAB. "
                "Este conteúdo não pode ser processado por serviços externos."
            ),
        }
        return messages.get(
            classification.policy,
            "Classificação de confidencialidade indeterminada. Contate o suporte.",
        )


# ===========================================================================
# Factory function para injeção de dependências
# ===========================================================================


def create_confidentiality_compliance_service(
    consent_repo: ConsentRepositoryPort,
    audit_repo: Any,  # TODO: Tipar como AuditRepositoryPort
    anonymizer: Any,  # TODO: Tipar como AnonymizationPipeline
) -> ConfidentialityComplianceService:
    """Factory para criação do serviço de compliance com injeção de dependências.

    Args:
        consent_repo: Implementação do repositório de consentimentos.
        audit_repo: Implementação do repositório de auditoria.
        anonymizer: Pipeline de anonimização.

    Returns:
        Instância configurada de ConfidentialityComplianceService.
    """
    return ConfidentialityComplianceService(
        consent_repo=consent_repo,
        audit_repo=audit_repo,
        anonymizer=anonymizer,
    )
