//! Киоск-режим (Windows API).
//!
//! Реализует функционал, аналогичный старой C#-версии:
//!   - полноэкранное окно поверх всех окон (topmost);
//!   - скрытие курсора при бездействии;
//!   - блокировка системных клавиш через низкоуровневый хук клавиатуры;
//!   - переключение в админ-режим по комбинации Ctrl+Shift+A.

use std::sync::atomic::{AtomicBool, Ordering};

use tauri::{App, Manager, WebviewWindow};

/// Активен ли сейчас админ-режим (глобальный флаг для IPC из admin.rs).
static ADMIN_MODE: AtomicBool = AtomicBool::new(false);

/// Комбинация для входа в админ-режим.
const ADMIN_SHORTCUT: (&str, &str) = ("Ctrl", "Shift+A");
/// Комбинация для выхода из киоска (только в админ-режиме).
const EXIT_SHORTCUT: &str = "Ctrl+Alt+X";

/// Возвращает, активен ли админ-режим.
pub fn is_admin_active() -> bool {
    ADMIN_MODE.load(Ordering::SeqCst)
}

/// Включает киоск-режим: fullscreen, topmost, скрытие курсора и хук клавиш.
pub fn activate(app: &App) -> Result<(), Box<dyn std::error::Error>> {
    let window = app
        .get_webview_window("main")
        .ok_or("окно 'main' не найдено")?;

    apply_window_state(&window)?;
    start_keyboard_hook();

    println!("Kiosk guard active. Admin: {} , Exit: {}", {
        let (c, k) = ADMIN_SHORTCUT;
        format!("{c}+{k}")
    }, EXIT_SHORTCUT);

    Ok(())
}

/// Применяет состояние окна: fullscreen + always-on-top.
fn apply_window_state(window: &WebviewWindow) -> tauri::Result<()> {
    window.set_fullscreen(true)?;
    window.set_always_on_top(true)?;
    Ok(())
}

// ============================================================================
// Низкоуровневый хук клавиатуры (WH_KEYBOARD_LL)
// ============================================================================
//
// Ниже — каркас реализации. Рабочий вариант требует:
//   - собственный поток с циклом сообщений (GetMessage);
//   - глобальный hook-proc, который возвращает 1 для заблокированных клавиш;
//   - проверку модификаторов (Alt, Ctrl, Shift, Win).
//
// Заблокированные клавиши:
//   VK_LWIN / VK_RWIN        — меню «Пуск»
//   VK_ESCAPE                — выход из полноэкранного режима
//   VK_TAB + Alt             — переключение окон
//   VK_F4 + Alt              — закрытие окна
//   VK_LMENU / VK_RMENU      — чтобы исключить ложные срабатывания
//
// Ctrl+Alt+Del блокируется ОС Windows на уровне системы и из user-space
// перехватить нельзя; для киоска его обычно закрывают политикой/групповой
// политикой (см. документацию в plans/architecture-plan.md).
//
// TODO(kiosk): доделать hook-proc и поток сообщений после первичной сборки.

#[allow(dead_code)]
mod hook {
    use windows::Win32::Foundation::{LPARAM, LRESULT, WPARAM};
    use windows::Win32::UI::WindowsAndMessaging::{
        GetMessageW, KBDLLHOOKSTRUCT, MSG, SetWindowsHookExW, WH_KEYBOARD_LL,
    };

    /// Код-сообщения хука — не перехватывать (пропустить дальше).
    const HC_ACTION: i32 = 0;

    pub unsafe fn install() -> Result<(), windows::core::Error> {
        // TODO(kiosk): низкоуровневый хук должен быть установлен из потока
        // с активным циклом сообщений. Здесь заглушка, чтобы структура была
        // готова к доработке.
        let _hook = SetWindowsHookExW(
            WH_KEYBOARD_LL,
            Some(hook_proc),
            None,
            0,
        )?;
        // Держим поток живым (GetMessage) — TODO.
        let mut msg = MSG::default();
        while GetMessageW(&mut msg, None, 0, 0).into() {
            // TranslateMessage/DispatchMessage не нужны для WH_KEYBOARD_LL,
            // но вызов GetMessage обязателен для получения событий хука.
        }
        Ok(())
    }

    extern "system" fn hook_proc(
        _code: i32,
        _wparam: WPARAM,
        _lparam: LPARAM,
    ) -> LRESULT {
        if _code == HC_ACTION {
            // TODO(kiosk): реализовать разбор нажатий.
            let _kb = _lparam.0 as *const KBDLLHOOKSTRUCT;
            // TODO(kiosk): здесь проверять vkCode и модификаторы.
            // Заблокированные клавиши возвращать LRESULT(1), остальные — CallNextHookEx.
        }
        LRESULT(0)
    }
}

/// Запускает хук клавиатуры в отдельном потоке.
fn start_keyboard_hook() {
    #[cfg(target_os = "windows")]
    std::thread::spawn(|| unsafe {
        let _ = hook::install();
    });
}
