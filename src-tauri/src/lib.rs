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
pub mod settings;
pub mod updater;

use std::sync::Mutex;

use tauri::{Manager, WindowEvent};

/// Порт, на котором слушает Python-бэкенд (совпадает с `config.server_port`).
pub const BACKEND_PORT: u16 = 8765;
/// Endpoint для проверки, что бэкенд готов.
pub const HEALTH_URL: &str = "http://127.0.0.1:8765/";
/// URL, по которому WebView загружает SPA. Теперь это тот же HTTP-сервер,
/// который раздаёт приложение и по локальной сети (один origin).
pub const FRONTEND_URL: &str = "http://127.0.0.1:8765/";

/// Точка входа приложения (вызывается из `main.rs`).
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            // 0. Автообновление из своей ветки (только в релизной сборке под
            // конкретный канал). В dev и локальных сборках не запускается:
            // это и не мешает разработке, и не требует настроенного pubkey.
            // Состояние статуса регистрируем всегда, чтобы команда
            // get_update_status работала и в браузерной/локальной версии.
            app.manage(updater::UpdaterState(std::sync::Mutex::new(
                updater::initial_status(app.handle()),
            )));

            #[cfg(not(debug_assertions))]
            if updater::is_enabled() {
                app.handle()
                    .plugin(tauri_plugin_updater::Builder::new().build())?;
                updater::spawn_auto_update(app.handle().clone());
            }

            // 1. Запускаем Python-бэкенд как child process и передаём владение
            // в состояние приложения. Раньше результат отбрасывался
            // (`spawn_and_wait(...)?;`) — Drop вызывался сразу после этой
            // строки и убивал бэкенд: в dev он выживал случайно (осиротевший
            // uvicorn), а в release пропадал вовсе.
            let backend = process::BackendProcess::spawn_and_wait(app.handle())?;
            app.manage(Mutex::new(backend));

            // 2. Направляем WebView на SPA, раздаваемый бэкендом (одна точка
            // входа и для киоска, и для браузеров по LAN). Затем показываем окно.
            //
            // В dev остаёмся на devUrl (Vite): живой код с HMR, локальный
            // origin (IPC без remote-capabilities) и прокси /api на бэкенд.
            // Раньше navigate на бэкенд выполнялся и в dev — и WebView грузил
            // устаревший собранный frontend/dist вместо текущего кода.
            //
            // Cache-busting (release): в URL добавляем версию бинарника
            // (?v=...). При каждом обновлении URL меняется, поэтому WebView2
            // считает документ новым и грузит свежий index.html/assets вместо
            // старого бандла из своего дискового кэша.
            if let Some(window) = app.get_webview_window("main") {
                #[cfg(debug_assertions)]
                {
                    window.show()?;
                    window.open_devtools();
                    eprintln!("[kiosk] dev-режим: WebView на devUrl (Vite), DevTools открыты");
                }

                #[cfg(not(debug_assertions))]
                {
                    let mut url =
                        tauri::Url::parse(FRONTEND_URL).expect("static frontend URL must be valid");
                    url.set_query(Some(&format!("v={}", app.package_info().version)));
                    window.navigate(url)?;
                    window.show()?;
                }
            }

            // 3. Киоск-режим (Windows API).
            #[cfg(target_os = "windows")]
            kiosk::activate(app)?;

            Ok(())
        })
        .on_window_event(|_window, event| {
            // Страховка киоск-режима: любое закрытие окна (Alt+F4, WM_CLOSE,
            // системное меню) блокируется на уровне Tauri, даже если
            // низкоуровневый хук клавиатуры по какой-то причине не сработал.
            // Единственный способ выхода — админ-команда `exit_app`, которая
            // вызывает AppHandle::exit (CloseRequested при этом не срабатывает).
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                eprintln!("[kiosk] попытка закрытия окна заблокирована (Alt+F4/WM_CLOSE)");
            }
        })
        .invoke_handler(tauri::generate_handler![
            admin::exit_app,
            admin::restart_app,
            admin::is_admin_active,
            admin::clear_admin_mode,
            admin::set_exit_allowed,
            admin::get_update_channel,
            updater::get_update_status,
        ])
        .run(tauri::generate_context!())
        .expect("error while running School Kiosk");
}
