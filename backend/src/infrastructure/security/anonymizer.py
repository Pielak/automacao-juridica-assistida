"""Pipeline de anonimização de dados jurídicos para envio seguro a LLMs.

Implementa um pipeline de anonimização utilizando Microsoft Presidio e
reconhecimento de entidades nomeadas (NER) para identificar e mascarar
dados pessoais sensíveis em textos jurídicos antes do envio a modelos
de linguagem (ex.: Anthropic Claude).

O pipeline suporta:
- Detecção de CPF, CNPJ, OAB, nomes, endereços, telefones, e-mails
- Entidades jurídicas específicas (número de processo, vara, comarca)
- Mapeamento reversível para deanonimização de respostas
- Configuração flexível de entidades a anonimizar

Exemplo de uso:
    from backend.src.infrastructure.security.anonymizer import (
        get_anonymizer,
        AnonymizerPipeline,
    )

    anonymizer = get_anonymizer()
    resultado = anonymizer.anonymize(texto_juridico)
    print(resultado.anonymized_text)

    # Após receber resposta da LLM, deanonimizar
    texto_original = anonymizer.deanonymize(
        resultado.anonymized_text,
        resultado.mapping,
    )
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any

from backend.src.infrastructure.config.settings import get_settings

try:
    from presidio_analyzer import (
        AnalyzerEngine,
        PatternRecognizer,
        Pattern,
        RecognizerResult,
    )
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig

    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

import logging

import structlog

logger = structlog.get_logger(__name__)


class EntityType(str, Enum):
    """Tipos de entidades sensíveis reconhecidas pelo pipeline."""

    # Entidades pessoais padrão
    PERSON_NAME = "PERSON_NAME"
    CPF = "CPF"
    CNPJ = "CNPJ"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    ADDRESS = "ADDRESS"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"

    # Entidades jurídicas específicas
    OAB_NUMBER = "OAB_NUMBER"
    PROCESS_NUMBER = "PROCESS_NUMBER"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    RG = "RG"


# Mapeamento de placeholder legível por tipo de entidade
ENTITY_PLACEHOLDER_PREFIX: dict[str, str] = {
    EntityType.PERSON_NAME: "PESSOA",
    EntityType.CPF: "CPF",
    EntityType.CNPJ: "CNPJ",
    EntityType.EMAIL: "EMAIL",
    EntityType.PHONE: "TELEFONE",
    EntityType.ADDRESS: "ENDERECO",
    EntityType.DATE_OF_BIRTH: "DATA_NASC",
    EntityType.OAB_NUMBER: "OAB",
    EntityType.PROCESS_NUMBER: "PROCESSO",
    EntityType.BANK_ACCOUNT: "CONTA_BANCARIA",
    EntityType.RG: "RG",
}


@dataclass(frozen=True)
class DetectedEntity:
    """Representa uma entidade sensível detectada no texto.

    Attributes:
        entity_type: Tipo da entidade detectada.
        original_value: Valor original encontrado no texto.
        start: Posição inicial no texto original.
        end: Posição final no texto original.
        score: Nível de confiança da detecção (0.0 a 1.0).
        placeholder: Placeholder gerado para substituição.
    """

    entity_type: str
    original_value: str
    start: int
    end: int
    score: float
    placeholder: str


@dataclass
class AnonymizationResult:
    """Resultado do processo de anonimização.

    Attributes:
        anonymized_text: Texto com dados sensíveis substituídos por placeholders.
        original_text: Texto original antes da anonimização.
        mapping: Mapeamento de placeholder -> valor original para deanonimização.
        entities_detected: Lista de entidades detectadas.
        entity_count: Contagem total de entidades anonimizadas.
    """

    anonymized_text: str
    original_text: str
    mapping: dict[str, str] = field(default_factory=dict)
    entities_detected: list[DetectedEntity] = field(default_factory=list)
    entity_count: int = 0


@dataclass
class AnonymizerConfig:
    """Configuração do pipeline de anonimização.

    Attributes:
        enabled_entities: Tipos de entidades a detectar e anonimizar.
        score_threshold: Limiar mínimo de confiança para considerar uma detecção.
        language: Idioma do texto a ser analisado.
        use_presidio: Se True, utiliza Presidio como engine principal.
        use_regex_fallback: Se True, aplica detecção por regex como fallback.
    """

    enabled_entities: list[str] = field(default_factory=lambda: [
        EntityType.PERSON_NAME,
        EntityType.CPF,
        EntityType.CNPJ,
        EntityType.EMAIL,
        EntityType.PHONE,
        EntityType.OAB_NUMBER,
        EntityType.PROCESS_NUMBER,
        EntityType.RG,
        EntityType.ADDRESS,
        EntityType.BANK_ACCOUNT,
    ])
    score_threshold: float = 0.6
    language: str = "pt"
    use_presidio: bool = True
    use_regex_fallback: bool = True


class BrazilianLegalRecognizers:
    """Fábrica de reconhecedores customizados para entidades jurídicas brasileiras.

    Cria instâncias de PatternRecognizer do Presidio com padrões regex
    específicos para documentos e identificadores do sistema jurídico
    brasileiro.
    """

    @staticmethod
    def create_cpf_recognizer() -> PatternRecognizer | None:
        """Cria reconhecedor de CPF (formato: 000.000.000-00 ou 00000000000)."""
        if not PRESIDIO_AVAILABLE:
            return None

        cpf_pattern = Pattern(
            name="cpf_pattern",
            regex=r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b",
            score=0.85,
        )
        return PatternRecognizer(
            supported_entity="CPF",
            patterns=[cpf_pattern],
            supported_language="pt",
            name="Reconhecedor de CPF brasileiro",
        )

    @staticmethod
    def create_cnpj_recognizer() -> PatternRecognizer | None:
        """Cria reconhecedor de CNPJ (formato: 00.000.000/0000-00 ou 00000000000000)."""
        if not PRESIDIO_AVAILABLE:
            return None

        cnpj_pattern = Pattern(
            name="cnpj_pattern",
            regex=r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b",
            score=0.85,
        )
        return PatternRecognizer(
            supported_entity="CNPJ",
            patterns=[cnpj_pattern],
            supported_language="pt",
            name="Reconhecedor de CNPJ brasileiro",
        )

    @staticmethod
    def create_oab_recognizer() -> PatternRecognizer | None:
        """Cria reconhecedor de número OAB (formato: OAB/UF 000000 ou OAB 000.000)."""
        if not PRESIDIO_AVAILABLE:
            return None

        oab_pattern = Pattern(
            name="oab_pattern",
            regex=r"\bOAB\s*/\s*[A-Z]{2}\s*\d{3,6}\b|\bOAB\s+\d{3}\.?\d{3}\b",
            score=0.9,
        )
        return PatternRecognizer(
            supported_entity="OAB_NUMBER",
            patterns=[oab_pattern],
            supported_language="pt",
            name="Reconhecedor de número OAB",
        )

    @staticmethod
    def create_process_number_recognizer() -> PatternRecognizer | None:
        """Cria reconhecedor de número de processo CNJ.

        Formato CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
        """
        if not PRESIDIO_AVAILABLE:
            return None

        process_pattern = Pattern(
            name="process_number_cnj",
            regex=r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b",
            score=0.95,
        )
        return PatternRecognizer(
            supported_entity="PROCESS_NUMBER",
            patterns=[process_pattern],
            supported_language="pt",
            name="Reconhecedor de número de processo CNJ",
        )

    @staticmethod
    def create_rg_recognizer() -> PatternRecognizer | None:
        """Cria reconhecedor de RG (formato: 00.000.000-0 ou variações)."""
        if not PRESIDIO_AVAILABLE:
            return None

        rg_pattern = Pattern(
            name="rg_pattern",
            regex=r"\b\d{2}\.\d{3}\.\d{3}-[\dXx]\b",
            score=0.75,
        )
        return PatternRecognizer(
            supported_entity="RG",
            patterns=[rg_pattern],
            supported_language="pt",
            name="Reconhecedor de RG brasileiro",
        )

    @staticmethod
    def create_phone_recognizer() -> PatternRecognizer | None:
        """Cria reconhecedor de telefone brasileiro."""
        if not PRESIDIO_AVAILABLE:
            return None

        phone_pattern = Pattern(
            name="phone_br_pattern",
            regex=(
                r"\b(?:\+55\s?)?(?:\(?\d{2}\)?\s?)"
                r"(?:9\s?)?\d{4}[\s-]?\d{4}\b"
            ),
            score=0.8,
        )
        return PatternRecognizer(
            supported_entity="PHONE",
            patterns=[phone_pattern],
            supported_language="pt",
            name="Reconhecedor de telefone brasileiro",
        )

    @staticmethod
    def create_bank_account_recognizer() -> PatternRecognizer | None:
        """Cria reconhecedor de conta bancária (agência/conta)."""
        if not PRESIDIO_AVAILABLE:
            return None

        bank_pattern = Pattern(
            name="bank_account_pattern",
            regex=(
                r"\b(?:ag(?:[eê]ncia)?|ag\.?)\s*:?\s*\d{4}[\s-]?\d?\s*"
                r"(?:c(?:onta)?|cc|c/c)\.?\s*:?\s*\d{5,12}[\s-]?\d?\b"
            ),
            score=0.8,
        )
        return PatternRecognizer(
            supported_entity="BANK_ACCOUNT",
            patterns=[bank_pattern],
            supported_language="pt",
            name="Reconhecedor de conta bancária",
        )

    @classmethod
    def get_all_recognizers(cls) -> list[Any]:
        """Retorna todos os reconhecedores customizados disponíveis."""
        factories = [
            cls.create_cpf_recognizer,
            cls.create_cnpj_recognizer,
            cls.create_oab_recognizer,
            cls.create_process_number_recognizer,
            cls.create_rg_recognizer,
            cls.create_phone_recognizer,
            cls.create_bank_account_recognizer,
        ]
        return [r for r in (f() for f in factories) if r is not None]


class RegexFallbackDetector:
    """Detector de entidades sensíveis baseado em regex puro.

    Utilizado como fallback quando o Presidio não está disponível
    ou como camada adicional de detecção.
    """

    # Padrões regex para entidades brasileiras
    PATTERNS: dict[str, re.Pattern[str]] = {
        EntityType.CPF: re.compile(
            r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"
        ),
        EntityType.CNPJ: re.compile(
            r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"
        ),
        EntityType.OAB_NUMBER: re.compile(
            r"\bOAB\s*/\s*[A-Z]{2}\s*\d{3,6}\b",
            re.IGNORECASE,
        ),
        EntityType.PROCESS_NUMBER: re.compile(
            r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b"
        ),
        EntityType.EMAIL: re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        ),
        EntityType.PHONE: re.compile(
            r"\b(?:\+55\s?)?(?:\(?\d{2}\)?\s?)(?:9\s?)?\d{4}[\s-]?\d{4}\b"
        ),
        EntityType.RG: re.compile(
            r"\b\d{2}\.\d{3}\.\d{3}-[\dXx]\b"
        ),
    }

    def detect(
        self,
        text: str,
        enabled_entities: list[str] | None = None,
    ) -> list[DetectedEntity]:
        """Detecta entidades sensíveis no texto usando padrões regex.

        Args:
            text: Texto a ser analisado.
            enabled_entities: Lista de tipos de entidade a detectar.
                Se None, detecta todos os tipos disponíveis.

        Returns:
            Lista de entidades detectadas.
        """
        entities: list[DetectedEntity] = []
        target_entities = enabled_entities or list(self.PATTERNS.keys())

        for entity_type, pattern in self.PATTERNS.items():
            if entity_type not in target_entities:
                continue

            for match in pattern.finditer(text):
                placeholder = self._generate_placeholder(entity_type)
                entities.append(
                    DetectedEntity(
                        entity_type=entity_type,
                        original_value=match.group(),
                        start=match.start(),
                        end=match.end(),
                        score=0.85,
                        placeholder=placeholder,
                    )
                )

        return entities

    @staticmethod
    def _generate_placeholder(entity_type: str) -> str:
        """Gera um placeholder único para uma entidade."""
        prefix = ENTITY_PLACEHOLDER_PREFIX.get(entity_type, "DADO")
        short_id = uuid.uuid4().hex[:8].upper()
        return f"[{prefix}_{short_id}]"


class AnonymizerPipeline:
    """Pipeline principal de anonimização de dados jurídicos.

    Combina Microsoft Presidio (quando disponível) com reconhecedores
    customizados para entidades jurídicas brasileiras e um fallback
    baseado em regex para garantir cobertura máxima.

    O pipeline gera mapeamentos reversíveis que permitem deanonimizar
    as respostas recebidas de LLMs.

    Attributes:
        config: Configuração do pipeline.
        _analyzer: Engine de análise do Presidio (se disponível).
        _anonymizer_engine: Engine de anonimização do Presidio.
        _regex_detector: Detector de fallback baseado em regex.
    """

    def __init__(self, config: AnonymizerConfig | None = None) -> None:
        """Inicializa o pipeline de anonimização.

        Args:
            config: Configuração do pipeline. Se None, usa configuração padrão.
        """
        self.config = config or AnonymizerConfig()
        self._regex_detector = RegexFallbackDetector()
        self._analyzer: Any | None = None
        self._anonymizer_engine: Any | None = None
        self._initialized = False

        if self.config.use_presidio and PRESIDIO_AVAILABLE:
            self._initialize_presidio()

    def _initialize_presidio(self) -> None:
        """Inicializa as engines do Presidio com reconhecedores customizados."""
        try:
            # Configurar NLP engine para português
            # TODO: Configurar modelo spaCy pt_core_news_lg para melhor NER em português.
            #       Requer instalação: python -m spacy download pt_core_news_lg
            #       Por padrão, tenta usar o modelo disponível.
            nlp_config = {
                "nlp_engine_name": "spacy",
                "models": [
                    {"lang_code": "pt", "model_name": "pt_core_news_sm"},
                ],
            }

            try:
                provider = NlpEngineProvider(nlp_configuration=nlp_config)
                nlp_engine = provider.create_engine()
            except Exception as nlp_err:
                logger.warning(
                    "Não foi possível carregar modelo spaCy para português. "
                    "Utilizando fallback regex.",
                    error=str(nlp_err),
                )
                self._initialized = False
                return

            self._analyzer = AnalyzerEngine(
                nlp_engine=nlp_engine,
                supported_languages=["pt"],
            )

            # Registrar reconhecedores customizados brasileiros
            custom_recognizers = BrazilianLegalRecognizers.get_all_recognizers()
            for recognizer in custom_recognizers:
                self._analyzer.registry.add_recognizer(recognizer)

            self._anonymizer_engine = AnonymizerEngine()
            self._initialized = True

            logger.info(
                "Pipeline Presidio inicializado com sucesso.",
                custom_recognizers_count=len(custom_recognizers),
            )

        except Exception as e:
            logger.error(
                "Erro ao inicializar pipeline Presidio. "
                "Utilizando fallback regex.",
                error=str(e),
            )
            self._initialized = False

    def anonymize(self, text: str) -> AnonymizationResult:
        """Anonimiza dados sensíveis em um texto jurídico.

        Executa o pipeline completo de detecção e substituição de
        entidades sensíveis, gerando um mapeamento reversível.

        Args:
            text: Texto jurídico a ser anonimizado.

        Returns:
            AnonymizationResult com texto anonimizado e mapeamento.

        Raises:
            ValueError: Se o texto estiver vazio ou for None.
        """
        if not text or not text.strip():
            raise ValueError("O texto para anonimização não pode estar vazio.")

        logger.info(
            "Iniciando anonimização de texto jurídico.",
            text_length=len(text),
        )

        detected_entities: list[DetectedEntity] = []

        # Etapa 1: Detecção via Presidio (se disponível e habilitado)
        if self._initialized and self.config.use_presidio:
            presidio_entities = self._detect_with_presidio(text)
            detected_entities.extend(presidio_entities)

        # Etapa 2: Detecção via regex (fallback ou complementar)
        if self.config.use_regex_fallback or not self._initialized:
            regex_entities = self._regex_detector.detect(
                text,
                enabled_entities=self.config.enabled_entities,
            )
            # Mesclar sem duplicatas (baseado em posição)
            detected_entities = self._merge_entities(
                detected_entities,
                regex_entities,
            )

        # Etapa 3: Filtrar por threshold de confiança
        detected_entities = [
            e for e in detected_entities
            if e.score >= self.config.score_threshold
        ]

        # Etapa 4: Ordenar por posição (do final para o início para substituição segura)
        detected_entities.sort(key=lambda e: e.start, reverse=True)

        # Etapa 5: Gerar placeholders únicos e construir mapeamento
        mapping: dict[str, str] = {}
        anonymized_text = text

        # Mapa para reutilizar placeholder para valores idênticos
        value_to_placeholder: dict[str, str] = {}

        for entity in detected_entities:
            # Reutilizar placeholder se o mesmo valor já foi encontrado
            cache_key = f"{entity.entity_type}:{entity.original_value}"
            if cache_key in value_to_placeholder:
                placeholder = value_to_placeholder[cache_key]
            else:
                placeholder = entity.placeholder
                value_to_placeholder[cache_key] = placeholder

            mapping[placeholder] = entity.original_value

            # Substituir no texto (do final para o início)
            anonymized_text = (
                anonymized_text[:entity.start]
                + placeholder
                + anonymized_text[entity.end:]
            )

        # Reordenar entidades para a ordem original (início -> fim)
        detected_entities.reverse()

        result = AnonymizationResult(
            anonymized_text=anonymized_text,
            original_text=text,
            mapping=mapping,
            entities_detected=detected_entities,
            entity_count=len(detected_entities),
        )

        logger.info(
            "Anonimização concluída.",
            entities_found=result.entity_count,
            entity_types=[e.entity_type for e in detected_entities],
        )

        return result

    def deanonymize(
        self,
        anonymized_text: str,
        mapping: dict[str, str],
    ) -> str:
        """Restaura dados originais em um texto anonimizado.

        Substitui os placeholders pelos valores originais usando o
        mapeamento gerado durante a anonimização.

        Args:
            anonymized_text: Texto contendo placeholders de anonimização.
            mapping: Mapeamento de placeholder -> valor original.

        Returns:
            Texto com dados originais restaurados.
        """
        if not mapping:
            return anonymized_text

        result = anonymized_text
        # Ordenar por tamanho do placeholder (maior primeiro) para evitar
        # substituições parciais
        sorted_placeholders = sorted(
            mapping.keys(),
            key=len,
            reverse=True,
        )

        for placeholder in sorted_placeholders:
            original_value = mapping[placeholder]
            result = result.replace(placeholder, original_value)

        logger.info(
            "Deanonimização concluída.",
            placeholders_replaced=len(mapping),
        )

        return result

    def _detect_with_presidio(self, text: str) -> list[DetectedEntity]:
        """Detecta entidades sensíveis usando o Presidio Analyzer.

        Args:
            text: Texto a ser analisado.

        Returns:
            Lista de entidades detectadas pelo Presidio.
        """
        if not self._analyzer:
            return []

        try:
            # Mapear entidades habilitadas para nomes do Presidio
            presidio_entities = self._map_to_presidio_entities(
                self.config.enabled_entities
            )

            results: list[RecognizerResult] = self._analyzer.analyze(
                text=text,
                entities=presidio_entities,
                language=self.config.language,
                score_threshold=self.config.score_threshold,
            )

            detected: list[DetectedEntity] = []
            for result in results:
                original_value = text[result.start:result.end]
                entity_type = self._map_from_presidio_entity(result.entity_type)
                placeholder = self._generate_placeholder(entity_type)

                detected.append(
                    DetectedEntity(
                        entity_type=entity_type,
                        original_value=original_value,
                        start=result.start,
                        end=result.end,
                        score=result.score,
                        placeholder=placeholder,
                    )
                )

            return detected

        except Exception as e:
            logger.error(
                "Erro na detecção via Presidio.",
                error=str(e),
            )
            return []

    @staticmethod
    def _map_to_presidio_entities(enabled: list[str]) -> list[str]:
        """Mapeia tipos de entidade internos para nomes do Presidio."""
        # Mapeamento de entidades internas -> Presidio
        mapping = {
            EntityType.PERSON_NAME: "PERSON",
            EntityType.CPF: "CPF",
            EntityType.CNPJ: "CNPJ",
            EntityType.EMAIL: "EMAIL_ADDRESS",
            EntityType.PHONE: "PHONE_NUMBER",
            EntityType.ADDRESS: "LOCATION",
            EntityType.DATE_OF_BIRTH: "DATE_TIME",
            EntityType.OAB_NUMBER: "OAB_NUMBER",
            EntityType.PROCESS_NUMBER: "PROCESS_NUMBER",
            EntityType.BANK_ACCOUNT: "BANK_ACCOUNT",
            EntityType.RG: "RG",
        }
        return [mapping.get(e, e) for e in enabled if e in mapping]

    @staticmethod
    def _map_from_presidio_entity(presidio_type: str) -> str:
        """Mapeia nome de entidade do Presidio para tipo interno."""
        reverse_mapping = {
            "PERSON": EntityType.PERSON_NAME,
            "EMAIL_ADDRESS": EntityType.EMAIL,
            "PHONE_NUMBER": EntityType.PHONE,
            "LOCATION": EntityType.ADDRESS,
            "DATE_TIME": EntityType.DATE_OF_BIRTH,
        }
        return reverse_mapping.get(presidio_type, presidio_type)

    @staticmethod
    def _generate_placeholder(entity_type: str) -> str:
        """Gera um placeholder único e determinístico para uma entidade."""
        prefix = ENTITY_PLACEHOLDER_PREFIX.get(entity_type, "DADO")
        short_id = uuid.uuid4().hex[:8].upper()
        return f"[{prefix}_{short_id}]"

    @staticmethod
    def _merge_entities(
        primary: list[DetectedEntity],
        secondary: list[DetectedEntity],
    ) -> list[DetectedEntity]:
        """Mescla duas listas de entidades, evitando sobreposições.

        Entidades da lista primária têm prioridade. Entidades da lista
        secundária são adicionadas apenas se não sobrepõem nenhuma
        entidade primária.

        Args:
            primary: Lista de entidades com prioridade.
            secondary: Lista de entidades secundárias.

        Returns:
            Lista mesclada sem sobreposições.
        """
        if not primary:
            return secondary
        if not secondary:
            return primary

        merged = list(primary)

        # Verificar sobreposição para cada entidade secundária
        for sec_entity in secondary:
            has_overlap = False
            for pri_entity in primary:
                # Verificar se há sobreposição de intervalos
                if (
                    sec_entity.start < pri_entity.end
                    and sec_entity.end > pri_entity.start
                ):
                    has_overlap = True
                    break

            if not has_overlap:
                merged.append(sec_entity)

        return merged

    @property
    def is_presidio_available(self) -> bool:
        """Indica se o Presidio está disponível e inicializado."""
        return self._initialized and PRESIDIO_AVAILABLE


def create_anonymizer_pipeline(
    config: AnonymizerConfig | None = None,
) -> AnonymizerPipeline:
    """Cria uma nova instância do pipeline de anonimização.

    Factory function para criação do pipeline com configuração
    personalizada ou padrão.

    Args:
        config: Configuração do pipeline. Se None, usa padrão.

    Returns:
        Instância configurada do AnonymizerPipeline.
    """
    return AnonymizerPipeline(config=config)


@lru_cache(maxsize=1)
def get_anonymizer() -> AnonymizerPipeline:
    """Retorna instância singleton do pipeline de anonimização.

    Utiliza cache para garantir que apenas uma instância seja criada
    durante o ciclo de vida da aplicação.

    Returns:
        Instância singleton do AnonymizerPipeline.
    """
    settings = get_settings()

    # TODO: Ler configurações de anonimização do settings quando
    #       os campos correspondentes forem adicionados ao Settings.
    #       Ex.: settings.ANONYMIZER_SCORE_THRESHOLD,
    #            settings.ANONYMIZER_ENABLED_ENTITIES

    config = AnonymizerConfig(
        use_presidio=PRESIDIO_AVAILABLE,
        use_regex_fallback=True,
        score_threshold=0.6,
    )

    logger.info(
        "Criando instância singleton do pipeline de anonimização.",
        presidio_available=PRESIDIO_AVAILABLE,
        use_regex_fallback=config.use_regex_fallback,
    )

    return AnonymizerPipeline(config=config)


def anonymize_for_llm(text: str) -> tuple[str, dict[str, str]]:
    """Função utilitária para anonimizar texto antes de enviar a uma LLM.

    Atalho conveniente que retorna apenas o texto anonimizado e o
    mapeamento necessário para deanonimização posterior.

    Args:
        text: Texto jurídico a ser anonimizado.

    Returns:
        Tupla (texto_anonimizado, mapeamento_para_deanonimizacao).

    Raises:
        ValueError: Se o texto estiver vazio.
    """
    anonymizer = get_anonymizer()
    result = anonymizer.anonymize(text)
    return result.anonymized_text, result.mapping


def deanonymize_from_llm(
    llm_response: str,
    mapping: dict[str, str],
) -> str:
    """Função utilitária para deanonimizar resposta recebida de uma LLM.

    Atalho conveniente que restaura os dados originais na resposta
    da LLM usando o mapeamento gerado durante a anonimização.

    Args:
        llm_response: Texto de resposta da LLM contendo placeholders.
        mapping: Mapeamento gerado pela função anonymize_for_llm.

    Returns:
        Texto com dados originais restaurados.
    """
    anonymizer = get_anonymizer()
    return anonymizer.deanonymize(llm_response, mapping)
