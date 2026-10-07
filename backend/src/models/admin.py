import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.mixins import IDMixin, TimestampMixin, TimeToLiveMixin


class AdminProfile(IDMixin, TimestampMixin, Base):
    __tablename__ = "admin_profiles"

    login: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    fullname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_default: Mapped[bool] = mapped_column(default=False)

    tokens: Mapped[list[AdminToken]] = relationship(
        back_populates="admin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"AdminProfile(id={self.id}, login={self.login})"


class AdminToken(IDMixin, TimeToLiveMixin, Base):
    __tablename__ = "admin_tokens"

    admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admin_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )

    admin: Mapped[AdminProfile] = relationship(back_populates="tokens")

    __table_args__ = (Index("ix_admin_token_expires", "admin_id", "expires_at"),)

    def __repr__(self) -> str:
        return f"AdminToken(admin_id={self.admin_id}, expires_at={self.expires_at})"
