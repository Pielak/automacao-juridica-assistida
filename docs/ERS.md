# ERS — Especificação de Requisitos de Software

> **Projeto**: Automação Jurídica Assistida (`automacao-juridica-assistida`)  
> **Versão do OCG**: 8  
> **Gerado em**: 2026-04-22 14:14 UTC  
> **Padrão**: IEEE 830-1998  
> **Fonte**: GCA — Gestão de Codificação Assistida

> Este documento é gerado automaticamente pelo GCA a partir do contexto canônico do projeto (OCG, backlog, testes, repositórios). O histórico de revisões vive no Git: `git log -p docs/ERS.md`.

---

## 1. Introdução

### 1.1 Propósito

Sistema para auxiliar advogados de Processo Cível em suas atividades do dia a dia.

### 1.2 Escopo

**Entregáveis previstos:**

- [expected] Arquitetura
- [expected] Stack
- [expected] Doc técnico
- [expected] Backlog
- [expected] Plano testes
- [expected] Gap analysis
- [expected] Plano observabilidade
- [expected] Plano deploy
- [expected] Doc negocial
- [expected] Plano segurança
- [expected] Especificação de Requisitos Funcionais v2.0 (57 RFs, 15 módulos candidatos)
- [expected] Matriz de rastreabilidade RF→Módulo→Teste (pendente — derivada de G004)
- [expected] Decisão arquitetural web vs desktop (pendente — derivada de G001)
- [expected] Mapeamento de 15 módulos candidatos com status de codegen-readiness (7 ready, 8 pendentes)
- [expected] Especificação de stack de processamento documental: OCR (Tesseract vs EasyOCR), PDF parser, IA local (pendente — derivada de G003)
- [expected] Plano de resiliência para integração DataJud: circuit breaker, fallback, cache local (pendente — derivada de MC008)
- [expected] Roadmap de fases (Fase 1-4) com critérios de entrada/saída (pendente — derivada de G006)
- [expected] Catálogo de 15 módulos candidatos (MC001-MC015) com mapeamento RF→Módulo, blockers e status codegen-readiness (atualizado: 0/15 ready)
- [expected] PoC de viabilidade técnica: modelo IA local em hardware-alvo com dataset jurídico representativo (derivada de G004/G007)
- [expected] Especificação de arquitetura de sincronização multi-dispositivo para Fase 3 (derivada de G008)
- [expected] Especificação de Integração DataJud: 14 módulos candidatos (MOD-DJ-01 a MOD-DJ-AUDIT), 3/14 ready_for_codegen, backlog técnico com Query DSL e catálogo de aliases
- [expected] PoC de resiliência DataJud: circuit breaker (3 retries, backoff exponencial, 5 falhas → 30s open), rate limiting, modo degradado (pendente — derivada de G001/G005)
- [expected] Catálogo de 15 módulos DataJud (MOD-DJ-001 a MOD-DJ-015) com decomposição componentizada: HTTP Client, Data Mapper, Connector Service, Pagination Handler, Data Model, Secret Rotation, Observability, Async Queue, Tribunal Catalog, Retry Handler, Contract Tests, Search API, Data Validation, Sigiloso Handler, Incremental Sync (1/15 ready_for_codegen: MOD-DJ-004)
- [expected] Especificação de DTOs internos para domínio DataJud: Processo, Movimento, Classe, OrgaoJulgador (pendente — derivada de G007/PD001)
- [expected] Definição de contrato REST para busca DataJud no frontend: endpoints, parâmetros, schema de resposta, política de Query DSL (pendente — derivada de G008/PD002)
- [output_formats] Painel GCA
- [output_formats] Markdown
- [output_formats] PDF
- [source] questionnaire_deterministic_fallback

### 1.3 Definições, Siglas e Abreviaturas

_Nenhum termo aprovado ainda. Rode a extração automática em `/projects/:id/docs` → aba Glossário e aprove os candidatos relevantes. Para acrônimos canônicos do GCA (OCG, RBAC, GP, P1–P7, etc), consulte o capítulo 1 do help global._

### 1.4 Referências

_(Sem referências externas declaradas até o momento.)_

---

## 2. Descrição Geral

### 2.1 Perspectiva do Produto

- **Modelo de execução**: On-premises, Containerizado

### 2.2 Funcionalidades do Produto

_(Requisitos ainda não classificados pelo GP. Funcionalidades aparecerão aqui conforme módulos forem marcados como `functional`.)_

### 2.3 Características dos Usuários

Papéis canônicos no GCA: **Admin** (instância), **GP** (projeto, soberano), **Dev**, **Tester** e **QA**. Ver capítulo 3 do help global para detalhes das permissões e fluxos operacionais.

### 2.4 Restrições

- **Linguagem backend**: Python
- **Framework backend**: FastAPI
- **Frontend**: React, Vite+React
- **Banco**: PostgreSQL
- **Cache**: habilitado

### 2.5 Suposições e Dependências

_(Sem suposições ou dependências externas declaradas.)_

---

## 3. Requisitos Específicos

### 3.1 Requisitos Funcionais

_Nenhum requisito classificado como `functional` pelo GP até o momento._

### 3.2 Requisitos Não-Funcionais

_Nenhum requisito classificado como `non_functional` pelo GP até o momento. Achados dos pilares P4 (performance) e P7 (segurança) podem ser convertidos em RNFs via UI do backlog._

#### 3.2.1 Achados dos pilares (leitura do OCG)

**Compliance:**
- {"control": "JWT", "source": "Q43 — Controles de segurança obrigatórios", "status": "declared"}
- {"control": "HTTPS", "source": "Q43 — Controles de segurança obrigatórios", "status": "declared"}
- {"control": "Cripto repouso", "source": "Q43 — Controles de segurança obrigatórios", "status": "declared"}
- {"control": "Auditoria", "source": "Q43 — Controles de segurança obrigatórios", "status": "declared"}
- {"control": "MFA", "source": "Q43 — Controles de segurança obrigatórios", "status": "declared"}
- {"control": "Classificação da informação: Confidencial", "source": "Q6 — Classificação da informação", "status": "declared"}
- {"control": "Restrição de IA: Anonimização", "source": "Q42 — Restrições de IA", "status": "declared"}
- {"control": "Plano testes", "source": "Q48 — Entregáveis esperados", "status": "declared"}

### 3.3 Regras de Negócio

_Nenhuma regra de negócio registrada. GP popula via a aba OCG (seção BUSINESS_RULES) ou marcando módulos do backlog como `business_rule`._

### 3.4 Interfaces Externas

_Nenhum repositório externo vinculado ao projeto._

### 3.5 Requisitos pendentes de classificação

Existem **40** módulos no backlog ainda não classificados pelo GP. Abaixo até 10 exemplos — classifique cada um como `functional`, `non_functional` ou `business_rule` na aba Backlog do projeto para que apareçam nas seções corretas deste documento:

- **Ingestão e Normalização Documental** (feature, prioridade `medium`)
- **Triagem Pré-Processual** (feature, prioridade `medium`)
- **Pesquisa Legislação e Jurisprudência** (feature, prioridade `medium`)
- **Geração Assistida de Peças** (feature, prioridade `medium`)
- **Fluxo de Trabalho e Revisão** (feature, prioridade `medium`)
- **Motor de Cálculos Cíveis** (feature, prioridade `medium`)
- **Análise de Risco e Estratégia** (feature, prioridade `medium`)
- **Fluxos Contencioso Cível** (feature, prioridade `medium`)
- **Painel Gerencial e Portfólio** (feature, prioridade `medium`)
- **Gestão Cliente e Financeira** (feature, prioridade `medium`)
- _… e mais 30 módulos._

---

## 4. Matriz de Rastreabilidade

Cobertura agregada: **40** requisitos (RF `0` · RNF `0` · BR `0` · pendentes `40`). Com spec: **1**. Com código gerado: **0**. Rastreamento completo (spec + código): **0**.

| ID | Requisito | Categoria | Test Specs | Código gerado |
|---|---|---|---|---|
| **REQ-001** | Cadastro e Dossiê do Caso | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-002** | Ingestão e Normalização Documental | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-003** | Triagem Pré-Processual | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-004** | Pesquisa Legislação e Jurisprudência | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-005** | Geração Assistida de Peças | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-006** | Fluxo de Trabalho e Revisão | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-007** | Motor de Cálculos Cíveis | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-008** | Análise de Risco e Estratégia | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-009** | Fluxos Contencioso Cível | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-010** | Painel Gerencial e Portfólio | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-011** | Gestão Cliente e Financeira | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-012** | Configurações e Conectores | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-013** | Auditoria e Rastreabilidade | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-014** | Conector DataJud | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-015** | Seletor de Tribunal e Aliases | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-016** | DataJud HTTP Client | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-017** | DataJud Data Mapper | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-018** | DataJud Connector Service | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-019** | DataJud Pagination Handler | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-020** | DataJud Data Model | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-021** | DataJud Secret Rotation | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-022** | DataJud Observability | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-023** | DataJud Async Queue | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-024** | DataJud Tribunal Catalog | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-025** | DataJud Retry Handler | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-026** | DataJud Contract Tests | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-027** | DataJud Search API | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-028** | DataJud Data Validation | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-029** | DataJud Sigiloso Handler | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-030** | DataJud Incremental Sync | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-031** | Esqueleto do Backend (API Skeleton) | `—` | `unit` (draft) | _(sem código)_ |
| **REQ-032** | Schema Inicial do Banco de Dados | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-033** | Bootstrap do Frontend (SPA + autenticação) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-034** | Camada de Cache | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-035** | Contrato de Integração com IA | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-036** | Container da Aplicação (Dockerfile + compose) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-037** | Pipeline de CI/CD Inicial | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-038** | Gestão de Secrets e Audit Log | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-039** | Ambiente de Deploy Inicial (dev) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-040** | Observabilidade Básica (logs estruturados + métricas) | `—` | _(sem spec)_ | _(sem código)_ |

> A matriz é gerada sob demanda no momento da regeneração do ERS. Atualize via `POST /projects/:id/docs/ers/regenerate` ou veja o estado atual em `/projects/:id/docs` → aba **Rastreabilidade**.

---

## Histórico de Revisão

O histórico completo do ERS vive no Git do projeto. Para ver diffs entre versões, use:

```bash
git log -p docs/ERS.md
```

Cada regeneração cria um commit com mensagem canônica `docs(ers): regen a partir do OCG vN — <motivos>` emitido pelo GCA na aba Doc Viva do projeto.

