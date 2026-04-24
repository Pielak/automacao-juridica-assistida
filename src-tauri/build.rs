//! Build script for the Tauri application.
//!
//! This script handles:
//! - Standard Tauri build context generation (resource compilation, icon processing)
//! - Registration of the Python sidecar binary for IA/processing tasks
//! - Platform-specific sidecar naming conventions

fn main() {
    // Register the Python sidecar so Tauri bundles it with the application.
    // The sidecar binary is expected at:
    //   sidecar-python/dist/sidecar-python{.exe on Windows}
    //
    // During development, the sidecar can be run directly via Python.
    // For production builds, the sidecar should be compiled to a standalone
    // binary using PyInstaller or Nuitka and placed in the expected path.
    //
    // The key in tauri.conf.json -> bundle -> externalBin should reference
    // "sidecar-python/dist/sidecar-python" (without platform suffix).
    // Tauri automatically appends the target triple suffix at build time.

    // Inform Cargo to re-run this build script if the sidecar source changes
    println!("cargo:rerun-if-changed=../sidecar-python/src/");
    println!("cargo:rerun-if-changed=../sidecar-python/pyproject.toml");

    // Inform Cargo to re-run if migration files change
    println!("cargo:rerun-if-changed=migrations/");

    // Inform Cargo to re-run if Tauri config changes
    println!("cargo:rerun-if-changed=tauri.conf.json");

    // Run the standard Tauri build procedure.
    // This generates the Tauri context (icons, resources, IPC glue code)
    // and validates the tauri.conf.json configuration.
    tauri_build::build();
}
