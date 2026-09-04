//! Legacy-настройки приложения (файл на диске).
//!
//! Собственник настроек — бэкенд (`settings.json` в каталоге данных, см.
//! backend/src/core/app_settings.py). Этот файл (`%APPDATA%\com.schoolkiosk.app
//! \settings.json`) теперь играет роль «seed»: установщик пишет сюда выбранный
//! каталог статики (см. windows/hooks.nsh), а бэкенд на первом запуске переносит
//! его в свой файл настроек. После этого Tauri этот файл не читает и не пишет.
//!
//! Путь можно переопределить переменной окружения `SCHOOL_KIOSK_SETTINGS_FILE`
//! (используется в тестах и для отладки).

use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager};

/// Схема файла настроек.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct AppSettings {
    /// Каталог статики (изображения расписания), который использует бэкенд.
    ///
    /// `None` означает «использовать значение по умолчанию»
    /// (`<data_dir>/uploads` на стороне Python-бэкенда).
    pub static_dir: Option<PathBuf>,
}

/// DTO для возврата настроек во фронтенд (админ-панель).
#[derive(Debug, Clone, Serialize)]
pub struct SettingsDto {
    pub static_dir: Option<String>,
}

impl From<&AppSettings> for SettingsDto {
    fn from(s: &AppSettings) -> Self {
        Self {
            static_dir: s
                .static_dir
                .as_ref()
                .map(|p| p.to_string_lossy().into_owned()),
        }
    }
}

impl AppSettings {
    /// Загружает настройки из файла. Если файла ещё нет — создаёт его со
    /// значениями по умолчанию и возвращает их.
    pub fn load(path: &Path) -> std::io::Result<Self> {
        if !path.exists() {
            let defaults = Self::default();
            if let Some(parent) = path.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::write(path, serde_json::to_string_pretty(&defaults)?)?;
            return Ok(defaults);
        }
        let raw = fs::read_to_string(path)?;
        Ok(serde_json::from_str(&raw).unwrap_or_default())
    }

    /// Сохраняет настройки в файл (создаёт родительские каталоги при необходимости).
    pub fn save(&self, path: &Path) -> std::io::Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::write(path, serde_json::to_string_pretty(self)?)
    }

    /// Резолвит каталог статики. Возвращает `None`, если пользователь не задал
    /// свой путь — тогда бэкенд использует значение по умолчанию.
    pub fn resolved_static_dir(&self) -> Option<PathBuf> {
        self.static_dir.clone()
    }
}

/// Возвращает путь к файлу настроек относительно каталога конфигурации
/// приложения. Учитывает переопределение через `SCHOOL_KIOSK_SETTINGS_FILE`.
pub fn settings_file_path(app_config_dir: &Path) -> PathBuf {
    std::env::var_os("SCHOOL_KIOSK_SETTINGS_FILE")
        .map(PathBuf::from)
        .unwrap_or_else(|| app_config_dir.join("settings.json"))
}

/// Загружает настройки для приложения, вычисляя каталог конфигурации Tauri.
pub fn load_for(app: &AppHandle) -> AppSettings {
    let cfg_dir = app
        .path()
        .app_config_dir()
        .unwrap_or_else(|_| std::env::temp_dir());
    let path = settings_file_path(&cfg_dir);
    AppSettings::load(&path).unwrap_or_default()
}

/// Сохраняет настройки для приложения.
pub fn save_for(app: &AppHandle, settings: &AppSettings) -> std::io::Result<()> {
    let cfg_dir = app
        .path()
        .app_config_dir()
        .unwrap_or_else(|_| std::env::temp_dir());
    let path = settings_file_path(&cfg_dir);
    settings.save(&path)
}
