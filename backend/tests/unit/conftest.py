"""Фикстуры для юнит-тестов."""

from pathlib import Path

import pytest
from src.core.config import runtime_paths


@pytest.fixture(autouse=True)
def _reset_runtime_paths():
    """Сбрасывает пути, загруженные из БД в lifespan, между тестами."""
    runtime_paths.static_dir = None
    runtime_paths.local_image_dir = None
    yield
    runtime_paths.static_dir = None
    runtime_paths.local_image_dir = None


@pytest.fixture(autouse=True)
def _isolate_legacy_settings(monkeypatch):
    """Изолирует юнит-тесты от реального legacy-файла настроек Tauri
    (`%APPDATA%\\com.schoolkiosk.app\\settings.json`).

    При локальном запуске бэкенда этот файл создаётся/наполняется и содержит
    реальный ``static_dir`` пользователя. Поскольку тесты конфигурации
    изолируют только каталог данных (``SCHOOL_KIOSK_DATA_DIR``), но не
    legacy-файл, миграция в ``AppSettingsStore._load()`` переносит его
    ``static_dir`` во временные каталоги данных и ломает ожидаемые значения.
    Указываем несуществующий путь, чтобы миграция не срабатывала.
    """
    monkeypatch.setenv(
        "SCHOOL_KIOSK_LEGACY_SETTINGS_FILE",
        str(Path("__no_legacy_settings__") / "settings.json"),
    )
