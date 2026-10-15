from pydantic import BaseModel, Field
from python_weather.enums import Kind


class DailyForecast(BaseModel):
    pass


class ForecastSchema(BaseModel):
    cloud_cover: int | None = Field(default=None, description="Облачность")
    daily_forecasts: list[DailyForecast] = Field(
        default_factory=list, description="Дневные прогнозы"
    )
    description: str | None = Field(default=None, description="Описание")
    humidity: int | None = Field(default=None, description="Влажность")
    kind: Kind | None = Field(default=None, description="Тип погоды")
