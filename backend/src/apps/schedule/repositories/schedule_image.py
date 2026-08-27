import uuid

from sqlalchemy import case, delete, insert, select, update
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from src.enums.schedule import DayOfWeek
from src.models import ScheduleImage


class ScheduleImageRepository:
    """Репозиторий для работы с изображениями расписания.

    Инкапсулирует низкоуровневые SQL-операции над сущностью
    :class:`ScheduleImage`. Методы не управляют транзакциями —
    commit/rollback выполняет вызывающий код (например, менеджер).
    """

    model = ScheduleImage

    async def get(self, session: AsyncSession, id: uuid.UUID) -> ScheduleImage | None:
        """Возвращает изображение расписания по идентификатору.

        Args:
            session: Активная асинхронная сессия базы данных.
            id: Уникальный идентификатор изображения.

        Returns:
            Найденное изображение либо ``None``, если запись отсутствует.
        """
        query = select(self.model).where(self.model.id == id)
        result: Result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, data: dict) -> ScheduleImage:
        """Создаёт новое изображение расписания.

        Args:
            session: Активная асинхронная сессия базы данных.
            data: Словарь значений полей для вставки.

        Returns:
            Созданное изображение :class:`ScheduleImage`.
        """
        query = insert(self.model).values(**data).returning(self.model)
        result: Result = await session.execute(query)
        return result.scalar_one()

    async def delete(self, session: AsyncSession, id: uuid.UUID) -> None:
        """Удаляет изображение расписания по идентификатору.

        Args:
            session: Активная асинхронная сессия базы данных.
            id: Уникальный идентификатор изображения.

        Returns:
            Результат выполнения запроса (для проверки ``rowcount``).
        """
        query = delete(self.model).where(self.model.id == id)
        return await session.execute(query)

    async def get_all(self, session: AsyncSession) -> list[ScheduleImage]:
        """Возвращает все изображения расписания.

        Результат сортируется по дню недели (порядок определяется
        перечислением :class:`DayOfWeek`).

        Args:
            session: Активная асинхронная сессия базы данных.

        Returns:
            Список всех изображений :class:`ScheduleImage`.
        """
        weekday_order = case(
            {day.name: index for index, day in enumerate(DayOfWeek, start=1)},
            value=self.model.day_of_week,
        )
        query = select(self.model).order_by(weekday_order)
        result: Result = await session.execute(query)
        return result.scalars().all()

    async def update(
        self, session: AsyncSession, id: uuid.UUID, data: dict
    ) -> ScheduleImage:
        """Обновляет изображение расписания по идентификатору.

        Обновляются только поля, переданные в ``data``.

        Args:
            session: Активная асинхронная сессия базы данных.
            id: Уникальный идентификатор изображения.
            data: Словарь обновляемых полей.

        Returns:
            Обновлённое изображение :class:`ScheduleImage`.
        """
        query = (
            update(self.model)
            .where(self.model.id == id)
            .values(**data)
            .returning(self.model)
        )
        result: Result = await session.execute(query)
        return result.scalar_one()
