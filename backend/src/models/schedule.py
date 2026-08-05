from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.mixins import IDMixin, TimestampMixin


class ScheduleImage(IDMixin, TimestampMixin, Base):
    __tablename__ = "schedules"
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled")
    image: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"Schedule(id={self.id}, name={self.name})"
