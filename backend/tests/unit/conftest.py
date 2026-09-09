"""Фикстуры для юнит-тестов."""

from pathlib import Path

import pytest


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
