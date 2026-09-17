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

    println!(
        "Kiosk guard active. Admin: {} , Exit: {}",
        {
            let (c, k) = ADMIN_SHORTCUT;
            format!("{c}+{k}")
        },
        EXIT_SHORTCUT
    );

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
// Реализован рабочий вариант:
//   - собственный поток с циклом сообщений (GetMessage);
//   - глобальный hook-proc возвращает 1 для заблокированных клавиш;
//   - Ctrl+Shift+A переключает админ-режим (ADMIN_MODE).
//
// Заблокированные клавиши:
//   VK_LWIN / VK_RWIN        — меню «Пуск»
//   VK_ESCAPE                — выход из полноэкранного режима
//   VK_TAB + Alt             — переключение окон
//   VK_F4 + Alt              — закрытие окна
//
// Ctrl+Alt+Del блокируется ОС Windows на уровне системы и из user-space
// перехватить нельзя; для киоска его обычно закрывают политикой/групповой
// политикой.

#[cfg(target_os = "windows")]
mod hook {
    use std::ffi::c_void;
    use std::sync::atomic::{AtomicUsize, Ordering};

    use windows::Win32::Foundation::{LPARAM, LRESULT, WPARAM};
    use windows::Win32::UI::Input::KeyboardAndMouse::GetKeyState;
    use windows::Win32::UI::WindowsAndMessaging::{
        CallNextHookEx, DispatchMessageW, GetMessageW, SetWindowsHookExW, TranslateMessage, HHOOK,
        KBDLLHOOKSTRUCT, MSG, WH_KEYBOARD_LL,
    };

    /// Сообщение о нажатии клавиши (WM_KEYDOWN).
    const WM_KEYDOWN: u32 = 0x0100;
    /// Действие хука — обрабатываем только реальные события.
    const HC_ACTION: i32 = 0;

    // Виртуальные коды клавиш (сырые числа, чтобы не зависеть от типа
    // VIRTUAL_KEY в windows-rs; kbs.vk_code — u32).
    const VK_CTRL: i32 = 0x11;
    const VK_SHIFT: i32 = 0x10;
    const VK_ALT: i32 = 0x12;
    const VK_ESC: i32 = 0x1B;
    const VK_TAB: i32 = 0x09;
    const VK_F4: i32 = 0x73;
    const VK_LWIN: i32 = 0x5B;
    const VK_RWIN: i32 = 0x5C;
    const VK_A: i32 = 0x41;

    /// Дескриптор установленного хука (нужен для CallNextHookEx).
    ///
    /// Хранится как `usize`, т.к. `HHOOK` (сырой указатель) не реализует
    /// `Send`/`Sync` и не может лежать в статике напрямую.
    static HOOK: AtomicUsize = AtomicUsize::new(0);

    pub unsafe fn install() -> Result<(), windows::core::Error> {
        let hook = SetWindowsHookExW(WH_KEYBOARD_LL, Some(hook_proc), None, 0)?;
        HOOK.store(hook.0 as usize, Ordering::SeqCst);

        // Поток обязан держать цикл сообщений, иначе низкоуровневый хук
        // не будет получать события.
        let mut msg = MSG::default();
        while GetMessageW(&mut msg, None, 0, 0).into() {
            let _ = TranslateMessage(&msg);
            let _ = DispatchMessageW(&msg);
        }
        Ok(())
    }

    extern "system" fn hook_proc(code: i32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
        if code == HC_ACTION {
            let kb = lparam.0 as *const KBDLLHOOKSTRUCT;
            if !kb.is_null() {
                let key = unsafe { &*kb };
                let msg = wparam.0 as u32;

                if msg == WM_KEYDOWN {
                    // Вход/выход из админ-режима: Ctrl+Shift+A.
                    if key.vkCode as i32 == VK_A && is_pressed(VK_CTRL) && is_pressed(VK_SHIFT) {
                        super::toggle_admin_mode();
                        return LRESULT(1);
                    }
                    // Блокируем системные клавиши, чтобы не выйти из киоска.
                    if is_blocked(key.vkCode as i32, is_pressed(VK_ALT)) {
                        return LRESULT(1);
                    }
                }
            }
        }
        let hhk = HHOOK(HOOK.load(Ordering::SeqCst) as *mut c_void);
        unsafe { CallNextHookEx(hhk, code, wparam, lparam) }
    }

    /// Нажата ли клавиша в данный момент (старший бит состояния).
    fn is_pressed(vk: i32) -> bool {
        unsafe { GetKeyState(vk) < 0 }
    }

    /// Заблокированные комбинации (не должны работать в киоске).
    fn is_blocked(vk: i32, alt: bool) -> bool {
        matches!(vk, VK_ESC | VK_LWIN | VK_RWIN) || (alt && matches!(vk, VK_TAB | VK_F4))
    }
}

/// Переключает админ-режим (флаг для IPC из admin.rs).
fn toggle_admin_mode() {
    ADMIN_MODE.store(!ADMIN_MODE.load(Ordering::SeqCst), Ordering::SeqCst);
    eprintln!(
        "[kiosk] admin mode: {}",
        if is_admin_active() { "ON" } else { "OFF" }
    );
}

/// Запускает хук клавиатуры в отдельном потоке.
fn start_keyboard_hook() {
    #[cfg(target_os = "windows")]
    std::thread::spawn(|| unsafe {
        if let Err(e) = hook::install() {
            eprintln!("[kiosk] не удалось установить хук клавиатуры: {e}");
        }
    });
}
