"""Юнит-тесты для модели ScheduleImage."""

import uuid

from sqlalchemy import Boolean, String
from src.enums.schedule import DayOfWeek
from src.models.schedule import ScheduleImage


def test_schedule_image_defaults(sync_session):
    """Тест, что ScheduleImage применяет значения по умолчанию при flush."""
    image = ScheduleImage(image="schedule.png")
    sync_session.add(image)
    sync_session.flush()

    assert image.name == "Untitled"
    assert image.image == "schedule.png"
    assert image.is_active is False
    assert image.day_of_week.value == 1


def test_schedule_image_custom_values(sync_session):
    """Тест, что ScheduleImage применяет пользовательские значения при flush."""
    image = ScheduleImage(
        name="Weekday schedule",
        image="weekday.png",
        is_active=True,
        day_of_week=DayOfWeek.THURSDAY,
    )
    sync_session.add(image)
    sync_session.flush()

    assert image.name == "Weekday schedule"
    assert image.image == "weekday.png"
    assert image.is_active is True
    assert image.day_of_week.value == 4
    assert image.created_at is not None


def test_schedule_image_id_is_uuid(sync_session):
    """Тест, что ScheduleImage.id является UUID."""
    image = ScheduleImage(image="schedule.png")
    sync_session.add(image)
    sync_session.flush()

    assert isinstance(image.id, uuid.UUID)


def test_schedule_image_id_unique_per_instance(sync_session):
    """Тест, что ScheduleImage.id уникальный для каждого объекта."""
    first = ScheduleImage(image="a.png")
    second = ScheduleImage(image="b.png")
    sync_session.add_all([first, second])
    sync_session.flush()

    assert first.id != second.id


def test_schedule_image_table_name():
    """Проверка названия таблицы ScheduleImage."""
    assert ScheduleImage.__tablename__ == "schedule_images"


def test_schedule_image_columns():
    """Проверка наличия в таблице колонок ScheduleImage."""
    columns = ScheduleImage.__table__.columns

    assert "id" in columns
    assert "name" in columns
    assert "image" in columns
    assert "is_active" in columns
    assert "created_at" in columns
    assert "updated_at" in columns
    assert "day_of_week" in columns


def test_schedule_image_name_column():
    """Тест свойств колонки name."""
    column = ScheduleImage.__table__.columns["name"]

    assert isinstance(column.type, String)
    assert column.type.length == 255
    assert column.nullable is False
    assert column.default.arg == "Untitled"


def test_schedule_image_image_column():
    """Тест свойств колонки image."""
    column = ScheduleImage.__table__.columns["image"]

    assert isinstance(column.type, String)
    assert column.type.length == 255
    assert column.nullable is False


def test_schedule_image_is_active_column():
    """Tест свойств колонки is_active."""
    column = ScheduleImage.__table__.columns["is_active"]

    assert isinstance(column.type, Boolean)
    assert column.nullable is False
    assert column.default.arg is False


def test_schedule_image_id_is_primary_key():
    """Наличие первичного ключа и вхождение поля ID."""
    primary_key_columns = list(ScheduleImage.__table__.primary_key)
    assert [column.name for column in primary_key_columns] == ["id"]


def test_schedule_image_repr():
    """Тест строкового представления объекта ScheduleImage."""
    image = ScheduleImage(id=uuid.uuid4(), name="Weekday schedule")

    assert repr(image) == f"ScheduleImage(id={image.id}, name=Weekday schedule)"
