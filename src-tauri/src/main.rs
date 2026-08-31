// Предотвращает открытие лишнего окна консоли в Windows при запуске .exe.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    school_kiosk_lib::run()
}
