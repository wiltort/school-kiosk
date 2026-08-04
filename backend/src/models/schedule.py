from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.models.base import TimestampMixin


class Schedule(TimestampMixin, Base):
    __tablename__ = "schedules"
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled")
    image: Mapped[str] = mapped_column(String(255), nullable=True)
    type: Mapped[str] = mapped_column(String(25), nullable=False, default="image")

    def __repr__(self) -> str:
        return f"Schedule(id={self.id}, name={self.name}, type={self.type})"
