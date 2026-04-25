# Documentação — Automação Jurídica Assistida

Bem-vindo à documentação do projeto **Automação Jurídica Assistida**. Este índice centraliza todos os recursos necessários para entender, desenvolver, implantar e contribuir com o sistema.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Stack Tecnológica](#stack-tecnológica)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Guia de Início Rápido](#guia-de-início-rápido)
- [Documentação da API](#documentação-da-api)
- [Módulos do Sistema](#módulos-do-sistema)
- [Deployment](#deployment)
- [Segurança](#segurança)
- [Guia de Contribuição](#guia-de-contribuição)
- [ADRs — Registros de Decisão Arquitetural](#adrs--registros-de-decisão-arquitetural)
- [Referências](#referências)

---

## Visão Geral

O **Automação Jurídica Assistida** é uma plataforma web para automação de processos jurídicos com assistência de inteligência artificial. O sistema permite:

- **Gestão de documentos jurídicos** — upload, versionamento e ciclo de vida completo
- **Análise assistida por IA** — integração com Claude (Anthropic) para análise semântica de documentos
- **Chat jurídico inteligente** — interface conversacional para consultas sobre documentos e jurisprudência
- **Integração com DataJud** — consulta e acompanhamento de processos judiciais
- **Auditoria completa** — rastreabilidade de todas as ações para compliance jurídico
- **Controle de acesso granular** — RBAC com autenticação multifator (MFA)

---

## Arquitetura

### Estilo Arquitetural

**Monólito Modular com Clean Architecture (Ports & Adapters)**

Esta abordagem foi escolhida para permitir evolução incremental sem a complexidade prematura de microserviços. Cada módulo funcional é isolado com interfaces bem definidas.

### Camadas

```
┌─────────────────────────────────────────────────┐
│              PRESENTATION (React SPA)            │
│   Vite + TypeScript + React 18 + Tailwind CSS   │
├─────────────────────────────────────────────────┤
│                 Nginx (Proxy Reverso)            │
├─────────────────────────────────────────────────┤
│              API LAYER (FastAPI REST)            │
│   Routers modulares · Middleware JWT · OpenAPI   │
├─────────────────────────────────────────────────┤
│           APPLICATION LAYER (Use Cases)          │
│   Services · Ports · DTOs · Regras de Negócio   │
├─────────────────────────────────────────────────┤
│             DOMAIN LAYER (Entidades)             │
│   Modelos de domínio · Value Objects · Enums    │
├─────────────────────────────────────────────────┤
│         INFRASTRUCTURE LAYER (Adapters)          │
│   PostgreSQL · Redis · Celery · Anthropic SDK   │
└─────────────────────────────────────────────────┘
```

### Diagrama de Módulos

```
┌──────────┐  ┌────────────┐  ┌──────────┐  ┌────────┐  ┌───────┐
│   Auth   │  │  Documents  │  │ Analysis │  │  Chat  │  │ Audit │
│          │  │             │  │          │  │        │  │       │
│ JWT/MFA  │  │ Upload/CRUD │  │ IA/NLP   │  │ Claude │  │ Logs  │
│ RBAC     │  │ Versionamento│ │ DataJud  │  │ RAG    │  │ Trail │
└──────────┘  └────────────┘  └──────────┘  └────────┘  └───────┘
```

Para detalhes completos da arquitetura, consulte:

- [`docs/architecture/overview.md`](#) — Visão detalhada das camadas e fluxos
- [`docs/architecture/modules.md`](#) — Especificação de cada módulo
- [`docs/architecture/data-flow.md`](#) — Fluxos de dados entre componentes

<!-- TODO: Criar os arquivos de arquitetura detalhados listados acima -->

---

## Stack Tecnológica

### Frontend

| Tecnologia | Versão | Propósito |
|---|---|---|
| React | 18+ | Framework de UI |
| Vite | 5+ | Build tool e dev server |
| TypeScript | 5+ | Tipagem estática |
| React Hook Form + Zod | latest | Validação tipada de formulários |
| TanStack Query | latest | Gerenciamento de estado servidor/cache |
| React Router | v6 | Roteamento com guards de autenticação |
| Tailwind CSS | latest | Sistema de design responsivo |
| react-dropzone | latest | Upload de arquivos com validação |
| Axios | latest | Cliente HTTP com interceptors JWT |

### Backend

| Tecnologia | Versão | Propósito |
|---|---|---|
| Python | 3.11+ | Linguagem principal |
| FastAPI | 0.100+ | Framework web assíncrono |
| Pydantic | v2 | Serialização e validação |
| SQLAlchemy | 2.0 | ORM assíncrono |
| asyncpg | latest | Driver PostgreSQL assíncrono |
| Alembic | latest | Migrações de banco de dados |
| Celery | 5+ | Processamento assíncrono de tarefas |
| python-jose / PyJWT | latest | Autenticação JWT (RS256) |
| pyotp | latest | MFA via TOTP |
| httpx | latest | Cliente HTTP assíncrono |
| anthropic SDK | latest | Integração com Claude |
| structlog | latest | Logs estruturados |
| slowapi | latest | Rate limiting |
| tenacity | latest | Retry e circuit breaker |

### Infraestrutura

| Tecnologia | Propósito |
|---|---|
| PostgreSQL 15+ | Banco de dados principal |
| Redis | Cache, sessões e broker Celery |
| Nginx | Proxy reverso e servidor de estáticos |
| Docker + Docker Compose | Containerização e orquestração local |

---

## Estrutura do Projeto

```
automacao-juridica-assistida/
├── docs/                          # Documentação do projeto
│   ├── README.md                  # Este arquivo — índice da documentação
│   ├── architecture/              # Documentação de arquitetura
│   ├── api/                       # Documentação da API
│   ├── deployment/                # Guias de deployment
│   ├── adr/                       # Registros de Decisão Arquitetural
│   └── contributing/              # Guias de contribuição
├── frontend/                      # Aplicação React (SPA)
│   ├── src/
│   │   ├── components/            # Componentes reutilizáveis
│   │   ├── pages/                 # Páginas/rotas
│   │   ├── hooks/                 # Custom hooks
│   │   ├── services/              # Clientes de API
│   │   ├── stores/                # Estado global
│   │   ├── types/                 # Tipos TypeScript
│   │   └── utils/                 # Utilitários
│   ├── public/                    # Arquivos estáticos
│   ├── vite.config.ts             # Configuração do Vite
│   ├── tsconfig.json              # Configuração TypeScript
│   └── package.json               # Dependências frontend
├── backend/                       # Aplicação FastAPI
│   ├── app/
│   │   ├── main.py                # Ponto de entrada da aplicação
│   │   ├── core/                  # Configurações, segurança, dependências
│   │   ├── modules/               # Módulos funcionais
│   │   │   ├── auth/              # Autenticação e autorização
│   │   │   ├── users/             # Gestão de usuários
│   │   │   ├── documents/         # Gestão de documentos
│   │   │   ├── analysis/          # Análise assistida por IA
│   │   │   ├── chat/              # Chat jurídico inteligente
│   │   │   └── audit/             # Auditoria e logs
│   │   ├── domain/                # Entidades e regras de domínio
│   │   ├── infrastructure/        # Adaptadores (DB, cache, APIs externas)
│   │   └── shared/                # Código compartilhado entre módulos
│   ├── migrations/                # Migrações Alembic
│   ├── tests/                     # Testes automatizados
│   ├── alembic.ini                # Configuração Alembic
│   └── pyproject.toml             # Dependências e configuração Python
├── docker-compose.yml             # Orquestração de containers
├── .env.example                   # Variáveis de ambiente de exemplo
└── README.md                      # README principal do repositório
```

<!-- TODO: Atualizar a estrutura conforme o scaffold evolui -->

---

## Guia de Início Rápido

### Pré-requisitos

- **Docker** 24+ e **Docker Compose** v2+
- **Node.js** 20+ e **pnpm** 8+ (para desenvolvimento frontend)
- **Python** 3.11+ e **Poetry** 1.7+ (para desenvolvimento backend)
- **PostgreSQL** 15+ (se executando sem Docker)
- **Redis** 7+ (se executando sem Docker)

### Configuração com Docker (recomendado)

```bash
# 1. Clonar o repositório
git clone <url-do-repositorio>
cd automacao-juridica-assistida

# 2. Copiar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações (chaves API, secrets, etc.)

# 3. Subir todos os serviços
docker compose up -d

# 4. Executar migrações do banco de dados
docker compose exec backend alembic upgrade head

# 5. Acessar a aplicação
# Frontend: http://localhost:3000
# Backend (API docs): http://localhost:8000/docs
# Backend (ReDoc): http://localhost:8000/redoc
```

### Configuração Manual (desenvolvimento)

#### Backend

```bash
cd backend

# Criar ambiente virtual e instalar dependências
poetry install

# Ativar ambiente virtual
poetry shell

# Executar migrações
alembic upgrade head

# Iniciar servidor de desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Iniciar worker Celery (em outro terminal)
celery -A app.core.celery_app worker --loglevel=info
```

#### Frontend

```bash
cd frontend

# Instalar dependências
pnpm install

# Iniciar servidor de desenvolvimento
pnpm dev

# Build de produção
pnpm build
```

### Executando Testes

```bash
# Backend — testes unitários e de integração
cd backend
pytest --cov=app tests/

# Frontend — testes unitários
cd frontend
pnpm test

# Frontend — testes e2e
pnpm test:e2e
```

---

## Documentação da API

### Documentação Interativa (auto-gerada)

O FastAPI gera documentação interativa automaticamente a partir dos schemas Pydantic:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### Endpoints Principais

| Módulo | Prefixo | Descrição |
|---|---|---|
| Auth | `/api/v1/auth` | Login, registro, refresh token, MFA |
| Usuários | `/api/v1/users` | CRUD de usuários e perfis RBAC |
| Documentos | `/api/v1/documents` | Upload, CRUD, versionamento |
| Análise | `/api/v1/analysis` | Análise de documentos via IA |
| Chat | `/api/v1/chat` | Chat jurídico inteligente |
| Auditoria | `/api/v1/audit` | Consulta de logs de auditoria |

### Autenticação

Todos os endpoints (exceto login e registro) requerem autenticação via **JWT Bearer Token**:

```
Authorization: Bearer <access_token>
```

- **Algoritmo**: RS256
- **Expiração do access token**: 15 minutos
- **Expiração do refresh token**: 7 dias
- **MFA**: TOTP obrigatório para perfis administrativos

Para documentação detalhada da API, consulte:

- [`docs/api/authentication.md`](#) — Fluxos de autenticação e autorização
- [`docs/api/endpoints.md`](#) — Referência completa de endpoints
- [`docs/api/error-codes.md`](#) — Códigos de erro e tratamento

<!-- TODO: Criar os arquivos de documentação da API listados acima -->

---

## Módulos do Sistema

### Auth — Autenticação e Autorização

Gerencia autenticação JWT com suporte a MFA (TOTP), controle de sessões e RBAC (Role-Based Access Control).

**Perfis de acesso:**
- `admin` — Acesso total ao sistema
- `advogado` — Gestão de documentos e análises
- `estagiario` — Visualização e edições limitadas
- `cliente` — Acesso somente leitura aos seus processos

### Documents — Gestão de Documentos

Upload, armazenamento, versionamento e ciclo de vida de documentos jurídicos. Suporta múltiplos formatos (PDF, DOCX, ODT) com validação de tipo e tamanho.

**Ciclo de vida do documento:**
```
Rascunho → Em Revisão → Aprovado → Assinado → Arquivado
                ↓
            Rejeitado → Rascunho
```

### Analysis — Análise Assistida por IA

Integração com Claude (Anthropic) para análise semântica de documentos jurídicos, extração de informações relevantes e sugestões automatizadas.

**Funcionalidades:**
- Resumo automático de peças processuais
- Extração de entidades (partes, datas, valores)
- Análise de risco e pontos de atenção
- Sugestões de jurisprudência relevante

### Chat — Chat Jurídico Inteligente

Interface conversacional para consultas sobre documentos, legislação e jurisprudência, utilizando RAG (Retrieval-Augmented Generation) com Claude.

### Audit — Auditoria e Compliance

Registro imutável de todas as ações do sistema para rastreabilidade e compliance com normas jurídicas (LGPD, OAB, CNJ).

---

## Deployment

### Ambientes

| Ambiente | Propósito | URL |
|---|---|---|
| Desenvolvimento | Desenvolvimento local | `localhost:3000` / `localhost:8000` |
| Staging | Testes de integração e QA | <!-- TODO: Definir URL de staging --> |
| Produção | Ambiente de produção | <!-- TODO: Definir URL de produção --> |

### Variáveis de Ambiente

Consulte o arquivo `.env.example` na raiz do projeto para a lista completa de variáveis de ambiente necessárias. As principais são:

| Variável | Descrição | Obrigatória |
|---|---|---|
| `DATABASE_URL` | URL de conexão PostgreSQL | Sim |
| `REDIS_URL` | URL de conexão Redis | Sim |
| `JWT_PRIVATE_KEY` | Chave privada RSA para JWT | Sim |
| `JWT_PUBLIC_KEY` | Chave pública RSA para JWT | Sim |
| `ANTHROPIC_API_KEY` | Chave de API da Anthropic | Sim |
| `SECRET_KEY` | Chave secreta da aplicação | Sim |
| `ALLOWED_ORIGINS` | Origens permitidas para CORS | Sim |
| `CELERY_BROKER_URL` | URL do broker Celery (Redis) | Sim |
| `LOG_LEVEL` | Nível de log (INFO, DEBUG, etc.) | Não |

Para guias detalhados de deployment, consulte:

- [`docs/deployment/docker.md`](#) — Deployment com Docker Compose
- [`docs/deployment/production.md`](#) — Checklist e guia de produção
- [`docs/deployment/monitoring.md`](#) — Monitoramento e observabilidade
- [`docs/deployment/backup.md`](#) — Estratégia de backup e recuperação

<!-- TODO: Criar os guias de deployment detalhados -->

---

## Segurança

### Medidas Implementadas

- **Autenticação**: JWT com RS256 + MFA (TOTP) obrigatório para admins
- **Autorização**: RBAC granular por módulo e recurso
- **Senhas**: Hashing com bcrypt (passlib)
- **Rate Limiting**: slowapi para proteção contra abuso
- **CORS**: Configuração restritiva por ambiente
- **CSP**: Content Security Policy via headers
- **Validação de entrada**: Pydantic v2 em todas as rotas
- **Upload seguro**: Validação de tipo MIME, tamanho máximo e varredura
- **Logs estruturados**: structlog com correlation ID por request
- **Auditoria**: Registro imutável de todas as ações sensíveis
- **LGPD**: Mecanismos de consentimento, anonimização e direito ao esquecimento

### Relatório de Segurança

Para reportar vulnerabilidades de segurança, **NÃO abra uma issue pública**. Envie um e-mail para:

<!-- TODO: Definir e-mail de segurança do projeto -->
`seguranca@<dominio-do-projeto>.com.br`

Para mais detalhes, consulte:

- [`docs/security/overview.md`](#) — Visão geral de segurança
- [`docs/security/authentication.md`](#) — Detalhes de autenticação e MFA
- [`docs/security/data-protection.md`](#) — Proteção de dados e LGPD

<!-- TODO: Criar os documentos de segurança detalhados -->

---

## Guia de Contribuição

### Fluxo de Trabalho

1. **Fork** o repositório (contribuidores externos) ou crie uma **branch** a partir de `develop`
2. Nomeie a branch seguindo o padrão: `feature/descricao`, `fix/descricao`, `docs/descricao`
3. Faça commits seguindo o padrão **Conventional Commits** em PT-BR:
   - `feat: adicionar validação de CPF no cadastro`
   - `fix: corrigir cálculo de prazo processual`
   - `docs: atualizar guia de deployment`
   - `refactor: extrair lógica de autenticação para service`
   - `test: adicionar testes para módulo de análise`
4. Abra um **Pull Request** para `develop` com descrição detalhada
5. Aguarde **code review** de pelo menos 1 revisor
6. Após aprovação, faça **squash merge**

### Padrões de Código

#### Python (Backend)

- **Formatter**: `black` (line-length=88)
- **Linter**: `ruff`
- **Type checker**: `mypy` (strict mode)
- **Docstrings**: Google style, em PT-BR
- **Testes**: `pytest` com cobertura mínima de 80%

```python
def calcular_prazo_processual(data_inicio: date, dias_uteis: int) -> date:
    """Calcula o prazo processual considerando dias úteis.

    Exclui finais de semana e feriados nacionais/estaduais
    conforme calendário do tribunal.

    Args:
        data_inicio: Data de início da contagem do prazo.
        dias_uteis: Quantidade de dias úteis do prazo.

    Returns:
        Data final do prazo processual.

    Raises:
        ValueError: Se a quantidade de dias úteis for negativa.
    """
    ...
```

#### TypeScript (Frontend)

- **Formatter**: `prettier`
- **Linter**: `eslint` com config recomendada para React + TypeScript
- **Testes**: `vitest` + `@testing-library/react`
- **JSDoc**: Em PT-BR para exports públicos

```typescript
/**
 * Hook para gerenciar o upload de documentos jurídicos.
 *
 * Realiza validação de tipo MIME, tamanho máximo e
 * envia o arquivo para a API com progresso em tempo real.
 *
 * @param options - Opções de configuração do upload
 * @returns Estado do upload e funções de controle
 */
export function useDocumentUpload(options: UploadOptions): UploadResult {
  // ...
}
```

### Idioma

- **Código** (nomes de variáveis, funções, classes): **Inglês**
- **Documentação** (docstrings, comentários, README): **Português (PT-BR)**
- **Commits**: **Português (PT-BR)** seguindo Conventional Commits
- **Issues e PRs**: **Português (PT-BR)**
- **Termos técnicos**: Manter em inglês (JWT, middleware, endpoint, etc.)

Para mais detalhes, consulte:

- [`docs/contributing/setup.md`](#) — Configuração do ambiente de desenvolvimento
- [`docs/contributing/code-style.md`](#) — Guia de estilo de código detalhado
- [`docs/contributing/testing.md`](#) — Guia de testes
- [`docs/contributing/review.md`](#) — Processo de code review

<!-- TODO: Criar os guias de contribuição detalhados -->

---

## ADRs — Registros de Decisão Arquitetural

Decisões arquiteturais significativas são documentadas como ADRs (Architecture Decision Records):

| ID | Título | Status |
|---|---|---|
| ADR-001 | Escolha de monólito modular vs microserviços | Aceita |
| ADR-002 | Índice vetorial para busca semântica (FAISS vs Milvus) | Pendente |
| ADR-003 | Estratégia de autenticação JWT com RS256 | Aceita |
| ADR-004 | Integração com Anthropic Claude para análise jurídica | Aceita |
| ADR-005 | Design tokens e sistema de design | Pendente |

<!-- TODO: Criar os arquivos ADR individuais em docs/adr/ seguindo o template -->

Template para novas ADRs: [`docs/adr/template.md`](#)

---

## Referências

### Documentação das Tecnologias

- [React](https://react.dev/) — Documentação oficial do React
- [Vite](https://vitejs.dev/) — Documentação oficial do Vite
- [TypeScript](https://www.typescriptlang.org/docs/) — Documentação oficial do TypeScript
- [FastAPI](https://fastapi.tiangolo.com/) — Documentação oficial do FastAPI
- [Pydantic v2](https://docs.pydantic.dev/latest/) — Documentação oficial do Pydantic
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) — Documentação oficial do SQLAlchemy
- [Celery](https://docs.celeryq.dev/) — Documentação oficial do Celery
- [Anthropic API](https://docs.anthropic.com/) — Documentação da API Claude

### Referências Jurídicas

- [API DataJud — CNJ](https://datajud-wiki.cnj.jus.br/) — Documentação da API do DataJud
- [LGPD — Lei nº 13.709/2018](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm) — Lei Geral de Proteção de Dados
- [Provimento nº 74/2018 — CNJ](https://atos.cnj.jus.br/atos/detalhar/2640) — Padrões mínimos de TI para segurança de dados no Poder Judiciário

### Padrões e Boas Práticas

- [Clean Architecture — Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Conventional Commits](https://www.conventionalcommits.org/pt-br/v1.0.0/)
- [12-Factor App](https://12factor.net/pt_br/)

---

## Contato e Suporte

<!-- TODO: Preencher com informações reais da equipe -->

- **Tech Lead**: A definir
- **E-mail da equipe**: A definir
- **Canal de comunicação**: A definir

---

> **Nota**: Esta documentação é um documento vivo e deve ser atualizada conforme o projeto evolui. Ao implementar novas funcionalidades ou tomar decisões arquiteturais, atualize a documentação correspondente.

*Última atualização: Gerado durante o scaffold inicial do projeto.*
