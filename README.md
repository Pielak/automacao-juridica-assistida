# Automação Jurídica Assistida

> Plataforma de automação jurídica assistida por inteligência artificial, projetada para auxiliar profissionais do Direito na análise, elaboração e gestão de documentos jurídicos com suporte de IA (Claude/Anthropic).

---

## Índice

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Stack Tecnológica](#stack-tecnológica)
- [Pré-requisitos](#pré-requisitos)
- [Configuração do Ambiente](#configuração-do-ambiente)
- [Executando o Projeto](#executando-o-projeto)
- [Estrutura de Diretórios](#estrutura-de-diretórios)
- [Módulos Funcionais](#módulos-funcionais)
- [Autenticação e Segurança](#autenticação-e-segurança)
- [Integração com IA (Anthropic/Claude)](#integração-com-ia-anthropicclaude)
- [Testes](#testes)
- [Migrações de Banco de Dados](#migrações-de-banco-de-dados)
- [Deploy](#deploy)
- [Contribuição](#contribuição)
- [Licença](#licença)

---

## Visão Geral

O **Automação Jurídica Assistida** é um sistema web que combina um portal autenticado (SPA) com uma API REST robusta para oferecer:

- **Análise inteligente de documentos jurídicos** com suporte de IA generativa (Claude da Anthropic)
- **Gestão do ciclo de vida de documentos** com state machine integrada
- **Chat assistido por IA** para consultas jurídicas contextualizadas
- **Integração com DataJud** para consulta e acompanhamento processual
- **Busca semântica** em bases de jurisprudência e documentos
- **Auditoria completa** de todas as operações para conformidade regulatória
- **Controle de acesso granular** via RBAC (Role-Based Access Control) com MFA

---

## Arquitetura

### Estilo: Monólito Modular com Clean Architecture

O projeto adota uma arquitetura de **monólito modular** seguindo os princípios de **Clean Architecture (Ports & Adapters)**. Essa abordagem permite evolução incremental sem a complexidade prematura de microserviços.

```
┌─────────────────────────────────────────────────────────┐
│                    APRESENTAÇÃO                         │
│         React SPA (Vite + TypeScript)                   │
│         Nginx (proxy reverso + estáticos)               │
├─────────────────────────────────────────────────────────┤
│                      API (FastAPI)                       │
│   Routers modulares │ Middleware JWT │ Rate Limiting     │
│   OpenAPI docs      │ Logging (correlation ID)          │
│   Validação Pydantic v2                                 │
├─────────────────────────────────────────────────────────┤
│                   APLICAÇÃO (Use Cases)                  │
│   Use cases por módulo │ Orquestração de regras         │
│   Ports (interfaces)   │ DTOs entre camadas             │
├─────────────────────────────────────────────────────────┤
│                      DOMÍNIO                            │
│   Entidades │ Value Objects │ Regras de negócio         │
│   Eventos de domínio │ Interfaces de repositório        │
├─────────────────────────────────────────────────────────┤
│                   INFRAESTRUTURA                        │
│   PostgreSQL (SQLAlchemy 2.0 + asyncpg)                 │
│   Redis (cache + sessões + broker Celery)               │
│   Anthropic SDK (Claude) │ FAISS/Milvus (vetorial)      │
│   Celery (tarefas assíncronas) │ S3/MinIO (arquivos)    │
└─────────────────────────────────────────────────────────┘
```

### Princípios Arquiteturais

- **Separação de responsabilidades**: cada camada tem papel bem definido
- **Inversão de dependência**: camadas internas não conhecem as externas
- **Módulos isolados**: auth, documents, analysis, chat, audit — cada um com interfaces próprias
- **Testabilidade**: ports permitem mocks e testes unitários sem infraestrutura

---

## Stack Tecnológica

### Frontend

| Tecnologia | Versão | Propósito |
|---|---|---|
| React | 18+ | Framework de UI |
| Vite | 5+ | Build tool com HMR instantâneo |
| TypeScript | 5+ | Tipagem estática |
| React Hook Form + Zod | latest | Validação tipada de formulários |
| TanStack Query | latest | Gerenciamento de estado servidor/cache |
| React Router | v6 | Roteamento com guards de autenticação |
| Tailwind CSS | latest | Sistema de design responsivo |
| Axios | latest | Cliente HTTP com interceptors JWT |
| react-dropzone | latest | Upload de arquivos com validação |

### Backend

| Tecnologia | Versão | Propósito |
|---|---|---|
| Python | 3.11+ | Linguagem principal |
| FastAPI | 0.100+ | Framework REST com OpenAPI automático |
| Pydantic | v2 | Serialização/validação de alta performance |
| SQLAlchemy | 2.0 | ORM assíncrono |
| asyncpg | latest | Driver PostgreSQL assíncrono |
| Alembic | latest | Migrações de banco de dados |
| Celery | 5+ | Processamento assíncrono de tarefas |
| python-jose / PyJWT | latest | Autenticação JWT (RS256) |
| pyotp | latest | MFA via TOTP |
| httpx | latest | Cliente HTTP assíncrono |
| anthropic | latest | SDK oficial da Anthropic (Claude) |
| tenacity | latest | Retry e circuit breaker |
| slowapi | latest | Rate limiting |
| structlog | latest | Logs estruturados |
| passlib[bcrypt] | latest | Hashing de senhas |

### Infraestrutura

| Tecnologia | Propósito |
|---|---|
| PostgreSQL 15+ | Banco de dados relacional principal |
| Redis 7+ | Cache, sessões e broker Celery |
| Nginx | Proxy reverso e servidor de estáticos |
| Docker + Docker Compose | Containerização e orquestração local |
| MinIO (ou S3) | Armazenamento de arquivos/documentos |

---

## Pré-requisitos

Antes de iniciar, certifique-se de ter instalado:

- **Docker** 24+ e **Docker Compose** v2+
- **Node.js** 20 LTS+ e **npm** 10+ (para desenvolvimento frontend)
- **Python** 3.11+ e **pip** (para desenvolvimento backend)
- **Git** 2.40+

Para desenvolvimento local sem Docker:

- **PostgreSQL** 15+
- **Redis** 7+

---

## Configuração do Ambiente

### 1. Clonar o repositório

```bash
git clone https://github.com/sua-org/automacao-juridica-assistida.git
cd automacao-juridica-assistida
```

### 2. Configurar variáveis de ambiente

Copie o arquivo de exemplo e ajuste conforme necessário:

```bash
cp .env.example .env
```

Variáveis obrigatórias:

```env
# Banco de Dados
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/automacao_juridica
DATABASE_URL_SYNC=postgresql://user:password@localhost:5432/automacao_juridica

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Autenticação
JWT_SECRET_KEY=<gerar-chave-segura>
JWT_ALGORITHM=RS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Anthropic (Claude)
ANTHROPIC_API_KEY=<sua-chave-api>
ANTHROPIC_MODEL=claude-sonnet-4-20250514
ANTHROPIC_MAX_TOKENS=4096

# Aplicação
APP_ENV=development
APP_DEBUG=true
APP_SECRET_KEY=<gerar-chave-segura>
CORS_ORIGINS=http://localhost:5173

# Armazenamento de Arquivos
STORAGE_BACKEND=minio
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=documentos-juridicos
```

### 3. Iniciar com Docker Compose (recomendado)

```bash
# Subir toda a infraestrutura + aplicação
docker compose up -d

# Verificar status dos serviços
docker compose ps

# Acompanhar logs
docker compose logs -f
```

### 4. Configuração manual (desenvolvimento)

#### Backend

```bash
# Criar e ativar ambiente virtual
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt
pip install -r requirements-dev.txt  # dependências de desenvolvimento

# Executar migrações
alembic upgrade head

# Iniciar servidor de desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
# Instalar dependências
cd frontend
npm install

# Iniciar servidor de desenvolvimento
npm run dev
```

#### Worker Celery

```bash
# Em um terminal separado, dentro do diretório backend com venv ativado
celery -A app.infrastructure.celery_app worker --loglevel=info
```

---

## Executando o Projeto

Após a configuração, os serviços estarão disponíveis em:

| Serviço | URL | Descrição |
|---|---|---|
| Frontend (SPA) | http://localhost:5173 | Portal autenticado React |
| Backend (API) | http://localhost:8000 | API REST FastAPI |
| Documentação API | http://localhost:8000/docs | Swagger UI (OpenAPI) |
| Documentação API (alt) | http://localhost:8000/redoc | ReDoc |
| MinIO Console | http://localhost:9001 | Console de gerenciamento de arquivos |
| Flower (Celery) | http://localhost:5555 | Monitoramento de tarefas Celery |

---

## Estrutura de Diretórios

```
automacao-juridica-assistida/
├── README.md                          # Este arquivo
├── docker-compose.yml                 # Orquestração de containers
├── .env.example                       # Template de variáveis de ambiente
├── .gitignore                         # Arquivos ignorados pelo Git
│
├── backend/                           # Aplicação backend (Python/FastAPI)
│   ├── alembic/                       # Migrações de banco de dados
│   │   ├── versions/                  # Arquivos de migração
│   │   └── env.py                     # Configuração do Alembic
│   ├── app/
│   │   ├── main.py                    # Ponto de entrada FastAPI
│   │   ├── config.py                  # Configurações da aplicação
│   │   │
│   │   ├── domain/                    # Camada de domínio
│   │   │   ├── entities/              # Entidades de domínio
│   │   │   ├── value_objects/         # Value Objects
│   │   │   ├── events/                # Eventos de domínio
│   │   │   └── interfaces/            # Interfaces (ports) de repositório
│   │   │
│   │   ├── application/               # Camada de aplicação
│   │   │   ├── use_cases/             # Casos de uso por módulo
│   │   │   │   ├── auth/              # Autenticação e autorização
│   │   │   │   ├── documents/         # Gestão de documentos
│   │   │   │   ├── analysis/          # Análise com IA
│   │   │   │   ├── chat/              # Chat assistido
│   │   │   │   └── audit/             # Auditoria
│   │   │   ├── dtos/                  # Data Transfer Objects
│   │   │   └── services/              # Serviços de aplicação
│   │   │
│   │   ├── infrastructure/            # Camada de infraestrutura
│   │   │   ├── database/              # Configuração e modelos SQLAlchemy
│   │   │   ├── repositories/          # Implementações de repositório
│   │   │   ├── external/              # Integrações externas (Anthropic, DataJud)
│   │   │   ├── celery_app.py          # Configuração do Celery
│   │   │   └── storage/               # Armazenamento de arquivos
│   │   │
│   │   └── api/                       # Camada de API (apresentação)
│   │       ├── routers/               # Routers FastAPI por módulo
│   │       ├── middleware/            # Middlewares (auth, logging, rate limit)
│   │       ├── dependencies/          # Injeção de dependências
│   │       └── schemas/               # Schemas Pydantic de request/response
│   │
│   ├── tests/                         # Testes do backend
│   │   ├── unit/                      # Testes unitários
│   │   ├── integration/               # Testes de integração
│   │   └── conftest.py                # Fixtures compartilhadas
│   │
│   ├── requirements.txt               # Dependências de produção
│   ├── requirements-dev.txt           # Dependências de desenvolvimento
│   ├── Dockerfile                     # Imagem Docker do backend
│   ├── alembic.ini                    # Configuração do Alembic
│   └── pyproject.toml                 # Configuração do projeto Python
│
├── frontend/                          # Aplicação frontend (React/TypeScript)
│   ├── public/                        # Arquivos estáticos públicos
│   ├── src/
│   │   ├── main.tsx                   # Ponto de entrada React
│   │   ├── App.tsx                    # Componente raiz
│   │   ├── vite-env.d.ts              # Tipos do Vite
│   │   │
│   │   ├── pages/                     # Páginas/rotas da aplicação
│   │   ├── components/                # Componentes reutilizáveis
│   │   │   ├── ui/                    # Componentes de UI base
│   │   │   ├── forms/                 # Componentes de formulário
│   │   │   └── layout/                # Componentes de layout
│   │   │
│   │   ├── hooks/                     # Custom hooks
│   │   ├── services/                  # Serviços de API (Axios)
│   │   ├── stores/                    # Estado global (se necessário)
│   │   ├── types/                     # Tipos TypeScript compartilhados
│   │   ├── utils/                     # Utilitários
│   │   ├── guards/                    # Guards de rota (autenticação)
│   │   └── styles/                    # Estilos globais e configuração Tailwind
│   │
│   ├── tests/                         # Testes do frontend
│   ├── index.html                     # HTML raiz
│   ├── vite.config.ts                 # Configuração do Vite
│   ├── tailwind.config.ts             # Configuração do Tailwind CSS
│   ├── tsconfig.json                  # Configuração do TypeScript
│   ├── package.json                   # Dependências e scripts
│   └── Dockerfile                     # Imagem Docker do frontend
│
├── nginx/                             # Configuração do Nginx
│   └── nginx.conf                     # Proxy reverso + estáticos
│
└── docs/                              # Documentação adicional
    ├── adr/                           # Architecture Decision Records
    ├── api/                           # Documentação complementar da API
    └── guides/                        # Guias de uso e operação
```

---

## Módulos Funcionais

### Auth (Autenticação e Autorização)
- Registro e login de usuários
- Autenticação JWT com RS256
- Refresh tokens com rotação
- MFA via TOTP (Google Authenticator / Authy)
- Gestão de sessões
- RBAC com perfis granulares

### Documents (Gestão de Documentos)
- Upload de documentos jurídicos (PDF, DOCX, etc.)
- Validação de tipo, tamanho e varredura de segurança
- Ciclo de vida com state machine (rascunho → revisão → aprovado → arquivado)
- Versionamento de documentos
- Integração com DataJud para consulta processual

### Analysis (Análise com IA)
- Análise de documentos jurídicos via Claude (Anthropic)
- Extração de cláusulas, riscos e pontos de atenção
- Sugestões de melhorias e adequações
- Processamento assíncrono via Celery para documentos extensos
- Circuit breaker e retry para resiliência na comunicação com a API

### Chat (Chat Assistido por IA)
- Chat contextualizado com documentos carregados
- Histórico de conversas persistido
- Referências cruzadas com jurisprudência
- Rate limiting por usuário

### Audit (Auditoria)
- Log de todas as operações sensíveis
- Trilha de auditoria imutável
- Relatórios de conformidade
- Retenção configurável de logs

---

## Autenticação e Segurança

O sistema implementa múltiplas camadas de segurança:

### Autenticação
- **JWT com RS256**: tokens assinados com chave assimétrica
- **Refresh tokens**: rotação automática para sessões longas
- **MFA obrigatório**: TOTP via Google Authenticator ou Authy
- **Hashing de senhas**: bcrypt via passlib

### Autorização
- **RBAC**: controle de acesso baseado em papéis
- **Perfis**: Administrador, Advogado Sênior, Advogado, Estagiário, Auditor
- **Guards de rota**: proteção tanto no frontend quanto no backend

### Segurança da API
- **Rate limiting**: via slowapi para prevenção de abuso
- **CORS**: configuração restritiva por ambiente
- **Validação de entrada**: Pydantic v2 em todos os endpoints
- **Headers de segurança**: CSP, X-Frame-Options, etc.
- **Request ID correlation**: rastreabilidade de requisições

### Segurança de Dados
- **Criptografia em trânsito**: TLS/HTTPS obrigatório em produção
- **Criptografia em repouso**: campos sensíveis criptografados no banco
- **Auditoria**: log imutável de todas as operações
- **LGPD**: conformidade com Lei Geral de Proteção de Dados

---

## Integração com IA (Anthropic/Claude)

A integração com a API da Anthropic (Claude) segue boas práticas de resiliência:

```python
# Exemplo conceitual de configuração (ver implementação real em app/infrastructure/external/)
# - SDK oficial anthropic para chamadas
# - tenacity para retry com backoff exponencial
# - Circuit breaker para falhas consecutivas
# - httpx como cliente HTTP assíncrono subjacente
# - Rate limiting respeitando limites da API Anthropic
```

### Funcionalidades de IA

1. **Análise de documentos**: envio de texto extraído para análise estruturada
2. **Chat contextual**: conversação com contexto de documentos carregados
3. **Busca semântica**: embeddings para busca por similaridade (FAISS/Milvus — decisão pendente, ver ADR G002)
4. **Sumarização**: resumos automáticos de peças processuais

---

## Testes

### Backend

```bash
cd backend

# Executar todos os testes
pytest

# Testes com cobertura
pytest --cov=app --cov-report=html

# Apenas testes unitários
pytest tests/unit/

# Apenas testes de integração
pytest tests/integration/

# Testes com output detalhado
pytest -v --tb=short
```

### Frontend

```bash
cd frontend

# Executar testes
npm run test

# Testes com cobertura
npm run test:coverage

# Testes em modo watch
npm run test:watch
```

### Convenções de Teste

- **Unitários**: testam use cases e lógica de domínio isoladamente (mocks para ports)
- **Integração**: testam fluxos completos com banco de dados de teste
- **Cobertura mínima**: 80% para merge em branches protegidas
- **Nomenclatura**: `test_<funcionalidade>_<cenario>_<resultado_esperado>`

---

## Migrações de Banco de Dados

```bash
cd backend

# Criar nova migração
alembic revision --autogenerate -m "descricao_da_migracao"

# Aplicar migrações pendentes
alembic upgrade head

# Reverter última migração
alembic downgrade -1

# Ver histórico de migrações
alembic history

# Ver migração atual
alembic current
```

### Boas Práticas para Migrações

- Sempre revisar migrações auto-geradas antes de aplicar
- Migrações devem ser idempotentes quando possível
- Nunca editar migrações já aplicadas em ambientes compartilhados
- Incluir migração de rollback (downgrade) funcional

---

## Deploy

### Ambientes

| Ambiente | Propósito | Branch |
|---|---|---|
| development | Desenvolvimento local | feature/* |
| staging | Testes de integração e QA | develop |
| production | Produção | main |

### Deploy com Docker

```bash
# Build das imagens
docker compose -f docker-compose.prod.yml build

# Deploy
docker compose -f docker-compose.prod.yml up -d
```

### Checklist de Deploy para Produção

- [ ] Variáveis de ambiente configuradas (sem valores padrão inseguros)
- [ ] `APP_DEBUG=false`
- [ ] JWT_SECRET_KEY com chave RS256 gerada adequadamente
- [ ] CORS_ORIGINS restrito ao domínio de produção
- [ ] TLS/HTTPS configurado no Nginx
- [ ] Migrações de banco aplicadas
- [ ] Backup de banco de dados configurado
- [ ] Monitoramento e alertas ativos
- [ ] Rate limiting ajustado para produção
- [ ] Logs estruturados direcionados para agregador (ex: ELK, Datadog)

---

## Contribuição

### Fluxo de Trabalho

1. Crie uma branch a partir de `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/minha-funcionalidade
   ```

2. Implemente a funcionalidade seguindo as convenções do projeto

3. Escreva testes para a funcionalidade

4. Certifique-se de que todos os testes passam:
   ```bash
   # Backend
   cd backend && pytest
   
   # Frontend
   cd frontend && npm run test
   ```

5. Execute os linters:
   ```bash
   # Backend
   ruff check .
   ruff format --check .
   mypy app/
   
   # Frontend
   npm run lint
   npm run type-check
   ```

6. Faça commit seguindo [Conventional Commits](https://www.conventionalcommits.org/):
   ```bash
   git commit -m "feat(documents): adicionar upload de documentos com validação"
   git commit -m "fix(auth): corrigir expiração de refresh token"
   git commit -m "docs(readme): atualizar instruções de setup"
   ```

7. Abra um Pull Request para `develop`

### Convenções de Código

#### Python (Backend)
- **Formatter**: ruff format
- **Linter**: ruff
- **Type checker**: mypy
- **Docstrings**: obrigatórias em módulos, classes e funções públicas (PT-BR)
- **Estilo**: PEP 8, com line length de 100 caracteres

#### TypeScript (Frontend)
- **Formatter**: Prettier
- **Linter**: ESLint com config recomendada para React + TypeScript
- **JSDoc**: obrigatório em exports públicos (PT-BR)
- **Estilo**: Airbnb-like com adaptações para TypeScript

#### Idioma
- **Código** (variáveis, funções, classes): inglês
- **Documentação** (docstrings, comentários, mensagens): português brasileiro (PT-BR)
- **Termos técnicos** (JWT, middleware, async, etc.): mantidos em inglês
- **Mensagens de erro para o usuário**: português brasileiro
- **Commits**: português brasileiro com prefixo Conventional Commits em inglês

### Architecture Decision Records (ADRs)

Decisões arquiteturais significativas são documentadas em `docs/adr/`. ADRs pendentes:

- **G002**: Escolha entre FAISS e Milvus para índice vetorial de busca semântica
- **G005**: Definição de design tokens (cores, tipografia, breakpoints)

---

## Licença

<!-- TODO: Definir licença do projeto. Sugestões: MIT para open source ou licença proprietária para uso comercial. Consultar equipe jurídica. -->

Este projeto é de uso restrito. Consulte a equipe responsável para informações sobre licenciamento.

---

## Contato

<!-- TODO: Adicionar informações de contato da equipe responsável pelo projeto. -->

Para dúvidas, sugestões ou reportar problemas, entre em contato com a equipe de desenvolvimento.

---

> **Nota**: Este projeto está em desenvolvimento ativo. Consulte os ADRs em `docs/adr/` para decisões arquiteturais pendentes e o board de issues para funcionalidades planejadas.