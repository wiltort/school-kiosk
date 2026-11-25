"""Тесты seed настроек и реестра сервисов."""

import json

import pytest
from sqlalchemy import select
from src.apps.settings.services.seed import (
    read_legacy_settings,
    seed_app_settings,
    seed_app_units,
)
from src.core.settings_schema import SETTINGS_SCHEMA, SettingsKey
from src.models import AppSetting, AppUnit


def test_read_legacy_settings_missing_and_invalid(tmp_path):
    """Отсутствующий или битый файл даёт пустой словарь."""
    assert read_legacy_settings(None) == {}
    assert read_legacy_settings(tmp_path / "missing.json") == {}

    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert read_legacy_settings(broken) == {}


def test_read_legacy_settings(tmp_path):
    """Корректный legacy-файл читается как словарь."""
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"location": "Казань"}), encoding="utf-8")
    assert read_legacy_settings(path) == {"location": "Казань"}


@pytest.mark.asyncio
async def test_seed_app_settings_from_legacy(async_session):
    """Legacy-значения переносятся в app_settings, остальные — дефолты."""
    created = await seed_app_settings(
        async_session,
        legacy_settings={
            "welcome_message": "Привет",
            "schedule_mode": "week",
            "location": "Казань",
            "use_weather": True,
        },
    )
    await async_session.commit()

    assert created == len(SETTINGS_SCHEMA)

    welcome = await async_session.get(AppSetting, SettingsKey.UI_WELCOME_MESSAGE.value)
    assert welcome is not None and welcome.value == "Привет"

    mode = await async_session.get(AppSetting, SettingsKey.SCHEDULE_MODE.value)
    assert mode is not None and mode.value == "week"

    weather = await async_session.get(AppSetting, SettingsKey.WEATHER_ENABLED.value)
    assert weather is not None and weather.value is True

    location = await async_session.get(AppSetting, SettingsKey.WEATHER_LOCATION.value)
    assert location is not None and location.value == "Казань"


@pytest.mark.asyncio
async def test_seed_app_settings_does_not_overwrite(async_session):
    """Повторный seed не перезаписывает существующие значения."""
    await seed_app_settings(
        async_session, legacy_settings={"welcome_message": "Первый"}
    )
    await async_session.commit()

    created = await seed_app_settings(
        async_session, legacy_settings={"welcome_message": "Второй"}
    )
    assert created == 0

    welcome = await async_session.get(AppSetting, SettingsKey.UI_WELCOME_MESSAGE.value)
    assert welcome is not None and welcome.value == "Первый"


@pytest.mark.asyncio
async def test_seed_app_settings_skips_invalid_legacy(async_session):
    """Некорректное legacy-значение заменяется дефолтом."""
    await seed_app_settings(async_session, legacy_settings={"schedule_mode": "month"})
    await async_session.commit()

    mode = await async_session.get(AppSetting, SettingsKey.SCHEDULE_MODE.value)
    assert mode is not None and mode.value == "single"


@pytest.mark.asyncio
async def test_seed_app_units_is_idempotent(async_session):
    """Дефолтные сервисы создаются один раз."""
    created = await seed_app_units(async_session)
    await async_session.commit()
    assert created == 3

    again = await seed_app_units(async_session)
    assert again == 0

    keys = (await async_session.execute(select(AppUnit.key))).scalars().all()
    assert set(keys) == {"schedule", "weather", "announcements"}
