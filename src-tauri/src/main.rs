// src-tauri/src/main.rs
//! Entry-point da aplicação Tauri para o sistema de Automação Jurídica Assistida.
//!
//! Responsável por:
//! - Bootstrap do runtime Tauri
//! - Registro de commands IPC (processos, documentos, IA chat)
//! - Inicialização do banco de dados SQLCipher
//! - Configuração do sidecar Python
//! - Registro de event handlers globais

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use automacao_juridica_assistida::commands;
use automacao_juridica_assistida::infra;

fn main() {
    // Inicializa logging estruturado para auditoria e debug.
    // Em release, logs vão para arquivo; em debug, para stdout.
    #[cfg(debug_assertions)]
    {
        env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("debug"))
            .format_timestamp_millis()
            .init();
    }
    #[cfg(not(debug_assertions))]
    {
        env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info"))
            .format_timestamp_millis()
            .init();
    }

    log::info!("Iniciando Automação Jurídica Assistida...");

    tauri::Builder::default()
        .setup(|app| {
            log::info!("Executando setup da aplicação Tauri...");

            // ---------------------------------------------------------------
            // 1. Inicializa o banco de dados SQLCipher
            // ---------------------------------------------------------------
            let app_handle = app.handle().clone();
            let db_pool = infra::database::initialize_database(&app_handle)
                .map_err(|e| {
                    log::error!("Falha ao inicializar banco de dados: {}", e);
                    e
                })?;

            // Armazena o pool/conexão como estado gerenciado do Tauri
            app.manage(db_pool);
            log::info!("Banco de dados SQLCipher inicializado com sucesso.");

            // ---------------------------------------------------------------
            // 2. Inicializa o gerenciador de criptografia
            // ---------------------------------------------------------------
            let crypto_manager = infra::crypto::CryptoManager::new(&app_handle)
                .map_err(|e| {
                    log::error!("Falha ao inicializar gerenciador de criptografia: {}", e);
                    e
                })?;

            app.manage(crypto_manager);
            log::info!("Gerenciador de criptografia inicializado.");

            // ---------------------------------------------------------------
            // 3. Inicializa o gerenciador do sidecar Python
            // ---------------------------------------------------------------
            let sidecar_manager = infra::sidecar::SidecarManager::new(&app_handle)
                .map_err(|e| {
                    log::error!("Falha ao inicializar sidecar Python: {}", e);
                    e
                })?;

            app.manage(sidecar_manager);
            log::info!("Gerenciador de sidecar Python inicializado.");

            // ---------------------------------------------------------------
            // 4. Registra event listeners globais
            // ---------------------------------------------------------------
            let handle_for_events = app.handle().clone();
            app.listen("app://shutdown-requested", move |_event| {
                log::info!("Shutdown solicitado pelo frontend. Encerrando sidecar...");
                // TODO: Implementar graceful shutdown do sidecar Python
                // e flush de logs de auditoria pendentes.
                let _ = &handle_for_events;
            });

            log::info!("Setup da aplicação concluído com sucesso.");
            Ok(())
        })
        // -------------------------------------------------------------------
        // Registro de todos os Tauri Commands (IPC handlers)
        // -------------------------------------------------------------------
        .invoke_handler(tauri::generate_handler![
            // Commands de Processos Jurídicos
            commands::processos::criar_processo,
            commands::processos::listar_processos,
            commands::processos::buscar_processo,
            commands::processos::atualizar_processo,
            commands::processos::excluir_processo,
            // Commands de Documentos
            commands::documentos::upload_documento,
            commands::documentos::listar_documentos,
            commands::documentos::buscar_documento,
            commands::documentos::excluir_documento,
            commands::documentos::gerar_peca_juridica,
            // Commands de IA / Chat
            commands::ia_chat::iniciar_chat,
            commands::ia_chat::enviar_mensagem,
            commands::ia_chat::encerrar_chat,
            commands::ia_chat::listar_historico_chat,
        ])
        // -------------------------------------------------------------------
        // Plugins Tauri (se necessário no futuro)
        // -------------------------------------------------------------------
        // TODO: Avaliar plugins para:
        // - tauri-plugin-fs (acesso seguro ao filesystem)
        // - tauri-plugin-dialog (diálogos nativos de arquivo)
        // - tauri-plugin-notification (notificações de prazos)
        // - tauri-plugin-updater (auto-update da aplicação)
        .run(tauri::generate_context!())
        .expect("Erro fatal ao executar a aplicação Tauri");
}
