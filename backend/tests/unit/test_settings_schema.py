"""Тесты реестра и валидации настроек приложения."""

import pytest
from src.core.settings_schema import (
    DEFAULT_APP_UNITS,
    SETTINGS_BY_KEY,
    SETTINGS_SCHEMA,
    SettingsKey,
    SettingType,
)
from src.enums.schedule_modes import ScheduleMode
from src.enums.weather_api import WeatherAPIEnum


def test_schema_keys_are_unique():
    """Ключи реестра уникальны и совпадают с индексом по ключу."""
    keys = [spec.key.value for spec in SETTINGS_SCHEMA]
    assert len(keys) == len(set(keys))
    assert set(keys) == set(SETTINGS_BY_KEY)


def test_default_units_are_unique():
    """Дефолтные сервисы имеют уникальные ключи и порядок."""
    keys = [unit["key"] for unit in DEFAULT_APP_UNITS]
    orders = [unit["order"] for unit in DEFAULT_APP_UNITS]
    assert len(keys) == len(set(keys))
    assert len(orders) == len(set(orders))


def test_bool_coerce():
    """Логические настройки принимают bool и строковые представления."""
    spec = SETTINGS_BY_KEY[SettingsKey.WEATHER_ENABLED.value]
    assert spec.type is SettingType.BOOL
    assert spec.coerce(True) is True
    assert spec.coerce("false") is False
    assert spec.coerce(0) is False
    with pytest.raises(ValueError):
        spec.coerce("maybe")


def test_int_coerce_bounds():
    """Числовые настройки проверяют границы."""
    spec = SETTINGS_BY_KEY[SettingsKey.WEATHER_REFRESH_INTERVAL.value]
    assert spec.coerce("30") == 30
    with pytest.raises(ValueError):
        spec.coerce(1)
    with pytest.raises(ValueError):
        spec.coerce(5000)
    with pytest.raises(ValueError):
        spec.coerce("abc")


def test_enum_coerce():
    """Enum-настройки принимают только допустимые значения."""
    mode = SETTINGS_BY_KEY[SettingsKey.SCHEDULE_MODE.value]
    assert mode.coerce("week") == ScheduleMode.WEEK.value
    with pytest.raises(ValueError):
        mode.coerce("month")

    api = SETTINGS_BY_KEY[SettingsKey.WEATHER_API.value]
    assert api.coerce("wttr.in") == WeatherAPIEnum.WTTR.value


def test_str_coerce_and_nullable():
    """Строки обрезаются; nullable-настройки нормализуют пустое в None."""
    welcome = SETTINGS_BY_KEY[SettingsKey.UI_WELCOME_MESSAGE.value]
    assert welcome.coerce("") is None
    assert welcome.coerce("  Привет  ") == "Привет"

    location = SETTINGS_BY_KEY[SettingsKey.WEATHER_LOCATION.value]
    assert location.coerce("  Казань ") == "Казань"
    with pytest.raises(ValueError):
        location.coerce("   ")
    with pytest.raises(ValueError):
        location.coerce(None)
