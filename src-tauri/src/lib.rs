//! Módulo raiz da aplicação Automação Jurídica Assistida (Tauri backend).
//!
//! Re-exporta os submódulos principais:
//! - `domain` — entidades e regras de negócio puras
//! - `commands` — Tauri commands (IPC handlers)
//! - `infra` — infraestrutura (database, crypto, sidecar)
//!
//! A função [`run`] inicializa e executa a aplicação Tauri.

pub mod commands;
pub mod domain;
pub mod infra;

use infra::database::Database;
use infra::sidecar::SidecarManager;
use std::sync::Arc;
use tokio::sync::Mutex;

/// Estado global compartilhado da aplicação, gerenciado pelo Tauri.
///
/// Contém referências thread-safe para o banco de dados criptografado
/// e o gerenciador do sidecar Python.
pub struct AppState {
    /// Conexão com o banco SQLite/SQLCipher criptografado.
    pub db: Arc<Mutex<Database>>,
    /// Gerenciador do processo sidecar Python (IA, DataJud, pseudonimização).
    pub sidecar: Arc<Mutex<SidecarManager>>,
}

/// Inicializa e executa a aplicação Tauri.
///
/// Esta função:
/// 1. Abre (ou cria) o banco SQLite criptografado via SQLCipher.
/// 2. Executa migrações pendentes.
/// 3. Inicializa o gerenciador do sidecar Python.
/// 4. Registra o estado global e os Tauri commands.
/// 5. Inicia o event loop do Tauri.
///
/// # Panics
///
/// Panics se a inicialização do banco de dados ou do Tauri falhar.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Construir o Tauri app com setup assíncrono
    tauri::Builder::default()
        .setup(|app| {
            let app_handle = app.handle().clone();

            // Resolver o diretório de dados da aplicação para armazenar o banco
            let app_data_dir = app_handle
                .path()
                .app_data_dir()
                .expect("Falha ao resolver diretório de dados da aplicação");

            // Garantir que o diretório existe
            std::fs::create_dir_all(&app_data_dir)
                .expect("Falha ao criar diretório de dados da aplicação");

            let db_path = app_data_dir.join("automacao_juridica.db");

            // TODO: A chave de criptografia deve ser derivada de forma segura.
            // Em produção, usar prompt de senha do usuário + PBKDF2/Argon2
            // ou integração com keychain do SO. Por ora, lê de variável de ambiente.
            let db_key = std::env::var("AJA_DB_KEY")
                .unwrap_or_else(|_| "dev-insecure-key-change-me".to_string());

            // Inicializar banco de dados criptografado
            let db = Database::open(&db_path, &db_key)
                .expect("Falha ao abrir banco de dados SQLCipher");

            // Executar migrações
            db.run_migrations()
                .expect("Falha ao executar migrações do banco de dados");

            // Inicializar sidecar Python
            let sidecar = SidecarManager::new(&app_handle);

            // Construir estado compartilhado
            let state = AppState {
                db: Arc::new(Mutex::new(db)),
                sidecar: Arc::new(Mutex::new(sidecar)),
            };

            // Registrar estado no Tauri para acesso via commands
            app.manage(state);

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // Commands de processos jurídicos
            commands::processos::criar_processo,
            commands::processos::listar_processos,
            commands::processos::buscar_processo,
            commands::processos::atualizar_processo,
            // Commands de documentos
            commands::documentos::upload_documento,
            commands::documentos::listar_documentos,
            commands::documentos::gerar_documento,
            // Commands de IA / chat
            commands::ia_chat::enviar_mensagem,
            commands::ia_chat::iniciar_sessao_chat,
        ])
        .run(tauri::generate_context!())
        .expect("Erro ao executar a aplicação Tauri");
}

/// Trait auxiliar para acesso ao `PathResolver` do Tauri de forma ergonômica.
trait AppHandlePath {
    fn path(&self) -> &dyn tauri::path::PathResolver;
}
