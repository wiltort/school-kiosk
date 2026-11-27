//! Управление Python-бэкендом как child process.
//!
//! Приложение запускает FastAPI-бэкенд и следит за его жизненным циклом:
//! при закрытии Tauri бэкенд тоже должен остановиться.

use std::io;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager};

use crate::{BACKEND_PORT, HEALTH_URL};

/// Сколько ждать готовности бэкенда при старте.
const STARTUP_TIMEOUT: Duration = Duration::from_secs(60);
/// Интервал между health-check запросами.
const POLL_INTERVAL: Duration = Duration::from_millis(300);

/// Обёртка над дочерним процессом Python-бэкенда.
pub struct BackendProcess {
    child: Child,
    /// Windows Job Object, в который помещено всё дерево процессов бэкенда.
    ///
    /// С флагом `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` ОС убивает процессы job,
    /// как только закрывается последний хэндл job. Хэндл живёт в этом поле,
    /// поэтому его закрытие (в том числе автоматическое — при завершении
    /// `kiosk.exe` через `std::process::exit`, `TerminateProcess` или падение)
    /// гарантированно убивает бэкенд: сирот не остаётся даже на путях, где
    /// деструкторы Rust не выполняются.
    #[cfg(target_os = "windows")]
    job: Option<job::JobObject>,
    /// Защита от повторной остановки: `shutdown` вызывается из `RunEvent::Exit`,
    /// IPC-команд `exit_app`/`restart_app` и `Drop`.
    stopped: bool,
}

impl BackendProcess {
    /// Спавнит бэкенд в фоне и блокирует поток до тех пор, пока тот не ответит
    /// на health-check (или не истечёт таймаут).
    pub fn spawn_and_wait(app: &AppHandle) -> io::Result<Self> {
        // Порт уже занят — значит, живёт бэкенд от предыдущего запуска.
        // В dev на Windows poetry/uvicorn порождают цепочку процессов, и
        // `child.kill()` не завершает её целиком (см. `shutdown`). Без этой
        // проверки health-check ниже «успешно» ответит на старый процесс,
        // новый бэкенд упадёт с `address already in use`, а приложение будет
        // работать со старым кодом: свежие правки не применяются, запросов
        // нет в логах — то есть тихая рассинхронизация кода и рантайма.
        if is_port_busy(BACKEND_PORT) {
            return Err(io::Error::new(
                io::ErrorKind::AddrInUse,
                format!(
                    "порт {BACKEND_PORT} уже занят: вероятно, остался бэкенд от прошлого \
                     запуска. Остановите его (`make kill-backend`) и запустите приложение снова"
                ),
            ));
        }

        let child = spawn_backend(app)?;

        // Привязываем процесс (и всех его потомков) к Job Object сразу после
        // спавна. Дальше жизненный цикл бэкенда гарантирует сама ОС.
        #[cfg(target_os = "windows")]
        let job = match job::JobObject::create_and_assign(child.id()) {
            Ok(job) => {
                eprintln!(
                    "[backend] Job Object создан, pid={} привязан (kill-on-close)",
                    child.id()
                );
                Some(job)
            }
            Err(e) => {
                eprintln!(
                    "[backend] не удалось привязать pid={} к Job Object: {e}; \
                     останавливать будем через taskkill",
                    child.id()
                );
                None
            }
        };

        #[cfg(target_os = "windows")]
        let mut proc = Self {
            child,
            job,
            stopped: false,
        };
        #[cfg(not(target_os = "windows"))]
        let mut proc = Self {
            child,
            stopped: false,
        };

        let deadline = Instant::now() + STARTUP_TIMEOUT;
        while Instant::now() < deadline {
            if is_backend_ready() {
                return Ok(proc);
            }
            thread::sleep(POLL_INTERVAL);
        }

        // Таймаут — останавливаем бэкенд и сообщаем об ошибке.
        proc.shutdown();
        Err(io::Error::new(
            io::ErrorKind::TimedOut,
            format!("Python backend не ответил на {HEALTH_URL} за {STARTUP_TIMEOUT:?}"),
        ))
    }

    /// Останавливает дочерний процесс вместе с потомками (вызывается при выходе).
    ///
    /// На Windows dev-бэкенд запускается цепочкой `cmd -> uvicorn.exe ->
    /// python.exe`: `child.kill()` завершает только непосредственный процесс,
    /// а сервер остаётся сиротой и продолжает держать порт 8765. Поэтому на
    /// Windows завершаем всё дерево через `taskkill /T`.
    pub fn shutdown(&mut self) {
        if self.stopped {
            return;
        }
        self.stopped = true;

        let pid = self.child.id();
        eprintln!("[backend] shutdown: останавливаю дерево процессов pid={pid}");

        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;

            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            let status = Command::new("taskkill")
                .args(["/F", "/T", "/PID", &pid.to_string()])
                .creation_flags(CREATE_NO_WINDOW)
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .status();
            eprintln!("[backend] taskkill /F /T /PID {pid} -> {status:?}");

            // Закрываем хэндл Job Object: kill-on-close добьёт всё, что
            // осталось в дереве (например, потомков, переживших taskkill,
            // или отвязавшийся uvicorn).
            if let Some(job) = self.job.take() {
                drop(job);
                eprintln!("[backend] Job Object закрыт (потомки убиты ОС)");
            }
        }

        let _ = self.child.kill();
        let _ = self.child.wait();
        eprintln!("[backend] shutdown: завершено для pid={pid}");
    }
}

impl Drop for BackendProcess {
    fn drop(&mut self) {
        eprintln!(
            "[backend] Drop для BackendProcess вызван (pid={})",
            self.child.id()
        );
        self.shutdown();
    }
}

/// Останавливает бэкенд из managed-state приложения, если он ещё жив.
///
/// Нужен на путях выхода, где деструкторы Rust **не** выполняются: `tao`
/// завершает event-loop через `std::process::exit`, поэтому `Drop` для
/// [`BackendProcess`] не вызывается. Вызывается из `RunEvent::Exit` и из
/// IPC-команд `exit_app`/`restart_app`.
pub fn shutdown_backend(app: &AppHandle) {
    let Some(state) = app.try_state::<std::sync::Mutex<BackendProcess>>() else {
        return;
    };
    let mut backend = match state.inner().lock() {
        Ok(guard) => guard,
        // Мьютекс отравлен после паники: состояние всё равно доступно.
        Err(poisoned) => poisoned.into_inner(),
    };
    backend.shutdown();
}

/// Windows Job Object: привязка дерева процессов бэкенда к `kiosk.exe`.
#[cfg(target_os = "windows")]
mod job {
    use std::ffi::c_void;
    use std::io;

    use windows::core::PCWSTR;
    use windows::Win32::Foundation::{CloseHandle, HANDLE};
    use windows::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
        SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    };
    use windows::Win32::System::Threading::{OpenProcess, PROCESS_SET_QUOTA, PROCESS_TERMINATE};

    /// Хэндл job-объекта. Пока он открыт, ОС удерживает все процессы job;
    /// при закрытии (включая аварийное завершение `kiosk.exe`, когда ОС сама
    /// закрывает хэндлы) убивает их.
    ///
    /// Хэндл хранится как `usize`, т.к. `HANDLE` (сырой указатель) не реализует
    /// `Send`/`Sync`, а `BackendProcess` живёт в managed-state Tauri.
    pub struct JobObject(usize);

    impl JobObject {
        /// Создаёт job с `KILL_ON_JOB_CLOSE` и помещает в него процесс `pid`.
        pub fn create_and_assign(pid: u32) -> io::Result<Self> {
            unsafe {
                let job = CreateJobObjectW(None, PCWSTR::null()).map_err(to_io)?;

                let mut info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION::default();
                info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
                SetInformationJobObject(
                    job,
                    JobObjectExtendedLimitInformation,
                    &info as *const _ as *const c_void,
                    std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
                )
                .map_err(to_io)?;

                // PROCESS_SET_QUOTA обязателен для AssignProcessToJobObject.
                let process = OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, false, pid)
                    .map_err(to_io)?;
                let assigned = AssignProcessToJobObject(job, process);
                let _ = CloseHandle(process);
                assigned.map_err(to_io)?;

                Ok(Self(job.0 as usize))
            }
        }
    }

    impl Drop for JobObject {
        fn drop(&mut self) {
            unsafe {
                let _ = CloseHandle(HANDLE(self.0 as *mut c_void));
            }
        }
    }

    fn to_io(err: windows::core::Error) -> io::Error {
        io::Error::other(err.to_string())
    }
}

/// Вычитывает stdout/stderr дочернего процесса в фоновых потоках.
///
/// Без этого каналы (буфер ~64 КБ) рано или поздно переполняются, и бэкенд
/// блокируется на записи в stderr — выглядит как «зависший» процесс. Свой лог
/// Python-бэкенд пишет в файл (`<data_dir>/logs/backend.log`), сюда попадают
/// лишь остатки вывода (uvicorn и т.п.), поэтому строки просто выводим
/// в stderr оболочки.
fn drain_child_output(mut child: Child) -> Child {
    if let Some(reader) = child.stdout.take() {
        drain_pipe(reader, "stdout");
    }
    if let Some(reader) = child.stderr.take() {
        drain_pipe(reader, "stderr");
    }
    child
}

/// Читает переданный pipe до EOF в отдельном потоке.
fn drain_pipe<R: io::Read + Send + 'static>(reader: R, label: &'static str) {
    std::thread::spawn(move || {
        use std::io::{BufRead, BufReader};
        let mut lines = BufReader::new(reader).lines();
        while let Some(Ok(line)) = lines.next() {
            eprintln!("[backend:{label}] {line}");
        }
    });
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
    // user-переопределённая команда (аргументы уже в строке)
    if backend_command_override() {
        let mut cmd = Command::new(backend_command());
        cmd.args(backend_args());
        let child = cmd.stdout(Stdio::piped()).stderr(Stdio::piped()).spawn()?;
        return Ok(drain_child_output(child));
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
        apply_runtime_env(&mut cmd, app);
        let child = cmd.stdout(Stdio::piped()).stderr(Stdio::piped()).spawn()?;
        Ok(drain_child_output(child))
    }

    #[cfg(not(debug_assertions))]
    {
        spawn_packaged_backend(app)
    }
}

/// Прокидывает бэкенду переменные окружения, связанные с runtime-настройками.
///
/// Собственник настроек — бэкенд (`settings.json` в каталоге данных), поэтому
/// каталог статики сюда больше не передаётся. Здесь только:
///   - `SCHOOL_KIOSK_APP_EXE` — путь к `kiosk.exe` для автозагрузки (winreg);
///   - `SCHOOL_KIOSK_LEGACY_SETTINGS_FILE` — legacy-файл настроек Tauri,
///     из которого бэкенд на первом запуске переносит `static_dir` (seed).
fn apply_runtime_env(cmd: &mut Command, app: &AppHandle) {
    if let Ok(exe) = std::env::current_exe() {
        cmd.env("SCHOOL_KIOSK_APP_EXE", exe);
    }
    if let Some(legacy) = legacy_settings_file(app) {
        cmd.env("SCHOOL_KIOSK_LEGACY_SETTINGS_FILE", legacy);
    }
}

/// Путь к legacy-файлу настроек Tauri (`app_config_dir/settings.json`).
fn legacy_settings_file(app: &AppHandle) -> Option<PathBuf> {
    let cfg_dir = app.path().app_config_dir().ok()?;
    Some(crate::settings::settings_file_path(&cfg_dir))
}

/// Запускает standalone-бэкенд (`python-backend.exe` от PyInstaller),
/// который лежит рядом с `kiosk.exe`. Каталог данных и сетевые параметры
/// передаются через переменные окружения.
#[cfg(not(debug_assertions))]
fn spawn_packaged_backend(app: &AppHandle) -> io::Result<Child> {
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
    apply_runtime_env(&mut cmd, app);
    let child = cmd.stdout(Stdio::piped()).stderr(Stdio::piped()).spawn()?;
    Ok(drain_child_output(child))
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

/// Занят ли TCP-порт на loopback (например, бэкендом прошлого запуска).
fn is_port_busy(port: u16) -> bool {
    use std::net::TcpListener;

    TcpListener::bind(("127.0.0.1", port)).is_err()
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
