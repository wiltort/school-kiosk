"""Юнит-тесты для модели ScheduleImage."""

import uuid

import pytest
from sqlalchemy import Boolean, String
from src.apps.schedule.repositories import ScheduleImageRepository
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


@pytest.mark.asyncio
async def test_repository_get_populate_existing_bypasses_identity_map(
    async_session_maker,
):
    """get(populate_existing=True) читает данные из БД, минуя identity map."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        image = ScheduleImage(image="a.png")
        session.add(image)
        await session.commit()

        loaded = await repo.get(session, image.id)
        assert loaded is not None and loaded.name == "Untitled"

        loaded.name = "Dirty"  # грязное изменение без flush
        cached = await repo.get(session, image.id)
        assert cached is loaded  # identity map вернул тот же объект

        fresh = await repo.get(session, image.id, populate_existing=True)
        assert fresh is loaded  # тот же экземпляр, но атрибуты перечитаны
        assert fresh.name == "Untitled"


@pytest.mark.asyncio
async def test_repository_get_local_by_name_finds_active_local(async_session_maker):
    """get_local_by_name находит активную локальную запись по имени."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        image = ScheduleImage(
            image="local/a.png", name="Локальное", is_local=True, is_active=True
        )
        session.add(image)
        await session.commit()

        found = await repo.get_local_by_name(session, "Локальное")

        assert found is not None
        assert found.id == image.id


@pytest.mark.asyncio
async def test_repository_get_local_by_name_ignores_inactive(async_session_maker):
    """get_local_by_name игнорирует неактивные записи."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        session.add(
            ScheduleImage(
                image="local/a.png", name="Локальное", is_local=True, is_active=False
            )
        )
        await session.commit()

        found = await repo.get_local_by_name(session, "Локальное")

        assert found is None


@pytest.mark.asyncio
async def test_repository_get_local_by_name_ignores_non_local(async_session_maker):
    """get_local_by_name игнорирует нелокальные записи."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        session.add(
            ScheduleImage(
                image="a.png", name="Локальное", is_local=False, is_active=True
            )
        )
        await session.commit()

        found = await repo.get_local_by_name(session, "Локальное")

        assert found is None


@pytest.mark.asyncio
async def test_repository_get_local_by_name_missing_returns_none(async_session_maker):
    """get_local_by_name возвращает None для несуществующего имени."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        session.add(
            ScheduleImage(
                image="local/a.png", name="Другое", is_local=True, is_active=True
            )
        )
        await session.commit()

        found = await repo.get_local_by_name(session, "Локальное")

        assert found is None


@pytest.mark.asyncio
async def test_repository_get_by_path_finds_by_image_path(async_session_maker):
    """get_by_path ищет записи по пути файла (колонка image)."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        image = ScheduleImage(image="local/a.png", is_active=True)
        session.add(image)
        await session.commit()

        found = await repo.get_by_path(session, "local/a.png")

        assert found is not None
        assert found.id == image.id


@pytest.mark.asyncio
async def test_repository_get_by_path_with_is_local_filter(async_session_maker):
    """get_by_path учитывает фильтр is_local."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        image = ScheduleImage(image="local/a.png", is_local=True, is_active=True)
        session.add(image)
        await session.commit()

        found = await repo.get_by_path(session, "local/a.png", is_local=True)
        assert found is not None and found.id == image.id

        missing = await repo.get_by_path(session, "local/a.png", is_local=False)
        assert missing is None


@pytest.mark.asyncio
async def test_repository_get_by_path_ignores_inactive_by_default(
    async_session_maker,
):
    """get_by_path по умолчанию ищет только активные записи."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        image = ScheduleImage(image="local/a.png", is_active=False)
        session.add(image)
        await session.commit()

        assert await repo.get_by_path(session, "local/a.png") is None

        found = await repo.get_by_path(session, "local/a.png", is_active=False)
        assert found is not None and found.id == image.id


@pytest.mark.asyncio
async def test_repository_get_by_path_missing_returns_none(async_session_maker):
    """get_by_path возвращает None для отсутствующего пути."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        session.add(ScheduleImage(image="local/a.png", is_active=True))
        await session.commit()

        found = await repo.get_by_path(session, "local/ghost.png")

        assert found is None


@pytest.mark.asyncio
async def test_repository_filter_by_single_field(async_session_maker):
    """filter возвращает записи по одному условию."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        active = ScheduleImage(image="a.png", is_active=True)
        inactive = ScheduleImage(image="b.png", is_active=False)
        session.add_all([active, inactive])
        await session.commit()

        found = await repo.filter(session, is_active=True)

        assert [item.id for item in found] == [active.id]


@pytest.mark.asyncio
async def test_repository_filter_by_multiple_fields(async_session_maker):
    """filter объединяет несколько условий через AND."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        first = ScheduleImage(image="a.png", name="A", is_local=True, is_active=True)
        second = ScheduleImage(image="b.png", name="B", is_local=True, is_active=True)
        third = ScheduleImage(image="c.png", name="C", is_local=False, is_active=True)
        session.add_all([first, second, third])
        await session.commit()

        found = await repo.filter(session, is_local=True, is_active=True)

        assert {item.id for item in found} == {first.id, second.id}


@pytest.mark.asyncio
async def test_repository_filter_empty_kwargs_returns_empty(async_session_maker):
    """filter без условий возвращает пустой список."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        session.add(ScheduleImage(image="a.png", is_active=True))
        await session.commit()

        assert await repo.filter(session) == []


@pytest.mark.asyncio
async def test_repository_filter_no_match_returns_empty(async_session_maker):
    """filter возвращает пустой список, если записи не найдены."""
    repo = ScheduleImageRepository()
    async with async_session_maker() as session:
        session.add(ScheduleImage(image="a.png", is_active=False))
        await session.commit()

        found = await repo.filter(session, is_active=True)

        assert found == []
