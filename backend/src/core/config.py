import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings

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


class Settings(BaseSettings):
    model_config = {"env_prefix": "BACKEND_"}

    app_name: str = "School Kiosk API"
    app_description: str = "API backend for School Kiosk"
    app_version: str = "0.1.0"

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

    @property
    def data_dir(self) -> Path:
        """Каталог данных (вычисляется каждый раз — дёшево и позволяет env)."""
        return _resolve_data_dir()

    @property
    def static_dir(self) -> Path:
        """Каталог статики (загруженные изображения).

        Переопределяется переменной окружения `SCHOOL_KIOSK_STATIC_DIR` —
        её задаёт Rust-оболочка Tauri из файла настроек (см. src-tauri/src/settings.rs).
        Если не задана — используется каталог загрузок внутри каталога данных.
        """
        env = os.environ.get("SCHOOL_KIOSK_STATIC_DIR")
        if env:
            return Path(env).expanduser()
        return self.data_dir / "uploads"

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
    def upload_dir(self) -> Path:
        """Каталог, из которого раздаётся статика (`upload_url`)."""
        return self.static_dir

    @property
    def database_url(self) -> str:
        """SQLite-файл лежит внутри каталога данных, а не рядом с кодом."""
        db_path = self.data_dir / "school_kiosk.db"
        return f"sqlite+aiosqlite:///{db_path.as_posix()}"


settings = Settings()
