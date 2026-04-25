# Procedimentos de Backup e Restore — Automação Jurídica Assistida

## Sumário

1. [Visão Geral](#visão-geral)
2. [Classificação dos Dados](#classificação-dos-dados)
3. [Política de Backup](#política-de-backup)
4. [Infraestrutura de Backup](#infraestrutura-de-backup)
5. [Procedimentos de Backup](#procedimentos-de-backup)
   - 5.1 [Backup do PostgreSQL](#51-backup-do-postgresql)
   - 5.2 [Backup de Arquivos (Documentos Jurídicos)](#52-backup-de-arquivos-documentos-jurídicos)
   - 5.3 [Backup do Redis](#53-backup-do-redis)
   - 5.4 [Backup de Configurações e Secrets](#54-backup-de-configurações-e-secrets)
   - 5.5 [Backup do Índice Vetorial](#55-backup-do-índice-vetorial)
6. [Procedimentos de Restore](#procedimentos-de-restore)
   - 6.1 [Restore do PostgreSQL](#61-restore-do-postgresql)
   - 6.2 [Restore de Arquivos](#62-restore-de-arquivos)
   - 6.3 [Restore do Redis](#63-restore-do-redis)
   - 6.4 [Restore de Configurações e Secrets](#64-restore-de-configurações-e-secrets)
   - 6.5 [Restore do Índice Vetorial](#65-restore-do-índice-vetorial)
7. [Automação com Cron / Celery](#automação-com-cron--celery)
8. [Verificação e Testes de Integridade](#verificação-e-testes-de-integridade)
9. [Retenção e Rotação](#retenção-e-rotação)
10. [Segurança e Criptografia](#segurança-e-criptografia)
11. [Disaster Recovery (DR)](#disaster-recovery-dr)
12. [Conformidade LGPD](#conformidade-lgpd)
13. [Runbook de Emergência](#runbook-de-emergência)
14. [Contatos e Escalação](#contatos-e-escalação)

---

## Visão Geral

Este documento descreve os procedimentos operacionais de backup e restore para o sistema **Automação Jurídica Assistida**. Dado que o sistema manipula **dados jurídicos confidenciais** (petições, documentos processuais, análises de IA, dados pessoais de partes envolvidas), os procedimentos seguem requisitos rigorosos de:

- **Confidencialidade**: Criptografia em repouso e em trânsito para todos os backups.
- **Integridade**: Verificação de checksums (SHA-256) em cada backup.
- **Disponibilidade**: RPO (Recovery Point Objective) e RTO (Recovery Time Objective) definidos.
- **Conformidade**: Aderência à LGPD, Marco Civil da Internet e normas da OAB.

### Objetivos de Recuperação

| Métrica | Valor Alvo | Descrição |
|---------|------------|----------|
| **RPO** | ≤ 1 hora | Perda máxima de dados aceitável |
| **RTO** | ≤ 4 horas | Tempo máximo para restauração completa |
| **Retenção mínima** | 5 anos | Conforme legislação processual brasileira |
| **Teste de restore** | Mensal | Validação obrigatória de integridade |

---

## Classificação dos Dados

Todos os dados do sistema são classificados conforme seu nível de sensibilidade:

| Categoria | Exemplos | Classificação | Tratamento no Backup |
|-----------|----------|---------------|---------------------|
| Documentos jurídicos | Petições, contratos, procurações | **CONFIDENCIAL** | Criptografia AES-256, acesso restrito |
| Dados pessoais | Nomes, CPFs, endereços de partes | **SENSÍVEL (LGPD)** | Criptografia AES-256, log de acesso |
| Análises de IA | Respostas do Claude, embeddings | **CONFIDENCIAL** | Criptografia AES-256 |
| Dados de autenticação | Hashes de senha, tokens MFA | **CRÍTICO** | Criptografia AES-256, isolamento |
| Logs de auditoria | Trilha de ações do sistema | **RESTRITO** | Criptografia, imutabilidade |
| Configurações | Variáveis de ambiente, secrets | **CRÍTICO** | Vault/KMS, backup separado |
| Metadados do sistema | Schemas, migrações Alembic | **INTERNO** | Versionado no Git + backup |

---

## Política de Backup

### Estratégia 3-2-1

Adotamos a estratégia **3-2-1** como padrão mínimo:

- **3** cópias dos dados (produção + 2 backups)
- **2** tipos de mídia/storage diferentes
- **1** cópia offsite (região geográfica diferente)

### Tipos de Backup

| Tipo | Frequência | Janela | Retenção | Escopo |
|------|-----------|--------|----------|--------|
| **Full** | Semanal (domingo 02:00 BRT) | 2h máx | 90 dias | Todos os dados |
| **Incremental** | Diário (02:00 BRT) | 30min máx | 30 dias | Alterações desde último full |
| **WAL Archiving** | Contínuo | Tempo real | 7 dias | PostgreSQL WAL logs |
| **Snapshot** | A cada 6 horas | 5min | 48 horas | Snapshots de volume |

---

## Infraestrutura de Backup

### Componentes

```
┌─────────────────────────────────────────────────────────┐
│                    PRODUÇÃO                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │PostgreSQL│  │  Minio/  │  │  Redis   │  │ FAISS/ │  │
│  │  (dados) │  │   S3     │  │ (cache)  │  │ Milvus │  │
│  │          │  │ (arquivos│  │          │  │(vetores│  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘  │
│       │             │             │             │        │
└───────┼─────────────┼─────────────┼─────────────┼───────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────┐
│              SERVIDOR DE BACKUP (LOCAL)                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │  /backup/                                        │   │
│  │  ├── postgresql/                                 │   │
│  │  │   ├── full/                                   │   │
│  │  │   ├── incremental/                            │   │
│  │  │   └── wal_archive/                            │   │
│  │  ├── files/                                      │   │
│  │  ├── redis/                                      │   │
│  │  ├── vector_index/                               │   │
│  │  └── configs/                                    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼ (cópia offsite criptografada)
┌─────────────────────────────────────────────────────────┐
│           STORAGE OFFSITE (S3 / Região Diferente)       │
│  Bucket: automacao-juridica-backup-offsite               │
│  Criptografia: SSE-S3 + client-side AES-256             │
│  Lifecycle: Glacier após 30 dias                        │
└─────────────────────────────────────────────────────────┘
```

### Variáveis de Ambiente Necessárias

```bash
# Configuração de backup — definir em /etc/automacao-juridica/backup.env

# PostgreSQL
BACKUP_PG_HOST=localhost
BACKUP_PG_PORT=5432
BACKUP_PG_DATABASE=automacao_juridica
BACKUP_PG_USER=backup_user
BACKUP_PG_PASSWORD=  # Usar vault/secrets manager

# Storage local
BACKUP_LOCAL_PATH=/backup/automacao-juridica
BACKUP_RETENTION_DAYS_FULL=90
BACKUP_RETENTION_DAYS_INCREMENTAL=30
BACKUP_RETENTION_DAYS_WAL=7

# Storage offsite (S3-compatible)
BACKUP_S3_ENDPOINT=https://s3.sa-east-1.amazonaws.com
BACKUP_S3_BUCKET=automacao-juridica-backup-offsite
BACKUP_S3_ACCESS_KEY=  # Usar vault/secrets manager
BACKUP_S3_SECRET_KEY=  # Usar vault/secrets manager
BACKUP_S3_REGION=sa-east-1

# Criptografia
BACKUP_ENCRYPTION_KEY=  # Chave AES-256, armazenada em vault separado
BACKUP_GPG_KEY_ID=  # ID da chave GPG para criptografia assimétrica

# Notificações
BACKUP_NOTIFY_EMAIL=infra@escritorio.com.br
BACKUP_NOTIFY_SLACK_WEBHOOK=  # Opcional
```

---

## Procedimentos de Backup

### 5.1 Backup do PostgreSQL

O PostgreSQL armazena todos os dados estruturados do sistema: usuários, documentos (metadados), análises, logs de auditoria, sessões e configurações RBAC.

#### 5.1.1 Backup Full (Semanal)

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/backup_pg_full.sh
# Propósito: Backup full do PostgreSQL com criptografia
# Execução: Semanal (domingo 02:00 BRT via cron)

set -euo pipefail

# Carregar variáveis de ambiente
source /etc/automacao-juridica/backup.env

# Variáveis
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_LOCAL_PATH}/postgresql/full"
BACKUP_FILE="pg_full_${DATE}.sql.gz.enc"
CHECKSUM_FILE="pg_full_${DATE}.sha256"
LOG_FILE="/var/log/automacao-juridica/backup_pg_full_${DATE}.log"

# Criar diretório se não existir
mkdir -p "${BACKUP_DIR}"
mkdir -p /var/log/automacao-juridica

echo "[$(date -Iseconds)] Iniciando backup full do PostgreSQL..." | tee -a "${LOG_FILE}"

# Executar pg_dump com compressão e criptografia
PGPASSWORD="${BACKUP_PG_PASSWORD}" pg_dump \
  --host="${BACKUP_PG_HOST}" \
  --port="${BACKUP_PG_PORT}" \
  --username="${BACKUP_PG_USER}" \
  --dbname="${BACKUP_PG_DATABASE}" \
  --format=custom \
  --compress=9 \
  --verbose \
  --file="/tmp/pg_full_${DATE}.dump" \
  2>> "${LOG_FILE}"

# Verificar se o dump foi criado com sucesso
if [ ! -f "/tmp/pg_full_${DATE}.dump" ]; then
  echo "[$(date -Iseconds)] ERRO: Falha ao criar dump do PostgreSQL" | tee -a "${LOG_FILE}"
  # Enviar alerta
  curl -s -X POST "${BACKUP_NOTIFY_SLACK_WEBHOOK}" \
    -H 'Content-type: application/json' \
    -d '{"text":"🔴 FALHA no backup full do PostgreSQL - Automação Jurídica"}' || true
  exit 1
fi

# Criptografar com GPG (chave assimétrica)
gpg --batch --yes --trust-model always \
  --recipient "${BACKUP_GPG_KEY_ID}" \
  --output "${BACKUP_DIR}/${BACKUP_FILE}" \
  --encrypt "/tmp/pg_full_${DATE}.dump" \
  2>> "${LOG_FILE}"

# Gerar checksum SHA-256
sha256sum "${BACKUP_DIR}/${BACKUP_FILE}" > "${BACKUP_DIR}/${CHECKSUM_FILE}"

# Registrar tamanho do backup
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
echo "[$(date -Iseconds)] Backup full concluído: ${BACKUP_FILE} (${BACKUP_SIZE})" | tee -a "${LOG_FILE}"

# Limpar arquivo temporário de forma segura
shred -u "/tmp/pg_full_${DATE}.dump"

# Copiar para storage offsite
aws s3 cp \
  "${BACKUP_DIR}/${BACKUP_FILE}" \
  "s3://${BACKUP_S3_BUCKET}/postgresql/full/${BACKUP_FILE}" \
  --sse AES256 \
  --endpoint-url "${BACKUP_S3_ENDPOINT}" \
  --region "${BACKUP_S3_REGION}" \
  2>> "${LOG_FILE}"

aws s3 cp \
  "${BACKUP_DIR}/${CHECKSUM_FILE}" \
  "s3://${BACKUP_S3_BUCKET}/postgresql/full/${CHECKSUM_FILE}" \
  --sse AES256 \
  --endpoint-url "${BACKUP_S3_ENDPOINT}" \
  --region "${BACKUP_S3_REGION}" \
  2>> "${LOG_FILE}"

echo "[$(date -Iseconds)] Backup offsite concluído com sucesso" | tee -a "${LOG_FILE}"

# Notificação de sucesso
curl -s -X POST "${BACKUP_NOTIFY_SLACK_WEBHOOK}" \
  -H 'Content-type: application/json' \
  -d "{\"text\":\"✅ Backup full PostgreSQL concluído - ${BACKUP_SIZE} - Automação Jurídica\"}" || true

# Registrar no log de auditoria do sistema
# TODO: Integrar com endpoint de auditoria do backend (POST /api/v1/audit/backup-event)

exit 0
```

#### 5.1.2 Backup Incremental (Diário) via WAL Archiving

Configurar o PostgreSQL para arquivamento contínuo de WAL:

```ini
# postgresql.conf — configurações de WAL archiving
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /backup/automacao-juridica/postgresql/wal_archive/%f && cp %p /backup/automacao-juridica/postgresql/wal_archive/%f && gpg --batch --yes --trust-model always --recipient $BACKUP_GPG_KEY_ID --output /backup/automacao-juridica/postgresql/wal_archive/%f.enc --encrypt /backup/automacao-juridica/postgresql/wal_archive/%f && shred -u /backup/automacao-juridica/postgresql/wal_archive/%f'
archive_timeout = 300  # Forçar arquivamento a cada 5 minutos (RPO ≤ 5min)
max_wal_senders = 3
wal_keep_size = 1GB
```

#### 5.1.3 Backup com pg_basebackup (Para PITR)

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/backup_pg_basebackup.sh
# Propósito: Backup base para Point-in-Time Recovery (PITR)
# Execução: Semanal (sábado 03:00 BRT)

set -euo pipefail
source /etc/automacao-juridica/backup.env

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_LOCAL_PATH}/postgresql/basebackup"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -Iseconds)] Iniciando pg_basebackup para PITR..."

PGPASSWORD="${BACKUP_PG_PASSWORD}" pg_basebackup \
  --host="${BACKUP_PG_HOST}" \
  --port="${BACKUP_PG_PORT}" \
  --username="${BACKUP_PG_USER}" \
  --pgdata="${BACKUP_DIR}/base_${DATE}" \
  --format=tar \
  --gzip \
  --compress=9 \
  --wal-method=stream \
  --checkpoint=fast \
  --label="automacao_juridica_base_${DATE}" \
  --verbose

# Criptografar o diretório completo
tar -cf - -C "${BACKUP_DIR}" "base_${DATE}" | \
  gpg --batch --yes --trust-model always \
    --recipient "${BACKUP_GPG_KEY_ID}" \
    --output "${BACKUP_DIR}/base_${DATE}.tar.enc" \
    --encrypt

# Limpar diretório não criptografado
rm -rf "${BACKUP_DIR}/base_${DATE}"

# Gerar checksum
sha256sum "${BACKUP_DIR}/base_${DATE}.tar.enc" > "${BACKUP_DIR}/base_${DATE}.sha256"

echo "[$(date -Iseconds)] pg_basebackup concluído com sucesso"
```

### 5.2 Backup de Arquivos (Documentos Jurídicos)

Documentos jurídicos (PDFs, DOCXs, imagens digitalizadas) são armazenados em storage de objetos (MinIO/S3 local).

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/backup_files.sh
# Propósito: Backup incremental de documentos jurídicos
# Execução: Diário (03:00 BRT)

set -euo pipefail
source /etc/automacao-juridica/backup.env

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_LOCAL_PATH}/files"
LAST_BACKUP_MARKER="${BACKUP_DIR}/.last_backup_timestamp"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -Iseconds)] Iniciando backup de documentos jurídicos..."

# Usar rclone para sincronização incremental com criptografia
# rclone deve estar configurado com remote 'minio-local' e 'offsite-s3'

# Sincronizar do MinIO local para diretório de backup
rclone sync \
  minio-local:automacao-juridica-documents \
  "${BACKUP_DIR}/documents_${DATE}" \
  --transfers=4 \
  --checkers=8 \
  --log-file=/var/log/automacao-juridica/backup_files_${DATE}.log \
  --log-level=INFO \
  --stats=30s

# Criar arquivo tar criptografado
tar -cf - -C "${BACKUP_DIR}" "documents_${DATE}" | \
  gpg --batch --yes --trust-model always \
    --recipient "${BACKUP_GPG_KEY_ID}" \
    --output "${BACKUP_DIR}/documents_${DATE}.tar.enc" \
    --encrypt

# Gerar checksum
sha256sum "${BACKUP_DIR}/documents_${DATE}.tar.enc" > "${BACKUP_DIR}/documents_${DATE}.sha256"

# Limpar diretório temporário
rm -rf "${BACKUP_DIR}/documents_${DATE}"

# Copiar para offsite
rclone copy \
  "${BACKUP_DIR}/documents_${DATE}.tar.enc" \
  offsite-s3:${BACKUP_S3_BUCKET}/files/ \
  --log-file=/var/log/automacao-juridica/backup_files_offsite_${DATE}.log

rclone copy \
  "${BACKUP_DIR}/documents_${DATE}.sha256" \
  offsite-s3:${BACKUP_S3_BUCKET}/files/ \
  --log-file=/var/log/automacao-juridica/backup_files_offsite_${DATE}.log

# Atualizar marcador de último backup
date -Iseconds > "${LAST_BACKUP_MARKER}"

echo "[$(date -Iseconds)] Backup de documentos concluído com sucesso"
```

### 5.3 Backup do Redis

Redis é usado para cache e filas do Celery. Embora seja volátil por natureza, fazemos backup do RDB para recuperação rápida.

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/backup_redis.sh
# Propósito: Backup do snapshot RDB do Redis
# Execução: Diário (03:30 BRT)

set -euo pipefail
source /etc/automacao-juridica/backup.env

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_LOCAL_PATH}/redis"
REDIS_DATA_DIR="/var/lib/redis"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -Iseconds)] Iniciando backup do Redis..."

# Forçar snapshot RDB
redis-cli BGSAVE
sleep 5  # Aguardar conclusão do BGSAVE

# Verificar se o BGSAVE foi concluído
while [ "$(redis-cli LASTSAVE)" == "$(cat ${BACKUP_DIR}/.last_redis_save 2>/dev/null || echo 0)" ]; do
  sleep 1
done
redis-cli LASTSAVE > "${BACKUP_DIR}/.last_redis_save"

# Copiar e criptografar o dump.rdb
cp "${REDIS_DATA_DIR}/dump.rdb" "/tmp/redis_dump_${DATE}.rdb"

gpg --batch --yes --trust-model always \
  --recipient "${BACKUP_GPG_KEY_ID}" \
  --output "${BACKUP_DIR}/redis_${DATE}.rdb.enc" \
  --encrypt "/tmp/redis_dump_${DATE}.rdb"

sha256sum "${BACKUP_DIR}/redis_${DATE}.rdb.enc" > "${BACKUP_DIR}/redis_${DATE}.sha256"

shred -u "/tmp/redis_dump_${DATE}.rdb"

echo "[$(date -Iseconds)] Backup do Redis concluído"
```

### 5.4 Backup de Configurações e Secrets

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/backup_configs.sh
# Propósito: Backup de configurações do sistema (exceto secrets em vault)
# Execução: Semanal (domingo 04:00 BRT)

set -euo pipefail
source /etc/automacao-juridica/backup.env

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_LOCAL_PATH}/configs"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -Iseconds)] Iniciando backup de configurações..."

# Listar arquivos de configuração a serem incluídos
CONFIG_FILES=(
  "/etc/automacao-juridica/"
  "/etc/nginx/sites-available/automacao-juridica"
  "/etc/nginx/conf.d/security-headers.conf"
  "/etc/systemd/system/automacao-juridica*.service"
  "/etc/cron.d/automacao-juridica-backup"
  "/opt/automacao-juridica/docker-compose.yml"
  "/opt/automacao-juridica/docker-compose.prod.yml"
  "/opt/automacao-juridica/.env.example"
)

# IMPORTANTE: NÃO incluir .env de produção (secrets estão no vault)
# Exportar secrets do vault separadamente

tar -czf "/tmp/configs_${DATE}.tar.gz" \
  --ignore-failed-read \
  "${CONFIG_FILES[@]}" \
  2>/dev/null || true

gpg --batch --yes --trust-model always \
  --recipient "${BACKUP_GPG_KEY_ID}" \
  --output "${BACKUP_DIR}/configs_${DATE}.tar.gz.enc" \
  --encrypt "/tmp/configs_${DATE}.tar.gz"

sha256sum "${BACKUP_DIR}/configs_${DATE}.tar.gz.enc" > "${BACKUP_DIR}/configs_${DATE}.sha256"

shred -u "/tmp/configs_${DATE}.tar.gz"

# Backup do Alembic migration history
pg_dump \
  --host="${BACKUP_PG_HOST}" \
  --port="${BACKUP_PG_PORT}" \
  --username="${BACKUP_PG_USER}" \
  --dbname="${BACKUP_PG_DATABASE}" \
  --table=alembic_version \
  --data-only \
  --file="${BACKUP_DIR}/alembic_version_${DATE}.sql"

echo "[$(date -Iseconds)] Backup de configurações concluído"
```

### 5.5 Backup do Índice Vetorial

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/backup_vector_index.sh
# Propósito: Backup do índice vetorial (FAISS ou Milvus)
# Execução: Diário (04:00 BRT)
# TODO: Ajustar conforme decisão do ADR G002 (FAISS vs Milvus)

set -euo pipefail
source /etc/automacao-juridica/backup.env

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_LOCAL_PATH}/vector_index"
VECTOR_INDEX_PATH="/var/lib/automacao-juridica/vector_index"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -Iseconds)] Iniciando backup do índice vetorial..."

# Para FAISS: copiar arquivos .index e .pkl
# Para Milvus: usar milvus-backup tool

# Abordagem FAISS (padrão até decisão ADR G002)
if [ -d "${VECTOR_INDEX_PATH}" ]; then
  tar -czf "/tmp/vector_index_${DATE}.tar.gz" \
    -C "$(dirname ${VECTOR_INDEX_PATH})" \
    "$(basename ${VECTOR_INDEX_PATH})"

  gpg --batch --yes --trust-model always \
    --recipient "${BACKUP_GPG_KEY_ID}" \
    --output "${BACKUP_DIR}/vector_index_${DATE}.tar.gz.enc" \
    --encrypt "/tmp/vector_index_${DATE}.tar.gz"

  sha256sum "${BACKUP_DIR}/vector_index_${DATE}.tar.gz.enc" > "${BACKUP_DIR}/vector_index_${DATE}.sha256"

  shred -u "/tmp/vector_index_${DATE}.tar.gz"

  echo "[$(date -Iseconds)] Backup do índice vetorial concluído"
else
  echo "[$(date -Iseconds)] AVISO: Diretório do índice vetorial não encontrado: ${VECTOR_INDEX_PATH}"
fi
```

---

## Procedimentos de Restore

> ⚠️ **ATENÇÃO**: Procedimentos de restore devem ser executados apenas por pessoal autorizado. Toda operação de restore deve ser registrada no log de auditoria e comunicada ao DPO (Data Protection Officer) quando envolver dados pessoais.

### Pré-requisitos para Restore

1. Acesso à chave GPG privada de descriptografia
2. Credenciais de acesso ao storage offsite
3. Autorização formal do responsável técnico
4. Registro no log de auditoria (motivo, responsável, escopo)
5. Ambiente de destino preparado e isolado (se restore de teste)

### 6.1 Restore do PostgreSQL

#### 6.1.1 Restore Full

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/restore_pg_full.sh
# Propósito: Restore completo do PostgreSQL a partir de backup full
# USO: ./restore_pg_full.sh <arquivo_backup.sql.gz.enc> [--target-db=nome_db]

set -euo pipefail
source /etc/automacao-juridica/backup.env

BACKUP_FILE="$1"
TARGET_DB="${2:-${BACKUP_PG_DATABASE}}"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/automacao-juridica/restore_pg_${DATE}.log"

if [ -z "${BACKUP_FILE}" ]; then
  echo "Uso: $0 <arquivo_backup.sql.gz.enc> [--target-db=nome_db]"
  echo "Exemplo: $0 /backup/automacao-juridica/postgresql/full/pg_full_20240115_020000.sql.gz.enc"
  exit 1
fi

echo "========================================" | tee -a "${LOG_FILE}"
echo "RESTORE DO POSTGRESQL" | tee -a "${LOG_FILE}"
echo "Arquivo: ${BACKUP_FILE}" | tee -a "${LOG_FILE}"
echo "Banco destino: ${TARGET_DB}" | tee -a "${LOG_FILE}"
echo "Data/Hora: $(date -Iseconds)" | tee -a "${LOG_FILE}"
echo "Operador: $(whoami)" | tee -a "${LOG_FILE}"
echo "========================================" | tee -a "${LOG_FILE}"

# Verificar checksum
CHECKSUM_FILE="${BACKUP_FILE%.sql.gz.enc}.sha256"
if [ -f "${CHECKSUM_FILE}" ]; then
  echo "Verificando integridade do backup..." | tee -a "${LOG_FILE}"
  if ! sha256sum -c "${CHECKSUM_FILE}"; then
    echo "ERRO CRÍTICO: Checksum do backup não confere! Abortando restore." | tee -a "${LOG_FILE}"
    exit 1
  fi
  echo "Checksum verificado com sucesso ✓" | tee -a "${LOG_FILE}"
else
  echo "AVISO: Arquivo de checksum não encontrado. Prosseguindo com cautela." | tee -a "${LOG_FILE}"
fi

# Descriptografar
echo "Descriptografando backup..." | tee -a "${LOG_FILE}"
gpg --batch --yes \
  --output "/tmp/pg_restore_${DATE}.dump" \
  --decrypt "${BACKUP_FILE}" \
  2>> "${LOG_FILE}"

# Confirmar operação
echo ""
echo "⚠️  ATENÇÃO: Esta operação irá SUBSTITUIR o banco '${TARGET_DB}'."
echo "Tem certeza que deseja continuar? (digite 'SIM' para confirmar)"
read -r CONFIRMACAO

if [ "${CONFIRMACAO}" != "SIM" ]; then
  echo "Operação cancelada pelo operador." | tee -a "${LOG_FILE}"
  shred -u "/tmp/pg_restore_${DATE}.dump"
  exit 0
fi

# Parar a aplicação para evitar conexões durante o restore
echo "Parando serviços da aplicação..." | tee -a "${LOG_FILE}"
systemctl stop automacao-juridica-api.service || true
systemctl stop automacao-juridica-worker.service || true

# Aguardar desconexão de clientes
sleep 5

# Terminar conexões ativas
PGPASSWORD="${BACKUP_PG_PASSWORD}" psql \
  --host="${BACKUP_PG_HOST}" \
  --port="${BACKUP_PG_PORT}" \
  --username="${BACKUP_PG_USER}" \
  --dbname=postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${TARGET_DB}' AND pid <> pg_backend_pid();" \
  2>> "${LOG_FILE}"

# Dropar e recriar o banco
PGPASSWORD="${BACKUP_PG_PASSWORD}" psql \
  --host="${BACKUP_PG_HOST}" \
  --port="${BACKUP_PG_PORT}" \
  --username="${BACKUP_PG_USER}" \
  --dbname=postgres \
  -c "DROP DATABASE IF EXISTS ${TARGET_DB};" \
  -c "CREATE DATABASE ${TARGET_DB} OWNER ${BACKUP_PG_USER};" \
  2>> "${LOG_FILE}"

# Executar restore
echo "Executando restore..." | tee -a "${LOG_FILE}"
PGPASSWORD="${BACKUP_PG_PASSWORD}" pg_restore \
  --host="${BACKUP_PG_HOST}" \
  --port="${BACKUP_PG_PORT}" \
  --username="${BACKUP_PG_USER}" \
  --dbname="${TARGET_DB}" \
  --verbose \
  --clean \
  --if-exists \
  --no-owner \
  "/tmp/pg_restore_${DATE}.dump" \
  2>> "${LOG_FILE}"

RESTORE_EXIT_CODE=$?

# Limpar arquivo temporário
shred -u "/tmp/pg_restore_${DATE}.dump"

if [ ${RESTORE_EXIT_CODE} -eq 0 ]; then
  echo "[$(date -Iseconds)] Restore concluído com sucesso ✓" | tee -a "${LOG_FILE}"
else
  echo "[$(date -Iseconds)] Restore concluído com avisos (exit code: ${RESTORE_EXIT_CODE})" | tee -a "${LOG_FILE}"
fi

# Verificar integridade pós-restore
echo "Verificando integridade pós-restore..." | tee -a "${LOG_FILE}"
PGPASSWORD="${BACKUP_PG_PASSWORD}" psql \
  --host="${BACKUP_PG_HOST}" \
  --port="${BACKUP_PG_PORT}" \
  --username="${BACKUP_PG_USER}" \
  --dbname="${TARGET_DB}" \
  -c "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;" \
  2>> "${LOG_FILE}" | tee -a "${LOG_FILE}"

# Executar migrações pendentes do Alembic (se houver)
echo "Verificando migrações pendentes do Alembic..." | tee -a "${LOG_FILE}"
cd /opt/automacao-juridica
alembic current 2>> "${LOG_FILE}" | tee -a "${LOG_FILE}"
alembic upgrade head 2>> "${LOG_FILE}" | tee -a "${LOG_FILE}"

# Reiniciar serviços
echo "Reiniciando serviços da aplicação..." | tee -a "${LOG_FILE}"
systemctl start automacao-juridica-api.service
systemctl start automacao-juridica-worker.service

echo "[$(date -Iseconds)] Procedimento de restore finalizado" | tee -a "${LOG_FILE}"
echo "Log completo em: ${LOG_FILE}"
```

#### 6.1.2 Point-in-Time Recovery (PITR)

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/restore_pg_pitr.sh
# Propósito: Restore do PostgreSQL para um ponto específico no tempo
# USO: ./restore_pg_pitr.sh <basebackup.tar.enc> <timestamp_alvo>
# Exemplo: ./restore_pg_pitr.sh base_20240115.tar.enc "2024-01-15 14:30:00 BRT"

set -euo pipefail
source /etc/automacao-juridica/backup.env

BASE_BACKUP="$1"
TARGET_TIME="$2"
DATE=$(date +%Y%m%d_%H%M%S)
PG_DATA_DIR="/var/lib/postgresql/16/main"  # Ajustar conforme versão
WAL_ARCHIVE="${BACKUP_LOCAL_PATH}/postgresql/wal_archive"

if [ -z "${BASE_BACKUP}" ] || [ -z "${TARGET_TIME}" ]; then
  echo "Uso: $0 <basebackup.tar.enc> <timestamp_alvo>"
  echo "Exemplo: $0 /backup/.../base_20240115.tar.enc '2024-01-15 14:30:00 BRT'"
  exit 1
fi

echo "========================================"
echo "POINT-IN-TIME RECOVERY"
echo "Base backup: ${BASE_BACKUP}"
echo "Timestamp alvo: ${TARGET_TIME}"
echo "========================================"

# Parar PostgreSQL
systemctl stop postgresql

# Backup do estado atual (segurança)
mv "${PG_DATA_DIR}" "${PG_DATA_DIR}.pre_pitr_${DATE}"

# Descriptografar e extrair base backup
mkdir -p "${PG_DATA_DIR}"
gpg --batch --yes \
  --output "/tmp/base_restore_${DATE}.tar" \
  --decrypt "${BASE_BACKUP}"

tar -xf "/tmp/base_restore_${DATE}.tar" -C "${PG_DATA_DIR}"
shred -u "/tmp/base_restore_${DATE}.tar"

# Descriptografar WAL files
for wal_enc in ${WAL_ARCHIVE}/*.enc; do
  wal_file="${wal_enc%.enc}"
  if [ ! -f "${wal_file}" ]; then
    gpg --batch --yes \
      --output "${wal_file}" \
      --decrypt "${wal_enc}"
  fi
done

# Configurar recovery
cat > "${PG_DATA_DIR}/postgresql.auto.conf" << EOF
restore_command = 'cp ${WAL_ARCHIVE}/%f %p'
recovery_target_time = '${TARGET_TIME}'
recovery_target_action = 'promote'
EOF

# Criar signal file para recovery
touch "${PG_DATA_DIR}/recovery.signal"

# Ajustar permissões
chown -R postgres:postgres "${PG_DATA_DIR}"
chmod 700 "${PG_DATA_DIR}"

# Iniciar PostgreSQL (entrará em modo recovery)
systemctl start postgresql

echo "PostgreSQL iniciado em modo recovery."
echo "Monitorar progresso com: tail -f /var/log/postgresql/postgresql-16-main.log"
echo "Após recovery, verificar dados e reiniciar serviços da aplicação."
```

### 6.2 Restore de Arquivos

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/restore_files.sh
# Propósito: Restore de documentos jurídicos
# USO: ./restore_files.sh <arquivo_backup.tar.enc>

set -euo pipefail
source /etc/automacao-juridica/backup.env

BACKUP_FILE="$1"
DATE=$(date +%Y%m%d_%H%M%S)

if [ -z "${BACKUP_FILE}" ]; then
  echo "Uso: $0 <arquivo_backup.tar.enc>"
  exit 1
fi

echo "[$(date -Iseconds)] Iniciando restore de documentos jurídicos..."

# Verificar checksum
CHECKSUM_FILE="${BACKUP_FILE%.tar.enc}.sha256"
if [ -f "${CHECKSUM_FILE}" ]; then
  sha256sum -c "${CHECKSUM_FILE}" || { echo "ERRO: Checksum inválido!"; exit 1; }
fi

# Descriptografar
gpg --batch --yes \
  --output "/tmp/files_restore_${DATE}.tar" \
  --decrypt "${BACKUP_FILE}"

# Extrair para diretório temporário
mkdir -p "/tmp/files_restore_${DATE}"
tar -xf "/tmp/files_restore_${DATE}.tar" -C "/tmp/files_restore_${DATE}"

# Sincronizar com MinIO/S3 local
rclone sync \
  "/tmp/files_restore_${DATE}/" \
  minio-local:automacao-juridica-documents \
  --transfers=4 \
  --log-level=INFO

# Limpar
rm -rf "/tmp/files_restore_${DATE}"
shred -u "/tmp/files_restore_${DATE}.tar"

echo "[$(date -Iseconds)] Restore de documentos concluído"
```

### 6.3 Restore do Redis

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/restore_redis.sh
# Propósito: Restore do Redis a partir de snapshot RDB
# USO: ./restore_redis.sh <redis_backup.rdb.enc>

set -euo pipefail
source /etc/automacao-juridica/backup.env

BACKUP_FILE="$1"
REDIS_DATA_DIR="/var/lib/redis"

if [ -z "${BACKUP_FILE}" ]; then
  echo "Uso: $0 <redis_backup.rdb.enc>"
  exit 1
fi

echo "[$(date -Iseconds)] Iniciando restore do Redis..."

# Parar Redis
systemctl stop redis-server

# Descriptografar
gpg --batch --yes \
  --output "${REDIS_DATA_DIR}/dump.rdb" \
  --decrypt "${BACKUP_FILE}"

# Ajustar permissões
chown redis:redis "${REDIS_DATA_DIR}/dump.rdb"
chmod 660 "${REDIS_DATA_DIR}/dump.rdb"

# Iniciar Redis
systemctl start redis-server

# Verificar
redis-cli DBSIZE

echo "[$(date -Iseconds)] Restore do Redis concluído"
```

### 6.4 Restore de Configurações e Secrets

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/restore_configs.sh
# Propósito: Restore de arquivos de configuração
# USO: ./restore_configs.sh <configs_backup.tar.gz.enc>
# NOTA: Secrets devem ser restaurados separadamente via vault

set -euo pipefail
source /etc/automacao-juridica/backup.env

BACKUP_FILE="$1"
DATE=$(date +%Y%m%d_%H%M%S)

if [ -z "${BACKUP_FILE}" ]; then
  echo "Uso: $0 <configs_backup.tar.gz.enc>"
  exit 1
fi

echo "[$(date -Iseconds)] Iniciando restore de configurações..."
echo "⚠️  ATENÇÃO: Este procedimento NÃO restaura secrets. Use o vault para isso."

# Descriptografar
gpg --batch --yes \
  --output "/tmp/configs_restore_${DATE}.tar.gz" \
  --decrypt "${BACKUP_FILE}"

# Extrair para diretório temporário para revisão
mkdir -p "/tmp/configs_restore_${DATE}"
tar -xzf "/tmp/configs_restore_${DATE}.tar.gz" -C "/tmp/configs_restore_${DATE}"

echo "Configurações extraídas em: /tmp/configs_restore_${DATE}"
echo "REVISE os arquivos antes de copiar para os diretórios de destino."
echo "Após revisão, copie manualmente os arquivos necessários."

# Limpar arquivo criptografado temporário
shred -u "/tmp/configs_restore_${DATE}.tar.gz"

echo "[$(date -Iseconds)] Extração de configurações concluída. Revisão manual necessária."
```

### 6.5 Restore do Índice Vetorial

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/restore_vector_index.sh
# Propósito: Restore do índice vetorial
# USO: ./restore_vector_index.sh <vector_index_backup.tar.gz.enc>
# TODO: Ajustar conforme decisão ADR G002 (FAISS vs Milvus)

set -euo pipefail
source /etc/automacao-juridica/backup.env

BACKUP_FILE="$1"
VECTOR_INDEX_PATH="/var/lib/automacao-juridica/vector_index"
DATE=$(date +%Y%m%d_%H%M%S)

if [ -z "${BACKUP_FILE}" ]; then
  echo "Uso: $0 <vector_index_backup.tar.gz.enc>"
  exit 1
fi

echo "[$(date -Iseconds)] Iniciando restore do índice vetorial..."

# Parar serviço da API (para evitar leituras durante restore)
systemctl stop automacao-juridica-api.service || true

# Backup do índice atual
if [ -d "${VECTOR_INDEX_PATH}" ]; then
  mv "${VECTOR_INDEX_PATH}" "${VECTOR_INDEX_PATH}.pre_restore_${DATE}"
fi

# Descriptografar e extrair
gpg --batch --yes \
  --output "/tmp/vector_restore_${DATE}.tar.gz" \
  --decrypt "${BACKUP_FILE}"

mkdir -p "$(dirname ${VECTOR_INDEX_PATH})"
tar -xzf "/tmp/vector_restore_${DATE}.tar.gz" -C "$(dirname ${VECTOR_INDEX_PATH})"

shred -u "/tmp/vector_restore_${DATE}.tar.gz"

# Reiniciar serviço
systemctl start automacao-juridica-api.service

echo "[$(date -Iseconds)] Restore do índice vetorial concluído"
```

---

## Automação com Cron / Celery

### Configuração do Cron

```cron
# /etc/cron.d/automacao-juridica-backup
# Backup automatizado do sistema Automação Jurídica Assistida

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=infra@escritorio.com.br

# Backup full do PostgreSQL — Semanal (domingo 02:00 BRT)
0 2 * * 0 root /opt/automacao-juridica/scripts/backup_pg_full.sh >> /var/log/automacao-juridica/cron_backup.log 2>&1

# Backup base para PITR — Semanal (sábado 03:00 BRT)
0 3 * * 6 root /opt/automacao-juridica/scripts/backup_pg_basebackup.sh >> /var/log/automacao-juridica/cron_backup.log 2>&1

# Backup de documentos jurídicos — Diário (03:00 BRT)
0 3 * * * root /opt/automacao-juridica/scripts/backup_files.sh >> /var/log/automacao-juridica/cron_backup.log 2>&1

# Backup do Redis — Diário (03:30 BRT)
30 3 * * * root /opt/automacao-juridica/scripts/backup_redis.sh >> /var/log/automacao-juridica/cron_backup.log 2>&1

# Backup do índice vetorial — Diário (04:00 BRT)
0 4 * * * root /opt/automacao-juridica/scripts/backup_vector_index.sh >> /var/log/automacao-juridica/cron_backup.log 2>&1

# Backup de configurações — Semanal (domingo 04:00 BRT)
0 4 * * 0 root /opt/automacao-juridica/scripts/backup_configs.sh >> /var/log/automacao-juridica/cron_backup.log 2>&1

# Rotação de backups antigos — Diário (05:00 BRT)
0 5 * * * root /opt/automacao-juridica/scripts/backup_rotate.sh >> /var/log/automacao-juridica/cron_backup.log 2>&1

# Verificação de integridade — Semanal (segunda 06:00 BRT)
0 6 * * 1 root /opt/automacao-juridica/scripts/backup_verify.sh >> /var/log/automacao-juridica/cron_backup.log 2>&1
```

### Tarefa Celery para Notificação de Status

```python
# Exemplo de integração com Celery para monitoramento de backups
# Arquivo: app/tasks/backup_monitor.py
# TODO: Implementar quando o módulo de tarefas Celery estiver configurado

# from celery import shared_task
# from datetime import datetime, timedelta
#
# @shared_task(name="backup.verificar_status")
# def verificar_status_backup():
#     """Verifica se os backups estão sendo executados conforme agendamento."""
#     # Verificar timestamp do último backup
#     # Alertar se backup está atrasado
#     pass
```

---

## Verificação e Testes de Integridade

### Script de Verificação Automática

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/backup_verify.sh
# Propósito: Verificação semanal de integridade dos backups
# Execução: Semanal (segunda 06:00 BRT)

set -euo pipefail
source /etc/automacao-juridica/backup.env

DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/automacao-juridica/backup_verify_${DATE}.log"
ERRORS=0

echo "========================================" | tee -a "${LOG_FILE}"
echo "VERIFICAÇÃO DE INTEGRIDADE DE BACKUPS" | tee -a "${LOG_FILE}"
echo "Data: $(date -Iseconds)" | tee -a "${LOG_FILE}"
echo "========================================" | tee -a "${LOG_FILE}"

# 1. Verificar checksums de todos os backups recentes
echo "" | tee -a "${LOG_FILE}"
echo "[1/5] Verificando checksums..." | tee -a "${LOG_FILE}"

for checksum_file in $(find "${BACKUP_LOCAL_PATH}" -name "*.sha256" -mtime -7); do
  if sha256sum -c "${checksum_file}" >> "${LOG_FILE}" 2>&1; then
    echo "  ✓ $(basename ${checksum_file})" | tee -a "${LOG_FILE}"
  else
    echo "  ✗ FALHA: $(basename ${checksum_file})" | tee -a "${LOG_FILE}"
    ERRORS=$((ERRORS + 1))
  fi
done

# 2. Verificar se backups recentes existem
echo "" | tee -a "${LOG_FILE}"
echo "[2/5] Verificando existência de backups recentes..." | tee -a "${LOG_FILE}"

# Verificar backup PostgreSQL (deve ter menos de 24h)
LATEST_PG=$(find "${BACKUP_LOCAL_PATH}/postgresql" -name "*.enc" -mtime -1 | head -1)
if [ -z "${LATEST_PG}" ]; then
  echo "  ✗ ALERTA: Nenhum backup PostgreSQL nas últimas 24h" | tee -a "${LOG_FILE}"
  ERRORS=$((ERRORS + 1))
else
  echo "  ✓ Backup PostgreSQL recente encontrado" | tee -a "${LOG_FILE}"
fi

# Verificar backup de arquivos (deve ter menos de 24h)
LATEST_FILES=$(find "${BACKUP_LOCAL_PATH}/files" -name "*.enc" -mtime -1 | head -1)
if [ -z "${LATEST_FILES}" ]; then
  echo "  ✗ ALERTA: Nenhum backup de arquivos nas últimas 24h" | tee -a "${LOG_FILE}"
  ERRORS=$((ERRORS + 1))
else
  echo "  ✓ Backup de arquivos recente encontrado" | tee -a "${LOG_FILE}"
fi

# 3. Verificar espaço em disco
echo "" | tee -a "${LOG_FILE}"
echo "[3/5] Verificando espaço em disco..." | tee -a "${LOG_FILE}"

DISK_USAGE=$(df -h "${BACKUP_LOCAL_PATH}" | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "${DISK_USAGE}" -gt 85 ]; then
  echo "  ✗ ALERTA: Disco de backup com ${DISK_USAGE}% de uso" | tee -a "${LOG_FILE}"
  ERRORS=$((ERRORS + 1))
else
  echo "  ✓ Espaço em disco adequado (${DISK_USAGE}% em uso)" | tee -a "${LOG_FILE}"
fi

# 4. Teste de descriptografia (amostra)
echo "" | tee -a "${LOG_FILE}"
echo "[4/5] Testando descriptografia de amostra..." | tee -a "${LOG_FILE}"

SAMPLE_FILE=$(find "${BACKUP_LOCAL_PATH}" -name "*.enc" -mtime -1 | head -1)
if [ -n "${SAMPLE_FILE}" ]; then
  if gpg --batch --yes --output /dev/null --decrypt "${SAMPLE_FILE}" 2>/dev/null; then
    echo "  ✓ Descriptografia de amostra bem-sucedida" | tee -a "${LOG_FILE}"
  else
    echo "  ✗ FALHA na descriptografia de amostra" | tee -a "${LOG_FILE}"
    ERRORS=$((ERRORS + 1))
  fi
else
  echo "  ⚠ Nenhum arquivo recente para teste" | tee -a "${LOG_FILE}"
fi

# 5. Verificar replicação offsite
echo "" | tee -a "${LOG_FILE}"
echo "[5/5] Verificando backups offsite..." | tee -a "${LOG_FILE}"

OFFSITE_COUNT=$(aws s3 ls "s3://${BACKUP_S3_BUCKET}/" \
  --endpoint-url "${BACKUP_S3_ENDPOINT}" \
  --region "${BACKUP_S3_REGION}" \
  --recursive | wc -l)

if [ "${OFFSITE_COUNT}" -gt 0 ]; then
  echo "  ✓ ${OFFSITE_COUNT} arquivos encontrados no storage offsite" | tee -a "${LOG_FILE}"
else
  echo "  ✗ ALERTA: Nenhum arquivo encontrado no storage offsite" | tee -a "${LOG_FILE}"
  ERRORS=$((ERRORS + 1))
fi

# Resultado final
echo "" | tee -a "${LOG_FILE}"
echo "========================================" | tee -a "${LOG_FILE}"
if [ ${ERRORS} -eq 0 ]; then
  echo "RESULTADO: ✅ Todas as verificações passaram" | tee -a "${LOG_FILE}"
  STATUS_EMOJI="✅"
else
  echo "RESULTADO: ❌ ${ERRORS} problema(s) encontrado(s)" | tee -a "${LOG_FILE}"
  STATUS_EMOJI="🔴"
fi
echo "========================================" | tee -a "${LOG_FILE}"

# Notificar
curl -s -X POST "${BACKUP_NOTIFY_SLACK_WEBHOOK}" \
  -H 'Content-type: application/json' \
  -d "{\"text\":\"${STATUS_EMOJI} Verificação de backup: ${ERRORS} problema(s) - Automação Jurídica\"}" || true

exit ${ERRORS}
```

### Teste Mensal de Restore

Procedimento obrigatório a ser executado **mensalmente**:

1. **Provisionar ambiente de teste** isolado (pode ser container Docker)
2. **Selecionar backup mais recente** de cada tipo
3. **Executar restore completo** no ambiente de teste
4. **Validar dados**:
   - Contagem de registros nas tabelas principais
   - Verificar integridade de documentos (abrir amostra de PDFs)
   - Testar login com usuário de teste
   - Verificar logs de auditoria
5. **Documentar resultado** no registro de testes
6. **Destruir ambiente de teste** (shred de dados)

```bash
# Checklist de teste mensal de restore
# Arquivo: /opt/automacao-juridica/scripts/restore_test_checklist.sh

#!/bin/bash
echo "=== CHECKLIST DE TESTE MENSAL DE RESTORE ==="
echo "Data: $(date -Iseconds)"
echo "Responsável: $(whoami)"
echo ""
echo "[ ] 1. Ambiente de teste provisionado e isolado"
echo "[ ] 2. Backup PostgreSQL restaurado com sucesso"
echo "[ ] 3. Contagem de registros confere com produção (±1%)"
echo "[ ] 4. Backup de documentos restaurado com sucesso"
echo "[ ] 5. Amostra de 10 documentos aberta e verificada"
echo "[ ] 6. Backup Redis restaurado com sucesso"
echo "[ ] 7. Índice vetorial restaurado e funcional"
echo "[ ] 8. Login de teste executado com sucesso"
echo "[ ] 9. Logs de auditoria íntegros"
echo "[ ] 10. Tempo total de restore registrado: _____ minutos"
echo "[ ] 11. Ambiente de teste destruído com segurança"
echo "[ ] 12. Relatório enviado ao responsável técnico"
echo ""
echo "Assinatura do responsável: ____________________"
echo "Data de conclusão: ____________________"
```

---

## Retenção e Rotação

### Script de Rotação

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/backup_rotate.sh
# Propósito: Rotação de backups antigos conforme política de retenção
# Execução: Diário (05:00 BRT)

set -euo pipefail
source /etc/automacao-juridica/backup.env

DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/automacao-juridica/backup_rotate_${DATE}.log"

echo "[$(date -Iseconds)] Iniciando rotação de backups..." | tee -a "${LOG_FILE}"

# Rotação de backups full (manter 90 dias)
echo "Rotacionando backups full (>${BACKUP_RETENTION_DAYS_FULL} dias)..." | tee -a "${LOG_FILE}"
find "${BACKUP_LOCAL_PATH}/postgresql/full" \
  -name "*.enc" \
  -mtime +${BACKUP_RETENTION_DAYS_FULL} \
  -exec shred -u {} \; \
  -print >> "${LOG_FILE}" 2>&1

# Rotação de checksums correspondentes
find "${BACKUP_LOCAL_PATH}/postgresql/full" \
  -name "*.sha256" \
  -mtime +${BACKUP_RETENTION_DAYS_FULL} \
  -delete \
  -print >> "${LOG_FILE}" 2>&1

# Rotação de WAL archives (manter 7 dias)
echo "Rotacionando WAL archives (>${BACKUP_RETENTION_DAYS_WAL} dias)..." | tee -a "${LOG_FILE}"
find "${BACKUP_LOCAL_PATH}/postgresql/wal_archive" \
  -name "*.enc" \
  -mtime +${BACKUP_RETENTION_DAYS_WAL} \
  -exec shred -u {} \; \
  -print >> "${LOG_FILE}" 2>&1

# Rotação de backups de arquivos (manter 30 dias localmente)
echo "Rotacionando backups de arquivos (>${BACKUP_RETENTION_DAYS_INCREMENTAL} dias)..." | tee -a "${LOG_FILE}"
find "${BACKUP_LOCAL_PATH}/files" \
  -name "*.enc" \
  -mtime +${BACKUP_RETENTION_DAYS_INCREMENTAL} \
  -exec shred -u {} \; \
  -print >> "${LOG_FILE}" 2>&1

# Rotação de backups Redis (manter 30 dias)
echo "Rotacionando backups Redis (>${BACKUP_RETENTION_DAYS_INCREMENTAL} dias)..." | tee -a "${LOG_FILE}"
find "${BACKUP_LOCAL_PATH}/redis" \
  -name "*.enc" \
  -mtime +${BACKUP_RETENTION_DAYS_INCREMENTAL} \
  -exec shred -u {} \; \
  -print >> "${LOG_FILE}" 2>&1

# Rotação de backups do índice vetorial (manter 30 dias)
echo "Rotacionando backups do índice vetorial..." | tee -a "${LOG_FILE}"
find "${BACKUP_LOCAL_PATH}/vector_index" \
  -name "*.enc" \
  -mtime +${BACKUP_RETENTION_DAYS_INCREMENTAL} \
  -exec shred -u {} \; \
  -print >> "${LOG_FILE}" 2>&1

# Rotação de logs antigos (manter 90 dias)
echo "Rotacionando logs de backup antigos..." | tee -a "${LOG_FILE}"
find /var/log/automacao-juridica \
  -name "backup_*.log" \
  -mtime +90 \
  -delete \
  -print >> "${LOG_FILE}" 2>&1

# Rotação no storage offsite (via lifecycle policy do S3)
# Configurado diretamente no bucket S3:
# - Transição para Glacier após 30 dias
# - Expiração após 5 anos (1825 dias) — conforme legislação

echo "[$(date -Iseconds)] Rotação de backups concluída" | tee -a "${LOG_FILE}"
```

### Política de Retenção por Tipo

| Tipo de Backup | Local | Offsite (S3) | Glacier/Archive | Total |
|---------------|-------|-------------|-----------------|-------|
| Full PostgreSQL | 90 dias | 365 dias | 5 anos | 5 anos |
| Incremental/WAL | 7 dias | 30 dias | — | 30 dias |
| Documentos jurídicos | 30 dias | 365 dias | 5 anos | 5 anos |
| Redis | 30 dias | — | — | 30 dias |
| Índice vetorial | 30 dias | 90 dias | — | 90 dias |
| Configurações | 90 dias | 365 dias | 5 anos | 5 anos |
| Logs de auditoria | 90 dias | 365 dias | 5 anos | 5 anos |

> **Nota legal**: A retenção de 5 anos atende ao prazo prescricional geral do Código Civil (Art. 206, §5°) e requisitos da LGPD para dados necessários ao exercício regular de direitos em processo judicial.

---

## Segurança e Criptografia

### Criptografia em Repouso

- **Algoritmo**: GPG com chave RSA-4096 (assimétrica) para backups
- **Chave privada**: Armazenada em HSM ou vault dedicado, **nunca** no servidor de backup
- **Rotação de chaves**: Anual, com re-criptografia dos backups ativos

### Criptografia em Trânsito

- **Transferência local → offsite**: TLS 1.3 via HTTPS (S3 endpoint)
- **Transferência entre servidores**: SSH/SCP com chaves Ed25519

### Gestão de Chaves GPG

```bash
# Gerar par de chaves GPG para backup (executar uma vez)
gpg --full-generate-key
# Selecionar: RSA and RSA, 4096 bits, sem expiração
# Nome: "Automação Jurídica - Backup"
# Email: backup@automacao-juridica.local

# Exportar chave pública (para servidor de backup)
gpg --export --armor "backup@automacao-juridica.local" > backup_public.key

# Exportar chave privada (armazenar em vault seguro)
gpg --export-secret-keys --armor "backup@automacao-juridica.local" > backup_private.key
# IMPORTANTE: Armazenar backup_private.key em vault/HSM e remover do servidor

# Importar chave pública no servidor de backup
gpg --import backup_public.key
gpg --edit-key "backup@automacao-juridica.local" trust
# Selecionar nível 5 (ultimate trust)
```

### Controle de Acesso

| Recurso | Permissão | Quem |
|---------|-----------|------|
| Scripts de backup | `750 root:backup` | root e grupo backup |
| Diretório de backup local | `700 root:root` | Apenas root |
| Chave GPG privada | Vault/HSM | Apenas DBA sênior + CTO |
| Credenciais S3 offsite | Vault | Apenas scripts automatizados |
| Scripts de restore | `750 root:backup` | root e grupo backup |
| Logs de backup | `640 root:adm` | root e grupo adm |

### Auditoria de Acesso a Backups

Todo acesso a backups deve ser registrado:

```bash
# Configurar auditd para monitorar acesso ao diretório de backup
# /etc/audit/rules.d/automacao-juridica-backup.rules

-w /backup/automacao-juridica/ -p rwxa -k backup_access
-w /opt/automacao-juridica/scripts/ -p x -k backup_script_exec
-w /etc/automacao-juridica/backup.env -p rwa -k backup_config_access
```

---

## Disaster Recovery (DR)

### Cenários de Desastre e Procedimentos

#### Cenário 1: Corrupção de Banco de Dados

| Etapa | Ação | Tempo Estimado |
|-------|------|---------------|
| 1 | Identificar extensão da corrupção | 15 min |
| 2 | Parar aplicação | 5 min |
| 3 | Tentar PITR para momento anterior à corrupção | 30 min |
| 4 | Se PITR falhar, restore full + WAL replay | 1-2h |
| 5 | Validar dados restaurados | 30 min |
| 6 | Reiniciar aplicação | 10 min |
| **Total** | | **~2-3h** |

#### Cenário 2: Perda Total do Servidor

| Etapa | Ação | Tempo Estimado |
|-------|------|---------------|
| 1 | Provisionar novo servidor | 30 min |
| 2 | Instalar dependências (Ansible/Docker) | 30 min |
| 3 | Baixar backups do storage offsite | 30-60 min |
| 4 | Restore PostgreSQL | 30-60 min |
| 5 | Restore documentos | 30-60 min |
| 6 | Restore Redis e índice vetorial | 15 min |
| 7 | Restore configurações | 15 min |
| 8 | Configurar secrets via vault | 15 min |
| 9 | Validação completa | 30 min |
| 10 | Atualizar DNS/proxy | 10 min |
| **Total** | | **~3-5h** |

#### Cenário 3: Ataque Ransomware

| Etapa | Ação | Tempo Estimado |
|-------|------|---------------|
| 1 | **Isolar** servidor comprometido da rede | Imediato |
| 2 | Notificar equipe de segurança e DPO | 15 min |
| 3 | Avaliar extensão do comprometimento | 1h |
| 4 | Provisionar ambiente limpo | 30 min |
| 5 | Verificar integridade dos backups offsite | 30 min |
| 6 | Restore completo em ambiente limpo | 2-3h |
| 7 | Análise forense do servidor comprometido | Paralelo |
| 8 | Rotação de TODAS as credenciais | 1h |
| 9 | Notificação ANPD (se dados pessoais afetados) | 72h |
| **Total (restore)** | | **~4-5h** |

### Procedimento de DR Completo

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/disaster_recovery.sh
# Propósito: Procedimento guiado de Disaster Recovery completo
# USO: ./disaster_recovery.sh
# NOTA: Este script é um guia interativo, NÃO executar automaticamente

set -euo pipefail

echo "╔══════════════════════════════════════════════════╗"
echo "║   DISASTER RECOVERY — AUTOMAÇÃO JURÍDICA        ║"
echo "║   Procedimento Guiado de Recuperação Completa    ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "Data/Hora: $(date -Iseconds)"
echo "Operador: $(whoami)"
echo ""
echo "⚠️  ATENÇÃO: Este procedimento deve ser executado"
echo "   apenas com autorização do responsável técnico."
echo ""
read -p "Motivo da recuperação: " DR_MOTIVO
read -p "Autorizado por: " DR_AUTORIZADO
echo ""

# Registrar início do DR
echo "[DR] Início: $(date -Iseconds) | Motivo: ${DR_MOTIVO} | Autorizado: ${DR_AUTORIZADO}" >> /var/log/automacao-juridica/disaster_recovery.log

echo "=== ETAPA 1: Verificar disponibilidade dos backups ==="
echo "Verificando storage offsite..."
# TODO: Implementar verificação automatizada do storage offsite

echo ""
echo "=== ETAPA 2: Restore do PostgreSQL ==="
echo "Selecione o backup a restaurar:"
ls -la /backup/automacao-juridica/postgresql/full/*.enc 2>/dev/null || echo "(backups locais não disponíveis)"
echo ""
read -p "Caminho do backup PostgreSQL: " PG_BACKUP
read -p "Confirma restore do PostgreSQL? (SIM/NÃO): " CONFIRM_PG
if [ "${CONFIRM_PG}" == "SIM" ]; then
  echo "Executando restore do PostgreSQL..."
  # /opt/automacao-juridica/scripts/restore_pg_full.sh "${PG_BACKUP}"
  echo "TODO: Descomentar linha acima após validação"
fi

echo ""
echo "=== ETAPA 3: Restore de Documentos ==="
read -p "Caminho do backup de documentos: " FILES_BACKUP
read -p "Confirma restore de documentos? (SIM/NÃO): " CONFIRM_FILES
if [ "${CONFIRM_FILES}" == "SIM" ]; then
  echo "Executando restore de documentos..."
  # /opt/automacao-juridica/scripts/restore_files.sh "${FILES_BACKUP}"
  echo "TODO: Descomentar linha acima após validação"
fi

echo ""
echo "=== ETAPA 4: Restore do Redis ==="
read -p "Restaurar Redis? (SIM/NÃO): " CONFIRM_REDIS
if [ "${CONFIRM_REDIS}" == "SIM" ]; then
  echo "Executando restore do Redis..."
  # /opt/automacao-juridica/scripts/restore_redis.sh <backup>
  echo "TODO: Descomentar linha acima após validação"
fi

echo ""
echo "=== ETAPA 5: Restore do Índice Vetorial ==="
read -p "Restaurar índice vetorial? (SIM/NÃO): " CONFIRM_VECTOR
if [ "${CONFIRM_VECTOR}" == "SIM" ]; then
  echo "Executando restore do índice vetorial..."
  # /opt/automacao-juridica/scripts/restore_vector_index.sh <backup>
  echo "TODO: Descomentar linha acima após validação"
fi

echo ""
echo "=== ETAPA 6: Validação ==="
echo "Executar checklist de validação:"
echo "[ ] PostgreSQL acessível e com dados"
echo "[ ] Documentos acessíveis no storage"
echo "[ ] Redis operacional"
echo "[ ] Índice vetorial funcional"
echo "[ ] API respondendo em /health"
echo "[ ] Login de teste bem-sucedido"
echo "[ ] Logs de auditoria íntegros"
echo ""

read -p "Validação concluída com sucesso? (SIM/NÃO): " CONFIRM_VALID

if [ "${CONFIRM_VALID}" == "SIM" ]; then
  echo "[DR] Conclusão com sucesso: $(date -Iseconds)" >> /var/log/automacao-juridica/disaster_recovery.log
  echo ""
  echo "✅ Disaster Recovery concluído com sucesso!"
else
  echo "[DR] Conclusão com problemas: $(date -Iseconds)" >> /var/log/automacao-juridica/disaster_recovery.log
  echo ""
  echo "⚠️  Disaster Recovery concluído com problemas. Verificar logs."
fi

echo ""
echo "Lembre-se de:"
echo "1. Notificar stakeholders sobre o incidente"
echo "2. Documentar o incidente no registro de ocorrências"
echo "3. Agendar post-mortem em até 48h"
echo "4. Se dados pessoais foram afetados, notificar ANPD em até 72h"
```

---

## Conformidade LGPD

### Requisitos de Backup sob a LGPD

1. **Minimização de dados**: Backups contêm apenas dados necessários para operação do sistema.

2. **Criptografia obrigatória**: Todos os backups contendo dados pessoais são criptografados com AES-256/RSA-4096.

3. **Controle de acesso**: Acesso a backups restrito ao mínimo necessário (princípio do menor privilégio).

4. **Registro de operações**: Toda operação de backup e restore é registrada com:
   - Data/hora
   - Responsável
   - Tipo de operação
   - Escopo dos dados
   - Resultado

5. **Direito ao esquecimento**: Quando um titular solicitar exclusão de dados:
   - Dados são removidos do banco de produção
   - Backups existentes são mantidos (exceção legal — Art. 16, LGPD)
   - Registro da solicitação é mantido para garantir que dados não sejam restaurados
   - Em caso de restore, script de "sanitização pós-restore" deve ser executado

6. **Retenção justificada**: Período de retenção de 5 anos justificado por:
   - Prazo prescricional geral (Art. 206, §5°, CC)
   - Exercício regular de direitos em processo judicial (Art. 7°, VI, LGPD)
   - Cumprimento de obrigação legal (Art. 7°, II, LGPD)

### Script de Sanitização Pós-Restore

```bash
#!/bin/bash
# Script: /opt/automacao-juridica/scripts/post_restore_sanitize.sh
# Propósito: Aplicar exclusões pendentes (LGPD) após restore de backup
# Deve ser executado SEMPRE após qualquer operação de restore

set -euo pipefail
source /etc/automacao-juridica/backup.env

echo "[$(date -Iseconds)] Executando sanitização pós-restore (LGPD)..."

# Verificar tabela de exclusões pendentes
# TODO: Implementar quando o módulo de LGPD estiver disponível
# A tabela 'lgpd_deletion_requests' deve conter registros de
# solicitações de exclusão que precisam ser reaplicadas após restore

PGPASSWORD="${BACKUP_PG_PASSWORD}" psql \
  --host="${BACKUP_PG_HOST}" \
  --port="${BACKUP_PG_PORT}" \
  --username="${BACKUP_PG_USER}" \
  --dbname="${BACKUP_PG_DATABASE}" \
  -c "
    -- Verificar se existem exclusões pendentes
    SELECT COUNT(*) as pendentes
    FROM lgpd_deletion_requests
    WHERE status = 'completed'
    AND completed_at IS NOT NULL;
  " 2>/dev/null || echo "Tabela lgpd_deletion_requests não encontrada (módulo LGPD pendente)"

# TODO: Para cada exclusão completada, reaplicar a exclusão dos dados
# Isso garante que dados excluídos por solicitação LGPD não sejam
# restaurados inadvertidamente a partir de backups antigos

echo "[$(date -Iseconds)] Sanitização pós-restore concluída"
```

---

## Runbook de Emergência

### Referência Rápida

```
╔══════════════════════════════════════════════════════════════╗
║              RUNBOOK DE EMERGÊNCIA — BACKUP/RESTORE          ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  📍 Localização dos backups:                                 ║
║     Local:   /backup/automacao-juridica/                     ║
║     Offsite: s3://automacao-juridica-backup-offsite/         ║
║                                                              ║
║  📍 Scripts:                                                 ║
║     /opt/automacao-juridica/scripts/                         ║
║                                                              ║
║  📍 Logs:                                                    ║
║     /var/log/automacao-juridica/                             ║
║                                                              ║
║  📍 Configuração:                                            ║
║     /etc/automacao-juridica/backup.env                       ║
║                                                              ║
║  🔑 Chave GPG:                                               ║
║     Vault corporativo — solicitar ao DBA sênior ou CTO       ║
║                                                              ║
║  ⚡ Comandos rápidos:                                        ║
║                                                              ║
║  # Listar backups disponíveis                                ║
║  ls -lhtr /backup/automacao-juridica/postgresql/full/        ║
║                                                              ║
║  # Verificar último backup                                   ║
║  find /backup/automacao-juridica -name '*.enc' -mtime -1     ║
║                                                              ║
║  # Restore rápido do PostgreSQL                              ║
║  /opt/automacao-juridica/scripts/restore_pg_full.sh \        ║
║    /backup/.../pg_full_YYYYMMDD.sql.gz.enc                   ║
║                                                              ║
║  # DR completo (guiado)                                      ║
║  /opt/automacao-juridica/scripts/disaster_recovery.sh        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Contatos e Escalação

| Nível | Responsável | Contato | Quando Acionar |
|-------|-------------|---------|----------------|
| L1 | Engenheiro de plantão | infra@escritorio.com.br | Falha em backup automatizado |
| L2 | DBA Sênior | dba@escritorio.com.br | Necessidade de restore |
| L3 | CTO / Arquiteto | cto@escritorio.com.br | Disaster Recovery |
| DPO | Encarregado de Dados | dpo@escritorio.com.br | Incidente com dados pessoais |
| Jurídico | Departamento Jurídico | juridico@escritorio.com.br | Notificação ANPD necessária |

> **Tempo de resposta esperado**:
> - L1: 30 minutos (horário comercial) / 1 hora (fora do horário)
> - L2: 1 hora
> - L3: 2 horas
> - DPO: 4 horas (obrigatório em até 72h para ANPD)

---

## Histórico de Revisões

| Versão | Data | Autor | Descrição |
|--------|------|-------|-----------|
| 1.0 | 2024-01-15 | Equipe de Infraestrutura | Versão inicial do documento |

<!-- TODO: Atualizar conforme decisão do ADR G002 (FAISS vs Milvus) para ajustar procedimentos do índice vetorial -->
<!-- TODO: Integrar com módulo de auditoria do backend para registro automático de operações de backup/restore -->
<!-- TODO: Adicionar procedimentos específicos para ambiente Docker/container quando deploy containerizado for definido -->
<!-- TODO: Definir design tokens de alerta para dashboard de monitoramento de backups (G005 ADR) -->