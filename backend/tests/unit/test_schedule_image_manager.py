"""Unit tests for the ScheduleImageManager CRUD operations."""

import asyncio
import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool
from src.apps.schedule.managers import ScheduleImageManager
from src.apps.schedule.schemas import (
    ScheduleImageCreate,
    ScheduleImageUpdate,
)
from src.enums.schedule import DayOfWeek
from src.models import Base, ScheduleImage


class _FakeDB:
    """Minimal stand-in for DBDependency exposing only `db_session`."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    @property
    def db_session(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory


@pytest.fixture()
def db():
    """Build an in-memory async SQLite session factory with a shared connection."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        bind=engine, expire_on_commit=False, autocommit=False
    )

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())

    yield _FakeDB(session_factory)

    asyncio.run(engine.dispose())


@pytest.fixture()
def manager(db):
    """Provide a ScheduleImageManager bound to the in-memory test DB."""
    return ScheduleImageManager(db=db)


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _sample_create(**overrides) -> ScheduleImageCreate:
    payload = {
        "name": "Расписание 1",
        "image": "schedule.png",
        "is_active": True,
        "day_of_week": DayOfWeek.MONDAY,
    }
    payload.update(overrides)
    return ScheduleImageCreate(**payload)


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------
def test_create_schedule_image(manager):
    """Test creating a schedule image returns the persisted record."""
    created = _run(manager.create(_sample_create()))

    assert isinstance(created.id, uuid.UUID)
    assert created.name == "Расписание 1"
    assert created.image == "schedule.png"
    assert created.is_active is True
    assert created.day_of_week == DayOfWeek.MONDAY
    assert created.created_at is not None
    assert created.updated_at is not None


def test_create_applies_model_defaults_for_none_fields(manager):
    """Test that optional None fields fall back to model defaults."""
    created = _run(
        manager.create(_sample_create(name=None, is_active=None, day_of_week=None))
    )

    assert created.name == "Untitled"
    assert created.is_active is False
    assert created.day_of_week == DayOfWeek.MONDAY


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------
def test_get_schedule_image(manager):
    """Test retrieving a schedule image by id."""
    created = _run(manager.create(_sample_create()))

    fetched = _run(manager.get(created.id))

    assert fetched.id == created.id
    assert fetched.name == created.name


def test_get_missing_raises_404(manager):
    """Test that getting a non-existent id raises HTTP 404."""
    missing_id = uuid.uuid4()

    with pytest.raises(Exception) as excinfo:
        _run(manager.get(missing_id))

    assert excinfo.value.status_code == 404


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------
def test_get_all_returns_created_records(manager):
    """Test retrieving all schedule images."""
    _run(manager.create(_sample_create(name="A", day_of_week=DayOfWeek.MONDAY)))
    _run(manager.create(_sample_create(name="B", day_of_week=DayOfWeek.TUESDAY)))

    records = _run(manager.get_all())

    assert len(records) == 2
    assert {r.name for r in records} == {"A", "B"}


def test_get_all_orders_by_day_of_week(manager):
    """Test that get_all sorts records by day_of_week."""
    _run(manager.create(_sample_create(name="late", day_of_week=DayOfWeek.FRIDAY)))
    _run(manager.create(_sample_create(name="early", day_of_week=DayOfWeek.MONDAY)))

    records = _run(manager.get_all())

    assert [r.name for r in records] == ["early", "late"]


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------
def test_update_partial_fields(manager):
    """Test updating only the provided fields."""
    created = _run(manager.create(_sample_create(name="Before")))

    updated = _run(manager.update(created.id, ScheduleImageUpdate(name="After")))

    assert updated.id == created.id
    assert updated.name == "After"
    assert updated.image == created.image  # unchanged
    assert updated.is_active == created.is_active  # unchanged


def test_update_missing_raises_404(manager):
    """Test that updating a non-existent id raises HTTP 404."""
    with pytest.raises(Exception) as excinfo:
        _run(manager.update(uuid.uuid4(), ScheduleImageUpdate(name="X")))

    assert excinfo.value.status_code == 404


def test_update_with_empty_payload_raises_400(manager):
    """Test that an update with no fields raises HTTP 400."""
    created = _run(manager.create(_sample_create()))

    with pytest.raises(Exception) as excinfo:
        _run(manager.update(created.id, ScheduleImageUpdate()))

    assert excinfo.value.status_code == 400


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------
def test_delete_removes_record(manager):
    """Test deleting an existing record."""
    created = _run(manager.create(_sample_create()))

    _run(manager.delete(created.id))

    # Verify the record is really gone.
    def _count() -> int:
        async def inner() -> int:
            async with manager.db.db_session() as session:
                result = await session.execute(
                    delete(ScheduleImage).where(ScheduleImage.id == created.id)
                )
                return result.rowcount

        return asyncio.run(inner())

    assert _count() == 0


def test_delete_missing_raises_404(manager):
    """Test that deleting a non-existent id raises HTTP 404."""
    with pytest.raises(Exception) as excinfo:
        _run(manager.delete(uuid.uuid4()))

    assert excinfo.value.status_code == 404
