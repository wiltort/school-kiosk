"""Тесты менеджера погоды: кеш, TTL и офлайн-фолбэк."""

import pytest
from fastapi import HTTPException
from src.apps.settings.managers import (
    SettingsManager,
    invalidate_settings_cache,
)
from src.apps.settings.repositories import SettingsRepository
from src.apps.weather.managers import AbstractWeatherManager, WeatherManager
from src.apps.weather.repositories import WeatherForecastRepository
from src.apps.weather.schemas import ForecastSchema
from src.core.database import DBDependency
from src.core.settings_schema import SettingsKey


class FakeProvider(AbstractWeatherManager):
    """Провайдер-заглушка без сетевых запросов."""

    name = "wttr.in"

    def __init__(self) -> None:
        self.calls = 0
        self.error: Exception | None = None
        self.forecast = ForecastSchema(location="Москва", temperature=12.5)

    async def get_weather(self, location: str) -> ForecastSchema:
        self.calls += 1
        if self.error is not None:
            raise self.error
        self.forecast.location = location
        return self.forecast


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def manager(async_session_maker, provider):
    """Менеджер погоды с фейковым провайдером."""
    invalidate_settings_cache()
    db = DBDependency(async_session_maker)
    return WeatherManager(
        db=db,
        settings_manager=SettingsManager(db=db, repo=SettingsRepository()),
        repo=WeatherForecastRepository(),
        provider=provider,
    )


@pytest.mark.asyncio
async def test_caches_forecast(manager, provider):
    """Повторный запрос в пределах TTL не обращается к провайдеру."""
    first = await manager.get_forecast()
    assert provider.calls == 1
    assert first.is_stale is False

    second = await manager.get_forecast()
    assert provider.calls == 1
    assert second.forecast.temperature == 12.5


@pytest.mark.asyncio
async def test_force_refresh_bypasses_cache(manager, provider):
    """force=True всегда запрашивает провайдера."""
    await manager.get_forecast()
    await manager.get_forecast(force=True)
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_falls_back_to_stale_cache(manager, provider):
    """При ошибке провайдера отдаётся устаревший кеш."""
    await manager.get_forecast()
    provider.error = RuntimeError("offline")

    result = await manager.get_forecast(force=True)
    assert result.is_stale is True
    assert result.forecast.temperature == 12.5


@pytest.mark.asyncio
async def test_provider_error_without_cache(manager, provider):
    """Без кеша ошибка провайдера превращается в 503."""
    provider.error = RuntimeError("offline")
    with pytest.raises(HTTPException) as exc:
        await manager.get_forecast()
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_disabled_weather_returns_404(manager):
    """Отключённая погода не отдаётся публичному API."""
    with pytest.raises(HTTPException) as exc:
        await manager.get_forecast(require_enabled=True)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_enabled_weather_returns_forecast(manager, provider):
    """Включённая погода отдаёт прогноз."""
    await manager.settings_manager.set(SettingsKey.WEATHER_ENABLED, True)

    result = await manager.get_forecast(require_enabled=True)
    assert result.forecast.location == "Москва"
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_refresh_if_enabled_skips_when_disabled(manager, provider):
    """Cron-обновление не трогает провайдера при выключенной погоде."""
    result = await manager.refresh_if_enabled()
    assert result is None
    assert provider.calls == 0
