import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.enums.announcements import AnnouncementKind
from src.models.base import Base
from src.models.mixins import IDMixin, TimestampMixin
from src.models.types import UTCDateTime

if TYPE_CHECKING:
    from src.models.admin import AdminProfile


class Announcement(IDMixin, TimestampMixin, Base):
    """Объявление школы: бегущая строка и/или лента новостей.

    Объявление видимо на киоске, если ``is_active=True`` и текущее время
    попадает в необязательное окно ``starts_at`` … ``expires_at``.
    """

    __tablename__ = "announcements"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[AnnouncementKind] = mapped_column(
        Enum(AnnouncementKind),
        nullable=False,
        default=AnnouncementKind.BOTH,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    starts_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True, index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("admin_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    author: Mapped[AdminProfile | None] = relationship(
        "AdminProfile",
        lazy="joined",
    )

    __table_args__ = (
        Index("ix_announcements_active_priority", "is_active", "priority"),
    )

    def __repr__(self) -> str:
        return f"Announcement(id={self.id}, title={self.title!r})"
