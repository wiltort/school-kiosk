import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status

from src.apps.announcements.repositories import AnnouncementRepository
from src.apps.announcements.schemas import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from src.core.database import DBDependency, get_db_dependency
from src.enums.announcements import AnnouncementKind
from src.utils.retry import with_retry_commit


class AnnouncementManager:
    """Управляет объявлениями школы."""

    def __init__(
        self,
        db: DBDependency = Depends(get_db_dependency),
        repo: AnnouncementRepository = Depends(),
    ) -> None:
        self.db = db
        self.repo = repo

    @staticmethod
    def _validate_window(
        starts_at: datetime | None, expires_at: datetime | None
    ) -> None:
        """Проверяет, что окно публикации задано корректно."""
        if starts_at and expires_at and expires_at <= starts_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Дата окончания должна быть позже даты начала",
            )

    async def list_active(
        self, kind: AnnouncementKind | None = None
    ) -> list[AnnouncementResponse]:
        """Возвращает объявления, видимые на киоске прямо сейчас."""
        now = datetime.now(UTC)
        async with self.db.db_session() as session:
            items = await self.repo.list_active(session, now, kind)
        return [AnnouncementResponse.model_validate(item) for item in items]

    async def list_all(self) -> list[AnnouncementResponse]:
        """Возвращает все объявления для админ-панели."""
        async with self.db.db_session() as session:
            items = await self.repo.list_all(session)
        return [AnnouncementResponse.model_validate(item) for item in items]

    async def get(self, id: uuid.UUID) -> AnnouncementResponse:
        """Возвращает объявление по идентификатору.

        Raises:
            HTTPException: 404, если объявление не найдено.
        """
        async with self.db.db_session() as session:
            item = await self.repo.get(session, id)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Объявление не найдено",
            )
        return AnnouncementResponse.model_validate(item)

    async def create(
        self,
        payload: AnnouncementCreate,
        *,
        author_id: uuid.UUID | None = None,
    ) -> AnnouncementResponse:
        """Создаёт объявление."""
        self._validate_window(payload.starts_at, payload.expires_at)
        data = payload.model_dump()
        data["author_id"] = author_id
        async with self.db.db_session() as session:
            item = await self.repo.create(session, data)
            await with_retry_commit(session)
        return AnnouncementResponse.model_validate(item)

    async def update(
        self, id: uuid.UUID, payload: AnnouncementUpdate
    ) -> AnnouncementResponse:
        """Частично обновляет объявление.

        Raises:
            HTTPException: 404, если объявление не найдено; 400 при
                некорректном окне публикации.
        """
        data = payload.model_dump(exclude_unset=True)
        async with self.db.db_session() as session:
            item = await self.repo.get(session, id)
            if item is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Объявление не найдено",
                )
            self._validate_window(
                data.get("starts_at", item.starts_at),
                data.get("expires_at", item.expires_at),
            )
            if data:
                await self.repo.update(session, item, data)
                await with_retry_commit(session)
        return AnnouncementResponse.model_validate(item)

    async def delete(self, id: uuid.UUID) -> None:
        """Удаляет объявление.

        Raises:
            HTTPException: 404, если объявление не найдено.
        """
        async with self.db.db_session() as session:
            item = await self.repo.get(session, id)
            if item is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Объявление не найдено",
                )
            await self.repo.delete(session, item)
            await with_retry_commit(session)
