from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.types import UTCDateTime


class AppSetting(Base):
    """Настройка приложения в формате key-value.

    Ключ — стабильная строка с точечным пространством имён (например,
    ``weather.location``). Значение хранится в JSON-колонке, поэтому
    поддерживает строки, числа, булевы значения, списки и словари.
    """

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"AppSetting(key={self.key!r})"
