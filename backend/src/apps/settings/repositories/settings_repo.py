from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AppSetting


class SettingsRepository:
    """Репозиторий настроек приложения в формате key-value.

    Инкапсулирует SQL-операции над сущностью :class:`AppSetting`.
    Методы не управляют транзакциями — commit/rollback выполняет
    вызывающий код (сервис).
    """

    model = AppSetting

    async def get(self, session: AsyncSession, key: str) -> AppSetting | None:
        """Возвращает настройку по ключу либо ``None``."""
        return await session.get(self.model, key)

    async def list_all(self, session: AsyncSession) -> list[AppSetting]:
        """Возвращает все сохранённые настройки."""
        result = await session.execute(select(self.model))
        return list(result.scalars().all())

    async def upsert(self, session: AsyncSession, key: str, value: Any) -> AppSetting:
        """Создаёт или обновляет настройку по ключу."""
        obj = await session.get(self.model, key)
        if obj is None:
            obj = self.model(key=key, value=value)
            session.add(obj)
        else:
            obj.value = value
        await session.flush()
        return obj

    async def upsert_many(self, session: AsyncSession, values: dict[str, Any]) -> None:
        """Создаёт или обновляет набор настроек."""
        for key, value in values.items():
            await self.upsert(session, key, value)

    async def delete(self, session: AsyncSession, key: str) -> None:
        """Удаляет настройку по ключу."""
        await session.execute(delete(self.model).where(self.model.key == key))
        await session.flush()
