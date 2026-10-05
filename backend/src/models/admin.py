from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.mixins import IDMixin, TimestampMixin


class AdminProfile(IDMixin, TimestampMixin, Base):
    __tablename__ = "admin_profiles"

    login: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    fullname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_default: Mapped[bool] = mapped_column(default=False)

    def __repr__(self) -> str:
        return f"AdminProfile(id={self.id}, login={self.login})"
