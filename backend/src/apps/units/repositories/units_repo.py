from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AppUnit


class AppUnitRepository:
    """Репозиторий реестра сервисов киоска."""

    model = AppUnit

    async def list_all(self, session: AsyncSession) -> list[AppUnit]:
        """Возвращает сервисы в порядке отображения."""
        result = await session.execute(select(self.model).order_by(self.model.order))
        return list(result.scalars().all())

    async def get_by_key(self, session: AsyncSession, key: str) -> AppUnit | None:
        """Возвращает сервис по стабильному ключу."""
        result = await session.execute(select(self.model).where(self.model.key == key))
        return result.scalar_one_or_none()

    async def update(self, session: AsyncSession, unit: AppUnit, data: dict) -> AppUnit:
        """Обновляет поля сервиса."""
        for field, value in data.items():
            setattr(unit, field, value)
        await session.flush()
        return unit

    async def set_orders(self, session: AsyncSession, ordered: list[AppUnit]) -> None:
        """Перенумеровывает сервисы согласно переданному порядку.

        Запись двухфазная: сначала уникальные отрицательные значения, затем
        итоговые положительные. Иначе промежуточное состояние нарушает
        ограничение ``UNIQUE(order)``.
        """
        for index, unit in enumerate(ordered, start=1):
            unit.order = -index
        await session.flush()
        for index, unit in enumerate(ordered, start=1):
            unit.order = index
        await session.flush()
