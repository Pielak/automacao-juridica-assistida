# ADR-001: Monólito Modular com Clean Architecture vs Microserviços

## Metadados

| Campo | Valor |
|---|---|
| **ID** | ADR-001 |
| **Título** | Adoção de Monólito Modular com Clean Architecture |
| **Status** | Aceita |
| **Data** | 2024-01-15 |
| **Decisores** | Equipe de Arquitetura, GP, Tech Lead |
| **Projeto** | Automação Jurídica Assistida |
| **Slug** | automacao-juridica-assistida |

---

## 1. Contexto

O projeto **Automação Jurídica Assistida** é uma plataforma que integra inteligência artificial (Claude/Anthropic) ao fluxo de trabalho jurídico, oferecendo funcionalidades como:

- Autenticação com MFA e controle de acesso baseado em papéis (RBAC)
- Upload e gestão de documentos jurídicos
- Análise automatizada de documentos via IA (Anthropic Claude)
- Chat assistido com contexto jurídico
- Integração com o DataJud (dados públicos do Judiciário)
- Trilha de auditoria completa para compliance (LGPD e regulamentações do setor jurídico)

A equipe inicial é composta por 3-5 desenvolvedores. O produto está em fase de MVP com expectativa de crescimento gradual de usuários (escritórios de advocacia de pequeno e médio porte). A base de usuários estimada para o primeiro ano é de centenas a poucos milhares de usuários concorrentes.

Precisamos decidir a arquitetura de backend que equilibre:
- **Velocidade de entrega** do MVP
- **Manutenibilidade** a médio/longo prazo
- **Segurança e compliance** (dados jurídicos sensíveis, LGPD)
- **Escalabilidade** suficiente para o crescimento projetado
- **Custo operacional** compatível com um produto em fase inicial

---

## 2. Alternativas Consideradas

### 2.1. Microserviços desde o início

**Descrição:** Cada módulo funcional (auth, documents, analysis, chat, audit) seria um serviço independente com seu próprio banco de dados, comunicando-se via mensageria (RabbitMQ/Kafka) e/ou REST/gRPC.

**Prós:**
- Escalabilidade independente por serviço
- Isolamento de falhas entre módulos
- Liberdade tecnológica por serviço (polyglot)
- Deploy independente de cada serviço

**Contras:**
- **Complexidade operacional prematura:** necessidade de orquestração (Kubernetes), service mesh, distributed tracing, circuit breakers entre serviços
- **Overhead de infraestrutura:** múltiplos bancos de dados, filas de mensageria, API gateways, service discovery
- **Custo elevado:** infraestrutura e DevOps significativamente mais caros para uma equipe pequena
- **Consistência de dados:** transações distribuídas (sagas) são complexas e propensas a erros, especialmente crítico em contexto jurídico onde integridade de dados é mandatória
- **Latência adicional:** comunicação inter-serviços adiciona latência em operações que hoje são chamadas de função
- **Equipe insuficiente:** 3-5 desenvolvedores não conseguem manter múltiplos serviços com qualidade
- **Debugging complexo:** rastrear problemas em sistemas distribuídos exige ferramentas e expertise adicionais

### 2.2. Monólito Tradicional (sem modularização)

**Descrição:** Aplicação única sem separação clara de módulos, com acoplamento direto entre funcionalidades.

**Prós:**
- Simplicidade máxima no início
- Deploy trivial
- Sem overhead de comunicação

**Contras:**
- **Big Ball of Mud:** tendência a acoplamento crescente e código espaguete
- **Dificuldade de evolução:** mudanças em um módulo afetam outros de forma imprevisível
- **Testabilidade comprometida:** dependências diretas dificultam testes unitários e de integração
- **Migração futura custosa:** extrair serviços de um monólito acoplado é significativamente mais caro
- **Onboarding difícil:** novos desenvolvedores têm dificuldade em entender o sistema como um todo

### 2.3. Monólito Modular com Clean Architecture (Escolhida) ✅

**Descrição:** Aplicação única (single deployment unit) organizada em módulos funcionais isolados, seguindo princípios de Clean Architecture (Ports & Adapters). Cada módulo possui fronteiras bem definidas com interfaces explícitas, permitindo evolução independente e eventual extração para microserviços se necessário.

**Prós:**
- **Simplicidade operacional:** um único artefato de deploy, um banco de dados, infraestrutura enxuta
- **Modularidade real:** módulos isolados com interfaces (ports) bem definidas impedem acoplamento acidental
- **Testabilidade:** Clean Architecture permite testes unitários puros no domínio, mocks via ports para infraestrutura
- **Transações ACID:** consistência de dados garantida pelo banco relacional, crítico para dados jurídicos
- **Performance:** chamadas entre módulos são chamadas de função in-process, sem latência de rede
- **Evolução incremental:** módulos podem ser extraídos para serviços independentes quando houver justificativa real (escala, equipe, domínio)
- **Custo operacional baixo:** compatível com equipe pequena e orçamento de MVP
- **Onboarding facilitado:** estrutura previsível e padronizada por módulo
- **Compliance facilitado:** trilha de auditoria e controle de acesso centralizados

**Contras:**
- Requer disciplina para manter fronteiras entre módulos
- Escalabilidade limitada a escala vertical (mitigado por processamento assíncrono via Celery)
- Um deploy afeta todos os módulos (mitigado por feature flags e testes abrangentes)

---

## 3. Decisão

**Adotamos o Monólito Modular com Clean Architecture (Alternativa 2.3).**

A aplicação será estruturada como um único artefato de deploy (FastAPI) organizado em módulos funcionais isolados, cada um seguindo a separação de camadas da Clean Architecture.

---

## 4. Estrutura de Camadas

A arquitetura segue o modelo de Clean Architecture (Ports & Adapters) com 4 camadas concêntricas:

```
┌─────────────────────────────────────────────────────┐
│                  APRESENTAÇÃO (API)                  │
│  FastAPI Routers, Middleware, Pydantic Schemas       │
├─────────────────────────────────────────────────────┤
│                  APLICAÇÃO (Use Cases)               │
│  Services, DTOs, Orquestração de regras             │
├─────────────────────────────────────────────────────┤
│                  DOMÍNIO (Entities)                  │
│  Modelos de domínio, Regras de negócio, Ports       │
├─────────────────────────────────────────────────────┤
│                  INFRAESTRUTURA (Adapters)           │
│  SQLAlchemy, Anthropic SDK, Celery, Redis, S3       │
└─────────────────────────────────────────────────────┘
```

### Regra de Dependência

As dependências apontam **sempre para dentro** (em direção ao domínio):

- **Apresentação** → depende de **Aplicação**
- **Aplicação** → depende de **Domínio**
- **Infraestrutura** → implementa interfaces (ports) definidas no **Domínio**
- **Domínio** → **não depende de nenhuma outra camada**

---

## 5. Estrutura de Módulos

Cada módulo funcional segue a mesma estrutura interna:

```
src/
├── modules/
│   ├── auth/                    # Autenticação, JWT, MFA, sessões
│   │   ├── domain/              # Entidades, value objects, ports
│   │   ├── application/         # Use cases, DTOs
│   │   ├── infrastructure/      # Implementações (JWT, bcrypt, TOTP)
│   │   └── presentation/        # Routers FastAPI, schemas Pydantic
│   │
│   ├── users/                   # CRUD de usuários, perfis RBAC
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   │
│   ├── documents/               # Upload, gestão, versionamento
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   │
│   ├── analysis/                # Análise via IA (Anthropic Claude)
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   │
│   ├── chat/                    # Chat assistido com contexto jurídico
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   │
│   ├── datajud/                 # Integração com DataJud
│   │   ├── domain/
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── presentation/
│   │
│   └── audit/                   # Trilha de auditoria e compliance
│       ├── domain/
│       ├── application/
│       ├── infrastructure/
│       └── presentation/
│
├── shared/                      # Código compartilhado entre módulos
│   ├── domain/                  # Base entities, value objects comuns
│   ├── infrastructure/          # Database, cache, logging, config
│   └── presentation/            # Middleware, exception handlers
│
└── main.py                      # Composição raiz (FastAPI app)
```

---

## 6. Regras de Comunicação entre Módulos

### 6.1. Comunicação Síncrona

Módulos comunicam-se **exclusivamente** através de interfaces públicas definidas na camada de aplicação (services). Nunca há acesso direto ao domínio ou infraestrutura de outro módulo.

```
✅ Permitido:  analysis.application.service → documents.application.service
❌ Proibido:   analysis.infrastructure.repo → documents.domain.entity
❌ Proibido:   analysis.presentation.router → documents.infrastructure.repo
```

### 6.2. Comunicação Assíncrona

Operações de longa duração (análise de documentos via IA, integração DataJud) utilizam **Celery** com **Redis** como broker, mantendo a responsividade da API.

### 6.3. Eventos entre Módulos

Para desacoplamento, módulos podem emitir eventos de domínio consumidos por outros módulos via um barramento de eventos in-process (padrão Observer/Mediator). Exemplo:

- `DocumentUploaded` → dispara análise automática (módulo analysis)
- `AnalysisCompleted` → registra na trilha de auditoria (módulo audit)
- `UserAuthenticated` → registra log de acesso (módulo audit)

---

## 7. Estratégia de Escalabilidade

### Fase 1 — MVP (atual)
- Monólito modular único
- PostgreSQL como banco principal
- Redis para cache e broker Celery
- Workers Celery para tarefas assíncronas (análise IA, integração DataJud)
- Deploy em container único (Docker) + workers separados

### Fase 2 — Crescimento (quando necessário)
- Escala horizontal do monólito (múltiplas instâncias atrás de load balancer)
- Escala independente de workers Celery por tipo de tarefa
- Read replicas do PostgreSQL para consultas pesadas
- CDN para assets estáticos do frontend

### Fase 3 — Extração seletiva (se justificado por métricas)
- Extração do módulo `analysis` como serviço independente (maior consumo de recursos por chamadas à API Anthropic)
- Extração do módulo `chat` se WebSocket exigir escala diferenciada
- Comunicação via mensageria (RabbitMQ/Kafka) entre serviços extraídos

**Critérios para extração de um módulo:**
1. Necessidade comprovada de escala independente (métricas de uso)
2. Equipe dedicada disponível para manter o serviço
3. Domínio suficientemente estável (poucas mudanças de interface)
4. Custo-benefício positivo (ganho de escala > custo operacional)

---

## 8. Decisões Técnicas Derivadas

| Aspecto | Decisão | Justificativa |
|---|---|---|
| **Framework** | FastAPI 0.100+ | Async nativo, OpenAPI automático, Pydantic v2 integrado |
| **ORM** | SQLAlchemy 2.0 + asyncpg | ORM assíncrono maduro, suporte a Clean Architecture via Repository Pattern |
| **Migrações** | Alembic | Padrão de mercado para SQLAlchemy, versionamento de schema |
| **Autenticação** | JWT com RS256 + MFA (TOTP) | Segurança robusta, stateless, compatível com SPA |
| **Tarefas assíncronas** | Celery 5+ com Redis | Processamento de IA e integrações sem bloquear a API |
| **Validação** | Pydantic v2 | Performance superior, integração nativa com FastAPI |
| **Logs** | structlog | Logs estruturados facilitam observabilidade e debugging |
| **Rate limiting** | slowapi | Proteção contra abuso, especialmente em endpoints de IA |
| **Resiliência IA** | tenacity | Retry com backoff exponencial para chamadas à Anthropic |

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Acoplamento entre módulos cresce com o tempo | Média | Alto | Revisões de código focadas em fronteiras; linting de imports; testes de arquitetura (ex: `import-linter`) |
| Monólito se torna gargalo de performance | Baixa | Médio | Workers Celery para tarefas pesadas; escala horizontal; métricas de performance desde o MVP |
| Dificuldade de deploy parcial | Média | Baixo | Feature flags; pipeline CI/CD com testes abrangentes; blue-green deployment |
| Banco de dados como ponto único de falha | Baixa | Alto | Backups automatizados; read replicas; monitoramento de saúde |
| Equipe não segue padrões de Clean Architecture | Média | Alto | Templates de módulo; documentação de padrões; ADRs complementares; code review obrigatório |

---

## 10. Métricas de Validação

A decisão será reavaliada se qualquer uma das seguintes condições for atingida:

- **Tempo de deploy** excede 15 minutos consistentemente
- **Tempo de resposta P95** da API excede 2 segundos em endpoints síncronos
- **Equipe** cresce além de 10 desenvolvedores trabalhando simultaneamente no backend
- **Conflitos de merge** em módulos distintos se tornam frequentes (>3 por sprint)
- **Workers Celery** não conseguem processar a fila em tempo aceitável (<5 min para análise de documento)

---

## 11. ADRs Relacionadas

| ADR | Título | Status |
|---|---|---|
| ADR-002 | Escolha de índice vetorial para busca semântica (FAISS vs Milvus) | Pendente (G002) |
| ADR-003 | State machine para ciclo de vida de documentos DataJud | Pendente |
| ADR-004 | Estratégia de autenticação e autorização (JWT + RBAC) | Pendente |
| ADR-005 | Design tokens e sistema de design do frontend | Pendente (G005) |

---

## 12. Referências

- Martin, R. C. (2017). *Clean Architecture: A Craftsman's Guide to Software Structure and Design*
- Richardson, C. (2018). *Microservices Patterns* — Capítulo sobre "Monolith First"
- Fowler, M. (2015). [MonolithFirst](https://martinfowler.com/bliki/MonolithFirst.html)
- FastAPI Documentation — [Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- Avaliação P5 (Arquitetura): Score 88/100 — Validação da escolha arquitetural
- Avaliação P7 (Segurança): Score 85/100 — Validação das decisões de segurança
- Avaliação P2 (Compliance): Score 82/100 — Validação de conformidade LGPD

---

## 13. Histórico de Revisões

| Data | Autor | Descrição |
|---|---|---|
| 2024-01-15 | Equipe de Arquitetura | Criação inicial da ADR |
