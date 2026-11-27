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
    eprintln!("[kiosk] exit_app: останавливаю бэкенд и вызываю AppHandle::exit(0)");
    // `AppHandle::exit` приводит к `RunEvent::Exit` (там тоже есть остановка),
    // но вызов здесь — страховка на случай, если событие не будет доставлено.
    crate::process::shutdown_backend(&app);
    app.exit(0);
}

/// Перезапуск приложения (полезно после смены настроек).
#[tauri::command]
pub fn restart_app(app: AppHandle) {
    eprintln!("[kiosk] restart_app: останавливаю бэкенд и перезапускаю приложение");
    // `AppHandle::restart`, вызванный с main-thread, завершает процесс БЕЗ
    // `RunEvent::Exit` — поэтому останавливаем бэкенд явно, иначе новый
    // экземпляр упрётся в занятый порт 8765.
    crate::process::shutdown_backend(&app);
    // `AppHandle::restart` не возвращает управление (приложение перезапускается).
    app.restart();
}

/// Сбрасывает флаг админ-режима. Вызывается фронтендом после реакции на
/// Ctrl+Shift+A, чтобы одно нажатие не открывало форму входа повторно
/// (см. useDesktopAdminPoll).
#[tauri::command]
pub fn clear_admin_mode() {
    #[cfg(target_os = "windows")]
    crate::kiosk::clear_admin_mode();
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

/// Разрешает/запрещает выход из киоска (Ctrl+Alt+X). Фронтенд вызывает с
/// `true` после успешного входа в админку и с `false` при выходе из неё.
#[tauri::command]
pub fn set_exit_allowed(allowed: bool) {
    #[cfg(target_os = "windows")]
    crate::kiosk::set_exit_allowed(allowed);
    #[cfg(not(target_os = "windows"))]
    let _ = allowed;
}

/// Возвращает канал автообновления текущей сборки (`dev` / `main`).
/// Позволяет админ-панели показать, из какой ветки обновляется киоск.
#[tauri::command]
pub fn get_update_channel() -> String {
    crate::updater::channel().to_string()
}
