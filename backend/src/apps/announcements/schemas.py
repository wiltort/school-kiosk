import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.enums.announcements import AnnouncementKind


class AnnouncementBase(BaseModel):
    """Общие поля объявления."""

    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    kind: AnnouncementKind = AnnouncementKind.BOTH
    priority: int = 0
    is_active: bool = True
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class AnnouncementCreate(AnnouncementBase):
    """Создание объявления."""


class AnnouncementUpdate(BaseModel):
    """Частичное обновление объявления."""

    title: str | None = Field(None, min_length=1, max_length=255)
    body: str | None = Field(None, min_length=1)
    kind: AnnouncementKind | None = None
    priority: int | None = None
    is_active: bool | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class AnnouncementResponse(AnnouncementBase):
    """Объявление в API."""

    id: uuid.UUID
    author_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
