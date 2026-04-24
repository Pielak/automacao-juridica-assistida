//! Registro centralizado de Tauri commands.
//!
//! Este módulo re-exporta todos os sub-módulos de commands e fornece
//! a função `register_commands` que retorna o `tauri::generate_handler!`
//! com todos os commands disponíveis para invocação via IPC pelo frontend.

pub mod documentos;
pub mod ia_chat;
pub mod processos;

// TODO: Adicionar módulo `datajud` quando os commands de consulta ao DataJud
// forem implementados (via sidecar Python). Ex:
// pub mod datajud;

// TODO: Adicionar módulo `auth` para commands de autenticação local
// (login, logout, troca de senha, RBAC checks). Ex:
// pub mod auth;

// TODO: Adicionar módulo `config` para commands de configuração do sistema
// (alterar chave de criptografia, configurar Ollama endpoint, etc). Ex:
// pub mod config;

use tauri::Builder;

/// Registra todos os Tauri commands no builder da aplicação.
///
/// Esta função é chamada em `main.rs` / `lib.rs` para expor os commands
/// ao frontend via `tauri::invoke()`.
///
/// # Exemplo
///
/// ```rust,no_run
/// // Em src-tauri/src/lib.rs ou main.rs:
/// use crate::commands;
///
/// tauri::Builder::default()
///     .invoke_handler(commands::generate_handler())
///     .run(tauri::generate_context!())
///     .expect("error while running tauri application");
/// ```
pub fn generate_handler() -> impl Fn(tauri::Invoke) {
    tauri::generate_handler![
        // ── Processos Jurídicos ──────────────────────────────────────
        processos::criar_processo,
        processos::listar_processos,
        processos::obter_processo,
        processos::atualizar_processo,
        processos::excluir_processo,
        // ── Documentos ──────────────────────────────────────────────
        documentos::upload_documento,
        documentos::listar_documentos,
        documentos::obter_documento,
        documentos::excluir_documento,
        // ── Chat IA (LLM local via Ollama/llama.cpp) ────────────────
        ia_chat::enviar_mensagem,
        ia_chat::iniciar_sessao_chat,
        ia_chat::listar_sessoes_chat,
        // TODO: Descomentar quando os módulos forem implementados:
        // ── DataJud ─────────────────────────────────────────────────
        // datajud::consultar_processo_datajud,
        // datajud::sincronizar_movimentacoes,
        // ── Autenticação / Autorização ──────────────────────────────
        // auth::login,
        // auth::logout,
        // auth::verificar_sessao,
        // ── Configurações ───────────────────────────────────────────
        // config::obter_configuracoes,
        // config::salvar_configuracoes,
    ]
}

/// Registra os commands diretamente em um `tauri::Builder` existente.
///
/// Alternativa conveniente a `generate_handler()` quando se deseja
/// encadear no builder pattern.
pub fn register_commands<R: tauri::Runtime>(builder: Builder<R>) -> Builder<R> {
    builder.invoke_handler(tauri::generate_handler![
        // ── Processos Jurídicos ──────────────────────────────────────
        processos::criar_processo,
        processos::listar_processos,
        processos::obter_processo,
        processos::atualizar_processo,
        processos::excluir_processo,
        // ── Documentos ──────────────────────────────────────────────
        documentos::upload_documento,
        documentos::listar_documentos,
        documentos::obter_documento,
        documentos::excluir_documento,
        // ── Chat IA (LLM local via Ollama/llama.cpp) ────────────────
        ia_chat::enviar_mensagem,
        ia_chat::iniciar_sessao_chat,
        ia_chat::listar_sessoes_chat,
    ])
}
