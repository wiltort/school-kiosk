from typing import Annotated

from fastapi import APIRouter, Depends

from src.apps.admin.auth import get_current_admin_dependency
from src.apps.admin.schemas import AdminTokenSchema
from src.apps.weather.managers import WeatherManager
from src.apps.weather.schemas import WeatherResponse

weather_router = APIRouter(prefix="/weather", tags=["weather"])
admin_weather_router = APIRouter(prefix="/admin/weather", tags=["admin_weather"])


@weather_router.get("/forecast", response_model=WeatherResponse)
async def get_forecast(
    manager: Annotated[WeatherManager, Depends()],
) -> WeatherResponse:
    """Публичный прогноз погоды (из кеша или от провайдера)."""
    return await manager.get_forecast(require_enabled=True)


@admin_weather_router.post("/refresh", response_model=WeatherResponse)
async def refresh_forecast(
    manager: Annotated[WeatherManager, Depends()],
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> WeatherResponse:
    """Принудительно обновляет прогноз погоды."""
    return await manager.get_forecast(force=True)
