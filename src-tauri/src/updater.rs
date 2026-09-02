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

use tauri::AppHandle;
use tauri_plugin_updater::UpdaterExt;

/// Ветка репозитория, в которую CI публикует фиды `latest.json`.
const FEED_BRANCH: &str = "update-feed";

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

/// Запускает фоновую проверку обновлений и их тихую установку.
///
/// Вызывается один раз при старте релизной сборки. Если найдена более новая
/// версия, она скачивается и устанавливается без диалогов; на Windows после
/// установки приложение автоматически завершается, а при следующем запуске
/// работает уже новая версия. Любые ошибки (сеть, подпись, нет фида) не
/// блокируют обычный запуск — они только логируются.
pub fn spawn_auto_update(app: AppHandle) {
    // Запускаем задачу и не ждём её: она живёт отдельно от окна.
    std::mem::drop(tauri::async_runtime::spawn(async move {
        if let Err(e) = auto_update(&app).await {
            eprintln!("[updater] {e}");
        }
    }));
}

/// Проверяет наличие обновления в канале текущей сборки и устанавливает его.
async fn auto_update(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let url: url::Url = endpoint().parse()?;

    let update = app
        .updater_builder()
        .endpoints(vec![url])?
        .build()?
        .check()
        .await?;

    let Some(update) = update else {
        // Обновлений нет — продолжаем обычный запуск.
        return Ok(());
    };

    eprintln!(
        "[updater] найдено обновление {} (текущая {})",
        update.version, update.current_version
    );
    update
        .download_and_install(
            |chunk_length, content_length| {
                eprintln!("[updater] скачано {chunk_length} из {content_length:?}");
            },
            || {
                eprintln!("[updater] скачивание завершено, устанавливаю...");
            },
        )
        .await?;
    Ok(())
}
