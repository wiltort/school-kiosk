//! Управление Python-бэкендом как child process.
//!
//! Приложение запускает FastAPI-бэкенд и следит за его жизненным циклом:
//! при закрытии Tauri бэкенд тоже должен остановиться.

use std::io;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use tauri::AppHandle;

use crate::{BACKEND_PORT, HEALTH_URL};

/// Сколько ждать готовности бэкенда при старте.
const STARTUP_TIMEOUT: Duration = Duration::from_secs(30);
/// Интервал между health-check запросами.
const POLL_INTERVAL: Duration = Duration::from_millis(300);

/// Обёртка над дочерним процессом Python-бэкенда.
pub struct BackendProcess {
    child: Child,
}

impl BackendProcess {
    /// Спавнит бэкенд в фоне и блокирует поток до тех пор, пока тот не ответит
    /// на health-check (или не истечёт таймаут).
    pub fn spawn_and_wait(_app: &AppHandle) -> io::Result<Self> {
        let child = spawn_backend()?;
        let mut proc = Self { child };

        let deadline = Instant::now() + STARTUP_TIMEOUT;
        while Instant::now() < deadline {
            if is_backend_ready() {
                return Ok(proc);
            }
            thread::sleep(POLL_INTERVAL);
        }

        // Таймаут — останавливаем бэкенд и сообщаем об ошибке.
        let _ = proc.child.kill();
        Err(io::Error::new(
            io::ErrorKind::TimedOut,
            format!("Python backend не ответил на {HEALTH_URL} за {STARTUP_TIMEOUT:?}"),
        ))
    }

    /// Останавливает дочерний процесс (вызывается при выходе).
    pub fn shutdown(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

impl Drop for BackendProcess {
    fn drop(&mut self) {
        self.shutdown();
    }
}

/// Запускает Python-бэкенд.
///
/// В dev-режиме бэкенд запускается через Poetry из папки `backend/`:
/// `poetry run uvicorn src.main:app --host 127.0.0.1 --port 8765`.
///
/// В продакшене здесь будет запускаться собранный `python-backend.exe`
/// (PyInstaller), который Tauri кладёт рядом с `kiosk.exe`.
fn spawn_backend() -> io::Result<Child> {
    let backend_dir = backend_dir();

    // Позволяет переопределить команду запуска через переменную окружения,
    // например для тестов: SCHOOL_KIOSK_BACKEND_CMD="python -m uvicorn src.main:app".
    let mut cmd = Command::new(backend_command());

    if !backend_command_override() {
        // default (dev через Poetry)
        cmd.current_dir(&backend_dir).args([
            "run",
            "uvicorn",
            "src.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            &BACKEND_PORT.to_string(),
        ]);
    } else {
        // user-переопределённая команда (аргументы уже в строке)
        cmd.args(backend_args());
    }

    cmd.stdout(Stdio::piped()).stderr(Stdio::piped()).spawn()
}

/// Путь к папке бэкенда (корень репозитория + `backend`).
fn backend_dir() -> PathBuf {
    std::env::var_os("SCHOOL_KIOSK_BACKEND_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../backend"))
}

/// Имя исполняемого файла: `poetry` по умолчанию, либо из env.
fn backend_command() -> String {
    std::env::var("SCHOOL_KIOSK_BACKEND_CMD").unwrap_or_else(|_| "poetry".into())
}

fn backend_command_override() -> bool {
    std::env::var("SCHOOL_KIOSK_BACKEND_CMD").is_ok()
}

fn backend_args() -> Vec<String> {
    // Для простоты берём команду из env целиком как один аргумент.
    std::env::var("SCHOOL_KIOSK_BACKEND_CMD")
        .map(|s| vec![s])
        .unwrap_or_default()
}

/// Пинг бэкенда через TCP connect (быстрый health-check без HTTP-парсинга).
fn is_backend_ready() -> bool {
    use std::net::TcpStream;
    TcpStream::connect_timeout(
        &format!("127.0.0.1:{BACKEND_PORT}")
            .parse()
            .expect("valid socket addr"),
        Duration::from_millis(200),
    )
    .is_ok()
}
