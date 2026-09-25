"""Тесты хранилища настроек приложения (src/core/app_settings.py)."""

import json

from src.core.app_settings import AppSettingsStore


def test_defaults_when_no_file(tmp_path):
    store = AppSettingsStore(tmp_path)
    assert store.as_dict() == {
        "static_dir": None,
        "autostart": False,
        "local_image_dir": None,
        "current_local_schedule_image_filename": None,
        "schedule_mode": "single",
        "welcome_message": None,
    }
    assert store.static_dir() is None
    assert store.autostart() is False
    assert store.welcome_message() is None


def test_update_persists_to_file(tmp_path):
    store = AppSettingsStore(tmp_path)
    result = store.update(
        static_dir="D:/KioskStatic",
        autostart=True,
        local_image_dir="C:/uploaded_images",
        current_local_schedule_image_filename="schedule.png",
        schedule_mode="week",
        welcome_message="Добро пожаловать!",
    )

    assert result == {
        "static_dir": "D:/KioskStatic",
        "autostart": True,
        "local_image_dir": "C:/uploaded_images",
        "current_local_schedule_image_filename": "schedule.png",
        "schedule_mode": "week",
        "welcome_message": "Добро пожаловать!",
    }

    # Данные реально записаны на диск.
    raw = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert raw["static_dir"] == "D:/KioskStatic"
    assert raw["autostart"] is True
    assert raw["local_image_dir"] == "C:/uploaded_images"
    assert raw["current_local_schedule_image_filename"] == "schedule.png"
    assert raw["schedule_mode"] == "week"
    assert raw["welcome_message"] == "Добро пожаловать!"

    # Новый экземпляр читает те же значения.
    reloaded = AppSettingsStore(tmp_path)
    assert reloaded.as_dict() == {
        "static_dir": "D:/KioskStatic",
        "autostart": True,
        "local_image_dir": "C:/uploaded_images",
        "current_local_schedule_image_filename": "schedule.png",
        "schedule_mode": "week",
        "welcome_message": "Добро пожаловать!",
    }
    assert reloaded.welcome_message() == "Добро пожаловать!"


def test_empty_static_dir_normalizes_to_none(tmp_path):
    store = AppSettingsStore(tmp_path)
    store.update(static_dir="  ")
    assert store.static_dir() is None


def test_empty_welcome_message_normalizes_to_none(tmp_path):
    store = AppSettingsStore(tmp_path)
    store.update(welcome_message="Привет!")
    assert store.welcome_message() == "Привет!"
    store.update(welcome_message="   ")
    assert store.welcome_message() is None


def test_wrong_schedule_mode_ignores_it(tmp_path):
    store = AppSettingsStore(tmp_path)
    store.update(schedule_mode="wrong")
    assert store.schedule_mode() == "single"


def test_partial_update_keeps_other_fields(tmp_path):
    store = AppSettingsStore(tmp_path)
    store.update(
        static_dir="C:/Static",
        autostart=True,
        local_image_dir="C:/uploaded_images",
        current_local_schedule_image_filename="schedule.png",
    )

    store.update(autostart=False)
    assert store.as_dict() == {
        "static_dir": "C:/Static",
        "autostart": False,
        "local_image_dir": "C:/uploaded_images",
        "current_local_schedule_image_filename": "schedule.png",
        "schedule_mode": "single",
        "welcome_message": None,
    }

    store.update(static_dir=None)
    assert store.as_dict() == {
        "static_dir": None,
        "autostart": False,
        "local_image_dir": "C:/uploaded_images",
        "current_local_schedule_image_filename": "schedule.png",
        "schedule_mode": "single",
        "welcome_message": None,
    }


def test_migrates_static_dir_from_legacy_seed(tmp_path):
    """При первом запуске static_dir переносится из legacy-файла Tauri."""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "settings.json").write_text(
        json.dumps({"static_dir": "Z:/LegacyStatic"}),
        encoding="utf-8",
    )

    data_dir = tmp_path / "data"
    store = AppSettingsStore(data_dir, legacy_file=legacy / "settings.json")

    assert store.static_dir() == "Z:/LegacyStatic"
    # Миграция записала бэкенд-файл.
    assert (data_dir / "settings.json").is_file()
    assert store.as_dict() == {
        "static_dir": "Z:/LegacyStatic",
        "autostart": False,
        "local_image_dir": None,
        "current_local_schedule_image_filename": None,
        "schedule_mode": "single",
        "welcome_message": None,
    }

    # Повторная загрузка больше не трогает legacy и читает свой файл.
    store.update(static_dir="Y:/Changed")
    reloaded = AppSettingsStore(data_dir, legacy_file=legacy / "settings.json")
    assert reloaded.static_dir() == "Y:/Changed"


def test_not_ignores_legacy_without_static_dir(tmp_path):
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    (legacy / "settings.json").write_text(
        json.dumps({"autostart": True}),
        encoding="utf-8",
    )

    store = AppSettingsStore(tmp_path / "data", legacy_file=legacy / "settings.json")
    assert store.as_dict() == {
        "static_dir": None,
        "autostart": True,
        "local_image_dir": None,
        "current_local_schedule_image_filename": None,
        "schedule_mode": "single",
        "welcome_message": None,
    }

    store.update(static_dir="Z:/Changed")
    assert store.as_dict() == {
        "static_dir": "Z:/Changed",
        "autostart": True,
        "local_image_dir": None,
        "current_local_schedule_image_filename": None,
        "schedule_mode": "single",
        "welcome_message": None,
    }
