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
    pub fn spawn_and_wait(app: &AppHandle) -> io::Result<Self> {
        let child = spawn_backend(app)?;
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
/// Приоритет:
///   1. Явное переопределение через `SCHOOL_KIOSK_BACKEND_CMD` (для тестов).
///   2. Dev (`debug_assertions`): через Poetry из папки `backend/`,
///      `poetry run uvicorn src.main:app --host 127.0.0.1 --port 8765`.
///   3. Release: собранный PyInstaller-ем `python-backend.exe`, лежащий рядом
///      с `kiosk.exe`.
fn spawn_backend(app: &AppHandle) -> io::Result<Child> {
    // Настройки приложения из файла (каталог статики и т.п.).
    let settings = crate::settings::load_for(app);

    // user-переопределённая команда (аргументы уже в строке)
    if backend_command_override() {
        let mut cmd = Command::new(backend_command());
        cmd.args(backend_args());
        return cmd.stdout(Stdio::piped()).stderr(Stdio::piped()).spawn();
    }

    #[cfg(debug_assertions)]
    {
        let mut cmd = Command::new("poetry");
        cmd.current_dir(backend_dir()).args([
            "run",
            "uvicorn",
            "src.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            &BACKEND_PORT.to_string(),
        ]);
        apply_static_dir_env(&mut cmd, &settings);
        cmd.stdout(Stdio::piped()).stderr(Stdio::piped()).spawn()
    }

    #[cfg(not(debug_assertions))]
    {
        spawn_packaged_backend(app, &settings)
    }
}

/// Прокидывает выбранный каталог статики в переменную окружения бэкенда
/// (`SCHOOL_KIOSK_STATIC_DIR`), если он задан в настройках.
fn apply_static_dir_env(cmd: &mut Command, settings: &crate::settings::AppSettings) {
    if let Some(dir) = settings.resolved_static_dir() {
        cmd.env("SCHOOL_KIOSK_STATIC_DIR", dir);
    }
}

/// Запускает standalone-бэкенд (`python-backend.exe` от PyInstaller),
/// который лежит рядом с `kiosk.exe`. Каталог данных и сетевые параметры
/// передаются через переменные окружения.
#[cfg(not(debug_assertions))]
fn spawn_packaged_backend(
    app: &AppHandle,
    settings: &crate::settings::AppSettings,
) -> io::Result<Child> {
    let exe_dir = std::env::current_exe()?
        .parent()
        .map(PathBuf::from)
        .ok_or_else(|| {
            io::Error::new(io::ErrorKind::NotFound, "нет каталога исполняемого файла")
        })?;

    let backend_exe = if cfg!(windows) {
        exe_dir.join("python-backend.exe")
    } else {
        exe_dir.join("python-backend")
    };

    let frontend_dir = exe_dir.join("web").join("dist");

    let mut cmd = Command::new(backend_exe);
    cmd.env("SCHOOL_KIOSK_DATA_DIR", data_dir(app))
        // Слушаем на всех интерфейсах, чтобы киоск был доступен по LAN.
        .env("BACKEND_SERVER_HOST", "0.0.0.0")
        .env("BACKEND_SERVER_PORT", BACKEND_PORT.to_string())
        .env("BACKEND_DEBUG", "false")
        // Каталог собранного SPA, который бэкенд раздаёт по HTTP (см. config.py).
        .env("SCHOOL_KIOSK_FRONTEND_DIR", &frontend_dir);
    apply_static_dir_env(&mut cmd, settings);
    cmd.stdout(Stdio::piped()).stderr(Stdio::piped()).spawn()
}

/// Каталог данных приложения (БД и загрузки изображений) — используется в
/// продакшене и передаётся бэкенду через `SCHOOL_KIOSK_DATA_DIR`.
#[cfg(not(debug_assertions))]
fn data_dir(app: &AppHandle) -> PathBuf {
    use tauri::Manager;
    app.path()
        .app_data_dir()
        .unwrap_or_else(|_| std::env::temp_dir().join("school-kiosk"))
}

/// Путь к папке бэкенда (корень репозитория + `backend`). Нужен только в dev,
/// где бэкенд запускается через Poetry; в release его заменяет packaged-бэкенд.
#[cfg(debug_assertions)]
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
