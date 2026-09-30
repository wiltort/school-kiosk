import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings

from src.core.app_settings import AppSettingsStore
from src.enums.schedule_modes import ScheduleMode

BASE_DIR = Path(__file__).resolve().parents[2]


def _resolve_data_dir() -> Path:
    r"""Каталог данных приложения (БД, загрузки изображений).

    Приоритет определения:
      1. Переменная окружения `SCHOOL_KIOSK_DATA_DIR` — её задаёт Rust-оболочка
         в продакшене (каталог данных приложения Tauri, например
         `%LOCALAPPDATA%\com.schoolkiosk.app`).
      2. Если процесс запущен из PyInstaller (`sys.frozen`) — `%LOCALAPPDATA%`
         (фолбэк на случай, если env не передали).
      3. В dev-режиме — `backend/data`.
    """
    env = os.environ.get("SCHOOL_KIOSK_DATA_DIR")
    if env:
        return Path(env).expanduser()
    if getattr(sys, "frozen", False):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "SchoolKiosk"
    return BASE_DIR / "data"


def _resolve_legacy_settings_file() -> Path | None:
    """Путь к legacy-файлу настроек Tauri (seed от установщика).

    Используется только для миграции ``static_dir`` при первом запуске,
    пока у бэкенда нет своего файла настроек. Переопределяется переменной
    окружения `SCHOOL_KIOSK_LEGACY_SETTINGS_FILE` (её задаёт Rust-оболочка,
    а также удобно задавать в тестах).
    """
    env = os.environ.get("SCHOOL_KIOSK_LEGACY_SETTINGS_FILE")
    if env:
        return Path(env).expanduser()
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "com.schoolkiosk.app" / "settings.json"
    return None


def _resource_dir() -> Path:
    """Каталог ресурсов приложения (``pyproject.toml`` и т. п.).

    В PyInstaller-сборке данные, добавленные через ``--add-data``, распаковываются
    в ``sys._MEIPASS``; в dev-режиме это корень пакета backend (``BASE_DIR``).
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", BASE_DIR))
    return BASE_DIR


def _read_app_version() -> str:
    """Версия приложения из ``pyproject.toml``; ``0.0.0``, если её нет.

    Никогда не возвращает ``None``: в frozen-сборке pyproject.toml может
    отсутствовать в бандле, и ``None`` сломал бы pydantic-валидацию Settings.
    """
    try:
        import tomllib

        pyproject = _resource_dir() / "pyproject.toml"
        if pyproject.is_file():
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            version = data["project"]["version"]
            if isinstance(version, str) and version:
                return version
    except OSError, KeyError, tomllib.TOMLDecodeError:
        pass
    return "0.0.0"


class Settings(BaseSettings):
    model_config = {"env_prefix": "BACKEND_"}

    app_name: str = "School Kiosk API"
    app_description: str = "API backend for School Kiosk"
    app_version: str = _read_app_version()

    debug: bool = False
    log_level: str = "INFO"
    log_format: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    api_prefix: str = "/api/v1"

    server_host: str = "0.0.0.0"  # noqa: S104 — dev сервер; в проде Rust передаёт 127.0.0.1
    server_port: int = 8765

    db_echo: bool = False

    default_admin_login: str = "admin"
    default_admin_password: str = "admin"  # noqa: S105

    upload_url: str = "/uploads"
    max_image_size: int = 10 * 1024 * 1024

    cron_enabled: bool = True

    @property
    def data_dir(self) -> Path:
        """Каталог данных."""
        return _resolve_data_dir()

    @property
    def app_settings(self) -> AppSettingsStore:
        """Хранилище настроек приложения (settings.json в каталоге данных)."""
        return AppSettingsStore(self.data_dir, _resolve_legacy_settings_file())

    @property
    def static_dir(self) -> Path:
        """Каталог статики (загруженные изображения).

        Приоритет:
          1. Настройки приложения (settings.json в каталоге данных) — основной
             источник, им управляет админ-панель;
          2. Переменная окружения `SCHOOL_KIOSK_STATIC_DIR` (legacy, для
             обратной совместимости);
          3. Каталог загрузок внутри каталога данных (`<data_dir>/uploads`).
        """
        stored = self.app_settings.static_dir()
        if stored:
            return Path(stored).expanduser()
        env = os.environ.get("SCHOOL_KIOSK_STATIC_DIR")
        if env:
            return Path(env).expanduser()
        return self.data_dir / "uploads"

    @property
    def local_image_dir(self) -> Path:
        """Каталог локальных изображений (загруженные изображения).

        Приоритет:
          1. Настройки приложения (settings.json в каталоге данных) — основной
             источник, им управляет админ-панель;
          2. Переменная окружения `SCHOOL_KIOSK_LOCAL_IMAGE_DIR` (legacy, для
             обратной совместимости);
           3. Каталог загрузок внутри каталога данных (`<data_dir>/uploads`).
        """
        stored = self.app_settings.local_image_dir()
        if stored:
            return Path(stored).expanduser()
        env = os.environ.get("SCHOOL_KIOSK_LOCAL_IMAGE_DIR")
        if env:
            return Path(env).expanduser()
        return self.data_dir / "local_images"

    @property
    def current_local_schedule_image_filename(self) -> str:
        """Имя текущего локального изображения расписания."""
        stored = self.app_settings.current_local_schedule_image_filename()
        if stored:
            return stored
        env = os.environ.get("SCHOOL_KIOSK_CURRENT_LOCAL_SCHEDULE_IMAGE_FILENAME")
        if env:
            return env
        return "current_schedule.jpg"

    @property
    def schedule_mode(self) -> ScheduleMode:
        """Режим отображения расписания."""
        stored = self.app_settings.schedule_mode()
        if stored:
            return ScheduleMode(stored)
        env = os.environ.get("SCHOOL_KIOSK_SCHEDULE_MODE")
        if env:
            return ScheduleMode(env)
        return ScheduleMode.SINGLE

    @property
    def frontend_dir(self) -> Path:
        """Каталог собранного фронтенда (SPA), который раздаётся по HTTP.

        Переопределяется переменной окружения `SCHOOL_KIOSK_FRONTEND_DIR` —
        её задаёт Rust-оболочка Tauri в продакшене (каталог `web/dist`
        рядом с `kiosk.exe`). Если не задана — используется `frontend/dist`
        в корне репозитория (dev-режим).
        """
        env = os.environ.get("SCHOOL_KIOSK_FRONTEND_DIR")
        if env:
            return Path(env).expanduser()
        return BASE_DIR.parent / "frontend" / "dist"

    @property
    def database_url(self) -> str:
        """SQLite-файл лежит внутри каталога данных, а не рядом с кодом.

        Создаём каталог данных, если его ещё нет (например, в чистом CI-чекауте,
        где ``data/`` игнорируется git): иначе SQLite не сможет открыть файл БД.
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)
        db_path = self.data_dir / "school_kiosk.db"
        return f"sqlite+aiosqlite:///{db_path.as_posix()}"


settings = Settings()
