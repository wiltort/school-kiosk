from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base
from src.models.mixins import IDMixin, TimestampMixin


class AppUnit(IDMixin, TimestampMixin, Base):
    """Сервис (плитка) киоска: расписание, погода, объявления и т. п.

    Реестр задаёт набор доступных на главном экране сервисов, их порядок
    и видимость. Настройки каждого сервиса хранятся в ``app_settings``
    с префиксом, совпадающим с :attr:`key`.
    """

    __tablename__ = "app_units"

    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"AppUnit(key={self.key!r}, order={self.order})"
