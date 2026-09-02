"""Юнит-тесты для конфигурации приложения."""

from src.core.config import BASE_DIR, Settings


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


def test_upload_dir_defaults_under_data_dir(monkeypatch):
    """По умолчанию статика лежит внутри каталога данных (`data/uploads`)."""
    monkeypatch.delenv("SCHOOL_KIOSK_STATIC_DIR", raising=False)
    monkeypatch.setenv("SCHOOL_KIOSK_DATA_DIR", str(BASE_DIR / ".tmp-data"))
    settings = Settings()
    assert settings.static_dir == BASE_DIR / ".tmp-data" / "uploads"
    assert settings.upload_dir == settings.static_dir


def test_static_dir_from_env(monkeypatch, tmp_path):
    """Переменная SCHOOL_KIOSK_STATIC_DIR переопределяет каталог статики."""
    target = tmp_path / "kiosk-static"
    monkeypatch.setenv("SCHOOL_KIOSK_STATIC_DIR", str(target))
    settings = Settings()
    assert settings.static_dir == target
    assert settings.upload_dir == target
