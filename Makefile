# ==============================================================================
# Automação Jurídica Assistida — Makefile
# ==============================================================================
# Atalhos de desenvolvimento para operações comuns do projeto.
#
# Uso:
#   make help        — Lista todos os comandos disponíveis
#   make dev         — Sobe ambiente de desenvolvimento completo
#   make build       — Build de produção (frontend + backend)
#   make test        — Executa todos os testes
#   make lint        — Executa linters e formatadores
#   make migrate     — Executa migrações do banco de dados
#   make docker-up   — Sobe todos os containers via Docker Compose
# ==============================================================================

.DEFAULT_GOAL := help

# ------------------------------------------------------------------------------
# Variáveis
# ------------------------------------------------------------------------------
SHELL := /bin/bash
.ONESHELL:

# Caminhos do projeto
BACKEND_DIR := backend
FRONTEND_DIR := frontend

# Python
PYTHON := python3
PIP := pip
UVICORN := uvicorn
ALEMBIC := alembic
CELERY := celery

# Node / Frontend
NPM := npm
PNPM := pnpm

# Docker
DOCKER_COMPOSE := docker compose
DOCKER_COMPOSE_FILE := docker-compose.yml

# Cores para output no terminal
COLOR_RESET := \033[0m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_CYAN := \033[36m
COLOR_BOLD := \033[1m

# ------------------------------------------------------------------------------
# Ajuda
# ------------------------------------------------------------------------------
.PHONY: help
help: ## Exibe esta mensagem de ajuda
	@echo ""
	@echo "$(COLOR_BOLD)$(COLOR_CYAN)╔══════════════════════════════════════════════════════════════╗$(COLOR_RESET)"
	@echo "$(COLOR_BOLD)$(COLOR_CYAN)║       Automação Jurídica Assistida — Comandos Make          ║$(COLOR_RESET)"
	@echo "$(COLOR_BOLD)$(COLOR_CYAN)╚══════════════════════════════════════════════════════════════╝$(COLOR_RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(COLOR_GREEN)%-20s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""

# ------------------------------------------------------------------------------
# Ambiente de Desenvolvimento
# ------------------------------------------------------------------------------
.PHONY: dev
dev: ## Sobe ambiente de desenvolvimento completo (backend + frontend + infra)
	@echo "$(COLOR_CYAN)▶ Subindo infraestrutura (PostgreSQL, Redis)...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) up -d postgres redis
	@echo "$(COLOR_CYAN)▶ Aguardando serviços de infraestrutura ficarem saudáveis...$(COLOR_RESET)"
	@sleep 3
	@echo "$(COLOR_CYAN)▶ Iniciando backend (FastAPI) e frontend (Vite) em paralelo...$(COLOR_RESET)"
	$(MAKE) -j2 dev-backend dev-frontend

.PHONY: dev-backend
dev-backend: ## Inicia o backend FastAPI em modo desenvolvimento
	@echo "$(COLOR_GREEN)▶ Iniciando FastAPI (modo dev com hot-reload)...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

.PHONY: dev-frontend
dev-frontend: ## Inicia o frontend Vite em modo desenvolvimento
	@echo "$(COLOR_GREEN)▶ Iniciando Vite dev server...$(COLOR_RESET)"
	cd $(FRONTEND_DIR) && \
	$(PNPM) dev

.PHONY: dev-worker
dev-worker: ## Inicia o Celery worker em modo desenvolvimento
	@echo "$(COLOR_GREEN)▶ Iniciando Celery worker (modo dev)...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(CELERY) -A app.worker worker --loglevel=debug --concurrency=2

# ------------------------------------------------------------------------------
# Instalação de Dependências
# ------------------------------------------------------------------------------
.PHONY: install
install: install-backend install-frontend ## Instala todas as dependências (backend + frontend)

.PHONY: install-backend
install-backend: ## Instala dependências Python do backend
	@echo "$(COLOR_CYAN)▶ Instalando dependências do backend...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(PIP) install --upgrade pip && \
	$(PIP) install -r requirements.txt -r requirements-dev.txt

.PHONY: install-frontend
install-frontend: ## Instala dependências Node do frontend
	@echo "$(COLOR_CYAN)▶ Instalando dependências do frontend...$(COLOR_RESET)"
	cd $(FRONTEND_DIR) && \
	$(PNPM) install

# ------------------------------------------------------------------------------
# Build de Produção
# ------------------------------------------------------------------------------
.PHONY: build
build: build-backend build-frontend ## Build completo de produção
	@echo "$(COLOR_GREEN)✔ Build de produção concluído com sucesso.$(COLOR_RESET)"

.PHONY: build-backend
build-backend: ## Build do backend (verificação de tipos e coleta de estáticos)
	@echo "$(COLOR_CYAN)▶ Verificando tipos do backend com mypy...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(PYTHON) -m mypy app/ --ignore-missing-imports
	@echo "$(COLOR_GREEN)✔ Backend verificado.$(COLOR_RESET)"

.PHONY: build-frontend
build-frontend: ## Build de produção do frontend (Vite)
	@echo "$(COLOR_CYAN)▶ Executando build de produção do frontend...$(COLOR_RESET)"
	cd $(FRONTEND_DIR) && \
	$(PNPM) build
	@echo "$(COLOR_GREEN)✔ Frontend compilado em $(FRONTEND_DIR)/dist/$(COLOR_RESET)"

# ------------------------------------------------------------------------------
# Migrações de Banco de Dados (Alembic)
# ------------------------------------------------------------------------------
.PHONY: migrate
migrate: ## Executa todas as migrações pendentes do banco de dados
	@echo "$(COLOR_CYAN)▶ Executando migrações do banco de dados...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(ALEMBIC) upgrade head
	@echo "$(COLOR_GREEN)✔ Migrações aplicadas com sucesso.$(COLOR_RESET)"

.PHONY: migrate-create
migrate-create: ## Cria nova migração (uso: make migrate-create MSG="descricao da migracao")
	@if [ -z "$(MSG)" ]; then \
		echo "$(COLOR_YELLOW)⚠ Uso: make migrate-create MSG=\"descricao da migracao\"$(COLOR_RESET)"; \
		exit 1; \
	fi
	@echo "$(COLOR_CYAN)▶ Criando nova migração: $(MSG)...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"
	@echo "$(COLOR_GREEN)✔ Migração criada. Revise o arquivo gerado antes de aplicar.$(COLOR_RESET)"

.PHONY: migrate-rollback
migrate-rollback: ## Reverte a última migração aplicada
	@echo "$(COLOR_YELLOW)▶ Revertendo última migração...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(ALEMBIC) downgrade -1
	@echo "$(COLOR_GREEN)✔ Migração revertida.$(COLOR_RESET)"

.PHONY: migrate-history
migrate-history: ## Exibe histórico de migrações
	@echo "$(COLOR_CYAN)▶ Histórico de migrações:$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(ALEMBIC) history --verbose

.PHONY: migrate-current
migrate-current: ## Exibe a migração atual do banco
	cd $(BACKEND_DIR) && \
	$(ALEMBIC) current

# ------------------------------------------------------------------------------
# Linting e Formatação
# ------------------------------------------------------------------------------
.PHONY: lint
lint: lint-backend lint-frontend ## Executa linters em todo o projeto
	@echo "$(COLOR_GREEN)✔ Linting concluído.$(COLOR_RESET)"

.PHONY: lint-backend
lint-backend: ## Lint do backend (ruff + mypy)
	@echo "$(COLOR_CYAN)▶ Executando ruff (lint) no backend...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(PYTHON) -m ruff check app/ tests/ && \
	$(PYTHON) -m ruff format --check app/ tests/
	@echo "$(COLOR_CYAN)▶ Executando mypy no backend...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(PYTHON) -m mypy app/ --ignore-missing-imports

.PHONY: lint-frontend
lint-frontend: ## Lint do frontend (ESLint + Prettier check)
	@echo "$(COLOR_CYAN)▶ Executando ESLint no frontend...$(COLOR_RESET)"
	cd $(FRONTEND_DIR) && \
	$(PNPM) lint
	@echo "$(COLOR_CYAN)▶ Verificando formatação com Prettier...$(COLOR_RESET)"
	cd $(FRONTEND_DIR) && \
	$(PNPM) format:check

.PHONY: format
format: format-backend format-frontend ## Formata todo o código automaticamente
	@echo "$(COLOR_GREEN)✔ Formatação concluída.$(COLOR_RESET)"

.PHONY: format-backend
format-backend: ## Formata código Python (ruff format)
	@echo "$(COLOR_CYAN)▶ Formatando código Python...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(PYTHON) -m ruff format app/ tests/ && \
	$(PYTHON) -m ruff check --fix app/ tests/

.PHONY: format-frontend
format-frontend: ## Formata código TypeScript/React (Prettier)
	@echo "$(COLOR_CYAN)▶ Formatando código frontend...$(COLOR_RESET)"
	cd $(FRONTEND_DIR) && \
	$(PNPM) format

# ------------------------------------------------------------------------------
# Testes
# ------------------------------------------------------------------------------
.PHONY: test
test: test-backend test-frontend ## Executa todos os testes do projeto
	@echo "$(COLOR_GREEN)✔ Todos os testes passaram.$(COLOR_RESET)"

.PHONY: test-backend
test-backend: ## Executa testes do backend (pytest)
	@echo "$(COLOR_CYAN)▶ Executando testes do backend...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(PYTHON) -m pytest tests/ \
		-v \
		--tb=short \
		--strict-markers \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=80

.PHONY: test-backend-unit
test-backend-unit: ## Executa apenas testes unitários do backend
	@echo "$(COLOR_CYAN)▶ Executando testes unitários do backend...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(PYTHON) -m pytest tests/unit/ -v --tb=short

.PHONY: test-backend-integration
test-backend-integration: ## Executa apenas testes de integração do backend
	@echo "$(COLOR_CYAN)▶ Executando testes de integração do backend...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(PYTHON) -m pytest tests/integration/ -v --tb=short

.PHONY: test-frontend
test-frontend: ## Executa testes do frontend (Vitest)
	@echo "$(COLOR_CYAN)▶ Executando testes do frontend...$(COLOR_RESET)"
	cd $(FRONTEND_DIR) && \
	$(PNPM) test -- --run

.PHONY: test-frontend-watch
test-frontend-watch: ## Executa testes do frontend em modo watch
	cd $(FRONTEND_DIR) && \
	$(PNPM) test

.PHONY: test-e2e
test-e2e: ## Executa testes end-to-end (requer ambiente rodando)
	@echo "$(COLOR_CYAN)▶ Executando testes end-to-end...$(COLOR_RESET)"
	# TODO: Configurar Playwright ou Cypress para testes E2E
	@echo "$(COLOR_YELLOW)⚠ Testes E2E ainda não configurados. Veja TODO no Makefile.$(COLOR_RESET)"

# ------------------------------------------------------------------------------
# Docker
# ------------------------------------------------------------------------------
.PHONY: docker-up
docker-up: ## Sobe todos os containers via Docker Compose
	@echo "$(COLOR_CYAN)▶ Subindo containers...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) up -d
	@echo "$(COLOR_GREEN)✔ Containers iniciados. Use 'make docker-logs' para acompanhar.$(COLOR_RESET)"

.PHONY: docker-down
docker-down: ## Para e remove todos os containers
	@echo "$(COLOR_YELLOW)▶ Parando containers...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) down
	@echo "$(COLOR_GREEN)✔ Containers removidos.$(COLOR_RESET)"

.PHONY: docker-down-volumes
docker-down-volumes: ## Para containers e remove volumes (APAGA DADOS!)
	@echo "$(COLOR_YELLOW)⚠ ATENÇÃO: Isso apagará todos os dados dos volumes!$(COLOR_RESET)"
	@read -p "Tem certeza? [s/N] " confirm && [ "$$confirm" = "s" ] || exit 1
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) down -v
	@echo "$(COLOR_GREEN)✔ Containers e volumes removidos.$(COLOR_RESET)"

.PHONY: docker-build
docker-build: ## Reconstrói imagens Docker
	@echo "$(COLOR_CYAN)▶ Reconstruindo imagens Docker...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) build --no-cache

.PHONY: docker-logs
docker-logs: ## Exibe logs de todos os containers (follow)
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) logs -f

.PHONY: docker-ps
docker-ps: ## Lista status dos containers
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) ps

.PHONY: docker-restart
docker-restart: ## Reinicia todos os containers
	@echo "$(COLOR_CYAN)▶ Reiniciando containers...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) restart

.PHONY: docker-shell-backend
docker-shell-backend: ## Abre shell no container do backend
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) exec backend /bin/bash

.PHONY: docker-shell-db
docker-shell-db: ## Abre psql no container do PostgreSQL
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) exec postgres psql -U $${POSTGRES_USER:-app} -d $${POSTGRES_DB:-automacao_juridica}

# ------------------------------------------------------------------------------
# Segurança
# ------------------------------------------------------------------------------
.PHONY: security-check
security-check: ## Verifica vulnerabilidades nas dependências
	@echo "$(COLOR_CYAN)▶ Verificando vulnerabilidades no backend (pip-audit)...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(PYTHON) -m pip_audit -r requirements.txt || true
	@echo "$(COLOR_CYAN)▶ Verificando vulnerabilidades no frontend (pnpm audit)...$(COLOR_RESET)"
	cd $(FRONTEND_DIR) && \
	$(PNPM) audit || true

# ------------------------------------------------------------------------------
# Utilitários
# ------------------------------------------------------------------------------
.PHONY: clean
clean: ## Remove artefatos de build, cache e arquivos temporários
	@echo "$(COLOR_CYAN)▶ Limpando artefatos...$(COLOR_RESET)"
	# Cache Python
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	# Coverage
	rm -rf $(BACKEND_DIR)/htmlcov $(BACKEND_DIR)/.coverage
	# Frontend
	rm -rf $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/node_modules/.vite
	@echo "$(COLOR_GREEN)✔ Artefatos removidos.$(COLOR_RESET)"

.PHONY: env-setup
env-setup: ## Cria arquivo .env a partir do .env.example
	@if [ -f .env ]; then \
		echo "$(COLOR_YELLOW)⚠ Arquivo .env já existe. Renomeie-o antes de gerar um novo.$(COLOR_RESET)"; \
	else \
		cp .env.example .env; \
		echo "$(COLOR_GREEN)✔ Arquivo .env criado. Edite-o com suas configurações.$(COLOR_RESET)"; \
	fi

.PHONY: seed
seed: ## Popula o banco com dados iniciais de desenvolvimento
	@echo "$(COLOR_CYAN)▶ Populando banco com dados de desenvolvimento...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(PYTHON) -m app.scripts.seed
	# TODO: Criar script app/scripts/seed.py com dados iniciais (usuários, perfis RBAC, etc.)

.PHONY: openapi-export
openapi-export: ## Exporta o schema OpenAPI para arquivo JSON
	@echo "$(COLOR_CYAN)▶ Exportando schema OpenAPI...$(COLOR_RESET)"
	cd $(BACKEND_DIR) && \
	$(PYTHON) -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))" > openapi.json
	@echo "$(COLOR_GREEN)✔ Schema exportado para $(BACKEND_DIR)/openapi.json$(COLOR_RESET)"

.PHONY: setup
setup: env-setup install migrate seed ## Setup completo do projeto (primeira vez)
	@echo ""
	@echo "$(COLOR_BOLD)$(COLOR_GREEN)╔══════════════════════════════════════════════════════════════╗$(COLOR_RESET)"
	@echo "$(COLOR_BOLD)$(COLOR_GREEN)║  ✔ Projeto configurado com sucesso!                         ║$(COLOR_RESET)"
	@echo "$(COLOR_BOLD)$(COLOR_GREEN)║  Execute 'make dev' para iniciar o desenvolvimento.         ║$(COLOR_RESET)"
	@echo "$(COLOR_BOLD)$(COLOR_GREEN)╚══════════════════════════════════════════════════════════════╝$(COLOR_RESET)"
	@echo ""

.PHONY: check
check: lint test security-check ## Executa todas as verificações (lint + test + segurança)
	@echo "$(COLOR_GREEN)✔ Todas as verificações passaram. Código pronto para commit.$(COLOR_RESET)"
