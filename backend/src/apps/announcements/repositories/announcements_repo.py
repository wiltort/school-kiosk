import uuid
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.enums.announcements import AnnouncementKind
from src.models import Announcement


class AnnouncementRepository:
    """Репозиторий объявлений школы."""

    model = Announcement

    async def list_active(
        self,
        session: AsyncSession,
        now: datetime,
        kind: AnnouncementKind | None = None,
    ) -> list[Announcement]:
        """Возвращает объявления, видимые в указанный момент."""
        conditions = [
            self.model.is_active.is_(True),
            or_(self.model.starts_at.is_(None), self.model.starts_at <= now),
            or_(self.model.expires_at.is_(None), self.model.expires_at > now),
        ]
        if kind is not None:
            allowed = (
                [kind]
                if kind is AnnouncementKind.BOTH
                else [
                    kind,
                    AnnouncementKind.BOTH,
                ]
            )
            conditions.append(self.model.kind.in_(allowed))

        query = (
            select(self.model)
            .where(*conditions)
            .order_by(self.model.priority.desc(), self.model.created_at.desc())
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def list_all(self, session: AsyncSession) -> list[Announcement]:
        """Возвращает все объявления (для админ-панели)."""
        query = select(self.model).order_by(
            self.model.priority.desc(), self.model.created_at.desc()
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get(self, session: AsyncSession, id: uuid.UUID) -> Announcement | None:
        """Возвращает объявление по идентификатору."""
        return await session.get(self.model, id)

    async def create(self, session: AsyncSession, data: dict) -> Announcement:
        """Создаёт объявление."""
        obj = self.model(**data)
        session.add(obj)
        await session.flush()
        return obj

    async def update(
        self, session: AsyncSession, obj: Announcement, data: dict
    ) -> Announcement:
        """Обновляет поля объявления."""
        for field, value in data.items():
            setattr(obj, field, value)
        await session.flush()
        return obj

    async def delete(self, session: AsyncSession, obj: Announcement) -> None:
        """Удаляет объявление."""
        await session.delete(obj)
        await session.flush()
