import uuid
from datetime import UTC, datetime

from sqlalchemy import UUID, Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from src.enums.schedule import DayOfWeek


class IDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class DayOfWeekMixin:
    day_of_week: Mapped[DayOfWeek] = mapped_column(
        Enum(DayOfWeek), default=DayOfWeek.MONDAY
    )


class ScheduleMixin(IDMixin, TimestampMixin, DayOfWeekMixin):
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"

    def __str__(self):
        return f"{self.__class__.__name__}: {self.name}"
