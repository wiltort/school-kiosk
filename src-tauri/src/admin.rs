//! IPC-команды для админ-режима.
//!
//! Вызываются из React через `@tauri-apps/api/core` (invoke).
//! Доступны только когда активен админ-режим (см. kiosk.rs / хеш).

use std::path::PathBuf;

use tauri::AppHandle;

use crate::settings::{self, SettingsDto};

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

/// Возвращает текущие настройки приложения (для админ-панели).
#[tauri::command]
pub fn get_settings(app: AppHandle) -> Result<SettingsDto, String> {
    let s = settings::load_for(&app);
    Ok(SettingsDto::from(&s))
}

/// Устанавливает каталог статики и сохраняет настройки в файл.
/// Если `path == None`, каталог сбрасывается на значение по умолчанию.
#[tauri::command]
pub fn set_static_dir(app: AppHandle, path: Option<String>) -> Result<SettingsDto, String> {
    let mut s = settings::load_for(&app);
    s.static_dir = path.map(PathBuf::from);
    settings::save_for(&app, &s).map_err(|e| e.to_string())?;
    Ok(SettingsDto::from(&s))
}

/// Возвращает канал автообновления текущей сборки (`dev` / `main`).
/// Позволяет админ-панели показать, из какой ветки обновляется киоск.
#[tauri::command]
pub fn get_update_channel() -> String {
    crate::updater::channel().to_string()
}
