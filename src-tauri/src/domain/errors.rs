//! Domain error types for the Automação Jurídica Assistida application.
//!
//! This module defines a comprehensive `DomainError` enum with typed variants
//! covering all domain-level failure modes: validation, authorization, entity
//! resolution, cryptography, database, IA/LLM, DataJud integration, file I/O,
//! sidecar communication, and template rendering.

use std::fmt;

/// Represents the 5 classification levels of legal secrecy (sigilo).
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum NivelSigilo {
    /// Public — no restrictions.
    Publico = 1,
    /// Internal — visible within the office.
    Interno = 2,
    /// Confidential — restricted to case participants.
    Confidencial = 3,
    /// Secret — restricted to lead attorneys.
    Secreto = 4,
    /// Ultra-secret — restricted to a single responsible attorney.
    UltraSecreto = 5,
}

impl fmt::Display for NivelSigilo {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            NivelSigilo::Publico => write!(f, "Público"),
            NivelSigilo::Interno => write!(f, "Interno"),
            NivelSigilo::Confidencial => write!(f, "Confidencial"),
            NivelSigilo::Secreto => write!(f, "Secreto"),
            NivelSigilo::UltraSecreto => write!(f, "Ultra-Secreto"),
        }
    }
}

/// Comprehensive domain error type.
///
/// Each variant carries enough context for the presentation layer to produce
/// meaningful user-facing messages while keeping sensitive details out of
/// logs (e.g., no raw SQL or file-system paths in user messages).
#[derive(Debug)]
pub enum DomainError {
    // ── Validation ───────────────────────────────────────────────────────
    /// A field failed schema or business-rule validation.
    ValidationError {
        field: String,
        message: String,
    },

    /// Multiple validation failures collected from a single operation.
    ValidationErrors {
        errors: Vec<(String, String)>,
    },

    // ── Entity resolution ────────────────────────────────────────────────
    /// The requested entity was not found.
    NotFound {
        entity: String,
        id: String,
    },

    /// A uniqueness constraint would be violated.
    AlreadyExists {
        entity: String,
        field: String,
        value: String,
    },

    // ── Authorization / Authentication ───────────────────────────────────
    /// The caller is not authenticated.
    Unauthenticated {
        reason: String,
    },

    /// The caller lacks the required role or attribute.
    Unauthorized {
        user_id: String,
        action: String,
        resource: String,
    },

    /// The caller's clearance level is insufficient for the requested
    /// secrecy level.
    InsufficientClearance {
        required: NivelSigilo,
        actual: NivelSigilo,
    },

    // ── Cryptography ─────────────────────────────────────────────────────
    /// An error occurred during encryption or decryption (SQLCipher, file
    /// encryption, key derivation, etc.).
    CryptoError {
        operation: String,
        message: String,
    },

    // ── Database ─────────────────────────────────────────────────────────
    /// A database operation failed.
    DatabaseError {
        operation: String,
        message: String,
    },

    /// A migration or schema issue was detected.
    MigrationError {
        message: String,
    },

    // ── IA / LLM ─────────────────────────────────────────────────────────
    /// The local LLM (llama.cpp / Ollama) returned an error or is
    /// unavailable.
    LlmError {
        model: String,
        message: String,
    },

    /// The pseudonymisation pipeline failed.
    PseudonymizationError {
        message: String,
    },

    // ── DataJud integration ──────────────────────────────────────────────
    /// Communication with the DataJud API failed.
    DataJudError {
        endpoint: String,
        status_code: Option<u16>,
        message: String,
    },

    // ── File / Document ──────────────────────────────────────────────────
    /// A file-system or document-handling error.
    FileError {
        path: String,
        message: String,
    },

    /// The uploaded file exceeds the allowed size or has a disallowed MIME
    /// type.
    FileRejected {
        filename: String,
        reason: String,
    },

    // ── Template rendering ───────────────────────────────────────────────
    /// Jinja2 template rendering (via Python sidecar) failed.
    TemplateError {
        template_name: String,
        message: String,
    },

    // ── Sidecar communication ────────────────────────────────────────────
    /// The Python sidecar process could not be reached or returned an
    /// unexpected response.
    SidecarError {
        command: String,
        message: String,
    },

    // ── Prazo (deadline) ─────────────────────────────────────────────────
    /// A legal deadline constraint was violated (e.g., attempting to
    /// perform an action after the deadline has passed).
    PrazoExpirado {
        processo_id: String,
        prazo: String,
    },

    // ── Generic / catch-all ──────────────────────────────────────────────
    /// An unexpected internal error. The `context` field should never
    /// contain PII.
    InternalError {
        context: String,
        message: String,
    },
}

impl fmt::Display for DomainError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            // Validation
            DomainError::ValidationError { field, message } => {
                write!(f, "Erro de validação no campo '{field}': {message}")
            }
            DomainError::ValidationErrors { errors } => {
                write!(f, "Erros de validação: ")?;
                for (i, (field, msg)) in errors.iter().enumerate() {
                    if i > 0 {
                        write!(f, "; ")?;
                    }
                    write!(f, "'{field}': {msg}")?;
                }
                Ok(())
            }

            // Entity resolution
            DomainError::NotFound { entity, id } => {
                write!(f, "{entity} com id '{id}' não encontrado(a)")
            }
            DomainError::AlreadyExists { entity, field, value } => {
                write!(f, "{entity} com {field}='{value}' já existe")
            }

            // Auth
            DomainError::Unauthenticated { reason } => {
                write!(f, "Não autenticado: {reason}")
            }
            DomainError::Unauthorized { user_id, action, resource } => {
                write!(
                    f,
                    "Usuário '{user_id}' não autorizado para '{action}' em '{resource}'"
                )
            }
            DomainError::InsufficientClearance { required, actual } => {
                write!(
                    f,
                    "Nível de sigilo insuficiente: requerido {required}, atual {actual}"
                )
            }

            // Crypto
            DomainError::CryptoError { operation, message } => {
                write!(f, "Erro de criptografia em '{operation}': {message}")
            }

            // Database
            DomainError::DatabaseError { operation, message } => {
                write!(f, "Erro de banco de dados em '{operation}': {message}")
            }
            DomainError::MigrationError { message } => {
                write!(f, "Erro de migração: {message}")
            }

            // IA
            DomainError::LlmError { model, message } => {
                write!(f, "Erro do LLM '{model}': {message}")
            }
            DomainError::PseudonymizationError { message } => {
                write!(f, "Erro de pseudonimização: {message}")
            }

            // DataJud
            DomainError::DataJudError { endpoint, status_code, message } => {
                if let Some(code) = status_code {
                    write!(f, "Erro DataJud [{code}] em '{endpoint}': {message}")
                } else {
                    write!(f, "Erro DataJud em '{endpoint}': {message}")
                }
            }

            // File
            DomainError::FileError { path, message } => {
                write!(f, "Erro de arquivo em '{path}': {message}")
            }
            DomainError::FileRejected { filename, reason } => {
                write!(f, "Arquivo '{filename}' rejeitado: {reason}")
            }

            // Template
            DomainError::TemplateError { template_name, message } => {
                write!(f, "Erro no template '{template_name}': {message}")
            }

            // Sidecar
            DomainError::SidecarError { command, message } => {
                write!(f, "Erro no sidecar (comando '{command}'): {message}")
            }

            // Prazo
            DomainError::PrazoExpirado { processo_id, prazo } => {
                write!(
                    f,
                    "Prazo expirado para processo '{processo_id}': {prazo}"
                )
            }

            // Internal
            DomainError::InternalError { context, message } => {
                write!(f, "Erro interno [{context}]: {message}")
            }
        }
    }
}

impl std::error::Error for DomainError {}

// ── Conversions from infrastructure errors ──────────────────────────────────

impl From<rusqlite::Error> for DomainError {
    fn from(err: rusqlite::Error) -> Self {
        DomainError::DatabaseError {
            operation: "sqlite".to_string(),
            message: err.to_string(),
        }
    }
}

impl From<serde_json::Error> for DomainError {
    fn from(err: serde_json::Error) -> Self {
        DomainError::InternalError {
            context: "serde_json".to_string(),
            message: err.to_string(),
        }
    }
}

impl From<std::io::Error> for DomainError {
    fn from(err: std::io::Error) -> Self {
        DomainError::FileError {
            path: String::new(),
            message: err.to_string(),
        }
    }
}

// ── Serialization for Tauri IPC ─────────────────────────────────────────────
//
// Tauri commands must return types that implement `serde::Serialize`.
// We serialize `DomainError` into a structured JSON object so the frontend
// can pattern-match on `error.kind`.

impl serde::Serialize for DomainError {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        use serde::ser::SerializeMap;

        let kind = match self {
            DomainError::ValidationError { .. } => "VALIDATION_ERROR",
            DomainError::ValidationErrors { .. } => "VALIDATION_ERRORS",
            DomainError::NotFound { .. } => "NOT_FOUND",
            DomainError::AlreadyExists { .. } => "ALREADY_EXISTS",
            DomainError::Unauthenticated { .. } => "UNAUTHENTICATED",
            DomainError::Unauthorized { .. } => "UNAUTHORIZED",
            DomainError::InsufficientClearance { .. } => "INSUFFICIENT_CLEARANCE",
            DomainError::CryptoError { .. } => "CRYPTO_ERROR",
            DomainError::DatabaseError { .. } => "DATABASE_ERROR",
            DomainError::MigrationError { .. } => "MIGRATION_ERROR",
            DomainError::LlmError { .. } => "LLM_ERROR",
            DomainError::PseudonymizationError { .. } => "PSEUDONYMIZATION_ERROR",
            DomainError::DataJudError { .. } => "DATAJUD_ERROR",
            DomainError::FileError { .. } => "FILE_ERROR",
            DomainError::FileRejected { .. } => "FILE_REJECTED",
            DomainError::TemplateError { .. } => "TEMPLATE_ERROR",
            DomainError::SidecarError { .. } => "SIDECAR_ERROR",
            DomainError::PrazoExpirado { .. } => "PRAZO_EXPIRADO",
            DomainError::InternalError { .. } => "INTERNAL_ERROR",
        };

        let mut map = serializer.serialize_map(Some(2))?;
        map.serialize_entry("kind", kind)?;
        map.serialize_entry("message", &self.to_string())?;
        map.end()
    }
}

/// Convenience type alias used throughout the application.
pub type DomainResult<T> = Result<T, DomainError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validation_error_display() {
        let err = DomainError::ValidationError {
            field: "cpf".to_string(),
            message: "CPF inválido".to_string(),
        };
        assert!(err.to_string().contains("cpf"));
        assert!(err.to_string().contains("CPF inválido"));
    }

    #[test]
    fn test_not_found_display() {
        let err = DomainError::NotFound {
            entity: "Processo".to_string(),
            id: "abc-123".to_string(),
        };
        let msg = err.to_string();
        assert!(msg.contains("Processo"));
        assert!(msg.contains("abc-123"));
    }

    #[test]
    fn test_insufficient_clearance_display() {
        let err = DomainError::InsufficientClearance {
            required: NivelSigilo::Secreto,
            actual: NivelSigilo::Interno,
        };
        let msg = err.to_string();
        assert!(msg.contains("Secreto"));
        assert!(msg.contains("Interno"));
    }

    #[test]
    fn test_serialization_contains_kind() {
        let err = DomainError::NotFound {
            entity: "Documento".to_string(),
            id: "42".to_string(),
        };
        let json = serde_json::to_string(&err).expect("serialize");
        assert!(json.contains("NOT_FOUND"));
        assert!(json.contains("Documento"));
    }

    #[test]
    fn test_nivel_sigilo_ordering() {
        assert!(NivelSigilo::Publico < NivelSigilo::UltraSecreto);
        assert!(NivelSigilo::Confidencial < NivelSigilo::Secreto);
    }

    #[test]
    fn test_domain_result_alias() {
        let ok: DomainResult<i32> = Ok(42);
        assert_eq!(ok.unwrap(), 42);

        let err: DomainResult<i32> = Err(DomainError::InternalError {
            context: "test".to_string(),
            message: "boom".to_string(),
        });
        assert!(err.is_err());
    }
}
