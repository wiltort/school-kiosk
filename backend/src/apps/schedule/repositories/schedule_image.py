import uuid

from sqlalchemy import case, select
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
        return await session.get(self.model, id)

    async def create(self, session: AsyncSession, data: dict) -> ScheduleImage:
        """Создаёт новое изображение расписания.

        Args:
            session: Активная асинхронная сессия базы данных.
            data: Словарь значений полей для вставки.

        Returns:
            Созданное изображение :class:`ScheduleImage`.
        """
        obj = self.model(**data)
        session.add(obj)
        await session.flush()
        return obj

    async def delete(self, session: AsyncSession, obj: ScheduleImage) -> None:
        """Удаляет изображение расписания.

        Args:
            session: Активная асинхронная сессия базы данных.
            obj: Удаляемое изображение.
        """
        await session.delete(obj)
        return await session.flush()

    async def list(
        self, session: AsyncSession, *, limit: int | None = None
    ) -> list[ScheduleImage]:
        """Возвращает список изображений расписания.

        Args:
            session: Активная асинхронная сессия базы данных.

        Returns:
            Список изображений :class:`ScheduleImage`.
        """
        weekday_order = case(
            {day.name: index for index, day in enumerate(DayOfWeek, start=1)},
            value=self.model.day_of_week,
        )
        query = select(self.model).order_by(weekday_order)
        if limit is not None:
            query = query.limit(limit)
        result: Result = await session.execute(query)
        return list(result.scalars().all())

    async def update(
        self, session: AsyncSession, obj: ScheduleImage, data: dict
    ) -> ScheduleImage:
        """Обновляет изображение расписания.

        Args:
            session: Активная асинхронная сессия базы данных.
            obj: Обновляемое изображение.
            data: Словарь значений полей для обновления.

        Returns:
            Обновлённое изображение :class:`ScheduleImage`.
        """
        for field, value in data.items():
            setattr(obj, field, value)
        await session.flush()
        return obj

    async def get_local_by_name(
        self, session: AsyncSession, name: str
    ) -> ScheduleImage | None:
        """Возвращает локальное изображение расписания по идентификатору.

        Args:
            session: Активная асинхронная сессия базы данных.
            name: Имя локального изображения.
        Returns:
            Найденное локальное изображение :class:`ScheduleImage`.
        """
        query = select(self.model).where(
            self.model.name == name, self.model.is_local, self.model.is_active
        )
        result: Result = await session.execute(query)
        return result.scalar_one_or_none()

    def get_by_path(self, session: AsyncSession, path: str) -> ScheduleImage | None:
        """Возвращает изображение расписания по пути.

        Args:
            session: Активная асинхронная сессия базы данных.
            path: Путь к изображению.

        Returns:
            Найденное изображение :class:`ScheduleImage`.
        """
        return (
            session.query(self.model)
            .filter_by(path=path, is_local=True, is_active=True)
            .first()
        )
