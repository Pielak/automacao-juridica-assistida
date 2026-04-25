# Guia de Deployment com Docker Compose

## Automação Jurídica Assistida

> Guia completo para configuração, execução e troubleshooting do ambiente Docker Compose do projeto **Automação Jurídica Assistida**.

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Estrutura dos Serviços](#2-estrutura-dos-serviços)
3. [Configuração Inicial](#3-configuração-inicial)
4. [Variáveis de Ambiente](#4-variáveis-de-ambiente)
5. [Comandos Essenciais](#5-comandos-essenciais)
6. [Build e Execução](#6-build-e-execução)
7. [Migrações de Banco de Dados](#7-migrações-de-banco-de-dados)
8. [Volumes e Persistência](#8-volumes-e-persistência)
9. [Rede e Comunicação entre Serviços](#9-rede-e-comunicação-entre-serviços)
10. [Monitoramento e Logs](#10-monitoramento-e-logs)
11. [Troubleshooting](#11-troubleshooting)
12. [Ambientes (Desenvolvimento vs Produção)](#12-ambientes-desenvolvimento-vs-produção)
13. [Segurança](#13-segurança)
14. [Referências](#14-referências)

---

## 1. Pré-requisitos

### Software Obrigatório

| Ferramenta       | Versão Mínima | Verificação                  |
|------------------|---------------|------------------------------|
| Docker Engine    | 24.0+         | `docker --version`           |
| Docker Compose   | 2.20+ (V2)    | `docker compose version`     |
| Git              | 2.30+         | `git --version`              |

### Recursos de Hardware Recomendados

| Recurso   | Desenvolvimento | Produção (mínimo) |
|-----------|-----------------|--------------------|
| CPU       | 2 cores         | 4 cores            |
| RAM       | 4 GB            | 8 GB               |
| Disco     | 10 GB livres    | 40 GB livres       |

### Sistema Operacional

- **Linux** (Ubuntu 22.04+, Debian 12+): recomendado para produção.
- **macOS** (com Docker Desktop 4.20+): adequado para desenvolvimento.
- **Windows** (com WSL2 + Docker Desktop): adequado para desenvolvimento.

---

## 2. Estrutura dos Serviços

O `docker-compose.yml` orquestra os seguintes serviços:

```
┌─────────────────────────────────────────────────────────┐
│                      Nginx (proxy)                      │
│                    Porta: 80 / 443                      │
├──────────────────────┬──────────────────────────────────┤
│   Frontend (React)   │        Backend (FastAPI)         │
│   Vite Dev / Build   │        Porta interna: 8000       │
├──────────────────────┴──────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ PostgreSQL  │  │    Redis    │  │  Celery Worker  │ │
│  │  Porta 5432 │  │  Porta 6379 │  │  (background)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Descrição dos Serviços

| Serviço        | Imagem Base                | Propósito                                                    |
|----------------|----------------------------|--------------------------------------------------------------|
| **backend**    | `python:3.11-slim`         | API REST FastAPI com documentação OpenAPI automática         |
| **frontend**   | `node:20-alpine`           | SPA React (Vite) — dev server ou build estático              |
| **postgres**   | `postgres:16-alpine`       | Banco de dados relacional principal                          |
| **redis**      | `redis:7-alpine`           | Cache, broker de filas (Celery) e sessões                    |
| **nginx**      | `nginx:1.25-alpine`        | Proxy reverso, servir arquivos estáticos, TLS termination    |
| **worker**     | Mesmo do backend           | Celery worker para tarefas assíncronas (análise IA, etc.)    |

---

## 3. Configuração Inicial

### Passo a Passo

```bash
# 1. Clonar o repositório
git clone https://github.com/sua-org/automacao-juridica-assistida.git
cd automacao-juridica-assistida

# 2. Copiar o arquivo de variáveis de ambiente
cp .env.example .env

# 3. Editar o .env com suas configurações
# IMPORTANTE: Nunca commite o arquivo .env no repositório!
nano .env  # ou use seu editor preferido

# 4. Criar diretórios necessários para volumes (se não existirem)
mkdir -p data/postgres data/redis data/uploads

# 5. Subir todos os serviços
docker compose up -d

# 6. Verificar se todos os containers estão rodando
docker compose ps

# 7. Executar migrações do banco de dados
docker compose exec backend alembic upgrade head

# 8. (Opcional) Criar usuário administrador inicial
docker compose exec backend python -m scripts.create_admin
```

---

## 4. Variáveis de Ambiente

### Arquivo `.env.example`

Abaixo estão todas as variáveis de ambiente utilizadas pelo projeto. Copie para `.env` e preencha conforme seu ambiente.

```env
# ==============================================================================
# GERAL
# ==============================================================================
ENVIRONMENT=development          # development | staging | production
DEBUG=true                        # true | false — desabilitar em produção
SECRET_KEY=ALTERE-PARA-CHAVE-SEGURA-COM-MINIMO-64-CARACTERES
ALLOWED_HOSTS=localhost,127.0.0.1

# ==============================================================================
# BACKEND — FastAPI
# ==============================================================================
BACKEND_PORT=8000
BACKEND_WORKERS=2                 # Número de workers uvicorn (produção: 4+)
BACKEND_LOG_LEVEL=info            # debug | info | warning | error
CORS_ORIGINS=http://localhost:3000,http://localhost:80

# ==============================================================================
# BANCO DE DADOS — PostgreSQL
# ==============================================================================
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=automacao_juridica
POSTGRES_USER=app_user
POSTGRES_PASSWORD=ALTERE-PARA-SENHA-SEGURA
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# ==============================================================================
# REDIS
# ==============================================================================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=ALTERE-PARA-SENHA-SEGURA
REDIS_URL=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/0
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/1
CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/2

# ==============================================================================
# AUTENTICAÇÃO — JWT
# ==============================================================================
JWT_SECRET_KEY=ALTERE-PARA-CHAVE-JWT-SEGURA-RS256
JWT_ALGORITHM=RS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ==============================================================================
# MFA — TOTP
# ==============================================================================
MFA_ISSUER_NAME=AutomacaoJuridica
MFA_ENABLED=true

# ==============================================================================
# ANTHROPIC — API Claude
# ==============================================================================
ANTHROPIC_API_KEY=sk-ant-ALTERE-PARA-SUA-CHAVE
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_MAX_TOKENS=4096
ANTHROPIC_TIMEOUT=120
ANTHROPIC_MAX_RETRIES=3

# ==============================================================================
# UPLOAD DE ARQUIVOS
# ==============================================================================
UPLOAD_MAX_SIZE_MB=50
UPLOAD_ALLOWED_EXTENSIONS=.pdf,.docx,.doc,.txt,.odt
UPLOAD_DIR=/app/uploads

# ==============================================================================
# NGINX
# ==============================================================================
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# ==============================================================================
# FRONTEND — React/Vite
# ==============================================================================
VITE_API_BASE_URL=http://localhost:80/api
VITE_APP_TITLE=Automação Jurídica Assistida
FRONTEND_PORT=3000

# ==============================================================================
# RATE LIMITING
# ==============================================================================
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_AUTH=20/minute
RATE_LIMIT_AI=10/minute
```

### Variáveis Críticas de Segurança

> ⚠️ **ATENÇÃO**: As variáveis abaixo DEVEM ser alteradas antes de qualquer deploy.

| Variável              | Descrição                                    | Como Gerar                                      |
|-----------------------|----------------------------------------------|--------------------------------------------------|
| `SECRET_KEY`          | Chave mestra da aplicação                    | `openssl rand -hex 64`                           |
| `POSTGRES_PASSWORD`   | Senha do banco de dados                      | `openssl rand -base64 32`                        |
| `REDIS_PASSWORD`      | Senha do Redis                               | `openssl rand -base64 32`                        |
| `JWT_SECRET_KEY`      | Chave para assinatura de tokens JWT          | `openssl genpkey -algorithm RSA -out jwt.pem`    |
| `ANTHROPIC_API_KEY`   | Chave de API da Anthropic (Claude)           | Obtida no console da Anthropic                   |

---

## 5. Comandos Essenciais

### Ciclo de Vida dos Containers

```bash
# Subir todos os serviços em background
docker compose up -d

# Subir com rebuild forçado das imagens
docker compose up -d --build

# Parar todos os serviços (mantém volumes)
docker compose stop

# Parar e remover containers (mantém volumes)
docker compose down

# Parar, remover containers E volumes (CUIDADO: apaga dados!)
docker compose down -v

# Reiniciar um serviço específico
docker compose restart backend

# Escalar workers do Celery
docker compose up -d --scale worker=3
```

### Logs

```bash
# Todos os logs em tempo real
docker compose logs -f

# Logs de um serviço específico
docker compose logs -f backend

# Últimas 100 linhas de um serviço
docker compose logs --tail=100 backend

# Logs com timestamps
docker compose logs -f -t backend
```

### Execução de Comandos

```bash
# Shell interativo no backend
docker compose exec backend bash

# Executar migrações Alembic
docker compose exec backend alembic upgrade head

# Criar nova migração Alembic
docker compose exec backend alembic revision --autogenerate -m "descricao_da_migracao"

# Shell do PostgreSQL
docker compose exec postgres psql -U app_user -d automacao_juridica

# CLI do Redis
docker compose exec redis redis-cli -a $REDIS_PASSWORD

# Executar testes
docker compose exec backend pytest -v

# Verificar saúde dos serviços
docker compose ps
```

---

## 6. Build e Execução

### Desenvolvimento

No modo de desenvolvimento, o backend roda com hot-reload (uvicorn `--reload`) e o frontend com o dev server do Vite (HMR).

```bash
# Subir ambiente de desenvolvimento
docker compose up -d

# O backend estará disponível em: http://localhost:8000
# A documentação OpenAPI em: http://localhost:8000/docs
# O frontend (via Vite) em: http://localhost:3000
# O proxy Nginx em: http://localhost:80
```

### Produção

Para produção, utilize o arquivo de override ou um compose file dedicado:

```bash
# Build otimizado para produção
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

#### Diferenças no modo produção:

| Aspecto               | Desenvolvimento                  | Produção                              |
|-----------------------|----------------------------------|---------------------------------------|
| Backend reload        | `--reload` ativo                 | Múltiplos workers uvicorn             |
| Frontend              | Vite dev server (HMR)            | Build estático servido pelo Nginx     |
| Debug                 | `DEBUG=true`                     | `DEBUG=false`                         |
| Logs                  | Nível `debug`                    | Nível `info` ou `warning`            |
| Volumes de código     | Bind mount (código local)        | Código copiado na imagem              |
| TLS/HTTPS             | Não configurado                  | Certificados via Let's Encrypt/certs  |
| Healthchecks          | Opcionais                        | Obrigatórios                          |

### Build Individual de Serviços

```bash
# Rebuild apenas do backend
docker compose build backend

# Rebuild sem cache (útil após mudanças em requirements)
docker compose build --no-cache backend

# Rebuild do frontend
docker compose build frontend
```

---

## 7. Migrações de Banco de Dados

O projeto utiliza **Alembic** para gerenciamento de migrações do PostgreSQL via SQLAlchemy 2.0.

```bash
# Verificar status atual das migrações
docker compose exec backend alembic current

# Aplicar todas as migrações pendentes
docker compose exec backend alembic upgrade head

# Reverter última migração
docker compose exec backend alembic downgrade -1

# Reverter todas as migrações (CUIDADO!)
docker compose exec backend alembic downgrade base

# Criar nova migração automática
docker compose exec backend alembic revision --autogenerate -m "adicionar_tabela_documentos"

# Criar migração manual (vazia)
docker compose exec backend alembic revision -m "seed_dados_iniciais"

# Ver histórico de migrações
docker compose exec backend alembic history
```

> **Dica**: Sempre revise as migrações geradas automaticamente antes de aplicar. O `--autogenerate` pode não capturar todas as alterações (ex.: mudanças em constraints, índices parciais).

---

## 8. Volumes e Persistência

### Volumes Nomeados

| Volume                | Serviço    | Caminho no Container    | Propósito                          |
|-----------------------|------------|-------------------------|------------------------------------||
| `postgres_data`       | postgres   | `/var/lib/postgresql/data` | Dados do banco de dados         |
| `redis_data`          | redis      | `/data`                 | Persistência do Redis              |
| `upload_data`         | backend    | `/app/uploads`          | Arquivos enviados pelos usuários   |

### Backup de Volumes

```bash
# Backup do PostgreSQL
docker compose exec postgres pg_dump -U app_user automacao_juridica > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore do PostgreSQL
cat backup_20240101_120000.sql | docker compose exec -T postgres psql -U app_user -d automacao_juridica

# Backup completo do volume PostgreSQL
docker run --rm \
  -v automacao-juridica-assistida_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres_data_$(date +%Y%m%d).tar.gz -C /data .

# Backup dos uploads
docker run --rm \
  -v automacao-juridica-assistida_upload_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/uploads_$(date +%Y%m%d).tar.gz -C /data .
```

---

## 9. Rede e Comunicação entre Serviços

Todos os serviços compartilham uma rede Docker interna. A comunicação entre eles usa os nomes dos serviços como hostnames.

```
┌──────────────────────────────────────────────────────┐
│                  Rede: app-network                    │
│                                                      │
│  nginx ──────► backend:8000                          │
│  nginx ──────► frontend:3000 (dev) / estático (prod) │
│  backend ────► postgres:5432                         │
│  backend ────► redis:6379                            │
│  worker ─────► postgres:5432                         │
│  worker ─────► redis:6379                            │
│  worker ─────► api.anthropic.com (externo)           │
│  backend ────► api.anthropic.com (externo)           │
└──────────────────────────────────────────────────────┘
```

### Portas Expostas ao Host

| Serviço    | Porta Interna | Porta no Host | Observação                          |
|------------|---------------|---------------|-------------------------------------|
| nginx      | 80            | 80            | Ponto de entrada principal          |
| nginx      | 443           | 443           | HTTPS (produção)                    |
| backend    | 8000          | 8000          | Acesso direto (dev apenas)          |
| frontend   | 3000          | 3000          | Vite dev server (dev apenas)        |
| postgres   | 5432          | 5432          | Acesso direto (dev apenas)          |
| redis      | 6379          | —             | Não exposto ao host (segurança)     |

> **Produção**: Exponha apenas as portas 80 e 443 do Nginx. Remova as portas expostas dos demais serviços.

---

## 10. Monitoramento e Logs

### Healthchecks

Os serviços possuem healthchecks configurados no `docker-compose.yml`:

```bash
# Verificar saúde de todos os serviços
docker compose ps

# Verificar healthcheck específico
docker inspect --format='{{json .State.Health}}' automacao-juridica-assistida-backend-1 | python -m json.tool
```

### Endpoints de Saúde

| Endpoint                | Serviço  | Descrição                                    |
|-------------------------|----------|----------------------------------------------|
| `GET /api/health`       | backend  | Status geral da API                          |
| `GET /api/health/db`    | backend  | Conectividade com PostgreSQL                 |
| `GET /api/health/redis` | backend  | Conectividade com Redis                      |

### Logs Estruturados

O backend utiliza **structlog** para logs estruturados em JSON:

```bash
# Filtrar logs de erro do backend
docker compose logs backend | grep '"level":"error"'

# Filtrar por request ID
docker compose logs backend | grep '"request_id":"abc-123"'

# Logs do Celery worker
docker compose logs -f worker
```

### Métricas de Containers

```bash
# Uso de recursos em tempo real
docker stats

# Uso de disco dos volumes
docker system df -v
```

---

## 11. Troubleshooting

### Problemas Comuns e Soluções

#### 🔴 Container do backend não inicia

**Sintoma**: O container `backend` reinicia em loop ou para imediatamente.

```bash
# 1. Verificar logs
docker compose logs backend

# 2. Causas comuns:
# - DATABASE_URL incorreta ou PostgreSQL ainda não está pronto
# - Erro de importação Python (dependência faltando)
# - Porta 8000 já em uso no host

# 3. Soluções:
# Verificar se o PostgreSQL está saudável
docker compose ps postgres

# Reconstruir a imagem
docker compose build --no-cache backend

# Verificar se a porta está livre
lsof -i :8000
```

#### 🔴 Erro de conexão com PostgreSQL

**Sintoma**: `Connection refused` ou `could not connect to server`.

```bash
# 1. Verificar se o PostgreSQL está rodando
docker compose ps postgres

# 2. Verificar logs do PostgreSQL
docker compose logs postgres

# 3. Testar conexão manualmente
docker compose exec postgres pg_isready -U app_user

# 4. Verificar variáveis de ambiente
docker compose exec backend env | grep POSTGRES

# 5. Se o volume estiver corrompido:
docker compose down
docker volume rm automacao-juridica-assistida_postgres_data
docker compose up -d
# ATENÇÃO: Isso apaga todos os dados do banco!
```

#### 🔴 Erro de conexão com Redis

**Sintoma**: `Connection refused` ao conectar no Redis.

```bash
# 1. Verificar se o Redis está rodando
docker compose ps redis

# 2. Testar conexão
docker compose exec redis redis-cli ping
# Resposta esperada: PONG

# 3. Se usa senha, testar com autenticação
docker compose exec redis redis-cli -a SUA_SENHA ping
```

#### 🔴 Migrações Alembic falham

**Sintoma**: Erro ao executar `alembic upgrade head`.

```bash
# 1. Verificar status atual
docker compose exec backend alembic current

# 2. Se há conflito de revisões
docker compose exec backend alembic heads
# Se houver múltiplos heads, fazer merge:
docker compose exec backend alembic merge heads -m "merge_conflito"

# 3. Se o banco está em estado inconsistente
# Marcar revisão manualmente (use com cuidado)
docker compose exec backend alembic stamp head
```

#### 🔴 Frontend não carrega / erro de CORS

**Sintoma**: Erros de CORS no console do navegador.

```bash
# 1. Verificar a variável CORS_ORIGINS no .env
# Deve incluir a URL exata do frontend
# Exemplo: CORS_ORIGINS=http://localhost:3000,http://localhost:80

# 2. Verificar configuração do Nginx
docker compose exec nginx cat /etc/nginx/conf.d/default.conf

# 3. Reiniciar o Nginx após alterações
docker compose restart nginx
```

#### 🔴 Upload de arquivos falha

**Sintoma**: Erro 413 (Request Entity Too Large) ou timeout.

```bash
# 1. Verificar limite no Nginx (client_max_body_size)
docker compose exec nginx cat /etc/nginx/nginx.conf | grep client_max_body_size

# 2. Verificar variável UPLOAD_MAX_SIZE_MB no .env

# 3. Verificar permissões do diretório de uploads
docker compose exec backend ls -la /app/uploads

# 4. Verificar espaço em disco
docker system df
```

#### 🔴 Worker Celery não processa tarefas

**Sintoma**: Tarefas ficam na fila mas não são executadas.

```bash
# 1. Verificar se o worker está rodando
docker compose ps worker

# 2. Verificar logs do worker
docker compose logs -f worker

# 3. Verificar conexão com o broker Redis
docker compose exec worker celery -A app.worker inspect ping

# 4. Listar tarefas ativas
docker compose exec worker celery -A app.worker inspect active

# 5. Listar tarefas na fila
docker compose exec redis redis-cli -a $REDIS_PASSWORD LLEN celery
```

#### 🔴 Erro de memória (OOM Kill)

**Sintoma**: Container é encerrado abruptamente.

```bash
# 1. Verificar se houve OOM kill
docker inspect --format='{{.State.OOMKilled}}' CONTAINER_NAME

# 2. Verificar uso de memória
docker stats --no-stream

# 3. Aumentar limites de memória no docker-compose.yml
# Adicionar em cada serviço:
#   deploy:
#     resources:
#       limits:
#         memory: 1G
```

#### 🔴 Lentidão geral

```bash
# 1. Verificar uso de recursos
docker stats

# 2. Verificar logs por queries lentas
docker compose logs backend | grep -i "slow\|timeout"

# 3. Verificar conexões do PostgreSQL
docker compose exec postgres psql -U app_user -d automacao_juridica \
  -c "SELECT count(*) FROM pg_stat_activity;"

# 4. Limpar recursos Docker não utilizados
docker system prune -f
```

### Resetar Ambiente Completamente

> ⚠️ **CUIDADO**: Este procedimento apaga TODOS os dados locais.

```bash
# Parar e remover tudo (containers, volumes, redes, imagens locais)
docker compose down -v --rmi local

# Remover volumes órfãos
docker volume prune -f

# Reconstruir do zero
docker compose up -d --build

# Reaplicar migrações
docker compose exec backend alembic upgrade head
```

---

## 12. Ambientes (Desenvolvimento vs Produção)

### Desenvolvimento

```bash
# Usar configuração padrão (docker-compose.yml)
docker compose up -d
```

Características:
- Hot-reload no backend (uvicorn `--reload`)
- HMR no frontend (Vite dev server)
- Bind mounts para código-fonte local
- Portas de debug expostas
- Logs em nível `debug`
- Documentação OpenAPI acessível (`/docs`, `/redoc`)

### Produção

```bash
# Usar override de produção
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

<!-- TODO: Criar arquivo docker-compose.prod.yml com as seguintes diferenças: -->
<!-- - Remover bind mounts de código -->
<!-- - Configurar múltiplos workers uvicorn -->
<!-- - Build estático do frontend servido pelo Nginx -->
<!-- - Habilitar TLS/HTTPS no Nginx -->
<!-- - Remover portas expostas desnecessárias -->
<!-- - Configurar restart: always em todos os serviços -->
<!-- - Adicionar limites de recursos (CPU/memória) -->
<!-- - Desabilitar documentação OpenAPI (/docs) -->

Checklist de produção:

- [ ] Todas as senhas e chaves foram alteradas (ver seção 4)
- [ ] `ENVIRONMENT=production` e `DEBUG=false`
- [ ] Certificados TLS configurados no Nginx
- [ ] Apenas portas 80/443 expostas ao host
- [ ] Backups automáticos configurados
- [ ] Monitoramento e alertas configurados
- [ ] Rate limiting ativo
- [ ] Logs em nível `info` ou superior
- [ ] Healthchecks ativos em todos os serviços
- [ ] `restart: always` em todos os serviços
- [ ] Limites de recursos (memory/CPU) definidos

---

## 13. Segurança

### Boas Práticas Implementadas

1. **Senhas e chaves**: Nunca hardcoded — sempre via variáveis de ambiente.
2. **Rede interna**: Serviços se comunicam via rede Docker isolada.
3. **Portas mínimas**: Em produção, apenas Nginx (80/443) é exposto.
4. **Imagens Alpine**: Superfície de ataque reduzida com imagens mínimas.
5. **Usuário não-root**: Containers rodam com usuário não privilegiado.
6. **Redis com senha**: Autenticação obrigatória no Redis.
7. **Rate limiting**: Proteção contra abuso via slowapi.

### Verificações de Segurança

```bash
# Escanear imagens por vulnerabilidades
docker scout cves automacao-juridica-assistida-backend

# Verificar se containers rodam como root
docker compose exec backend whoami
# Esperado: appuser (não root)

# Verificar variáveis sensíveis não vazam nos logs
docker compose logs backend | grep -i "password\|secret\|api_key"
# Esperado: nenhum resultado
```

### Rotação de Credenciais

```bash
# 1. Atualizar senhas no .env
nano .env

# 2. Reiniciar serviços afetados
docker compose restart backend worker

# 3. Para rotação de senha do PostgreSQL:
docker compose exec postgres psql -U postgres -c "ALTER USER app_user PASSWORD 'nova_senha';"
# Atualizar POSTGRES_PASSWORD no .env e reiniciar backend
```

---

## 14. Referências

- [Documentação oficial do Docker Compose](https://docs.docker.com/compose/)
- [FastAPI — Deployment](https://fastapi.tiangolo.com/deployment/docker/)
- [Alembic — Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Vite — Guia de Build](https://vitejs.dev/guide/build.html)
- [Nginx — Proxy Reverso](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Anthropic API — Documentação](https://docs.anthropic.com/)

---

> **Última atualização**: Gerado como parte do scaffold inicial do projeto.  
> **Responsável**: Equipe de DevOps / Engenharia  
> **Projeto**: Automação Jurídica Assistida
