"""Типы колонок SQLAlchemy для моделей."""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Дата-время в UTC с сохранением таймзоны при работе с SQLite.

    SQLite хранит даты строкой без смещения
    (``YYYY-MM-DD HH:MM:SS.ffffff``), из-за чего ``tzinfo`` молча теряется
    при записи и чтении. Тип нормализует значение на границе базы данных:

    - при записи aware-дата приводится к UTC и сохраняется без смещения;
    - при чтении naive-значение интерпретируется как UTC.

    Результат всегда aware (``tzinfo=UTC``): Pydantic сериализует такие
    даты с суффиксом ``Z``, а сравнение с ``datetime.now(UTC)`` в Python
    не падает с ``TypeError`` (offset-naive vs offset-aware).
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:  # noqa ARG002
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:  # noqa ARG002
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
