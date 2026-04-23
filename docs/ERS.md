# ERS — Especificação de Requisitos de Software

> **Projeto**: Automação Jurídica Assistida (`automacao-juridica-assistida`)  
> **Versão do OCG**: 24  
> **Gerado em**: 2026-04-23 03:05 UTC  
> **Padrão**: IEEE 830-1998  
> **Fonte**: GCA — Gestão de Codificação Assistida

> Este documento é gerado automaticamente pelo GCA a partir do contexto canônico do projeto (OCG, backlog, testes, repositórios). O histórico de revisões vive no Git: `git log -p docs/ERS.md`.

---

## 1. Introdução

### 1.1 Propósito

Sistema para auxiliar advogados de Processo Cível em suas atividades do dia a dia.

### 1.2 Escopo

**Entregáveis previstos:**

- [summary] 10 artefatos documentais solicitados pelo GP, priorizados e mapeados aos pilares responsáveis. Recomenda-se produção sequencial respeitando dependências.
- [items] Documento de caso de negócio com ROI, stakeholders, KPIs, timeline, equipe e orçamento
- [items] Documento de arquitetura com diagramas C4, decisões arquiteturais (ADRs), módulos do monólito e fluxos de integração com IA
- [items] Definição completa de tecnologias por camada conforme seção STACK_RECOMMENDATION
- [items] Threat model STRIDE, matriz RBAC, pipeline de anonimização, plano de resposta a incidentes, conformidade LGPD
- [items] Backlog priorizado com user stories, critérios de aceitação e estimativas, organizado por fases (MVP, v1.0, futuro)
- [items] Documentação técnica incluindo modelo de dados (ERD), contratos de API (OpenAPI), guia de desenvolvimento e padrões de código
- [items] Plano de testes cobrindo unitários, integração, E2E, segurança, performance e compliance conforme seção TESTING_REQUIREMENTS
- [items] Análise de lacunas identificadas por todos os 7 pilares, com recomendações de mitigação
- [items] Plano de observabilidade com métricas, dashboards, alertas, thresholds e runbooks
- [items] Plano de deploy on-premises com Docker/k3s, pipeline CI/CD, estratégia de rollback e procedimentos de disaster recovery

### 1.3 Definições, Siglas e Abreviaturas

_Nenhum termo aprovado ainda. Rode a extração automática em `/projects/:id/docs` → aba Glossário e aprove os candidatos relevantes. Para acrônimos canônicos do GCA (OCG, RBAC, GP, P1–P7, etc), consulte o capítulo 1 do help global._

### 1.4 Referências

_(Sem referências externas declaradas até o momento.)_

---

## 2. Descrição Geral

### 2.1 Perspectiva do Produto

- **Estilo arquitetural**: Monólito Modular com Clean Architecture
- **Modelo de execução**: On-premises, Containerizado

### 2.2 Funcionalidades do Produto

_(Requisitos ainda não classificados pelo GP. Funcionalidades aparecerão aqui conforme módulos forem marcados como `functional`.)_

### 2.3 Características dos Usuários

Papéis canônicos no GCA: **Admin** (instância), **GP** (projeto, soberano), **Dev**, **Tester** e **QA**. Ver capítulo 3 do help global para detalhes das permissões e fluxos operacionais.

### 2.4 Restrições

_(A stack recomendada ainda não foi consolidada pelo OCG.)_

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
- {"status": "OBRIGATÓRIA", "items": [{"item": "Realizar RIPD (Relatório de Impacto à Proteção de Dados Pessoais) conforme Art. 38 da LGPD", "status": "REQUIRED", "priority": "P0"}, {"item": "Documentar base legal para cada categoria de tratamento de dados pessoais (Art. 7º e 11 LGPD)", "status": "REQUIRED", "priority": "P0"}, {"item": "Implementar mecanismo de atendimento aos direitos dos titulares (acesso, retificação, exclusão, portabilidade — Arts. 17-22)", "status": "REQUIRED", "priority": "P0"}, {"item": "Definir procedimento de notificação de incidentes à ANPD (prazo de 2 dias úteis conforme Art. 48 LGPD)", "status": "REQUIRED", "priority": "P0"}, {"item": "Criar política de retenção e descarte de dados com prazos definidos por categoria", "status": "REQUIRED", "priority": "P0"}, {"item": "Documentar transferência internacional de dados (API Anthropic nos EUA) com cláusulas contratuais padrão se aplicável", "status": "REQUIRED", "priority": "P1"}, {"item": "Nomear ou designar DPO (Encarregado de Proteção de Dados) conforme Art. 41 LGPD", "status": "RECOMMENDED", "priority": "P1"}]}
- {"status": "OBRIGATÓRIO", "items": [{"item": "Garantir conformidade com sigilo profissional advocatício (Art. 7º Estatuto da OAB, Art. 154 CP) na arquitetura de acesso", "status": "REQUIRED", "priority": "P0"}, {"item": "RBAC granular com segregação de acesso por tipo de processo/cliente para respeitar sigilo", "status": "REQUIRED", "priority": "P0"}, {"item": "Garantir que dados sigilosos nunca sejam expostos a provedores de IA sem anonimização comprovada", "status": "REQUIRED", "priority": "P0"}]}
- {"status": "OBRIGATÓRIO", "items": [{"item": "Logs de auditoria imutáveis com retenção mínima de 6 meses para registros de acesso a aplicações", "status": "REQUIRED", "priority": "P0"}, {"item": "Logs não devem conter dados pessoais desnecessários", "status": "REQUIRED", "priority": "P1"}]}
- {"items": [{"item": "JWT com rotação de tokens, refresh tokens em httpOnly cookies e blacklist de tokens revogados", "status": "REQUIRED", "priority": "P0"}, {"item": "MFA obrigatório para todos os usuários com acesso a dados confidenciais (Keycloak TOTP/WebAuthn)", "status": "REQUIRED", "priority": "P0"}, {"item": "HTTPS/TLS 1.3 com HSTS em todas as comunicações, incluindo chamadas à API Anthropic", "status": "REQUIRED", "priority": "P0"}, {"item": "Criptografia AES-256 em repouso com gerenciamento de chaves via HashiCorp Vault", "status": "REQUIRED", "priority": "P0"}, {"item": "RBAC com matriz de permissões documentada: roles, endpoints, recursos e prevenção de escalação de privilégios", "status": "REQUIRED", "priority": "P0"}, {"item": "Pipeline de anonimização verificável (Presidio) com testes automatizados antes de chamadas à Anthropic", "status": "REQUIRED", "priority": "P0"}, {"item": "Logs de auditoria imutáveis (append-only) com timestamp confiável, armazenados separadamente dos logs operacionais", "status": "REQUIRED", "priority": "P0"}, {"item": "Rate limiting e proteção contra brute force em endpoints de autenticação (slowapi)", "status": "REQUIRED", "priority": "P1"}, {"item": "Headers de segurança HTTP: CSP, HSTS, X-Frame-Options, X-Content-Type-Options", "status": "REQUIRED", "priority": "P1"}, {"item": "Validação rigorosa de uploads: tipo MIME, tamanho máximo, scanning de malware, nomes sanitizados", "status": "REQUIRED", "priority": "P1"}, {"item": "Scanning de imagens Docker (Trivy/Grype) antes de cada deploy", "status": "REQUIRED", "priority": "P2"}, {"item": "Redis configurado com autenticação e TLS", "status": "RECOMMENDED", "priority": "P2"}, {"item": "Pentest obrigatório antes do lançamento em produção", "status": "REQUIRED", "priority": "P2"}, {"item": "Elaborar threat model formalizado (STRIDE) para o sistema jurídico", "status": "REQUIRED", "priority": "P1"}, {"item": "Documentar plano de resposta a incidentes com SLAs, notificação de breach e procedimentos de recovery", "status": "REQUIRED", "priority": "P1"}]}

### 3.3 Regras de Negócio

_Nenhuma regra de negócio registrada. GP popula via a aba OCG (seção BUSINESS_RULES) ou marcando módulos do backlog como `business_rule`._

### 3.4 Interfaces Externas

_Nenhum repositório externo vinculado ao projeto._

### 3.5 Requisitos pendentes de classificação

Existem **104** módulos no backlog ainda não classificados pelo GP. Abaixo até 10 exemplos — classifique cada um como `functional`, `non_functional` ou `business_rule` na aba Backlog do projeto para que apareçam nas seções corretas deste documento:

- **DataJud HTTP Client** (backend_service, prioridade `medium`)
- **DataJud Connector Service** (backend_service, prioridade `medium`)
- **DataJud Query DSL Builder** (backend_service, prioridade `medium`)
- **Paginação com Search After** (backend_service, prioridade `medium`)
- **DataJud Data Models (DTOs)** (backend_service, prioridade `medium`)
- **Secrets Management Integration** (infrastructure, prioridade `medium`)
- **DataJud Audit Logger** (observability, prioridade `medium`)
- **DataJud Health Check** (observability, prioridade `medium`)
- **Tribunal Alias Configuration** (backend_service, prioridade `medium`)
- **DataJud Cache Layer** (backend_service, prioridade `medium`)
- _… e mais 94 módulos._

---

## 4. Matriz de Rastreabilidade

Cobertura agregada: **104** requisitos (RF `0` · RNF `0` · BR `0` · pendentes `104`). Com spec: **1**. Com código gerado: **0**. Rastreamento completo (spec + código): **0**.

| ID | Requisito | Categoria | Test Specs | Código gerado |
|---|---|---|---|---|
| **REQ-001** | Esqueleto do Backend (API Skeleton) | `—` | `unit` (draft) | _(sem código)_ |
| **REQ-002** | Schema Inicial do Banco de Dados | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-003** | Bootstrap do Frontend (SPA + autenticação) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-004** | Camada de Cache | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-005** | Contrato de Integração com IA | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-006** | Container da Aplicação (Dockerfile + compose) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-007** | Pipeline de CI/CD Inicial | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-008** | Gestão de Secrets e Audit Log | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-009** | Ambiente de Deploy Inicial (dev) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-010** | Observabilidade Básica (logs estruturados + métricas) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-011** | DataJud HTTP Client | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-012** | DataJud Connector Service | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-013** | DataJud Query DSL Builder | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-014** | Paginação com Search After | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-015** | DataJud Data Models (DTOs) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-016** | Secrets Management Integration | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-017** | DataJud Audit Logger | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-018** | DataJud Health Check | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-019** | Tribunal Alias Configuration | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-020** | DataJud Cache Layer | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-021** | Async Data Ingestion Job | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-022** | DataJud Integration Tests | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-023** | API Gateway Rate Limiting | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-024** | Process Search Feature | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-025** | Process Timeline Visualization | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-026** | External Data Source Dashboard | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-027** | Secrets Rotation Automation | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-028** | DataJud Circuit Breaker | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-029** | Query Validation Middleware | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-030** | Data Source Fallback Service | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-031** | Shell da Aplicação Desktop | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-032** | Camada de Dados Criptografada | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-033** | Módulo de Cadastro e Dossiê do Caso | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-034** | Serviço de Ingestão e OCR | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-035** | Módulo de Triagem e Conflito de Interesses | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-036** | Conector HTTP para API do DataJud | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-037** | Módulo de Pesquisa Jurisprudencial Assistida | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-038** | Serviço de Inferência de IA Local | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-039** | Editor Colaborativo com Histórico de Versões | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-040** | Motor de Cálculos Cíveis | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-041** | Painel Gerencial de Portfólio | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-042** | Sistema de Auditoria com Hash Chain | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-043** | Gerenciador de Configurações e Conectores | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-044** | Middleware de Autenticação e Autorização Local | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-045** | Sistema de Logs Estruturados e Health Checks | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-046** | Pipeline de Build e Empacotamento | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-047** | Suite de Testes Automatizados Offline | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-048** | Módulo de Análise de Risco e Simulação | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-049** | Gestão de Contratos e Controle Financeiro | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-050** | Sistema de Backup e Restauração Local | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-051** | Desktop Runtime & Packaging | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-052** | Database Local Embarcado | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-053** | Logging Estruturado & Auditoria Local | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-054** | Health Checks & Self-Diagnostics | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-055** | Authentication & Session Manager (Local) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-056** | Error Handling & Validation Middleware | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-057** | Conector DataJud - Client & Mapper | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-058** | Conector DataJud - Operações de Negócio | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-059** | Job Queue & Async Processor (Local) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-060** | Resilience Module (Retry/Circuit Breaker) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-061** | Modelo de IA Local - Runtime Manager | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-062** | Modelo de IA Local - Update Service | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-063** | Editor de Peças com Templates | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-064** | Painel de Controle e Alertas de Prazos | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-065** | Gestão de Sigilo e Auditoria de Acesso | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-066** | Fluxo de Peer-Review e Aprovação | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-067** | Exportação de Documentos (DOCX/PDF) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-068** | Testes de Contrato para Conector DataJud | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-069** | CI/CD para Builds Desktop | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-070** | Testes de Integração Offline | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-071** | Desktop Application Runtime | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-072** | Embedded Database Layer | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-073** | Setup Wizard | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-074** | Local Authentication Service | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-075** | Dossier Management Core | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-076** | DataJud Connector Service | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-077** | Document Editor with Peer-Review | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-078** | Local AI Plugin Manager | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-079** | Processing Queue Manager | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-080** | Audit Logging Service | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-081** | Export Service with Confirmation | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-082** | Admin Configuration Panel | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-083** | Dashboard Executivo | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-084** | Rate Limiter & Anti-Scraping | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-085** | Local Notification System | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-086** | Data Encryption & Key Management | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-087** | Health Checks & Self-Diagnostics | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-088** | Offline Update Manager | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-089** | CI/CD for Desktop Packaging | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-090** | Contract Test Suite for Connectors | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-091** | Instalador Desktop (Electron/Tauri) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-092** | Configuração de Hardware e IA | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-093** | Gerenciador de Criptografia SQLCipher | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-094** | Controle de Acesso Baseado em Nível de Sigilo (RBAC/ABAC) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-095** | Integração Resiliente com DataJud | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-096** | Sistema de Peer-Review de Peças | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-097** | Mecanismo de Backup e Restauração Local | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-098** | Monitor de Prevenção de Violação (DataJud) | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-099** | Gerenciador de Licenças Offline | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-100** | Exportador com Controles DLP | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-101** | Pipeline de Build e Assinatura | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-102** | Auditoria Imutável com Hash Chain | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-103** | Sincronização Incremental com DataJud | `—` | _(sem spec)_ | _(sem código)_ |
| **REQ-104** | Paginação Assíncrona de Grandes Volumes | `—` | _(sem spec)_ | _(sem código)_ |

> A matriz é gerada sob demanda no momento da regeneração do ERS. Atualize via `POST /projects/:id/docs/ers/regenerate` ou veja o estado atual em `/projects/:id/docs` → aba **Rastreabilidade**.

---

## Histórico de Revisão

O histórico completo do ERS vive no Git do projeto. Para ver diffs entre versões, use:

```bash
git log -p docs/ERS.md
```

Cada regeneração cria um commit com mensagem canônica `docs(ers): regen a partir do OCG vN — <motivos>` emitido pelo GCA na aba Doc Viva do projeto.

