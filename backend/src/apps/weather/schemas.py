from datetime import datetime

from pydantic import BaseModel, Field


class DailyForecast(BaseModel):
    """Дневной прогноз."""

    date: str | None = Field(default=None, description="Дата в ISO-формате")
    highest_temperature: float | None = Field(
        default=None, description="Максимальная температура"
    )
    lowest_temperature: float | None = Field(
        default=None, description="Минимальная температура"
    )
    temperature: float | None = Field(default=None, description="Температура")


class ForecastSchema(BaseModel):
    """Текущий прогноз и дневной ряд."""

    location: str | None = Field(default=None, description="Населённый пункт")
    description: str | None = Field(default=None, description="Описание")
    kind: str | None = Field(default=None, description="Тип погоды")
    temperature: float | None = Field(default=None, description="Температура")
    feels_like: float | None = Field(default=None, description="Ощущается как")
    humidity: int | None = Field(default=None, description="Влажность")
    cloud_cover: int | None = Field(default=None, description="Облачность")
    wind_speed: float | None = Field(default=None, description="Скорость ветра")
    wind_direction: str | None = Field(default=None, description="Направление ветра")
    precipitation: float | None = Field(default=None, description="Осадки")
    pressure: float | None = Field(default=None, description="Давление")
    visibility: float | None = Field(default=None, description="Видимость")
    ultraviolet: str | None = Field(default=None, description="УФ-индекс")
    daily_forecasts: list[DailyForecast] = Field(
        default_factory=list, description="Дневные прогнозы"
    )


class WeatherResponse(BaseModel):
    """Ответ API прогноза погоды."""

    forecast: ForecastSchema
    fetched_at: datetime = Field(..., description="Когда прогноз был получен")
    expires_at: datetime = Field(..., description="Когда прогноз устареет")
    is_stale: bool = Field(
        default=False,
        description="True, если провайдер недоступен и отдан кеш",
    )
    source: str = Field(default="wttr.in", description="Провайдер прогноза")
