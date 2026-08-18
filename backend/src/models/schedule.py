import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.mixins import IDMixin, ScheduleMixin


class ScheduleImage(ScheduleMixin, Base):
    __tablename__ = "schedule_images"
    image: Mapped[str] = mapped_column(String(255), nullable=False)


class ScheduleTable(ScheduleMixin, Base):
    __tablename__ = "schedule_tables"

    schedule_columns: Mapped[list[ScheduleColumn]] = relationship(
        "ScheduleColumn",
        back_populates="schedule_table",
        lazy="joined",
        cascade="all, delete-orphan",
        order_by="ScheduleColumn.number",
    )


class ScheduleColumn(IDMixin, Base):
    __tablename__ = "schedule_columns"
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    header: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule_table_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schedule_tables.id", ondelete="CASCADE")
    )

    lessons: Mapped[list[Lesson]] = relationship(
        "Lesson",
        back_populates="schedule_column",
        lazy="joined",
        cascade="all, delete-orphan",
        order_by="Lesson.number",
    )
    schedule_table: Mapped[ScheduleTable] = relationship(
        "ScheduleTable",
        back_populates="schedule_columns",
        lazy="joined",
    )
    __table_args__ = (UniqueConstraint("number", "schedule_table_id"),)


class Lesson(IDMixin, Base):
    __tablename__ = "lessons"
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule_column_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schedule_columns.id", ondelete="CASCADE")
    )

    schedule_column: Mapped[ScheduleColumn] = relationship(
        "ScheduleColumn", back_populates="lessons", lazy="joined"
    )
    __table_args__ = (UniqueConstraint("number", "schedule_column_id"),)

    def __repr__(self):
        return f"Lesson(id={self.id}, name={self.name})"
