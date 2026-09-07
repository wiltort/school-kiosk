//! Автообновление приложения из своей ветки (канала).
//!
//! Канал (`dev` / `main`) запекается на этапе сборки через переменную окружения
//! `KIOSK_CHANNEL`, которую выставляет CI. Сборка из ветки `dev` всегда
//! обновляется только из канала `dev`, из `main` — из канала `main`.
//!
//! Для каждого канала CI публикует JSON-фид `latest.json` в отдельную ветку
//! репозитория `update-feed` по пути `<channel>/latest.json`, поэтому URL точки
//! входа стабилен. Установщик (NSIS) подписан minisign; публичный ключ зашит
//! в `tauri.conf.json`, и плагин отвергает неподписанные или подменённые
//! обновления.
//!
//! Проверка обновлений выполняется при старте и далее по расписанию. Ход работы
//! публикуется фронтенду через событие `update-status` (и доступен по запросу
//! через IPC-команду `get_update_status`), чтобы экран киоска мог показывать
//! актуальную версию, прогресс загрузки и ошибки.

use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_updater::UpdaterExt;

/// Ветка репозитория, в которую CI публикует фиды `latest.json`.
const FEED_BRANCH: &str = "update-feed";

/// Период повторной проверки обновлений, если первая не нашла ничего нового.
const CHECK_INTERVAL: Duration = Duration::from_secs(30 * 60);

/// Имя события, которое получает фронтенд для отображения статуса.
pub const STATUS_EVENT: &str = "update-status";

/// Фаза обновления, которую видит фронтенд.
#[derive(Clone, Copy, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum UpdatePhase {
    /// Идёт проверка наличия новой версии.
    Checking,
    /// Новая версия найдена, файл скачивается.
    Downloading,
    /// Обновление установлено, приложение перезапускается.
    Installing,
    /// Обновлений нет, приложение актуально.
    UpToDate,
    /// Произошла ошибка (сеть, подпись, нет фида и т.п.).
    Error,
}

/// Текущий статус обновления, публикуемый фронтенду.
#[derive(Clone, Serialize)]
pub struct UpdateStatus {
    pub phase: UpdatePhase,
    pub current_version: String,
    pub latest_version: Option<String>,
    /// Скачано байт (только при `phase == Downloading`).
    pub downloaded: Option<u64>,
    /// Всего байт (только при `phase == Downloading`).
    pub total: Option<u64>,
    /// Человекочитаемое пояснение (например, текст ошибки).
    pub message: Option<String>,
}

/// Состояние обновления, доступное через `get_update_status`.
pub struct UpdaterState(pub Mutex<UpdateStatus>);

/// Канал обновления текущей сборки.
///
/// Задаётся на этапе сборки через `KIOSK_CHANNEL`. По умолчанию — `dev`.
pub fn channel() -> &'static str {
    option_env!("KIOSK_CHANNEL").unwrap_or("dev")
}

/// Включено ли автообновление в этой сборке.
///
/// Автообновление активно только если сборка выполнена под конкретный канал
/// (CI выставляет `KIOSK_CHANNEL`). Локальные релизные сборки без канала
/// автообновление не запускают.
pub fn is_enabled() -> bool {
    option_env!("KIOSK_CHANNEL").is_some()
}

/// Стабильный URL фида обновлений для текущего канала.
///
/// Репозиторий задаётся на этапе сборки через `KIOSK_REPO` (вид `owner/repo`),
/// который CI берёт из `github.repository`. Фид живёт в ветке `update-feed`.
fn endpoint() -> String {
    let repo = option_env!("KIOSK_REPO").unwrap_or("school-kiosk/school-kiosk");
    format!(
        "https://raw.githubusercontent.com/{repo}/{FEED_BRANCH}/{}/latest.json",
        channel()
    )
}

// ============================================================================
// Файловое логирование обновления
// ============================================================================

/// Имя файла лога обновления (внутри каталога данных приложения).
const LOG_FILE: &str = "update.log";

/// Каталог данных приложения, где хранится лог обновления.
fn data_dir(app: &AppHandle) -> PathBuf {
    use tauri::Manager;
    app.path()
        .app_data_dir()
        .unwrap_or_else(|_| std::env::temp_dir().join("school-kiosk"))
}

/// Полный путь к файлу лога обновления.
fn log_path(app: &AppHandle) -> PathBuf {
    data_dir(app).join("logs").join(LOG_FILE)
}

/// Текущее время в формате `%Y-%m-%d %H:%M:%S` (локальная зона).
fn timestamp_now() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    // Преобразуем эпоху в (год, месяц, день, час, мин, сек) по UTC.
    let days = secs / 86_400;
    let rem = secs % 86_400;
    let (h, m, s) = (rem / 3600, (rem % 3600) / 60, rem % 60);
    let (y, mo, d) = civil_from_days(days);
    format!("{y:04}-{mo:02}-{d:02} {h:02}:{m:02}:{s:02}")
}

/// Числа дней → календарная дата (алгоритм Говарда Хиннанта).
fn civil_from_days(z: u64) -> (i64, u32, u32) {
    let z = z as i64 + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}

/// Пишет строку в файл лога (создаёт каталог при необходимости) и дублирует
/// в stderr. Ошибки записи в файл игнорируются — они не должны ломать работу.
fn log_line(app: &AppHandle, level: &str, message: &str) {
    let line = format!("[{}] [{level}] {message}", timestamp_now());
    eprintln!("[updater] {message}");
    let path = log_path(app);
    if let Some(parent) = path.parent() {
        if let Err(e) = std::fs::create_dir_all(parent) {
            eprintln!(
                "[updater] не удалось создать каталог лога {}: {e}",
                parent.display()
            );
            return;
        }
    }
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(&path) {
        let _ = writeln!(f, "{line}");
    }
}

/// Начальный статус (до первого результата проверки).
pub fn initial_status(app: &AppHandle) -> UpdateStatus {
    UpdateStatus {
        phase: UpdatePhase::Checking,
        current_version: app.package_info().version.to_string(),
        latest_version: None,
        downloaded: None,
        total: None,
        message: Some("Проверка обновлений…".to_string()),
    }
}

/// Публикует новый статус: сохраняет его в состоянии и шлёт событие фронтенду.
fn set_status(app: &AppHandle, status: UpdateStatus) {
    if let Some(state) = app.try_state::<UpdaterState>() {
        if let Ok(mut guard) = state.0.lock() {
            *guard = status.clone();
        }
    }
    let _ = app.emit(STATUS_EVENT, &status);
}

/// Запускает фоновое автообновление: проверяет при старте, затем по расписанию.
///
/// Не блокирует обычный запуск приложения — работает в отдельной задаче.
pub fn spawn_auto_update(app: AppHandle) {
    log_line(
        &app,
        "INFO",
        &format!(
            "автообновление запущено: канал={}, фид={}",
            channel(),
            endpoint()
        ),
    );
    std::mem::drop(tauri::async_runtime::spawn(async move {
        // Первая проверка — сразу при старте.
        run_check(&app).await;
        // Дальше — повторяем по расписанию, пока приложение запущено.
        loop {
            tokio::time::sleep(CHECK_INTERVAL).await;
            run_check(&app).await;
        }
    }));
}

/// Выполняет один цикл проверки/установки и публикует статус фронтенду.
async fn run_check(app: &AppHandle) {
    if let Err(err) = check_once(app).await {
        let current = app.package_info().version.to_string();
        log_line(app, "ERROR", &format!("ошибка проверки обновления: {err}"));
        set_status(
            app,
            UpdateStatus {
                phase: UpdatePhase::Error,
                current_version: current,
                latest_version: None,
                downloaded: None,
                total: None,
                message: Some(err.to_string()),
            },
        );
        eprintln!("[updater] {err}");
    }
}

/// Проверяет наличие обновления в канале и при необходимости устанавливает его.
async fn check_once(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let current = app.package_info().version.to_string();

    set_status(
        app,
        UpdateStatus {
            phase: UpdatePhase::Checking,
            current_version: current.clone(),
            latest_version: None,
            downloaded: None,
            total: None,
            message: Some("Проверка обновлений…".to_string()),
        },
    );

    let url: url::Url = endpoint().parse()?;
    log_line(
        app,
        "INFO",
        &format!("запрос фида обновлений: GET {url} (текущая версия {current})"),
    );
    let update = app
        .updater_builder()
        .endpoints(vec![url])?
        .build()?
        .check()
        .await?;

    let Some(update) = update else {
        // Обновлений нет — приложение актуально.
        log_line(app, "INFO", "ответ фида: обновлений нет, версия актуальна");
        set_status(
            app,
            UpdateStatus {
                phase: UpdatePhase::UpToDate,
                current_version: current,
                latest_version: None,
                downloaded: None,
                total: None,
                message: None,
            },
        );
        return Ok(());
    };

    let latest = update.version.clone();
    log_line(
        app,
        "INFO",
        &format!("ответ фида: найдено обновление {latest} (текущая {current})"),
    );

    let app_dl = app.clone();
    let cur_dl = current.clone();
    let latest_dl = latest.clone();
    // Для лога прогресса логируем только каждый N-й вызов, чтобы не засорять файл.
    let last_logged = Arc::new(AtomicU64::new(0));
    let app_fin = app.clone();
    let cur_fin = current.clone();
    let latest_fin = latest.clone();

    update
        .download_and_install(
            move |downloaded, total| {
                let downloaded_u64 = downloaded as u64;
                // Логируем прогресс: каждые ~1 МБ или завершение.
                let step: u64 = 1024 * 1024;
                let bucket = downloaded_u64 / step;
                let prev = last_logged.load(Ordering::Relaxed);
                if bucket != prev || total.map(|t| t == downloaded_u64).unwrap_or(false) {
                    last_logged.store(bucket, Ordering::Relaxed);
                    let pct = total
                        .and_then(|t| (downloaded_u64.checked_mul(100))?.checked_div(t))
                        .unwrap_or(0);
                    log_line(
                        &app_dl,
                        "DEBUG",
                        &format!("загрузка {latest_dl}: {downloaded_u64}/{total:?} байт ({pct}%)"),
                    );
                }
                set_status(
                    &app_dl,
                    UpdateStatus {
                        phase: UpdatePhase::Downloading,
                        current_version: cur_dl.clone(),
                        latest_version: Some(latest_dl.clone()),
                        downloaded: Some(downloaded_u64),
                        total,
                        message: Some("Загрузка обновления…".to_string()),
                    },
                );
            },
            move || {
                log_line(
                    &app_fin,
                    "INFO",
                    &format!("скачивание завершено, устанавливаю {latest_fin}…"),
                );
                set_status(
                    &app_fin,
                    UpdateStatus {
                        phase: UpdatePhase::Installing,
                        current_version: cur_fin.clone(),
                        latest_version: Some(latest_fin.clone()),
                        downloaded: None,
                        total: None,
                        message: Some("Установка обновления…".to_string()),
                    },
                );
            },
        )
        .await?;

    // После успешной тихой установки NSIS сам перезапускает приложение —
    // здесь ничего дополнительно делать не нужно.
    log_line(
        app,
        "INFO",
        &format!("обновление {latest} успешно установлено"),
    );
    Ok(())
}

/// Возвращает текущий статус обновления (для запроса при загрузке страницы).
#[tauri::command]
pub fn get_update_status(app: AppHandle) -> UpdateStatus {
    match app.try_state::<UpdaterState>() {
        Some(state) => state
            .0
            .lock()
            .map(|guard| guard.clone())
            .unwrap_or_else(|_| initial_status(&app)),
        None => initial_status(&app),
    }
}
