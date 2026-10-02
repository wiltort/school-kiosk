"""Юнит-тесты для конфигурации приложения."""

import tomllib

from src.core.config import BASE_DIR, Settings, _read_app_version


def test_settings_defaults():
    """Проверка правильности установленных настроек."""
    settings = Settings()
    assert settings.app_name == "School Kiosk API"
    assert settings.app_version
    assert settings.debug is False
    assert settings.api_prefix == "/api/v1"
    assert settings.server_host == "0.0.0.0"  # noqa: S104 — test value, not binding
    assert settings.server_port == 8765


def test_base_dir_resolved():
    """Проверка правильности установки BASE_DIR и наличия файлов проекта."""
    assert (BASE_DIR / "pyproject.toml").exists()
    assert (BASE_DIR / "src").exists()
    assert (BASE_DIR / "tests").exists()


def test_read_app_version_from_pyproject():
    """В dev-режиме версия читается из pyproject.toml репозитория."""
    data = tomllib.loads((BASE_DIR / "pyproject.toml").read_text(encoding="utf-8"))
    assert _read_app_version() == data["project"]["version"]


def test_read_app_version_fallback_without_pyproject(monkeypatch, tmp_path):
    """Регрессия: frozen-бандл без pyproject.toml возвращает 0.0.0, а не None."""
    monkeypatch.setattr("src.core.config._resource_dir", lambda: tmp_path)
    assert _read_app_version() == "0.0.0"


def test_read_app_version_from_bundled_pyproject(monkeypatch, tmp_path):
    """Версия из pyproject.toml, упакованного через --add-data (sys._MEIPASS)."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nversion = "4.5.6"\n', encoding="utf-8"
    )
    monkeypatch.setattr("src.core.config._resource_dir", lambda: tmp_path)
    assert _read_app_version() == "4.5.6"


def test_static_dir_defaults_under_data_dir(monkeypatch, tmp_path):
    """По умолчанию статика лежит внутри каталога данных (`data/uploads`)."""
    monkeypatch.delenv("SCHOOL_KIOSK_STATIC_DIR", raising=False)
    # Изолируем data_dir во временный каталог, чтобы локальный файл
    # `backend/.tmp-data/settings.json` (созданный локальным запуском) не влиял.
    monkeypatch.setenv("SCHOOL_KIOSK_DATA_DIR", str(tmp_path))
    settings = Settings()
    assert settings.static_dir == tmp_path / "uploads"


def test_static_dir_from_env(monkeypatch, tmp_path):
    """Переменная SCHOOL_KIOSK_STATIC_DIR переопределяет каталог статики."""
    target = tmp_path / "kiosk-static"
    # Изолируем data_dir, чтобы локальный settings.json не влиял на приоритет:
    # без файла настроек значение берётся из env.
    monkeypatch.setenv("SCHOOL_KIOSK_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SCHOOL_KIOSK_STATIC_DIR", str(target))
    settings = Settings()
    assert settings.static_dir == target
