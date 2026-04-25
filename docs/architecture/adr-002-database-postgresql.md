# ADR-002: Escolha de PostgreSQL como Database Engine Primário

## Status

**Aceito** — Data: 2024-01-15

## Contexto

O projeto **Automação Jurídica Assistida** necessita de um banco de dados relacional robusto para armazenar e gerenciar dados críticos do domínio jurídico, incluindo:

- **Dados de usuários e autenticação**: perfis, credenciais (hashes bcrypt), sessões JWT, configurações MFA (TOTP secrets).
- **Documentos jurídicos**: metadados de petições, contratos, pareceres e seus respectivos ciclos de vida (state machine de documentos DataJud).
- **Resultados de análises de IA**: outputs estruturados das interações com a API Anthropic (Claude), incluindo histórico de chat e análises semânticas.
- **Trilha de auditoria (audit trail)**: logs imutáveis de todas as operações sensíveis para compliance com LGPD e regulamentações da OAB.
- **Controle de acesso RBAC**: papéis, permissões e associações entre usuários e recursos.
- **Potencial armazenamento vetorial**: embeddings para busca semântica (decisão pendente — ver ADR pendente G002 sobre FAISS vs Milvus vs pgvector).

O sistema é arquitetado como um **Monólito Modular com Clean Architecture**, onde o banco de dados é acessado exclusivamente pela camada de infraestrutura através de ports (interfaces) definidos na camada de aplicação. A stack backend utiliza **Python 3.11+ com FastAPI**, **SQLAlchemy 2.0 com asyncpg** como ORM assíncrono, e **Alembic** para migrações.

### Requisitos Críticos do Domínio Jurídico

1. **Integridade transacional (ACID)**: documentos jurídicos e trilhas de auditoria exigem garantias fortes de consistência.
2. **Conformidade regulatória**: LGPD exige controle granular sobre dados pessoais, incluindo capacidade de anonimização e exclusão seletiva.
3. **Performance em consultas complexas**: relatórios jurídicos envolvem JOINs entre múltiplas tabelas, full-text search em português e agregações temporais.
4. **Escalabilidade vertical adequada**: o volume esperado (escritórios de advocacia de pequeno a médio porte) não justifica sharding horizontal na fase inicial.
5. **Segurança de dados em repouso e em trânsito**: dados jurídicos são sigilosos por natureza (sigilo profissional advocatício).

## Decisão

**Adotamos PostgreSQL 15+ como database engine primário e único do projeto.**

Especificamente:

- **PostgreSQL 15 ou superior** como SGBD relacional.
- **asyncpg** como driver assíncrono nativo para integração com FastAPI/SQLAlchemy 2.0.
- **Alembic** para versionamento e migração de schema.
- **pgcrypto** para funções criptográficas no nível do banco (quando necessário).
- **pg_trgm** e **unaccent** para full-text search otimizado em português brasileiro.
- **pgvector** como candidato para armazenamento de embeddings vetoriais (decisão final pendente no ADR G002).

## Alternativas Consideradas

### 1. MySQL 8.0+

| Critério | Avaliação |
|---|---|
| Conformidade ACID | ✅ Suportado com InnoDB |
| Full-text search em PT-BR | ⚠️ Limitado — sem suporte nativo a dicionários de idioma customizados |
| Tipos de dados avançados | ⚠️ JSONB inferior ao PostgreSQL, sem tipos range, array nativo limitado |
| Extensibilidade | ❌ Ecossistema de extensões muito inferior |
| Suporte a vetores | ❌ Sem equivalente a pgvector |
| Async drivers para Python | ⚠️ aiomysql menos maduro que asyncpg |
| Licenciamento | ⚠️ Oracle ownership — riscos de licenciamento futuro |

**Motivo da rejeição**: Full-text search inferior para português, ecossistema de extensões limitado, tipos de dados menos expressivos para o domínio jurídico.

### 2. MongoDB 7.0+

| Critério | Avaliação |
|---|---|
| Flexibilidade de schema | ✅ Schema-less facilita prototipagem |
| Conformidade ACID | ⚠️ Transações multi-documento adicionadas tardiamente, menos maduras |
| Integridade referencial | ❌ Sem foreign keys — integridade deve ser garantida na aplicação |
| Consultas complexas (JOINs) | ❌ Aggregation pipeline complexo e menos performático que SQL para JOINs |
| Auditoria e compliance | ⚠️ Audit trail mais difícil de garantir sem transações ACID robustas |
| Ecossistema Python async | ✅ Motor (async driver) é maduro |

**Motivo da rejeição**: O domínio jurídico é inerentemente relacional (documentos → partes → processos → tribunais → prazos). A ausência de integridade referencial nativa e transações ACID maduras é um risco inaceitável para dados jurídicos sigilosos e trilhas de auditoria.

### 3. SQLite

| Critério | Avaliação |
|---|---|
| Simplicidade | ✅ Zero configuração |
| Concorrência | ❌ Write lock global — inadequado para aplicação multi-usuário |
| Escalabilidade | ❌ Limitado a cenários single-user ou read-heavy |
| Extensões | ❌ Ecossistema mínimo |

**Motivo da rejeição**: Inadequado para aplicação web multi-usuário com requisitos de concorrência.

### 4. CockroachDB / YugabyteDB (NewSQL)

| Critério | Avaliação |
|---|---|
| Compatibilidade PostgreSQL | ✅ Wire-compatible com PostgreSQL |
| Escalabilidade horizontal | ✅ Distribuído nativamente |
| Complexidade operacional | ❌ Overhead significativo para o volume esperado |
| Custo | ❌ Mais caro em infraestrutura para benefício não necessário na fase atual |
| Maturidade do ecossistema | ⚠️ Menos extensões disponíveis que PostgreSQL vanilla |

**Motivo da rejeição**: Complexidade prematura. O volume esperado (dezenas a centenas de usuários simultâneos) não justifica banco distribuído. Se necessário no futuro, a compatibilidade wire-level com PostgreSQL facilita migração.

## Justificativa Detalhada

### 1. Integridade Transacional e Conformidade ACID

PostgreSQL é reconhecido como o SGBD open-source com a implementação ACID mais robusta. Para o domínio jurídico, isso é crítico:

- **Trilha de auditoria**: inserções em tabelas de audit log dentro da mesma transação que a operação auditada garantem consistência.
- **State machine de documentos**: transições de estado (rascunho → revisão → aprovado → protocolado) são atômicas.
- **Operações financeiras**: controle de honorários e custas processuais exige precisão transacional.

### 2. Full-Text Search Nativo em Português

PostgreSQL oferece full-text search (FTS) com suporte nativo a dicionários de idioma:

```sql
-- Exemplo: configuração de FTS para português brasileiro
CREATE TEXT SEARCH CONFIGURATION pt_br (COPY = portuguese);

-- Índice GIN para busca em documentos jurídicos
CREATE INDEX idx_documents_fts ON documents
  USING GIN (to_tsvector('portuguese', content));

-- Busca com ranking
SELECT id, title, ts_rank(to_tsvector('portuguese', content), query) AS rank
FROM documents, plainto_tsquery('portuguese', 'recurso extraordinário') query
WHERE to_tsvector('portuguese', content) @@ query
ORDER BY rank DESC;
```

Isso elimina a necessidade de um serviço externo de busca (Elasticsearch) na fase inicial, reduzindo complexidade operacional.

### 3. Tipos de Dados Avançados

- **JSONB**: armazenamento eficiente de metadados semi-estruturados (respostas da API Anthropic, configurações de análise).
- **ARRAY**: listas de tags, categorias jurídicas, partes processuais.
- **UUID**: chaves primárias seguras sem exposição de sequência.
- **TIMESTAMP WITH TIME ZONE**: essencial para prazos processuais (fuso horário correto).
- **RANGE types**: períodos de vigência de contratos, intervalos de datas processuais.
- **ENUM types**: estados de documentos, tipos de peças processuais.

### 4. Extensibilidade (pgvector)

A extensão **pgvector** permite armazenar embeddings vetoriais diretamente no PostgreSQL:

```sql
-- Exemplo: tabela de embeddings para busca semântica
CREATE EXTENSION vector;

CREATE TABLE document_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES documents(id),
  embedding vector(1536),  -- dimensão do embedding Anthropic/OpenAI
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_embeddings_ivfflat
  ON document_embeddings USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

Isso pode eliminar a necessidade de um serviço vetorial separado (FAISS/Milvus) para volumes moderados, simplificando a arquitetura. A decisão final será documentada no ADR G002.

### 5. Segurança

- **Row-Level Security (RLS)**: controle de acesso granular no nível do banco, complementando o RBAC da aplicação.
- **Criptografia em trânsito**: TLS nativo para conexões.
- **Criptografia em repouso**: suporte via pgcrypto e Transparent Data Encryption (TDE) em versões enterprise ou via filesystem encryption.
- **Audit logging**: extensão pgaudit para logging de operações DDL/DML.
- **Roles e privileges**: modelo de permissões granular para princípio de menor privilégio.

### 6. Ecossistema Python/FastAPI

A integração com a stack backend é madura e bem documentada:

- **SQLAlchemy 2.0**: suporte first-class a PostgreSQL com dialeto otimizado.
- **asyncpg**: driver assíncrono de alta performance (escrito em Cython), ideal para FastAPI.
- **Alembic**: migrações robustas com suporte a autogenerate a partir de modelos SQLAlchemy.
- **Pydantic v2**: serialização/deserialização eficiente de tipos PostgreSQL (UUID, datetime, JSONB).

### 7. Maturidade e Comunidade

- **35+ anos de desenvolvimento ativo** (desde 1986 como POSTGRES, 1996 como PostgreSQL).
- **Comunidade open-source robusta** sem riscos de licenciamento corporativo.
- **Licença PostgreSQL** (similar a MIT/BSD) — sem restrições comerciais.
- **Adoção massiva** em sistemas jurídicos e governamentais (PJe, e-SAJ utilizam PostgreSQL).

## Consequências

### Positivas

1. **Banco de dados único** para dados relacionais, full-text search e potencialmente vetores — simplifica operações e backup.
2. **Garantias ACID robustas** atendem aos requisitos de integridade do domínio jurídico.
3. **Full-text search nativo** em português elimina dependência de serviço externo de busca na fase inicial.
4. **Ecossistema Python maduro** com asyncpg + SQLAlchemy 2.0 + Alembic.
5. **Row-Level Security** complementa o RBAC da aplicação para defesa em profundidade.
6. **Caminho de evolução claro**: se necessário, migração para CockroachDB/YugabyteDB é facilitada pela compatibilidade wire-level.
7. **Custo zero de licenciamento** — open-source com licença permissiva.

### Negativas

1. **Escalabilidade horizontal limitada**: sharding nativo não é trivial (mitigação: Citus extension ou migração para NewSQL se necessário).
2. **Complexidade de tuning**: PostgreSQL requer configuração cuidadosa de `shared_buffers`, `work_mem`, `effective_cache_size` para performance ótima (mitigação: documentar configurações recomendadas por ambiente).
3. **Backup e recovery**: requer estratégia explícita de backup (pg_dump, WAL archiving, pg_basebackup) — não é "managed" por padrão (mitigação: usar serviço gerenciado em produção — AWS RDS, Google Cloud SQL, ou equivalente).
4. **pgvector pode não escalar**: para volumes muito grandes de embeddings (milhões+), FAISS ou Milvus podem ser necessários (mitigação: decisão será revisada no ADR G002 com base em benchmarks).

### Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Performance degradada com volume alto | Baixa (fase inicial) | Médio | Monitoramento com pg_stat_statements; índices otimizados; connection pooling com PgBouncer |
| Perda de dados | Muito baixa | Crítico | WAL archiving + backups diários + replicação síncrona em produção |
| Lock contention em tabelas de auditoria | Média | Baixo | Tabelas de audit com INSERT-only (append-only); particionamento por data |
| Complexidade de migrações | Média | Médio | Alembic com revisões versionadas; testes de migração em CI/CD; rollback scripts |

## Configuração Recomendada por Ambiente

### Desenvolvimento

- PostgreSQL 15+ via Docker (`postgres:15-alpine`)
- Configuração padrão com `log_statement = 'all'` para debugging
- Volume persistente local para dados

### Testes (CI/CD)

- PostgreSQL 15+ via Docker (efêmero por pipeline)
- Extensões habilitadas: `uuid-ossp`, `pgcrypto`, `pg_trgm`, `unaccent`
- Schema criado via Alembic migrations

### Produção

- Serviço gerenciado (AWS RDS PostgreSQL, Google Cloud SQL, ou Azure Database for PostgreSQL)
- Replicação com pelo menos 1 réplica de leitura
- Backups automáticos com retenção mínima de 30 dias
- Criptografia em repouso habilitada (AES-256)
- Connection pooling via PgBouncer ou equivalente do serviço gerenciado
- Monitoramento via `pg_stat_statements` + alertas de performance

## Extensões PostgreSQL Requeridas

| Extensão | Propósito | Prioridade |
|---|---|---|
| `uuid-ossp` | Geração de UUIDs v4 para chaves primárias | Obrigatória |
| `pgcrypto` | Funções criptográficas (gen_random_uuid, etc.) | Obrigatória |
| `pg_trgm` | Índices trigram para busca por similaridade | Obrigatória |
| `unaccent` | Remoção de acentos em buscas full-text | Obrigatória |
| `pgvector` | Armazenamento de embeddings vetoriais | Condicional (ver ADR G002) |
| `pgaudit` | Audit logging de operações DDL/DML | Recomendada (produção) |

## Integração com a Arquitetura Clean Architecture

Na arquitetura do projeto, o PostgreSQL é acessado exclusivamente pela **camada de infraestrutura**:

```
┌─────────────────────────────────────────────┐
│  Camada de Apresentação (FastAPI Routers)    │
├─────────────────────────────────────────────┤
│  Camada de Aplicação (Use Cases / Services)  │
│  ┌─────────────────────────────────────┐     │
│  │  Ports (Interfaces/Abstrações)      │     │
│  │  - IDocumentRepository              │     │
│  │  - IUserRepository                  │     │
│  │  - IAuditLogRepository              │     │
│  └─────────────────────────────────────┘     │
├─────────────────────────────────────────────┤
│  Camada de Infraestrutura (Adapters)         │
│  ┌─────────────────────────────────────┐     │
│  │  SQLAlchemy Repositories            │     │
│  │  (implementam os Ports acima)       │     │
│  │  - SQLAlchemyDocumentRepository     │     │
│  │  - SQLAlchemyUserRepository         │     │
│  │  - SQLAlchemyAuditLogRepository     │     │
│  └─────────────────────────────────────┘     │
│  ┌─────────────────────────────────────┐     │
│  │  asyncpg + SQLAlchemy 2.0 Engine    │     │
│  │  ↕                                  │     │
│  │  PostgreSQL 15+                     │     │
│  └─────────────────────────────────────┘     │
└─────────────────────────────────────────────┘
```

Essa separação garante que a escolha de PostgreSQL pode ser substituída no futuro sem impacto nas camadas superiores — basta implementar novos adapters que satisfaçam os mesmos ports.

## Referências

- [PostgreSQL 15 Documentation](https://www.postgresql.org/docs/15/)
- [SQLAlchemy 2.0 — PostgreSQL Dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
- [asyncpg — High Performance PostgreSQL Client](https://github.com/MagicStack/asyncpg)
- [pgvector — Open-source vector similarity search](https://github.com/pgvector/pgvector)
- [Alembic — Database Migrations](https://alembic.sqlalchemy.org/)
- ADR-001: Escolha da arquitetura Monólito Modular (referência cruzada)
- ADR G002 (pendente): Decisão sobre armazenamento vetorial (FAISS vs Milvus vs pgvector)
- ADR G005 (pendente): Design tokens do frontend

## Decisores

- **Arquiteto de Software** (P5 — Arquitetura, score 88)
- **Especialista em Segurança** (P7 — Segurança, score 85)
- **Especialista em Compliance** (P2 — Compliance, score 82)

## Revisão

Este ADR deve ser revisado em **6 meses** ou quando:
- O volume de dados ultrapassar 100GB.
- O número de usuários simultâneos ultrapassar 500.
- A decisão do ADR G002 (armazenamento vetorial) for finalizada.
- Houver necessidade de escalabilidade horizontal.