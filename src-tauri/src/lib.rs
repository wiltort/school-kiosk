//! School Kiosk — Tauri desktop shell (логика).
//!
//! Приложение-киоск:
//!   1. Запускает Python-бэкенд как child process.
//!   2. Ждёт health-check на порту 8765.
//!   3. Открывает WebView с React SPA.
//!   4. Активирует киоск-режим (полный экран + блокировка клавиш).

pub mod admin;
#[cfg(target_os = "windows")]
pub mod kiosk;
pub mod process;

use tauri::Manager;

/// Порт, на котором слушает Python-бэкенд (совпадает с `config.server_port`).
pub const BACKEND_PORT: u16 = 8765;
/// Endpoint для проверки, что бэкенд готов.
pub const HEALTH_URL: &str = "http://127.0.0.1:8765/";

/// Точка входа приложения (вызывается из `main.rs`).
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            // 1. Запускаем Python-бэкенд как child process.
            process::BackendProcess::spawn_and_wait(app.handle())?;

            // 2. Показываем окно после того, как бэкенд готов.
            if let Some(window) = app.get_webview_window("main") {
                window.show()?;
            }

            // 3. Киоск-режим (Windows API).
            #[cfg(target_os = "windows")]
            kiosk::activate(&app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            admin::exit_app,
            admin::restart_app,
        ])
        .run(tauri::generate_context!())
        .expect("error while running School Kiosk");
}
