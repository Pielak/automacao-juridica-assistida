//! Infrastructure layer module for Automação Jurídica Assistida.
//!
//! This module aggregates all infrastructure concerns including:
//! - **database**: SQLite + SQLCipher encrypted database access and connection management
//! - **crypto**: Cryptographic utilities (encryption at rest, key derivation, hashing)
//! - **sidecar**: Python sidecar process management for IA, pseudonymization, and DataJud integration
//!
//! # Architecture
//!
//! The infrastructure layer sits at the outermost ring of the Clean Architecture,
//! implementing interfaces defined by the domain/application layers. All external
//! dependencies (database, filesystem, external processes) are encapsulated here.
//!
//! # Security
//!
//! All database operations use SQLCipher with AES-256-CBC encryption and PBKDF2
//! (100k iterations) key derivation. Sensitive data never leaves this layer unencrypted.

pub mod crypto;
pub mod database;
pub mod sidecar;

// Re-export primary types for ergonomic access from commands layer
pub use crypto::CryptoService;
pub use database::Database;
pub use sidecar::SidecarManager;
