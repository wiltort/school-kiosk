"""Периодическое обновление прогноза погоды."""

import logging

from src.apps.settings.managers import SettingsManager
from src.apps.settings.repositories import SettingsRepository
from src.apps.weather.managers import WeatherManager, get_weather_provider
from src.apps.weather.repositories import WeatherForecastRepository
from src.core.database import get_db_dependency

logger = logging.getLogger(__name__)


def _build_manager() -> WeatherManager:
    """Собирает ``WeatherManager`` вне FastAPI-DI (для планировщика)."""
    db = get_db_dependency()
    return WeatherManager(
        db=db,
        settings_manager=SettingsManager(db=db, repo=SettingsRepository()),
        repo=WeatherForecastRepository(),
        provider=get_weather_provider(),
    )


async def run_weather_refresh() -> None:
    """Обновляет прогноз, если погода включена и кеш устарел.

    Задача запускается часто (каждые 5 минут), но фактический запрос
    к провайдеру выполняется только по истечении TTL из настройки
    ``weather.refresh_interval_minutes``.
    """
    manager = _build_manager()
    try:
        result = await manager.refresh_if_enabled()
    except Exception:
        logger.exception("Не удалось обновить прогноз погоды")
        return
    if result is not None:
        logger.info("Прогноз погоды обновлён: %s", result.forecast.location)
