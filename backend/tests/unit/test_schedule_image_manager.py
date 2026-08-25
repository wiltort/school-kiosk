"""Юнит-тесты для ScheduleImageManager CRUD операций."""

import uuid

import pytest
from sqlalchemy import select
from src.apps.schedule.managers import ScheduleImageManager
from src.apps.schedule.schemas import (
    ScheduleImageCreate,
    ScheduleImageUpdate,
)
from src.apps.schedule.services import ScheduleImageRepositoryService
from src.enums.schedule import DayOfWeek
from src.models import ScheduleImage


def _sample_create(**overrides) -> ScheduleImageCreate:
    payload = {
        "name": "Расписание 1",
        "image": "schedule.png",
        "is_active": True,
        "day_of_week": DayOfWeek.MONDAY,
    }
    payload.update(overrides)
    return ScheduleImageCreate(**payload)


@pytest.mark.asyncio
async def test_create_schedule_image(manager_factory):
    """Проверка создания изображения расписания."""
    manager = manager_factory(
        ScheduleImageManager, image_repo=ScheduleImageRepositoryService()
    )
    created = await manager.create(_sample_create())

    assert isinstance(created.id, uuid.UUID)
    assert created.name == "Расписание 1"
    assert created.image == "schedule.png"
    assert created.is_active is True
    assert created.day_of_week == DayOfWeek.MONDAY
    assert created.created_at is not None
    assert created.updated_at is not None


@pytest.mark.asyncio
async def test_create_applies_model_defaults_for_none_fields(manager_factory):
    """Проверка применения значений по умолчанию для полей."""
    manager = manager_factory(
        ScheduleImageManager, image_repo=ScheduleImageRepositoryService()
    )
    created = await manager.create(
        _sample_create(name=None, is_active=None, day_of_week=None)
    )

    assert created.name == "Untitled"
    assert created.is_active is False
    assert created.day_of_week == DayOfWeek.MONDAY


@pytest.mark.asyncio
async def test_get_schedule_image(manager_factory):
    """Тест получения изображния из бд."""
    manager = manager_factory(
        ScheduleImageManager, image_repo=ScheduleImageRepositoryService()
    )
    created = await manager.create(_sample_create())

    fetched = await manager.get(created.id)

    assert fetched.id == created.id
    assert fetched.name == created.name


@pytest.mark.asyncio
async def test_get_missing_raises_404(manager_factory):
    """Тест выброса HTTP 404 при вызове несуществующего ID."""
    missing_id = uuid.uuid4()
    manager = manager_factory(
        ScheduleImageManager, image_repo=ScheduleImageRepositoryService()
    )

    with pytest.raises(Exception) as excinfo:
        await manager.get(missing_id)

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_get_all_returns_created_records(manager_factory):
    """Тест получения всех созданных записей."""
    manager = manager_factory(
        ScheduleImageManager, image_repo=ScheduleImageRepositoryService()
    )
    await manager.create(_sample_create(name="A", day_of_week=DayOfWeek.MONDAY))
    await manager.create(_sample_create(name="B", day_of_week=DayOfWeek.TUESDAY))

    records = await manager.get_all()

    assert len(records) == 2
    assert {r.name for r in records} == {"A", "B"}


@pytest.mark.asyncio
async def test_get_all_orders_by_day_of_week(manager_factory):
    """Тест получения всех записей по дню недели."""
    manager = manager_factory(
        ScheduleImageManager, image_repo=ScheduleImageRepositoryService()
    )

    await manager.create(_sample_create(name="late", day_of_week=DayOfWeek.FRIDAY))
    await manager.create(_sample_create(name="early", day_of_week=DayOfWeek.MONDAY))

    records = await manager.get_all()

    assert [r.name for r in records] == ["early", "late"]


@pytest.mark.asyncio
async def test_update_partial_fields(manager_factory):
    """Тест частичного обновления полей."""
    manager = manager_factory(
        ScheduleImageManager, image_repo=ScheduleImageRepositoryService()
    )

    created = await manager.create(_sample_create(name="Before"))

    updated = await manager.update(created.id, ScheduleImageUpdate(name="After"))

    assert updated.id == created.id
    assert updated.name == "After"
    assert updated.image == created.image  # unchanged
    assert updated.is_active == created.is_active  # unchanged


@pytest.mark.asyncio
async def test_update_missing_raises_404(manager_factory):
    """Тест выброса HTTP 404 при редактировании изображения с несуществующим ID."""
    manager = manager_factory(
        ScheduleImageManager, image_repo=ScheduleImageRepositoryService()
    )
    with pytest.raises(Exception) as excinfo:
        await manager.update(uuid.uuid4(), ScheduleImageUpdate(name="X"))

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_update_with_empty_payload_raises_400(manager_factory):
    """Тест выброса HTTP 400 при пустом payload."""
    manager = manager_factory(
        ScheduleImageManager, image_repo=ScheduleImageRepositoryService()
    )
    created = await manager.create(_sample_create())

    with pytest.raises(Exception) as excinfo:
        await manager.update(created.id, ScheduleImageUpdate())

    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_removes_record(manager_factory, async_session_maker):
    """Тест удаления записи."""
    manager = manager_factory(
        ScheduleImageManager, image_repo=ScheduleImageRepositoryService()
    )
    created = await manager.create(_sample_create())

    await manager.delete(created.id)

    with pytest.raises(Exception) as excinfo:
        await manager.get(created.id)

    assert excinfo.value.status_code == 404

    async with async_session_maker() as session:
        result = await session.execute(
            select(ScheduleImage).where(ScheduleImage.id == created.id)
        )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_missing_raises_404(manager_factory):
    """Тест выброса HTTP 404 при удалении несуществующего изображения."""
    manager = manager_factory(
        ScheduleImageManager, image_repo=ScheduleImageRepositoryService()
    )

    with pytest.raises(Exception) as excinfo:
        await manager.delete(uuid.uuid4())

    assert excinfo.value.status_code == 404
