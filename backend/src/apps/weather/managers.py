"""Провайдеры прогноза погоды и сервис кеширования."""

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated

import python_weather
from fastapi import Depends, HTTPException, status

from src.apps.settings.services.settings_service import SettingsService
from src.apps.weather.repositories import WeatherForecastRepository
from src.apps.weather.schemas import (
    DailyForecast,
    ForecastSchema,
    WeatherResponse,
)
from src.core.database import DBDependency, get_db_dependency
from src.core.settings_schema import SettingsKey
from src.enums.weather_api import WeatherAPIEnum
from src.models import WeatherForecast
from src.utils.retry import with_retry_commit

logger = logging.getLogger(__name__)


class AbstractWeatherManager(ABC):
    """Интерфейс провайдера прогноза погоды."""

    name: str

    @abstractmethod
    async def get_weather(self, location: str) -> ForecastSchema:
        """Возвращает прогноз для указанной локации."""


def _enum_name(value: object) -> str | None:
    """Возвращает имя enum-значения либо ``None``."""
    if value is None:
        return None
    return getattr(value, "name", str(value))


class WttrWeatherManager(AbstractWeatherManager):
    """Провайдер wttr.in через библиотеку ``python-weather``."""

    name = WeatherAPIEnum.WTTR.value

    async def get_weather(self, location: str) -> ForecastSchema:
        async with python_weather.Client(unit=python_weather.METRIC) as client:
            forecast = await client.get(location)
        return ForecastSchema(
            location=forecast.location,
            description=forecast.description,
            kind=_enum_name(forecast.kind),
            temperature=forecast.temperature,
            feels_like=forecast.feels_like,
            humidity=forecast.humidity,
            cloud_cover=forecast.cloud_cover,
            wind_speed=forecast.wind_speed,
            wind_direction=_enum_name(forecast.wind_direction),
            precipitation=forecast.precipitation,
            pressure=forecast.pressure,
            visibility=forecast.visibility,
            ultraviolet=_enum_name(forecast.ultraviolet),
            daily_forecasts=[
                DailyForecast(
                    date=item.date.isoformat() if item.date else None,
                    highest_temperature=item.highest_temperature,
                    lowest_temperature=item.lowest_temperature,
                    temperature=item.temperature,
                )
                for item in forecast.daily_forecasts
            ],
        )


@lru_cache
def get_weather_provider() -> AbstractWeatherManager:
    """Возвращает провайдера погоды по умолчанию."""
    return WttrWeatherManager()


class WeatherManager:
    """Отдаёт прогноз с кешированием и фолбэком на устаревшие данные."""

    def __init__(
        self,
        db: Annotated[DBDependency, Depends(get_db_dependency)],
        settings_service: Annotated[SettingsService, Depends()],
        repo: Annotated[WeatherForecastRepository, Depends()],
        provider: Annotated[AbstractWeatherManager, Depends(get_weather_provider)],
    ) -> None:
        self.db = db
        self.settings_service = settings_service
        self.repo = repo
        self.provider = provider

    async def get_forecast(
        self,
        *,
        force: bool = False,
        require_enabled: bool = False,
    ) -> WeatherResponse:
        """Возвращает прогноз из кеша или от провайдера.

        Args:
            force: Игнорировать TTL кеша и запросить провайдера.
            require_enabled: Вернуть 404, если погода отключена в настройках.

        Raises:
            HTTPException: 404, если погода отключена; 503, если провайдер
                недоступен и кеша нет.
        """
        if require_enabled and not await self.settings_service.get_bool(
            SettingsKey.WEATHER_ENABLED
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Погода отключена в настройках",
            )

        location = (
            await self.settings_service.get_str(SettingsKey.WEATHER_LOCATION)
            or "Москва"
        )
        api = (
            await self.settings_service.get(SettingsKey.WEATHER_API)
            or WeatherAPIEnum.WTTR.value
        )
        now = datetime.now(UTC)

        async with self.db.db_session() as session:
            cached = await self.repo.get(session, location=location, api=api)

        if cached is not None and not force and cached.expires_at > now:
            return self._response(cached, is_stale=False)

        try:
            forecast = await self.provider.get_weather(location)
        except Exception as exc:
            logger.warning("Провайдер погоды недоступен: %s", exc)
            if cached is not None:
                return self._response(cached, is_stale=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Не удалось получить прогноз погоды",
            ) from exc

        interval = await self.settings_service.get_int(
            SettingsKey.WEATHER_REFRESH_INTERVAL
        )
        expires_at = now + timedelta(minutes=interval)
        async with self.db.db_session() as session:
            row = await self.repo.upsert(
                session,
                location=location,
                api=api,
                payload=forecast.model_dump(mode="json"),
                fetched_at=now,
                expires_at=expires_at,
            )
            await with_retry_commit(session)
        return self._response(row, is_stale=False)

    async def refresh_if_enabled(self) -> WeatherResponse | None:
        """Обновляет прогноз, если погода включена (для cron)."""
        if not await self.settings_service.get_bool(SettingsKey.WEATHER_ENABLED):
            return None
        return await self.get_forecast(force=True)

    @staticmethod
    def _response(row: WeatherForecast, *, is_stale: bool) -> WeatherResponse:
        return WeatherResponse(
            forecast=ForecastSchema.model_validate(row.payload),
            fetched_at=row.fetched_at,
            expires_at=row.expires_at,
            is_stale=is_stale,
            source=row.api,
        )
