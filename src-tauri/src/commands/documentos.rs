//! Tauri IPC commands for document management.
//!
//! Provides commands for uploading documents, generating legal pieces
//! (peças jurídicas) via the Python sidecar, and listing/retrieving documents
//! associated with legal processes.

use serde::{Deserialize, Serialize};
use tauri::State;
use std::path::PathBuf;

use crate::domain::entities::{Documento, NivelSigilo};
use crate::domain::errors::AppError;
use crate::infra::database::DbPool;
use crate::infra::crypto;
use crate::infra::sidecar::PythonSidecar;

// ---------------------------------------------------------------------------
// DTOs (Data Transfer Objects)
// ---------------------------------------------------------------------------

/// Payload received from the frontend when uploading a document.
#[derive(Debug, Deserialize)]
pub struct UploadDocumentoPayload {
    /// ID of the parent legal process.
    pub processo_id: String,
    /// Original file name (e.g. "peticao_inicial.pdf").
    pub nome_arquivo: String,
    /// MIME type reported by the browser (e.g. "application/pdf").
    pub mime_type: String,
    /// Raw file bytes encoded as base64 by the frontend.
    pub conteudo_base64: String,
    /// Confidentiality level inherited from the process or overridden.
    pub nivel_sigilo: Option<NivelSigilo>,
    /// Optional human-readable description.
    pub descricao: Option<String>,
}

/// Payload for requesting the generation of a legal piece via AI/templates.
#[derive(Debug, Deserialize)]
pub struct GerarPecaPayload {
    /// ID of the parent legal process.
    pub processo_id: String,
    /// Template identifier (e.g. "peticao_inicial", "contestacao").
    pub template_id: String,
    /// Key-value pairs that feed the Jinja2 template / LLM prompt.
    pub parametros: std::collections::HashMap<String, serde_json::Value>,
    /// Confidentiality level for the generated document.
    pub nivel_sigilo: Option<NivelSigilo>,
}

/// Filters accepted by the list command.
#[derive(Debug, Deserialize)]
pub struct ListDocumentosPayload {
    pub processo_id: Option<String>,
    pub tipo: Option<String>,
    /// Simple text search (delegates to FTS5 when available).
    pub busca: Option<String>,
    pub page: Option<u32>,
    pub page_size: Option<u32>,
}

/// Lightweight projection returned when listing documents.
#[derive(Debug, Serialize)]
pub struct DocumentoResumo {
    pub id: String,
    pub processo_id: String,
    pub nome_arquivo: String,
    pub mime_type: String,
    pub tamanho_bytes: u64,
    pub descricao: Option<String>,
    pub nivel_sigilo: String,
    pub criado_em: String,
    pub atualizado_em: String,
}

/// Paginated response wrapper.
#[derive(Debug, Serialize)]
pub struct PaginatedDocumentos {
    pub items: Vec<DocumentoResumo>,
    pub total: u64,
    pub page: u32,
    pub page_size: u32,
}

/// Result of a piece generation request.
#[derive(Debug, Serialize)]
pub struct GerarPecaResult {
    pub documento_id: String,
    pub nome_arquivo: String,
    pub conteudo_preview: String,
}

// ---------------------------------------------------------------------------
// Helper utilities
// ---------------------------------------------------------------------------

fn generate_id() -> String {
    uuid::Uuid::new_v4().to_string()
}

/// Resolve the encrypted storage directory for documents.
fn docs_storage_dir(app_handle: &tauri::AppHandle) -> Result<PathBuf, AppError> {
    let base = app_handle
        .path_resolver()
        .app_data_dir()
        .ok_or_else(|| AppError::Internal("Cannot resolve app data dir".into()))?;
    let dir = base.join("documentos");
    if !dir.exists() {
        std::fs::create_dir_all(&dir)
            .map_err(|e| AppError::Internal(format!("Failed to create docs dir: {e}")))?;
    }
    Ok(dir)
}

// ---------------------------------------------------------------------------
// Tauri Commands
// ---------------------------------------------------------------------------

/// Upload a document, encrypt it at rest, and persist metadata in SQLCipher.
///
/// The raw bytes (received as base64) are decrypted into memory, encrypted
/// with the per-file key via `infra::crypto`, and written to the local
/// encrypted store. Metadata is inserted into the `documentos` table.
#[tauri::command]
pub async fn upload_documento(
    app_handle: tauri::AppHandle,
    db: State<'_, DbPool>,
    payload: UploadDocumentoPayload,
) -> Result<DocumentoResumo, AppError> {
    use base64::Engine;

    // 1. Decode base64 content
    let raw_bytes = base64::engine::general_purpose::STANDARD
        .decode(&payload.conteudo_base64)
        .map_err(|e| AppError::Validation(format!("Invalid base64 content: {e}")))?;

    let tamanho_bytes = raw_bytes.len() as u64;
    let doc_id = generate_id();
    let now = chrono::Utc::now().to_rfc3339();
    let nivel = payload.nivel_sigilo.unwrap_or(NivelSigilo::Nivel1);

    // 2. Encrypt file bytes and persist to disk
    let storage_dir = docs_storage_dir(&app_handle)?;
    let file_path = storage_dir.join(format!("{doc_id}.enc"));

    let encrypted = crypto::encrypt_bytes(&raw_bytes)
        .map_err(|e| AppError::Internal(format!("Encryption failed: {e}")))?;

    tokio::fs::write(&file_path, &encrypted)
        .await
        .map_err(|e| AppError::Internal(format!("Failed to write document file: {e}")))?;

    // 3. Insert metadata into SQLCipher
    let conn = db.get()?;
    let nivel_str = serde_json::to_string(&nivel)
        .unwrap_or_else(|_| "\"nivel1\"".to_string())
        .trim_matches('"')
        .to_string();

    conn.execute(
        "INSERT INTO documentos (id, processo_id, nome_arquivo, mime_type, tamanho_bytes, \
         caminho_arquivo, descricao, nivel_sigilo, criado_em, atualizado_em) \
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
        rusqlite::params![
            doc_id,
            payload.processo_id,
            payload.nome_arquivo,
            payload.mime_type,
            tamanho_bytes,
            file_path.to_string_lossy().to_string(),
            payload.descricao,
            nivel_str,
            now,
            now,
        ],
    )
    .map_err(|e| AppError::Database(format!("Insert documento failed: {e}")))?;

    // 4. Audit log
    let audit_id = generate_id();
    conn.execute(
        "INSERT INTO audit_log (id, acao, entidade, entidade_id, details_json, criado_em) \
         VALUES (?1, 'documento_upload', 'documento', ?2, ?3, ?4)",
        rusqlite::params![
            audit_id,
            doc_id,
            serde_json::json!({
                "nome_arquivo": payload.nome_arquivo,
                "tamanho_bytes": tamanho_bytes,
                "processo_id": payload.processo_id,
            })
            .to_string(),
            now,
        ],
    )
    .map_err(|e| AppError::Database(format!("Audit log insert failed: {e}")))?;

    Ok(DocumentoResumo {
        id: doc_id,
        processo_id: payload.processo_id,
        nome_arquivo: payload.nome_arquivo,
        mime_type: payload.mime_type,
        tamanho_bytes,
        descricao: payload.descricao,
        nivel_sigilo: nivel_str,
        criado_em: now.clone(),
        atualizado_em: now,
    })
}

/// List documents with optional filters and pagination.
///
/// Supports filtering by `processo_id`, document `tipo`, and full-text search
/// via SQLite FTS5. Results are paginated.
#[tauri::command]
pub async fn listar_documentos(
    db: State<'_, DbPool>,
    payload: ListDocumentosPayload,
) -> Result<PaginatedDocumentos, AppError> {
    let conn = db.get()?;

    let page = payload.page.unwrap_or(1).max(1);
    let page_size = payload.page_size.unwrap_or(20).min(100);
    let offset = (page - 1) * page_size;

    // Build dynamic WHERE clause
    let mut conditions: Vec<String> = Vec::new();
    let mut params: Vec<Box<dyn rusqlite::types::ToSql>> = Vec::new();

    if let Some(ref pid) = payload.processo_id {
        conditions.push(format!("d.processo_id = ?{}", params.len() + 1));
        params.push(Box::new(pid.clone()));
    }

    if let Some(ref tipo) = payload.tipo {
        conditions.push(format!("d.mime_type = ?{}", params.len() + 1));
        params.push(Box::new(tipo.clone()));
    }

    if let Some(ref busca) = payload.busca {
        // Use LIKE as a fallback; FTS5 integration would use a JOIN on the
        // fts table when available.
        conditions.push(format!("d.nome_arquivo LIKE ?{}", params.len() + 1));
        params.push(Box::new(format!("%{busca}%")));
    }

    let where_clause = if conditions.is_empty() {
        String::new()
    } else {
        format!("WHERE {}", conditions.join(" AND "))
    };

    // Count total
    let count_sql = format!("SELECT COUNT(*) FROM documentos d {where_clause}");
    let param_refs: Vec<&dyn rusqlite::types::ToSql> = params.iter().map(|p| p.as_ref()).collect();
    let total: u64 = conn
        .query_row(&count_sql, param_refs.as_slice(), |row| row.get(0))
        .map_err(|e| AppError::Database(format!("Count query failed: {e}")))?;

    // Fetch page
    let select_sql = format!(
        "SELECT d.id, d.processo_id, d.nome_arquivo, d.mime_type, d.tamanho_bytes, \
         d.descricao, d.nivel_sigilo, d.criado_em, d.atualizado_em \
         FROM documentos d {where_clause} \
         ORDER BY d.criado_em DESC \
         LIMIT {page_size} OFFSET {offset}"
    );

    let mut stmt = conn
        .prepare(&select_sql)
        .map_err(|e| AppError::Database(format!("Prepare failed: {e}")))?;

    let rows = stmt
        .query_map(param_refs.as_slice(), |row| {
            Ok(DocumentoResumo {
                id: row.get(0)?,
                processo_id: row.get(1)?,
                nome_arquivo: row.get(2)?,
                mime_type: row.get(3)?,
                tamanho_bytes: row.get(4)?,
                descricao: row.get(5)?,
                nivel_sigilo: row.get(6)?,
                criado_em: row.get(7)?,
                atualizado_em: row.get(8)?,
            })
        })
        .map_err(|e| AppError::Database(format!("Query failed: {e}")))?;

    let mut items = Vec::new();
    for row in rows {
        items.push(row.map_err(|e| AppError::Database(format!("Row parse error: {e}")))?);
    }

    Ok(PaginatedDocumentos {
        items,
        total,
        page,
        page_size,
    })
}

/// Retrieve a single document's metadata by ID.
#[tauri::command]
pub async fn obter_documento(
    db: State<'_, DbPool>,
    documento_id: String,
) -> Result<DocumentoResumo, AppError> {
    let conn = db.get()?;

    conn.query_row(
        "SELECT id, processo_id, nome_arquivo, mime_type, tamanho_bytes, \
         descricao, nivel_sigilo, criado_em, atualizado_em \
         FROM documentos WHERE id = ?1",
        rusqlite::params![documento_id],
        |row| {
            Ok(DocumentoResumo {
                id: row.get(0)?,
                processo_id: row.get(1)?,
                nome_arquivo: row.get(2)?,
                mime_type: row.get(3)?,
                tamanho_bytes: row.get(4)?,
                descricao: row.get(5)?,
                nivel_sigilo: row.get(6)?,
                criado_em: row.get(7)?,
                atualizado_em: row.get(8)?,
            })
        },
    )
    .map_err(|e| match e {
        rusqlite::Error::QueryReturnedNoRows => {
            AppError::NotFound(format!("Documento {documento_id} não encontrado"))
        }
        other => AppError::Database(format!("Query failed: {other}")),
    })
}

/// Download a document: decrypt from disk and return base64-encoded content.
#[tauri::command]
pub async fn download_documento(
    app_handle: tauri::AppHandle,
    db: State<'_, DbPool>,
    documento_id: String,
) -> Result<String, AppError> {
    use base64::Engine;

    let conn = db.get()?;

    let caminho: String = conn
        .query_row(
            "SELECT caminho_arquivo FROM documentos WHERE id = ?1",
            rusqlite::params![documento_id],
            |row| row.get(0),
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => {
                AppError::NotFound(format!("Documento {documento_id} não encontrado"))
            }
            other => AppError::Database(format!("Query failed: {other}")),
        })?;

    let encrypted = tokio::fs::read(&caminho)
        .await
        .map_err(|e| AppError::Internal(format!("Failed to read document file: {e}")))?;

    let decrypted = crypto::decrypt_bytes(&encrypted)
        .map_err(|e| AppError::Internal(format!("Decryption failed: {e}")))?;

    let b64 = base64::engine::general_purpose::STANDARD.encode(&decrypted);
    Ok(b64)
}

/// Delete a document (metadata + encrypted file on disk).
#[tauri::command]
pub async fn excluir_documento(
    app_handle: tauri::AppHandle,
    db: State<'_, DbPool>,
    documento_id: String,
) -> Result<(), AppError> {
    let conn = db.get()?;

    // Fetch file path before deleting metadata
    let caminho: String = conn
        .query_row(
            "SELECT caminho_arquivo FROM documentos WHERE id = ?1",
            rusqlite::params![documento_id],
            |row| row.get(0),
        )
        .map_err(|e| match e {
            rusqlite::Error::QueryReturnedNoRows => {
                AppError::NotFound(format!("Documento {documento_id} não encontrado"))
            }
            other => AppError::Database(format!("Query failed: {other}")),
        })?;

    // Delete metadata
    conn.execute(
        "DELETE FROM documentos WHERE id = ?1",
        rusqlite::params![documento_id],
    )
    .map_err(|e| AppError::Database(format!("Delete failed: {e}")))?;

    // Delete encrypted file from disk (best-effort)
    let _ = tokio::fs::remove_file(&caminho).await;

    // Audit log
    let now = chrono::Utc::now().to_rfc3339();
    let audit_id = generate_id();
    conn.execute(
        "INSERT INTO audit_log (id, acao, entidade, entidade_id, details_json, criado_em) \
         VALUES (?1, 'documento_excluido', 'documento', ?2, '{}', ?3)",
        rusqlite::params![audit_id, documento_id, now],
    )
    .map_err(|e| AppError::Database(format!("Audit log insert failed: {e}")))?;

    Ok(())
}

/// Generate a legal piece (peça jurídica) using the Python sidecar.
///
/// The sidecar is invoked with the template ID and parameters. It uses
/// Jinja2 templates and optionally the local LLM to produce the document
/// content. The result is encrypted and stored like any other document.
#[tauri::command]
pub async fn gerar_peca(
    app_handle: tauri::AppHandle,
    db: State<'_, DbPool>,
    sidecar: State<'_, PythonSidecar>,
    payload: GerarPecaPayload,
) -> Result<GerarPecaResult, AppError> {
    use base64::Engine;

    // 1. Build the sidecar request
    let sidecar_request = serde_json::json!({
        "action": "gerar_peca",
        "template_id": payload.template_id,
        "processo_id": payload.processo_id,
        "parametros": payload.parametros,
    });

    // 2. Call the Python sidecar
    let sidecar_response = sidecar
        .invoke(sidecar_request)
        .await
        .map_err(|e| AppError::Internal(format!("Sidecar invocation failed: {e}")))?;

    // 3. Parse sidecar response
    let conteudo_base64 = sidecar_response
        .get("conteudo_base64")
        .and_then(|v| v.as_str())
        .ok_or_else(|| AppError::Internal("Sidecar response missing conteudo_base64".into()))?
        .to_string();

    let nome_arquivo = sidecar_response
        .get("nome_arquivo")
        .and_then(|v| v.as_str())
        .unwrap_or("peca_gerada.docx")
        .to_string();

    let preview = sidecar_response
        .get("preview")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    // 4. Decode, encrypt, and store
    let raw_bytes = base64::engine::general_purpose::STANDARD
        .decode(&conteudo_base64)
        .map_err(|e| AppError::Internal(format!("Invalid base64 from sidecar: {e}")))?;

    let tamanho_bytes = raw_bytes.len() as u64;
    let doc_id = generate_id();
    let now = chrono::Utc::now().to_rfc3339();
    let nivel = payload.nivel_sigilo.unwrap_or(NivelSigilo::Nivel1);
    let nivel_str = serde_json::to_string(&nivel)
        .unwrap_or_else(|_| "\"nivel1\"".to_string())
        .trim_matches('"')
        .to_string();

    let storage_dir = docs_storage_dir(&app_handle)?;
    let file_path = storage_dir.join(format!("{doc_id}.enc"));

    let encrypted = crypto::encrypt_bytes(&raw_bytes)
        .map_err(|e| AppError::Internal(format!("Encryption failed: {e}")))?;

    tokio::fs::write(&file_path, &encrypted)
        .await
        .map_err(|e| AppError::Internal(format!("Failed to write generated document: {e}")))?;

    // 5. Persist metadata
    let conn = db.get()?;
    let mime_type = if nome_arquivo.ends_with(".docx") {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    } else if nome_arquivo.ends_with(".pdf") {
        "application/pdf"
    } else {
        "application/octet-stream"
    };

    conn.execute(
        "INSERT INTO documentos (id, processo_id, nome_arquivo, mime_type, tamanho_bytes, \
         caminho_arquivo, descricao, nivel_sigilo, criado_em, atualizado_em) \
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)",
        rusqlite::params![
            doc_id,
            payload.processo_id,
            nome_arquivo,
            mime_type,
            tamanho_bytes,
            file_path.to_string_lossy().to_string(),
            format!("Peça gerada: {}", payload.template_id),
            nivel_str,
            now,
            now,
        ],
    )
    .map_err(|e| AppError::Database(format!("Insert generated documento failed: {e}")))?;

    // 6. Audit log
    let audit_id = generate_id();
    conn.execute(
        "INSERT INTO audit_log (id, acao, entidade, entidade_id, details_json, criado_em) \
         VALUES (?1, 'peca_gerada', 'documento', ?2, ?3, ?4)",
        rusqlite::params![
            audit_id,
            doc_id,
            serde_json::json!({
                "template_id": payload.template_id,
                "processo_id": payload.processo_id,
                "nome_arquivo": nome_arquivo,
            })
            .to_string(),
            now,
        ],
    )
    .map_err(|e| AppError::Database(format!("Audit log insert failed: {e}")))?;

    Ok(GerarPecaResult {
        documento_id: doc_id,
        nome_arquivo,
        conteudo_preview: preview,
    })
}
