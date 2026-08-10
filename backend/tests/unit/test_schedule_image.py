"""Unit tests for the ScheduleImage model."""

import uuid

import pytest
from sqlalchemy import Boolean, String, create_engine
from sqlalchemy.orm import Session
from src.enums.schedule import DayOfWeek
from src.models.base import Base
from src.models.schedule import ScheduleImage


@pytest.fixture()
def session():
    """Provide an in-memory SQLite session with the schema created."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def test_schedule_image_defaults(session):
    """Test that ScheduleImage applies default values on flush."""
    image = ScheduleImage(image="schedule.png")
    session.add(image)
    session.flush()

    assert image.name == "Untitled"
    assert image.image == "schedule.png"
    assert image.is_active is False
    assert image.day_of_week.value == 1


def test_schedule_image_custom_values(session):
    """Test that ScheduleImage stores explicitly provided values."""
    image = ScheduleImage(
        name="Weekday schedule",
        image="weekday.png",
        is_active=True,
        day_of_week=DayOfWeek.THURSDAY,
    )
    session.add(image)
    session.flush()

    assert image.name == "Weekday schedule"
    assert image.image == "weekday.png"
    assert image.is_active is True
    assert image.day_of_week.value == 4
    assert image.created_at is not None


def test_schedule_image_id_is_uuid(session):
    """Test that ScheduleImage generates a UUID primary key on flush."""
    image = ScheduleImage(image="schedule.png")
    session.add(image)
    session.flush()

    assert isinstance(image.id, uuid.UUID)


def test_schedule_image_id_unique_per_instance(session):
    """Test that each ScheduleImage instance gets a distinct id."""
    first = ScheduleImage(image="a.png")
    second = ScheduleImage(image="b.png")
    session.add_all([first, second])
    session.flush()

    assert first.id != second.id


def test_schedule_image_table_name():
    """Test that ScheduleImage maps to the expected table name."""
    assert ScheduleImage.__tablename__ == "schedule_images"


def test_schedule_image_columns():
    """Test that ScheduleImage declares the expected columns."""
    columns = ScheduleImage.__table__.columns

    assert "id" in columns
    assert "name" in columns
    assert "image" in columns
    assert "is_active" in columns
    assert "created_at" in columns
    assert "updated_at" in columns
    assert "day_of_week" in columns


def test_schedule_image_name_column():
    """Test the name column definition."""
    column = ScheduleImage.__table__.columns["name"]

    assert isinstance(column.type, String)
    assert column.type.length == 255
    assert column.nullable is False
    assert column.default.arg == "Untitled"


def test_schedule_image_image_column():
    """Test the image column definition."""
    column = ScheduleImage.__table__.columns["image"]

    assert isinstance(column.type, String)
    assert column.type.length == 255
    assert column.nullable is False


def test_schedule_image_is_active_column():
    """Test the is_active column definition."""
    column = ScheduleImage.__table__.columns["is_active"]

    assert isinstance(column.type, Boolean)
    assert column.nullable is False
    assert column.default.arg is False


def test_schedule_image_id_is_primary_key():
    """Test that the id column is the primary key."""
    primary_key_columns = list(ScheduleImage.__table__.primary_key)
    assert [column.name for column in primary_key_columns] == ["id"]


def test_schedule_image_repr():
    """Test the string representation of ScheduleImage."""
    image = ScheduleImage(id=uuid.uuid4(), name="Weekday schedule")

    assert repr(image) == f"ScheduleImage(id={image.id}, name=Weekday schedule)"
