from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.mixins import IDMixin
from src.models.types import UTCDateTime


class WeatherForecast(IDMixin, Base):
    """Кеш прогноза погоды для офлайн-режима киоска.

    Хранится последний успешный ответ провайдера для пары
    ``location`` + ``api``. Если провайдер недоступен, киоск показывает
    устаревший прогноз и время его последнего обновления.
    """

    __tablename__ = "weather_forecasts"

    location: Mapped[str] = mapped_column(String(255), nullable=False)
    api: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "location",
            "api",
            name="ux_weather_forecast_location_api",
        ),
    )

    def __repr__(self) -> str:
        return f"WeatherForecast(location={self.location!r}, api={self.api!r})"
