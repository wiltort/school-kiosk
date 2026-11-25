import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.apps.admin.auth import get_current_admin_dependency
from src.apps.admin.schemas import AdminTokenSchema
from src.apps.announcements.managers import AnnouncementManager
from src.apps.announcements.schemas import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from src.enums.announcements import AnnouncementKind

announcements_router = APIRouter(prefix="/announcements", tags=["announcements"])
admin_announcements_router = APIRouter(
    prefix="/admin/announcements", tags=["admin_announcements"]
)


@announcements_router.get("/active", response_model=list[AnnouncementResponse])
async def list_active_announcements(
    manager: Annotated[AnnouncementManager, Depends()],
    kind: Annotated[AnnouncementKind | None, Query()] = None,
) -> list[AnnouncementResponse]:
    """Публичная лента активных объявлений (без авторизации)."""
    return await manager.list_active(kind)


@admin_announcements_router.get("/", response_model=list[AnnouncementResponse])
async def list_announcements(
    manager: Annotated[AnnouncementManager, Depends()],
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> list[AnnouncementResponse]:
    """Все объявления для админ-панели."""
    return await manager.list_all()


@admin_announcements_router.post(
    "/",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_announcement(
    payload: AnnouncementCreate,
    manager: Annotated[AnnouncementManager, Depends()],
    token: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> AnnouncementResponse:
    """Создаёт объявление от имени текущего администратора."""
    return await manager.create(payload, author_id=token.admin_id)


@admin_announcements_router.get("/{id}", response_model=AnnouncementResponse)
async def get_announcement(
    id: uuid.UUID,
    manager: Annotated[AnnouncementManager, Depends()],
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> AnnouncementResponse:
    """Возвращает объявление по идентификатору."""
    return await manager.get(id)


@admin_announcements_router.patch("/{id}", response_model=AnnouncementResponse)
async def update_announcement(
    id: uuid.UUID,
    payload: AnnouncementUpdate,
    manager: Annotated[AnnouncementManager, Depends()],
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> AnnouncementResponse:
    """Частично обновляет объявление."""
    return await manager.update(id, payload)


@admin_announcements_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_announcement(
    id: uuid.UUID,
    manager: Annotated[AnnouncementManager, Depends()],
    _: Annotated[AdminTokenSchema, Depends(get_current_admin_dependency)],
) -> None:
    """Удаляет объявление."""
    await manager.delete(id)
