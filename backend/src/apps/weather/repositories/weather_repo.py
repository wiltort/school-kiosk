from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import WeatherForecast


class WeatherForecastRepository:
    """Репозиторий кеша прогноза погоды."""

    model = WeatherForecast

    async def get(
        self, session: AsyncSession, *, location: str, api: str
    ) -> WeatherForecast | None:
        """Возвращает кеш прогноза для пары локация + провайдер."""
        query = select(self.model).where(
            self.model.location == location,
            self.model.api == api,
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        session: AsyncSession,
        *,
        location: str,
        api: str,
        payload: dict[str, Any],
        fetched_at: datetime,
        expires_at: datetime,
    ) -> WeatherForecast:
        """Создаёт или обновляет кеш прогноза."""
        obj = await self.get(session, location=location, api=api)
        if obj is None:
            obj = self.model(
                location=location,
                api=api,
                payload=payload,
                fetched_at=fetched_at,
                expires_at=expires_at,
            )
            session.add(obj)
        else:
            obj.payload = payload
            obj.fetched_at = fetched_at
            obj.expires_at = expires_at
        await session.flush()
        return obj
