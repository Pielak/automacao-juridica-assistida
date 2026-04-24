//! Domain module for Automação Jurídica Assistida.
//!
//! This module contains pure domain entities and business rules.
//! No framework dependencies — only standard library and serde for serialization.
//! Entities: Processo, Documento, Usuario, Sigilo, Permissao, AuditLogEntry.
//! Errors: domain-specific error types.

pub mod entities;
pub mod errors;

// Re-export core domain types for ergonomic access
pub use entities::{
    Documento, NivelSigilo, Permissao, Processo, StatusDocumento, StatusProcesso, TipoDocumento,
    Usuario, UsuarioRole, AuditLogEntry, AuditAction,
};
pub use errors::DomainError;
