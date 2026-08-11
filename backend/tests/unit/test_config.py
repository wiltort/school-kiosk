"""Unit tests for application configuration."""

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
