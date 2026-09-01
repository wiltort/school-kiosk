//! IPC-команды для админ-режима.
//!
//! Вызываются из React через `@tauri-apps/api/core` (invoke).
//! Доступны только когда активен админ-режим (см. kiosk.rs / хеш).

use tauri::AppHandle;

/// Выход из приложения. Вызывается командой `exit_app` из WebView.
#[tauri::command]
pub fn exit_app(app: AppHandle) {
    app.exit(0);
}

/// Перезапуск приложения (полезно после смены настроек).
#[tauri::command]
pub fn restart_app(app: AppHandle) {
    // `AppHandle::restart` не возвращает управление (приложение перезапускается).
    app.restart();
}

/// Проверка, что админ-режим активен. Может вызываться фронтендом,
/// чтобы скрывать/показывать панель управления.
///
/// TODO: в реальной системе проверять по-настоящему — это заглушка,
/// которая читает состояние из kiosk.rs. Пока всегда false, пока не
/// реализован KioskGuard.
#[tauri::command]
pub fn is_admin_active() -> bool {
    #[cfg(target_os = "windows")]
    {
        crate::kiosk::is_admin_active()
    }
    #[cfg(not(target_os = "windows"))]
    {
        false
    }
}
