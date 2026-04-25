"""Módulo de configurações da aplicação — Automação Jurídica Assistida.

Utiliza Pydantic Settings para carregar variáveis de ambiente a partir de
arquivos .env, validando todas as configurações necessárias para o
funcionamento da aplicação: banco de dados, JWT, CORS, Redis, LLM (Anthropic),
Celery, e demais serviços de infraestrutura.

Exemplo de uso:
    from backend.src.infrastructure.config.settings import get_settings

    settings = get_settings()
    print(settings.DATABASE_URL)
"""

from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações centrais da aplicação.

    Todas as variáveis são carregadas do ambiente ou de um arquivo .env.
    Valores sensíveis utilizam SecretStr para evitar exposição acidental
    em logs ou serialização.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ──────────────────────────────────────────────
    # Aplicação
    # ──────────────────────────────────────────────
    APP_NAME: str = Field(
        default="Automação Jurídica Assistida",
        description="Nome da aplicação exibido na documentação OpenAPI.",
    )
    APP_VERSION: str = Field(
        default="0.1.0",
        description="Versão semântica da aplicação.",
    )
    APP_ENV: str = Field(
        default="development",
        description="Ambiente de execução: development, staging ou production.",
    )
    DEBUG: bool = Field(
        default=False,
        description="Ativa modo de depuração. Nunca usar em produção.",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Nível de log: DEBUG, INFO, WARNING, ERROR, CRITICAL.",
    )
    API_V1_PREFIX: str = Field(
        default="/api/v1",
        description="Prefixo base para todas as rotas da API v1.",
    )

    # ──────────────────────────────────────────────
    # Banco de Dados (PostgreSQL + asyncpg)
    # ──────────────────────────────────────────────
    DATABASE_URL: SecretStr = Field(
        ...,
        description=(
            "URL de conexão com o PostgreSQL. "
            "Formato: postgresql+asyncpg://user:pass@host:port/dbname"
        ),
    )
    DATABASE_POOL_SIZE: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Tamanho do pool de conexões do SQLAlchemy.",
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=20,
        ge=0,
        le=200,
        description="Número máximo de conexões extras além do pool.",
    )
    DATABASE_POOL_TIMEOUT: int = Field(
        default=30,
        ge=5,
        description="Timeout em segundos para obter conexão do pool.",
    )
    DATABASE_ECHO: bool = Field(
        default=False,
        description="Ativa log de SQL gerado pelo SQLAlchemy (apenas desenvolvimento).",
    )

    # ──────────────────────────────────────────────
    # JWT / Autenticação
    # ──────────────────────────────────────────────
    JWT_SECRET_KEY: SecretStr = Field(
        ...,
        description="Chave secreta para assinatura de tokens JWT (mínimo 32 caracteres).",
    )
    JWT_ALGORITHM: str = Field(
        default="RS256",
        description="Algoritmo de assinatura JWT. Recomendado: RS256 para produção.",
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=5,
        le=1440,
        description="Tempo de expiração do access token em minutos.",
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,
        le=90,
        description="Tempo de expiração do refresh token em dias.",
    )
    JWT_ISSUER: str = Field(
        default="automacao-juridica-assistida",
        description="Emissor (iss) incluído no payload do JWT.",
    )
    JWT_AUDIENCE: str = Field(
        default="automacao-juridica-assistida-api",
        description="Audiência (aud) esperada no payload do JWT.",
    )
    JWT_PUBLIC_KEY: SecretStr | None = Field(
        default=None,
        description="Chave pública RSA para verificação de tokens RS256 (PEM).",
    )
    JWT_PRIVATE_KEY: SecretStr | None = Field(
        default=None,
        description="Chave privada RSA para assinatura de tokens RS256 (PEM).",
    )

    # ──────────────────────────────────────────────
    # MFA (Multi-Factor Authentication)
    # ──────────────────────────────────────────────
    MFA_ENABLED: bool = Field(
        default=True,
        description="Habilita autenticação multifator via TOTP.",
    )
    MFA_ISSUER_NAME: str = Field(
        default="AutomacaoJuridica",
        description="Nome do emissor exibido no app autenticador (Google Authenticator/Authy).",
    )

    # ──────────────────────────────────────────────
    # Hashing de Senhas
    # ──────────────────────────────────────────────
    PASSWORD_BCRYPT_ROUNDS: int = Field(
        default=12,
        ge=10,
        le=14,
        description="Número de rounds do bcrypt para hashing de senhas.",
    )

    # ──────────────────────────────────────────────
    # CORS
    # ──────────────────────────────────────────────
    CORS_ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description=(
            "Lista de origens permitidas para CORS. "
            "Em produção, restringir ao domínio real da aplicação."
        ),
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=True,
        description="Permite envio de cookies/credenciais em requisições cross-origin.",
    )
    CORS_ALLOWED_METHODS: list[str] = Field(
        default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        description="Métodos HTTP permitidos em requisições CORS.",
    )
    CORS_ALLOWED_HEADERS: list[str] = Field(
        default=["Authorization", "Content-Type", "X-Request-ID"],
        description="Headers permitidos em requisições CORS.",
    )

    # ──────────────────────────────────────────────
    # Redis
    # ──────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="URL de conexão com o Redis para cache e rate limiting.",
    )
    REDIS_PASSWORD: SecretStr | None = Field(
        default=None,
        description="Senha do Redis, se configurada.",
    )
    REDIS_KEY_PREFIX: str = Field(
        default="aja:",
        description="Prefixo para todas as chaves armazenadas no Redis.",
    )
    REDIS_TTL_DEFAULT: int = Field(
        default=3600,
        ge=60,
        description="TTL padrão em segundos para entradas no cache Redis.",
    )

    # ──────────────────────────────────────────────
    # Celery (Processamento Assíncrono)
    # ──────────────────────────────────────────────
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="URL do broker de mensagens para o Celery.",
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        description="URL do backend de resultados do Celery.",
    )
    CELERY_TASK_ALWAYS_EAGER: bool = Field(
        default=False,
        description="Executa tarefas de forma síncrona (apenas para testes).",
    )
    CELERY_TASK_TIME_LIMIT: int = Field(
        default=300,
        ge=30,
        description="Tempo máximo em segundos para execução de uma tarefa Celery.",
    )

    # ──────────────────────────────────────────────
    # LLM — Anthropic (Claude)
    # ──────────────────────────────────────────────
    ANTHROPIC_API_KEY: SecretStr = Field(
        ...,
        description="Chave de API da Anthropic para acesso ao Claude.",
    )
    ANTHROPIC_MODEL: str = Field(
        default="claude-sonnet-4-20250514",
        description="Modelo Claude a ser utilizado nas análises jurídicas.",
    )
    ANTHROPIC_MAX_TOKENS: int = Field(
        default=4096,
        ge=256,
        le=200000,
        description="Número máximo de tokens na resposta do Claude.",
    )
    ANTHROPIC_TEMPERATURE: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "Temperatura para geração de texto. Valores baixos para análises "
            "jurídicas que exigem precisão."
        ),
    )
    ANTHROPIC_TIMEOUT: int = Field(
        default=120,
        ge=30,
        le=600,
        description="Timeout em segundos para chamadas à API da Anthropic.",
    )
    ANTHROPIC_MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Número máximo de tentativas em caso de falha na API Anthropic.",
    )
    ANTHROPIC_RETRY_BASE_DELAY: float = Field(
        default=1.0,
        ge=0.5,
        le=10.0,
        description="Delay base em segundos para retry exponencial (tenacity).",
    )

    # ──────────────────────────────────────────────
    # DataJud (API do Poder Judiciário)
    # ──────────────────────────────────────────────
    DATAJUD_API_BASE_URL: str = Field(
        default="https://datajud-wiki.cnj.jus.br/api",
        description="URL base da API DataJud do CNJ.",
    )
    DATAJUD_API_KEY: SecretStr | None = Field(
        default=None,
        description="Chave de API para acesso ao DataJud (se necessária).",
    )
    DATAJUD_TIMEOUT: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Timeout em segundos para chamadas à API DataJud.",
    )

    # ──────────────────────────────────────────────
    # Upload de Arquivos
    # ──────────────────────────────────────────────
    UPLOAD_MAX_FILE_SIZE_MB: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Tamanho máximo de arquivo para upload em megabytes.",
    )
    UPLOAD_ALLOWED_EXTENSIONS: list[str] = Field(
        default=[".pdf", ".docx", ".doc", ".txt", ".odt"],
        description="Extensões de arquivo permitidas para upload.",
    )
    UPLOAD_STORAGE_PATH: str = Field(
        default="./storage/uploads",
        description="Caminho local para armazenamento de arquivos enviados.",
    )

    # ──────────────────────────────────────────────
    # Rate Limiting (slowapi)
    # ──────────────────────────────────────────────
    RATE_LIMIT_DEFAULT: str = Field(
        default="100/minute",
        description="Limite padrão de requisições por minuto para endpoints gerais.",
    )
    RATE_LIMIT_AUTH: str = Field(
        default="10/minute",
        description="Limite de requisições por minuto para endpoints de autenticação.",
    )
    RATE_LIMIT_LLM: str = Field(
        default="20/minute",
        description="Limite de requisições por minuto para endpoints que consomem LLM.",
    )

    # ──────────────────────────────────────────────
    # Busca Vetorial (FAISS / Milvus — decisão pendente G002 ADR)
    # ──────────────────────────────────────────────
    VECTOR_STORE_TYPE: str = Field(
        default="faiss",
        description="Tipo de índice vetorial: 'faiss' (local) ou 'milvus' (distribuído). Decisão pendente G002 ADR.",
    )
    VECTOR_STORE_PATH: str = Field(
        default="./storage/vector_index",
        description="Caminho para armazenamento do índice FAISS local.",
    )
    MILVUS_HOST: str = Field(
        default="localhost",
        description="Host do servidor Milvus (se VECTOR_STORE_TYPE='milvus').",
    )
    MILVUS_PORT: int = Field(
        default=19530,
        description="Porta do servidor Milvus.",
    )

    # ──────────────────────────────────────────────
    # Auditoria e Segurança
    # ──────────────────────────────────────────────
    AUDIT_LOG_ENABLED: bool = Field(
        default=True,
        description="Habilita registro de trilha de auditoria para ações sensíveis.",
    )
    SESSION_MAX_CONCURRENT: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Número máximo de sessões simultâneas por usuário.",
    )

    # ──────────────────────────────────────────────
    # Validadores
    # ──────────────────────────────────────────────

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """Valida que o ambiente é um dos valores permitidos."""
        allowed = {"development", "staging", "production", "testing"}
        if v.lower() not in allowed:
            raise ValueError(
                f"Ambiente inválido: '{v}'. Valores permitidos: {', '.join(sorted(allowed))}"
            )
        return v.lower()

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Valida que o nível de log é válido."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in allowed:
            raise ValueError(
                f"Nível de log inválido: '{v}'. Valores permitidos: {', '.join(sorted(allowed))}"
            )
        return upper_v

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        """Valida que o algoritmo JWT é suportado."""
        allowed = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}
        if v.upper() not in allowed:
            raise ValueError(
                f"Algoritmo JWT inválido: '{v}'. Valores permitidos: {', '.join(sorted(allowed))}"
            )
        return v.upper()

    @field_validator("VECTOR_STORE_TYPE")
    @classmethod
    def validate_vector_store_type(cls, v: str) -> str:
        """Valida o tipo de armazenamento vetorial."""
        allowed = {"faiss", "milvus"}
        if v.lower() not in allowed:
            raise ValueError(
                f"Tipo de armazenamento vetorial inválido: '{v}'. "
                f"Valores permitidos: {', '.join(sorted(allowed))}"
            )
        return v.lower()

    @model_validator(mode="after")
    def validate_jwt_keys_for_rsa(self) -> "Settings":
        """Valida que chaves RSA estão presentes quando o algoritmo é RS*."""
        if self.JWT_ALGORITHM.startswith("RS"):
            if self.APP_ENV == "production":
                if not self.JWT_PRIVATE_KEY or not self.JWT_PUBLIC_KEY:
                    raise ValueError(
                        f"Para o algoritmo {self.JWT_ALGORITHM} em produção, "
                        "é obrigatório configurar JWT_PRIVATE_KEY e JWT_PUBLIC_KEY."
                    )
        return self

    @model_validator(mode="after")
    def validate_cors_in_production(self) -> "Settings":
        """Valida que CORS não permite origens inseguras em produção."""
        if self.APP_ENV == "production":
            insecure_origins = {"*", "http://localhost:5173", "http://localhost:3000"}
            for origin in self.CORS_ALLOWED_ORIGINS:
                if origin in insecure_origins:
                    raise ValueError(
                        f"Origem CORS insegura detectada em produção: '{origin}'. "
                        "Configure apenas domínios reais e com HTTPS."
                    )
        return self

    @model_validator(mode="after")
    def validate_debug_not_in_production(self) -> "Settings":
        """Impede que o modo debug esteja ativo em produção."""
        if self.APP_ENV == "production" and self.DEBUG:
            raise ValueError(
                "O modo DEBUG não pode estar ativo em ambiente de produção."
            )
        return self

    # ──────────────────────────────────────────────
    # Propriedades computadas
    # ──────────────────────────────────────────────

    @property
    def upload_max_file_size_bytes(self) -> int:
        """Retorna o tamanho máximo de upload em bytes."""
        return self.UPLOAD_MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        """Verifica se a aplicação está em ambiente de produção."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Verifica se a aplicação está em ambiente de desenvolvimento."""
        return self.APP_ENV == "development"

    @property
    def is_testing(self) -> bool:
        """Verifica se a aplicação está em ambiente de testes."""
        return self.APP_ENV == "testing"

    @property
    def database_url_sync(self) -> str:
        """Retorna a URL do banco de dados no formato síncrono (para Alembic)."""
        url = self.DATABASE_URL.get_secret_value()
        return url.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna a instância singleton das configurações da aplicação.

    Utiliza lru_cache para garantir que as configurações sejam carregadas
    e validadas apenas uma vez durante o ciclo de vida da aplicação.

    Returns:
        Settings: Instância validada das configurações.

    Raises:
        pydantic.ValidationError: Se alguma variável obrigatória estiver
            ausente ou com valor inválido.
    """
    return Settings()  # type: ignore[call-arg]
