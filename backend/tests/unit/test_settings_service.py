"""Тесты сервиса настроек приложения (БД + кеш)."""

import pytest
from src.apps.settings.repositories import SettingsRepository
from src.apps.settings.services.settings_service import (
    SettingsService,
    invalidate_settings_cache,
)
from src.core.database import DBDependency
from src.core.settings_schema import SETTINGS_SCHEMA, SettingsKey


@pytest.fixture
def service(async_session_maker):
    """Сервис настроек поверх тестовой in-memory БД."""
    invalidate_settings_cache()
    return SettingsService(
        db=DBDependency(async_session_maker),
        repo=SettingsRepository(),
    )


@pytest.mark.asyncio
async def test_defaults_when_db_empty(service):
    """Пустая БД отдаёт значения по умолчанию из схемы."""
    assert await service.get(SettingsKey.SCHEDULE_MODE) == "single"
    assert await service.get(SettingsKey.WEATHER_LOCATION) == "Москва"
    assert await service.get_bool(SettingsKey.WEATHER_ENABLED) is False
    assert await service.get_int(SettingsKey.WEATHER_REFRESH_INTERVAL) == 60

    data = await service.as_dict()
    assert set(data) == {spec.key.value for spec in SETTINGS_SCHEMA}


@pytest.mark.asyncio
async def test_set_and_get(service):
    """Сохранённые значения нормализуются и читаются обратно."""
    await service.set(SettingsKey.UI_WELCOME_MESSAGE, "  Привет  ")
    assert await service.get_str(SettingsKey.UI_WELCOME_MESSAGE) == "Привет"

    await service.set(SettingsKey.SCHEDULE_MODE, "week")
    assert await service.get(SettingsKey.SCHEDULE_MODE) == "week"


@pytest.mark.asyncio
async def test_set_rejects_unknown_key(service):
    """Неизвестный ключ не принимается."""
    with pytest.raises(ValueError):
        await service.set("unknown.key", 1)


@pytest.mark.asyncio
async def test_set_rejects_invalid_value(service):
    """Значение вне ограничений не принимается."""
    with pytest.raises(ValueError):
        await service.set(SettingsKey.WEATHER_REFRESH_INTERVAL, 1)


@pytest.mark.asyncio
async def test_ensure_defaults_inserts_rows(service, async_session_maker):
    """ensure_defaults заполняет БД всеми ключами схемы."""
    await service.ensure_defaults()
    async with async_session_maker() as session:
        rows = await SettingsRepository().list_all(session)
    assert len(rows) == len(SETTINGS_SCHEMA)


@pytest.mark.asyncio
async def test_cache_is_shared_and_invalidated(async_session_maker):
    """Кеш общий для одного движка и сбрасывается после записи."""
    invalidate_settings_cache()
    db = DBDependency(async_session_maker)
    first = SettingsService(db=db, repo=SettingsRepository())
    second = SettingsService(db=db, repo=SettingsRepository())

    assert await first.get(SettingsKey.SCHEDULE_MODE) == "single"
    await second.set(SettingsKey.SCHEDULE_MODE, "week")
    assert await first.get(SettingsKey.SCHEDULE_MODE) == "week"
