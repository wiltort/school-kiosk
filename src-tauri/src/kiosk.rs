//! Киоск-режим (Windows API).
//!
//! Реализует функционал, аналогичный старой C#-версии:
//!   - полноэкранное окно поверх всех окон (topmost);
//!   - скрытие курсора при бездействии;
//!   - блокировка системных клавиш через низкоуровневый хук клавиатуры;
//!   - переключение в админ-режим по комбинации Ctrl+Shift+A (с уведомлением
//!     фронтенда через событие `admin-mode` — опрос через IPC остаётся
//!     резервным механизмом);
//!   - выход из киоска по Ctrl+Alt+X, когда фронтенд разрешил выход
//!     (пользователь вошёл в админку — см. команду `set_exit_allowed`).

use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::OnceLock;

use tauri::{App, AppHandle, Emitter, Manager, WebviewWindow};

/// Активен ли сейчас админ-режим (глобальный флаг для IPC из admin.rs).
static ADMIN_MODE: AtomicBool = AtomicBool::new(false);

/// Разрешён ли выход из киоска (Ctrl+Alt+X). Фронтенд ставит `true` после
/// успешного входа в админку и снимает при выходе из неё.
static EXIT_ALLOWED: AtomicBool = AtomicBool::new(false);

/// Хэндл приложения — нужен хук-потоку для эмитта событий и выхода.
static APP_HANDLE: OnceLock<AppHandle> = OnceLock::new();

/// Комбинация для входа в админ-режим.
const ADMIN_SHORTCUT: (&str, &str) = ("Ctrl", "Shift+A");
/// Комбинация для выхода из киоска (только когда фронтенд разрешил выход).
const EXIT_SHORTCUT: &str = "Ctrl+Alt+X";

/// Возвращает, активен ли админ-режим.
pub fn is_admin_active() -> bool {
    ADMIN_MODE.load(Ordering::SeqCst)
}

/// Разрешён ли выход из киоска (Ctrl+Alt+X).
pub fn exit_allowed() -> bool {
    EXIT_ALLOWED.load(Ordering::SeqCst)
}

/// Разрешает/запрещает выход из киоска (вызывается из admin.rs).
pub fn set_exit_allowed(allowed: bool) {
    EXIT_ALLOWED.store(allowed, Ordering::SeqCst);
    eprintln!(
        "[kiosk] exit (Ctrl+Alt+X): {}",
        if allowed {
            "разрешён"
        } else {
            "запрещён"
        }
    );
}

/// Выход из приложения (для хук-потока; в хук-потоке нет AppHandle).
pub fn request_exit() {
    if let Some(app) = APP_HANDLE.get() {
        app.exit(0);
    }
}

/// Включает киоск-режим: fullscreen, topmost, скрытие курсора и хук клавиш.
pub fn activate(app: &App) -> Result<(), Box<dyn std::error::Error>> {
    let window = app
        .get_webview_window("main")
        .ok_or("окно 'main' не найдено")?;

    // Сохраняем хэндл для эмитта событий и выхода из хук-потока.
    let _ = APP_HANDLE.set(app.handle().clone());

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
// Важные детали реализации:
//   - состояние модификаторов (Ctrl/Shift/Alt) читается через
//     GetAsyncKeyState: GetKeyState в потоке LL-хука отражает только очередь
//     сообщений самого потока и всегда возвращает «не нажато»;
//   - системные комбинации (Alt+F4, Alt+Tab) приходят как WM_SYSKEYDOWN,
//     поэтому блокируются и WM_KEYDOWN (0x0100), и WM_SYSKEYDOWN (0x0104);
//   - автоповтор и «дребезг» Ctrl+Shift+A гасятся минимальным интервалом
//     между переключениями (см. toggle_admin_mode_throttled);
//   - помимо LL-хука Ctrl+Shift+A регистрируется через RegisterHotKey как
//     резервный путь: если ОС перестала доставлять события в LL-хук
//     (LowLevelHooksTimeout и т.п.), горячая клавиша продолжает работать.
//
// Ctrl+Alt+Del блокируется ОС Windows на уровне системы и из user-space
// перехватить нельзя; для киоска его обычно закрывают политикой/групповой
// политикой.

#[cfg(target_os = "windows")]
mod hook {
    use std::ffi::c_void;
    use std::sync::atomic::{AtomicUsize, Ordering};

    use windows::Win32::Foundation::{LPARAM, LRESULT, WPARAM};
    use windows::Win32::UI::Input::KeyboardAndMouse::{
        GetAsyncKeyState, RegisterHotKey, MOD_ALT, MOD_CONTROL, MOD_SHIFT,
    };
    use windows::Win32::UI::WindowsAndMessaging::{
        CallNextHookEx, DispatchMessageW, GetMessageW, SetWindowsHookExW, TranslateMessage, HHOOK,
        KBDLLHOOKSTRUCT, MSG, WH_KEYBOARD_LL, WM_HOTKEY,
    };

    /// Сообщение о нажатии клавиши (WM_KEYDOWN).
    const WM_KEYDOWN: u32 = 0x0100;
    /// Сообщение о нажатии системной клавиши (WM_SYSKEYDOWN): Alt+F4, Alt+Tab и т.п.
    const WM_SYSKEYDOWN: u32 = 0x0104;
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
    const VK_X: i32 = 0x58;

    /// Дескриптор установленного хука (нужен для CallNextHookEx).
    ///
    /// Хранится как `usize`, т.к. `HHOOK` (сырой указатель) не реализует
    /// `Send`/`Sync` и не может лежать в статике напрямую.
    static HOOK: AtomicUsize = AtomicUsize::new(0);

    /// Идентификатор резервной горячей клавиши Ctrl+Shift+A (RegisterHotKey).
    const HOTKEY_ID: i32 = 1;
    /// Идентификатор горячей клавиши выхода Ctrl+Alt+X (RegisterHotKey).
    const EXIT_HOTKEY_ID: i32 = 2;

    pub unsafe fn install() -> Result<(), windows::core::Error> {
        let hook = SetWindowsHookExW(WH_KEYBOARD_LL, Some(hook_proc), None, 0)?;
        HOOK.store(hook.0 as usize, Ordering::SeqCst);
        eprintln!("[kiosk] LL-хук клавиатуры установлен");

        // Резервный путь для Ctrl+Shift+A. Если LL-хук по какой-то причине не
        // получает события (LowLevelHooksTimeout, особенности окружения),
        // горячая клавиша от RegisterHotKey продолжает срабатывать: она живёт
        // на уровне системы, а не в цепочке хуков. Когда хук работает, он
        // гасит нажатие «A» (return 1) — и WM_HOTKEY не генерируется, т.е.
        // двойного переключения не будет.
        match RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_SHIFT, VK_A as u32) {
            Ok(()) => {
                eprintln!("[kiosk] резервная горячая клавиша Ctrl+Shift+A зарегистрирована")
            }
            Err(e) => eprintln!("[kiosk] RegisterHotKey(Ctrl+Shift+A) не удался: {e}"),
        }

        // Выход из киоска: RegisterHotKey — основной путь для Ctrl+Alt+X,
        // т.к. клавиша «X» хуком не гасится и доходит до системы. Срабатывает
        // только когда фронтенд разрешил выход (set_exit_allowed).
        match RegisterHotKey(None, EXIT_HOTKEY_ID, MOD_CONTROL | MOD_ALT, VK_X as u32) {
            Ok(()) => eprintln!("[kiosk] горячая клавиша выхода Ctrl+Alt+X зарегистрирована"),
            Err(e) => eprintln!("[kiosk] RegisterHotKey(Ctrl+Alt+X) не удался: {e}"),
        }

        // Поток обязан держать цикл сообщений, иначе низкоуровневый хук
        // не будет получать события. Здесь же обрабатываются WM_HOTKEY
        // от резервных горячих клавиш.
        let mut msg = MSG::default();
        loop {
            let ret = GetMessageW(&mut msg, None, 0, 0);
            // 0 — WM_QUIT, -1 — ошибка: в обоих случаях завершаем поток.
            if ret.0 <= 0 {
                break;
            }
            if msg.message == WM_HOTKEY {
                match msg.wParam.0 as i32 {
                    HOTKEY_ID => super::toggle_admin_mode_throttled(),
                    EXIT_HOTKEY_ID if super::exit_allowed() => {
                        eprintln!("[kiosk] выход по Ctrl+Alt+X");
                        super::request_exit();
                    }
                    _ => {}
                }
                continue;
            }
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
                let is_down = msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN;

                if is_down {
                    let vk = key.vkCode as i32;

                    // Вход/выход из админ-режима: Ctrl+Shift+A.
                    if vk == VK_A && is_pressed(VK_CTRL) && is_pressed(VK_SHIFT) {
                        // Гашение автоповтора зажатой «A» — внутри
                        // toggle_admin_mode_throttled.
                        super::toggle_admin_mode_throttled();
                        return LRESULT(1);
                    }

                    // Выход из киоска: Ctrl+Alt+X (только если фронтенд
                    // разрешил выход — см. set_exit_allowed). Дублирует
                    // RegisterHotKey: работает, даже если до WM_HOTKEY дело
                    // не дошло. Клавиша гасится, чтобы «X» не «протекла».
                    if vk == VK_X
                        && is_pressed(VK_CTRL)
                        && is_pressed(VK_ALT)
                        && super::exit_allowed()
                    {
                        eprintln!("[kiosk] выход по Ctrl+Alt+X");
                        super::request_exit();
                        return LRESULT(1);
                    }

                    // Блокируем системные клавиши, чтобы не выйти из киоска.
                    // Alt+F4 и Alt+Tab приходят как WM_SYSKEYDOWN — потому
                    // блокируем и его (is_down учитывает оба сообщения).
                    if is_blocked(vk, is_pressed(VK_ALT)) {
                        return LRESULT(1);
                    }
                }
            }
        }
        let hhk = HHOOK(HOOK.load(Ordering::SeqCst) as *mut c_void);
        unsafe { CallNextHookEx(hhk, code, wparam, lparam) }
    }

    /// Нажата ли клавиша в данный момент (старший бит состояния).
    ///
    /// Именно GetAsyncKeyState: GetKeyState в потоке LL-хука отражает
    /// синхронизированное состояние очереди сообщений самого потока (хук-поток
    /// не получает клавиатурных сообщений) и всегда выдаёт «не нажато».
    fn is_pressed(vk: i32) -> bool {
        unsafe { GetAsyncKeyState(vk) as u16 & 0x8000 != 0 }
    }

    /// Заблокированные комбинации (не должны работать в киоске).
    fn is_blocked(vk: i32, alt: bool) -> bool {
        matches!(vk, VK_ESC | VK_LWIN | VK_RWIN) || (alt && matches!(vk, VK_TAB | VK_F4))
    }
}

/// Время последнего переключения админ-режима (unix ms) — гасит автоповтор
/// и «дребезг» Ctrl+Shift+A для обоих путей срабатывания (LL-хук и
/// резервный RegisterHotKey).
static LAST_TOGGLE_MS: AtomicU64 = AtomicU64::new(0);

/// Минимальный интервал между переключениями админ-режима, мс.
/// Автоповтор клавиатуры шлёт keydown каждые ~30 мс, поэтому 500 мс
/// надёжно гасят повторы, но не мешают сознательному двойному нажатию.
const TOGGLE_DEBOUNCE_MS: u64 = 500;

/// Переключает админ-режим с защитой от автоповтора.
fn toggle_admin_mode_throttled() {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0);
    let last = LAST_TOGGLE_MS.load(Ordering::SeqCst);
    if now.saturating_sub(last) < TOGGLE_DEBOUNCE_MS {
        return;
    }
    LAST_TOGGLE_MS.store(now, Ordering::SeqCst);
    toggle_admin_mode();
}

/// Переключает админ-режим (флаг для IPC из admin.rs).
///
/// Помимо установки флага эмиттит в WebView событие `admin-mode` с текущим
/// состоянием: фронтенд реагирует мгновенно, опрос `is_admin_active` остаётся
/// как резервный механизм.
fn toggle_admin_mode() {
    ADMIN_MODE.store(!ADMIN_MODE.load(Ordering::SeqCst), Ordering::SeqCst);
    eprintln!(
        "[kiosk] admin mode: {}",
        if is_admin_active() { "ON" } else { "OFF" }
    );
    if let Some(app) = APP_HANDLE.get() {
        if let Err(e) = app.emit("admin-mode", is_admin_active()) {
            eprintln!("[kiosk] не удалось отправить событие admin-mode: {e}");
        }
    }
}

/// Сбрасывает админ-режим (флаг для IPC из admin.rs).
///
/// Фронтенд вызывает команду `clear_admin_mode` после того, как отреагировал
/// на горячую клавишу, чтобы один нажатый Ctrl+Shift+A не открывал форму
/// входа повторно (например, после выхода из админки).
pub fn clear_admin_mode() {
    ADMIN_MODE.store(false, Ordering::SeqCst);
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
