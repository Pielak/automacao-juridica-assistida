# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não Publicado]

### Adicionado

- Scaffold inicial do projeto **Automação Jurídica Assistida**
- Estrutura de monólito modular com Clean Architecture (Ports & Adapters)
- **Backend**: FastAPI 0.100+ com Python 3.11+
  - Configuração base do servidor FastAPI com routers modulares
  - Validação de dados com Pydantic v2
  - ORM assíncrono com SQLAlchemy 2.0 + asyncpg para PostgreSQL
  - Migrações de banco de dados com Alembic
  - Autenticação JWT com suporte a RS256
  - Suporte a MFA via TOTP (pyotp)
  - Rate limiting com slowapi
  - Logs estruturados com structlog
  - Hashing de senhas com passlib[bcrypt]
  - Processamento assíncrono de tarefas com Celery 5+
  - Integração com API Anthropic (Claude) via SDK oficial + httpx
  - Retry e circuit breaker com tenacity para chamadas externas
  - Upload de arquivos com python-multipart
- **Frontend**: React 18+ com Vite 5+ e TypeScript 5+
  - SPA com portal autenticado
  - Roteamento com React Router v6 e guards de autenticação
  - Formulários complexos com React Hook Form + Zod
  - Gerenciamento de estado servidor com TanStack Query (React Query)
  - Cliente HTTP com interceptors para JWT
  - Upload de arquivos com react-dropzone e validação
  - Sistema de design responsivo (mobile-first)
- **Infraestrutura**:
  - Configuração do Docker e Docker Compose para ambiente de desenvolvimento
  - Nginx como servidor de arquivos estáticos e proxy reverso
  - Configuração do PostgreSQL como banco de dados principal
  - Configuração do Redis como broker para Celery e cache
- **Módulos funcionais planejados**:
  - `auth` — autenticação JWT, MFA, gestão de sessões
  - `users` — CRUD de usuários e perfis RBAC
  - `documents` — gestão de documentos jurídicos com state machine (ciclo de vida DataJud)
  - `analysis` — análise de documentos com IA (Anthropic Claude)
  - `chat` — interface conversacional assistida por IA
  - `audit` — trilha de auditoria e logs de conformidade
- **Segurança**:
  - Middleware de autenticação JWT
  - Middleware de logging com correlação de request ID
  - Middleware de rate limiting
  - Headers de segurança (CSP)
- **Documentação**:
  - Documentação OpenAPI automática via FastAPI
  - CHANGELOG seguindo padrão Keep a Changelog
  - README com instruções de setup e desenvolvimento

### Decisões Pendentes

- G002 ADR — Escolha entre FAISS ou Milvus para índice vetorial (busca semântica)
- G005 ADR — Definição de design tokens (cores, tipografia, breakpoints)

---

<!-- Modelo para novas versões:

## [X.Y.Z] - AAAA-MM-DD

### Adicionado
- Novas funcionalidades.

### Alterado
- Mudanças em funcionalidades existentes.

### Obsoleto
- Funcionalidades que serão removidas em versões futuras.

### Removido
- Funcionalidades removidas.

### Corrigido
- Correções de bugs.

### Segurança
- Correções de vulnerabilidades.

-->
