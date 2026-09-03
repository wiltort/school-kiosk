//! IPC-команды для админ-режима.
//!
//! Вызываются из React через `@tauri-apps/api/core` (invoke). Доступны только
//! когда активен админ-режим (см. kiosk.rs).
//!
//! Настройки (папка изображений, автозагрузка) здесь НЕ живут: их владелец —
//! бэкенд, и админ-панель работает с ними через тот же HTTP-API, что и браузер
//! (см. backend/src/apps/admin). Здесь остаются только команды управления
//! жизненным циклом приложения и проверка админ-режима.

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

/// Проверка, что админ-режим активен. Вызывается фронтендом, чтобы
/// открыть панель управления на десктопе (после Ctrl+Shift+A).
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

/// Возвращает канал автообновления текущей сборки (`dev` / `main`).
/// Позволяет админ-панели показать, из какой ветки обновляется киоск.
#[tauri::command]
pub fn get_update_channel() -> String {
    crate::updater::channel().to_string()
}
