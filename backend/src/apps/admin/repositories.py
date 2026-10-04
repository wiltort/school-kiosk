from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AdminProfile


class AdminRepository:
    """Репозиторий для работы с администраторами."""

    model = AdminProfile

    async def get_by_login(self, session: AsyncSession, login: str) -> AdminProfile:
        """Получить администратора по логину.

        Args:
            session (AsyncSession): Сессия базы данных.
            login (str): Логин администратора.

        Returns:
            AdminProfile: Администратор.
        """
        query = select(self.model).where(self.model.login == login)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, data: dict) -> AdminProfile:
        """Создать администратора.

        Args:
            session (AsyncSession): Сессия базы данных.
            data (dict): Словарь с данными администратора.

        Returns:
            AdminProfile: Созданный администратор.
        """
        admin = self.model(**data)
        session.add(admin)
        await session.flush()
        return admin

    async def update(
        self, session: AsyncSession, admin: AdminProfile, data: dict
    ) -> AdminProfile:
        """Обновить администратора.

        Args:
            session (AsyncSession): Сессия базы данных.
            admin (AdminProfile): Администратор.
            data (dict): Словарь с данными администратора.

        Returns:
            AdminProfile: Обновленный администратор.
        """
        for field, value in data.items():
            setattr(admin, field, value)
        await session.flush()
        return admin

    async def delete(self, session: AsyncSession, admin: AdminProfile) -> None:
        """Удалить администратора.

        Args:
            session (AsyncSession): Сессия базы данных.
            admin (AdminProfile): Администратор.
        """
        await session.delete(admin)
        await session.flush()

    async def count(self, session: AsyncSession) -> int:
        """Получить количество администраторов.

        Args:
            session (AsyncSession): Сессия базы данных.

        Returns:
            int: Количество администраторов.
        """
        query = select(func.count(self.model.id))
        result = await session.execute(query)
        return result.scalar_one()
