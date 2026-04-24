# Automação Jurídica Assistida

> Sistema desktop local-first de automação jurídica assistida por IA, com foco em **sigilo**, **operação offline** e **processamento local** de dados sensíveis.

---

## Índice

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Stack Tecnológica](#stack-tecnológica)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Pré-requisitos](#pré-requisitos)
- [Setup de Desenvolvimento](#setup-de-desenvolvimento)
- [Executando o Projeto](#executando-o-projeto)
- [Banco de Dados](#banco-de-dados)
- [Sidecar Python](#sidecar-python)
- [IA Local](#ia-local)
- [Decisões Arquiteturais](#decisões-arquiteturais)
- [Segurança e Sigilo](#segurança-e-sigilo)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Scripts Úteis](#scripts-úteis)
- [Contribuição](#contribuição)
- [Licença](#licença)

---

## Visão Geral

O **Automação Jurídica Assistida** é uma aplicação desktop construída com [Tauri 2.x](https://v2.tauri.app/) que auxilia profissionais do Direito em:

- **Gestão de processos jurídicos** — cadastro, acompanhamento e controle de prazos
- **Geração de peças jurídicas** — templates Jinja2 com preenchimento assistido por IA
- **Chat com IA local** — análise de documentos e requisitos usando LLMs rodando localmente (llama.cpp / Ollama)
- **Consulta ao DataJud** — integração com a API pública do CNJ para acompanhamento processual
- **Pseudonimização automática** — remoção de PII antes de qualquer processamento por IA
- **Auditoria completa** — logs estruturados de todas as operações sensíveis

Todo o processamento ocorre **localmente na máquina do usuário**, sem envio de dados para servidores externos, garantindo conformidade com sigilo profissional (OAB) e LGPD.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    Tauri Desktop App                     │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │           Frontend (React + TypeScript)            │  │
│  │         WebView — Vite — Tailwind CSS             │  │
│  │  Formulários · Chat IA · Dashboard · Upload       │  │
│  └──────────────────────┬────────────────────────────┘  │
│                         │ IPC (invoke / events)         │
│  ┌──────────────────────▼────────────────────────────┐  │
│  │          Tauri Core (Rust)                        │  │
│  │  Commands · RBAC · Crypto · SQLCipher · IPC       │  │
│  │                                                   │  │
│  │  ┌─────────────┐  ┌────────────┐  ┌───────────┐  │  │
│  │  │   Domain     │  │ Commands   │  │   Infra   │  │  │
│  │  │  Entities    │  │ processos  │  │ database  │  │  │
│  │  │  Errors      │  │ documentos │  │ crypto    │  │  │
│  │  │  Rules       │  │ ia_chat    │  │ sidecar   │  │  │
│  │  └─────────────┘  └────────────┘  └─────┬─────┘  │  │
│  └─────────────────────────────────────────┬─────────┘  │
│                                            │            │
│  ┌─────────────────────────────────────────▼─────────┐  │
│  │         Sidecar Python (subprocess)               │  │
│  │  IA (llama.cpp/Ollama) · Pseudonimização          │  │
│  │  DataJud Client · Templates Jinja2                │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  SQLite + SQLCipher (AES-256-CBC, PBKDF2 100k)   │  │
│  │  FTS5 (busca textual) · JSON1 (auditoria)        │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Camadas (Clean Architecture)

| Camada | Localização | Responsabilidade |
|---|---|---|
| **Presentation** | `frontend/src/` | UI React, formulários, chat, dashboard |
| **IPC Bridge** | Tauri IPC (`invoke` / `events`) | Comunicação tipada JS ↔ Rust com streaming |
| **Application** | `src-tauri/src/commands/` | Orquestração, RBAC, validação, criptografia |
| **Domain** | `src-tauri/src/domain/` | Entidades puras, regras de negócio, 5 níveis de sigilo |
| **Infrastructure** | `src-tauri/src/infra/` | SQLCipher, llama.cpp, pseudonimização, DataJud, filesystem |
| **Sidecar** | `sidecar-python/src/` | Processamento pesado: IA, DataJud, templates |

---

## Stack Tecnológica

### Desktop Runtime

| Componente | Tecnologia | Justificativa |
|---|---|---|
| Framework Desktop | **Tauri 2.x** | Leve, seguro, WebView nativo, IPC Rust↔JS |
| Core Backend | **Rust** | Performance, segurança de memória, criptografia |
| Sidecar | **Python 3.11+** | Ecossistema IA/ML, templates, integração DataJud |

### Frontend

| Componente | Tecnologia |
|---|---|
| Framework | React 18+ |
| Linguagem | TypeScript (strict mode) |
| Build Tool | Vite |
| Estilização | Tailwind CSS |
| Formulários | React Hook Form + Zod |
| Estado/Cache | TanStack Query (React Query) |
| Roteamento | React Router v6 |
| Upload | React Dropzone |
| Datas | date-fns |

### Backend Rust (Tauri Core)

| Componente | Tecnologia |
|---|---|
| Banco de Dados | rusqlite + SQLCipher |
| Serialização | serde + serde_json |
| Async Runtime | tokio |
| IA Local | llama-cpp-rs ou Ollama client |

### Sidecar Python

| Componente | Tecnologia |
|---|---|
| Templates | Jinja2 |
| Validação | Pydantic v2 |
| Logs | structlog |
| HTTP Client | httpx |
| Retry | tenacity |
| Hashing | argon2-cffi |

### Banco de Dados

| Componente | Tecnologia |
|---|---|
| Engine | SQLite 3.x |
| Criptografia | SQLCipher (AES-256-CBC, PBKDF2 100k iterações) |
| Busca Textual | FTS5 |
| JSON | JSON1 extension |

---

## Estrutura do Projeto

```
automacao-juridica-assistida/
├── README.md                          # Este arquivo
├── .gitignore                         # Regras de exclusão do Git
├── .env.example                       # Template de variáveis de ambiente
│
├── src-tauri/                         # Backend Rust (Tauri core)
│   ├── Cargo.toml                     # Dependências Rust
│   ├── tauri.conf.json                # Configuração Tauri (janela, permissões, sidecar)
│   ├── build.rs                       # Build script Rust
│   ├── migrations/
│   │   └── 001_initial_schema.sql     # Schema inicial SQLite/SQLCipher
│   └── src/
│       ├── main.rs                    # Entry point Tauri
│       ├── lib.rs                     # Registro de comandos e setup
│       ├── domain/
│       │   ├── mod.rs                 # Módulo domain
│       │   ├── entities.rs            # Entidades: Processo, Documento, Usuário
│       │   └── errors.rs             # Erros de domínio tipados
│       ├── commands/
│       │   ├── mod.rs                 # Módulo commands
│       │   ├── processos.rs           # Comandos IPC: CRUD processos
│       │   ├── documentos.rs          # Comandos IPC: upload/gestão documentos
│       │   └── ia_chat.rs             # Comandos IPC: chat IA com streaming
│       └── infra/
│           ├── mod.rs                 # Módulo infraestrutura
│           ├── database.rs            # Conexão SQLCipher, migrations, pool
│           ├── crypto.rs              # Criptografia, derivação de chaves
│           └── sidecar.rs             # Gerenciamento do processo Python
│
├── sidecar-python/                    # Sidecar Python (IA, DataJud, templates)
│   ├── pyproject.toml                 # Dependências e config Python
│   └── src/
│       ├── __init__.py
│       ├── main.py                    # Entry point sidecar (stdin/stdout ou socket)
│       ├── datajud/
│       │   ├── __init__.py
│       │   ├── client.py              # Cliente HTTP DataJud API
│       │   ├── models.py              # Modelos Pydantic para DataJud
│       │   ├── query_builder.py       # Construtor de queries DataJud
│       │   ├── pagination.py          # Paginação de resultados
│       │   └── audit.py               # Auditoria de consultas DataJud
│       ├── ia/
│       │   ├── __init__.py
│       │   ├── llm_service.py         # Interface com llama.cpp/Ollama
│       │   └── pseudonymizer.py       # Motor de pseudonimização de PII
│       └── templates/
│           ├── __init__.py
│           └── engine.py              # Engine Jinja2 para peças jurídicas
│
└── frontend/                          # Frontend React (Tauri WebView)
    ├── package.json                   # Dependências Node.js
    ├── tsconfig.json                  # Configuração TypeScript
    ├── vite.config.ts                 # Configuração Vite
    ├── tailwind.config.ts             # Configuração Tailwind CSS
    ├── index.html                     # HTML entry point
    └── src/
        └── main.tsx                   # React entry point
```

---

## Pré-requisitos

### Obrigatórios

| Ferramenta | Versão Mínima | Instalação |
|---|---|---|
| **Rust** | 1.75+ | [rustup.rs](https://rustup.rs/) |
| **Node.js** | 18 LTS+ | [nodejs.org](https://nodejs.org/) |
| **Python** | 3.11+ | [python.org](https://www.python.org/) |
| **Tauri CLI** | 2.x | `cargo install tauri-cli --version "^2"` |
| **SQLCipher** | 4.x | Ver instruções por SO abaixo |

### Instalação do SQLCipher por SO

**Ubuntu/Debian:**
```bash
sudo apt-get install libsqlcipher-dev sqlcipher
```

**macOS:**
```bash
brew install sqlcipher
export SQLCIPHER_LIB_DIR=$(brew --prefix sqlcipher)/lib
export SQLCIPHER_INCLUDE_DIR=$(brew --prefix sqlcipher)/include
```

**Windows:**
```powershell
# Recomendado: usar vcpkg
vcpkg install sqlcipher:x64-windows
# Ou baixar binários pré-compilados de https://github.com/nickolay/sqlcipher-cmake
```

### Opcionais (para IA local)

| Ferramenta | Propósito | Instalação |
|---|---|---|
| **Ollama** | Servidor LLM local | [ollama.ai](https://ollama.ai/) |
| **llama.cpp** | Inferência LLM alternativa | [github.com/ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp) |

---

## Setup de Desenvolvimento

### 1. Clonar o repositório

```bash
git clone <repo-url> automacao-juridica-assistida
cd automacao-juridica-assistida
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Editar .env com suas configurações locais
```

### 3. Instalar dependências do Frontend

```bash
cd frontend
npm install
cd ..
```

### 4. Instalar dependências do Sidecar Python

```bash
cd sidecar-python
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install -e ".[dev]"
cd ..
```

### 5. Verificar dependências Rust

```bash
cd src-tauri
cargo check
cd ..
```

### 6. (Opcional) Baixar modelo de IA local

```bash
# Com Ollama:
ollama pull llama3.1:8b

# Ou baixar GGUF manualmente para uso com llama.cpp
# TODO: Documentar modelos recomendados para uso jurídico em português
```

---

## Executando o Projeto

### Modo Desenvolvimento (com hot-reload)

```bash
# Na raiz do projeto:
cargo tauri dev
```

Isso irá:
1. Iniciar o Vite dev server para o frontend (hot-reload)
2. Compilar e executar o backend Rust (Tauri)
3. O sidecar Python será iniciado sob demanda pelo Rust

### Build de Produção

```bash
cargo tauri build
```

O instalador será gerado em `src-tauri/target/release/bundle/`.

### Executar apenas o Frontend (isolado)

```bash
cd frontend
npm run dev
```

### Executar apenas o Sidecar Python (para testes)

```bash
cd sidecar-python
source .venv/bin/activate
python -m src.main
```

---

## Banco de Dados

### SQLite + SQLCipher

O banco de dados é criado automaticamente no primeiro uso, criptografado com SQLCipher.

- **Localização**: `{app_data_dir}/automacao-juridica.db` (diretório de dados do Tauri)
- **Criptografia**: AES-256-CBC com PBKDF2 (100.000 iterações)
- **Chave**: Derivada da senha mestra do usuário via Argon2

### Migrations

As migrations ficam em `src-tauri/migrations/` e são executadas automaticamente na inicialização:

```
src-tauri/migrations/
└── 001_initial_schema.sql    # Schema inicial: usuários, processos, documentos, auditoria
```

### Busca Full-Text

A extensão FTS5 é habilitada para busca textual em documentos jurídicos, permitindo consultas como:

```sql
SELECT * FROM documentos_fts WHERE documentos_fts MATCH 'habeas corpus';
```

---

## Sidecar Python

O sidecar Python é um processo separado gerenciado pelo Tauri core (Rust). A comunicação ocorre via **stdin/stdout** com mensagens JSON delimitadas por newline (JSON Lines).

### Módulos

| Módulo | Responsabilidade |
|---|---|
| `src/main.py` | Entry point, loop de mensagens, roteamento de comandos |
| `src/datajud/` | Cliente DataJud API (CNJ) com paginação, retry e auditoria |
| `src/ia/` | Serviço LLM local + motor de pseudonimização |
| `src/templates/` | Engine Jinja2 para geração de peças jurídicas |

### Protocolo de Comunicação

```json
// Rust → Python (request)
{"id": "uuid", "method": "ia.chat", "params": {"prompt": "..."}}

// Python → Rust (response)
{"id": "uuid", "result": {"text": "..."}, "error": null}

// Python → Rust (streaming)
{"id": "uuid", "stream": true, "chunk": "token..."}
{"id": "uuid", "stream": true, "done": true}
```

---

## IA Local

### Pipeline de Processamento

Todo texto enviado à IA passa obrigatoriamente pelo pipeline de pseudonimização:

```
Texto Original → Pseudonimização (remoção PII) → LLM Local → Re-identificação → Resposta
```

1. **Pseudonimização**: Nomes, CPFs, OABs, endereços e outros dados pessoais são substituídos por placeholders (`[PESSOA_1]`, `[CPF_1]`, etc.)
2. **Inferência Local**: O texto pseudonimizado é processado pelo LLM (Ollama/llama.cpp)
3. **Re-identificação**: Os placeholders na resposta são substituídos de volta pelos dados originais

### Modelos Recomendados

| Modelo | VRAM | Uso |
|---|---|---|
| `llama3.1:8b` | ~6 GB | Uso geral, análise de documentos |
| `llama3.1:70b` | ~40 GB | Análise complexa (requer GPU dedicada) |
| `sabia-2` | ~6 GB | Modelo otimizado para português (quando disponível) |

> **Nota**: A aplicação funciona sem IA — as funcionalidades de IA são opcionais e degradam graciosamente.

---

## Decisões Arquiteturais

### ADR-001: Desktop Local-First (Tauri) em vez de Web SPA

**Contexto**: Dados jurídicos são sigilosos (art. 7º do Estatuto da OAB) e não devem trafegar por servidores externos.

**Decisão**: Aplicação desktop com Tauri, processamento 100% local.

**Consequências**: (+) Sigilo garantido, operação offline, sem custos de servidor. (-) Distribuição mais complexa, atualizações manuais.

### ADR-002: SQLite+SQLCipher em vez de PostgreSQL

**Contexto**: Banco local, sem necessidade de acesso concorrente multi-usuário.

**Decisão**: SQLite com SQLCipher para criptografia em repouso.

**Consequências**: (+) Zero configuração, portável, criptografado. (-) Sem acesso remoto, limitações de concorrência.

### ADR-003: IA Local (llama.cpp/Ollama) em vez de APIs Cloud

**Contexto**: Dados de clientes não podem ser enviados para APIs externas sem consentimento explícito.

**Decisão**: Inferência LLM local com pseudonimização obrigatória como camada adicional de proteção.

**Consequências**: (+) Privacidade total, sem custos de API, offline. (-) Requer hardware adequado, modelos menores que GPT-4.

### ADR-004: Sidecar Python em vez de Rust puro

**Contexto**: Ecossistema Python é superior para IA/ML, templates e integração com APIs REST.

**Decisão**: Processo Python separado (sidecar) gerenciado pelo Tauri, comunicação via JSON Lines.

**Consequências**: (+) Acesso ao ecossistema Python, isolamento de falhas. (-) Overhead de IPC, necessidade de distribuir Python.

### ADR-005: Clean Architecture com Monólito Modular

**Contexto**: Projeto precisa de manutenibilidade a longo prazo com regras de negócio complexas.

**Decisão**: Separação rigorosa em camadas (domain, commands, infra) sem dependências circulares.

**Consequências**: (+) Testabilidade, substituibilidade de componentes. (-) Mais boilerplate inicial.

---

## Segurança e Sigilo

### Níveis de Sigilo

O sistema implementa **5 níveis de sigilo** para documentos e processos:

| Nível | Descrição | Acesso |
|---|---|---|
| 1 - Público | Informações de domínio público | Todos os usuários |
| 2 - Interno | Uso interno do escritório | Usuários autenticados |
| 3 - Confidencial | Dados de clientes | Equipe do caso |
| 4 - Restrito | Dados sensíveis (saúde, criminal) | Advogado responsável + sócios |
| 5 - Ultra-secreto | Segredo de justiça | Apenas advogado responsável |

### Medidas de Segurança

- **Criptografia em repouso**: SQLCipher (AES-256-CBC) com PBKDF2 100k iterações
- **Pseudonimização obrigatória**: Todo texto é pseudonimizado antes de processamento por IA
- **RBAC/ABAC**: Controle de acesso baseado em papéis e atributos
- **Auditoria completa**: Todas as operações sensíveis são logadas com timestamp, usuário e detalhes
- **Sem telemetria**: Nenhum dado é enviado para servidores externos
- **Chave derivada**: A chave do banco é derivada da senha do usuário (nunca armazenada em texto plano)

---

## Variáveis de Ambiente

Veja `.env.example` para a lista completa. Principais variáveis:

| Variável | Descrição | Padrão |
|---|---|---|
| `OLLAMA_BASE_URL` | URL do servidor Ollama local | `http://localhost:11434` |
| `OLLAMA_MODEL` | Modelo LLM padrão | `llama3.1:8b` |
| `DATAJUD_API_KEY` | Chave de API do DataJud (CNJ) | — |
| `DATAJUD_BASE_URL` | URL base da API DataJud | `https://datajud-wiki.cnj.jus.br/api` |
| `LOG_LEVEL` | Nível de log (DEBUG, INFO, WARN, ERROR) | `INFO` |
| `SQLCIPHER_KDF_ITERATIONS` | Iterações PBKDF2 para SQLCipher | `100000` |
| `SIDECAR_PYTHON_PATH` | Caminho para o executável Python do sidecar | Auto-detectado |

---

## Scripts Úteis

### Desenvolvimento

```bash
# Executar app em modo dev
cargo tauri dev

# Apenas frontend (sem Tauri)
cd frontend && npm run dev

# Verificar tipos TypeScript
cd frontend && npm run typecheck

# Lint frontend
cd frontend && npm run lint

# Verificar Rust
cd src-tauri && cargo clippy -- -D warnings

# Formatar Rust
cd src-tauri && cargo fmt

# Testes Rust
cd src-tauri && cargo test

# Testes Python
cd sidecar-python && python -m pytest

# Lint Python
cd sidecar-python && ruff check src/
```

### Build

```bash
# Build de produção (gera instalador)
cargo tauri build

# Build sidecar Python (executável standalone)
# TODO: Configurar PyInstaller ou Nuitka para bundling do sidecar
cd sidecar-python && python -m PyInstaller src/main.py --onefile --name sidecar
```

---

## Contribuição

### Convenções

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, etc.)
- **Branches**: `feature/<nome>`, `fix/<nome>`, `docs/<nome>`
- **Rust**: `cargo fmt` + `cargo clippy` sem warnings
- **Python**: Ruff + type hints obrigatórios + docstrings (Google style)
- **TypeScript**: ESLint + Prettier + strict mode

### Fluxo de Trabalho

1. Criar branch a partir de `main`
2. Implementar com testes
3. Garantir que `cargo clippy`, `npm run lint` e `ruff check` passam
4. Abrir Pull Request com descrição detalhada
5. Code review obrigatório

---

## Licença

<!-- TODO: Definir licença do projeto (proprietária ou open-source) -->

Este projeto é software proprietário. Todos os direitos reservados.

---

## Roadmap

- [ ] **v0.1** — Scaffold inicial, CRUD de processos, banco SQLCipher
- [ ] **v0.2** — Integração DataJud, consulta processual
- [ ] **v0.3** — Chat IA local com pseudonimização
- [ ] **v0.4** — Geração de peças jurídicas via templates
- [ ] **v0.5** — Dashboard de métricas e prazos
- [ ] **v1.0** — Release estável com instalador multiplataforma

---

> **Aviso Legal**: Este software é uma ferramenta de auxílio. Todas as peças jurídicas e análises geradas por IA devem ser revisadas por um advogado habilitado antes do uso.
