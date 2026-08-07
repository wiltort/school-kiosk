import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.enums.schedule import DayOfWeek


class IDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class DayOfWeekMixin:
    day_of_week: Mapped[DayOfWeek] = mapped_column(Enum(DayOfWeek))
