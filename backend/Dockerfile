# =============================================================================
# Dockerfile — Imagem multi-stage do backend Python com Uvicorn
# Projeto: Automação Jurídica Assistida
# Descrição: Build multi-stage otimizado para produção. Utiliza imagem slim
#            do Python 3.11, instala dependências via pip com cache de camadas
#            e executa o servidor ASGI Uvicorn com configurações seguras.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder — instala dependências e prepara o pacote
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Metadados da imagem
LABEL maintainer="Equipe Automação Jurídica <dev@automacaojuridica.com.br>"
LABEL description="Backend da plataforma de Automação Jurídica Assistida"

# Variáveis de ambiente para otimizar o build Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instala dependências de sistema necessárias para compilação de pacotes nativos
# (ex: asyncpg, bcrypt, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copia apenas os arquivos de definição de dependências primeiro
# para aproveitar o cache de camadas do Docker
COPY pyproject.toml README.md ./

# Cria um diretório src mínimo para que o hatchling consiga resolver o pacote
# durante a instalação em modo editável ou build
RUN mkdir -p src/automacao_juridica_assistida && \
    touch src/automacao_juridica_assistida/__init__.py

# Instala as dependências do projeto em um virtualenv isolado
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instala o projeto e suas dependências
# Usa --no-cache-dir para reduzir tamanho da imagem
RUN pip install --upgrade pip setuptools wheel && \
    pip install .

# ---------------------------------------------------------------------------
# Stage 2: Runtime — imagem final enxuta para produção
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

LABEL maintainer="Equipe Automação Jurídica <dev@automacaojuridica.com.br>"
LABEL description="Backend da plataforma de Automação Jurídica Assistida — Runtime"

# Variáveis de ambiente para runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Diretório da aplicação
    APP_HOME=/app \
    # Configurações do Uvicorn (podem ser sobrescritas via docker-compose ou k8s)
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    UVICORN_WORKERS=4 \
    UVICORN_LOG_LEVEL=info \
    # Ambiente padrão
    ENVIRONMENT=production

# Instala apenas dependências de runtime (libpq para asyncpg/psycopg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root para segurança
# (nunca executar containers em produção como root)
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Copia o virtualenv do stage builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Cria diretório da aplicação
RUN mkdir -p ${APP_HOME} && chown appuser:appuser ${APP_HOME}
WORKDIR ${APP_HOME}

# Copia o código-fonte da aplicação
COPY --chown=appuser:appuser . .

# Troca para o usuário não-root
USER appuser

# Expõe a porta do servidor (documentação; não publica automaticamente)
EXPOSE ${UVICORN_PORT}

# Healthcheck — verifica se a API está respondendo
# O endpoint /docs é gerado automaticamente pelo FastAPI
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:${UVICORN_PORT}/docs || exit 1

# Usa tini como init process para tratamento correto de sinais (SIGTERM, etc.)
ENTRYPOINT ["tini", "--"]

# Comando padrão: inicia o Uvicorn apontando para a aplicação FastAPI
# TODO: Ajustar o path do módulo da aplicação (ex: src.main:app) quando
#       o módulo principal do FastAPI for criado. O path abaixo assume
#       que existe um arquivo `src/main.py` com a instância `app` do FastAPI.
CMD ["sh", "-c", "uvicorn src.main:app --host ${UVICORN_HOST} --port ${UVICORN_PORT} --workers ${UVICORN_WORKERS} --log-level ${UVICORN_LOG_LEVEL} --proxy-headers --forwarded-allow-ips='*' --access-log"]
