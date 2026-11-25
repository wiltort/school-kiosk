"""Тесты менеджера объявлений."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from src.apps.announcements.managers import AnnouncementManager
from src.apps.announcements.repositories import AnnouncementRepository
from src.apps.announcements.schemas import AnnouncementCreate, AnnouncementUpdate
from src.core.database import DBDependency
from src.enums.announcements import AnnouncementKind


@pytest.fixture
def manager(async_session_maker):
    """Менеджер объявлений поверх тестовой in-memory БД."""
    return AnnouncementManager(
        db=DBDependency(async_session_maker),
        repo=AnnouncementRepository(),
    )


@pytest.mark.asyncio
async def test_create_and_list_active(manager):
    """Созданное активное объявление попадает в публичную ленту."""
    created = await manager.create(AnnouncementCreate(title="Новость", body="Текст"))
    assert created.title == "Новость"

    items = await manager.list_active()
    assert [item.id for item in items] == [created.id]


@pytest.mark.asyncio
async def test_time_window_filters(manager):
    """Будущие и истёкшие объявления не показываются."""
    now = datetime.now(UTC)
    await manager.create(
        AnnouncementCreate(
            title="Будущее",
            body="x",
            starts_at=now + timedelta(days=1),
        )
    )
    await manager.create(
        AnnouncementCreate(
            title="Истекло",
            body="x",
            expires_at=now - timedelta(days=1),
        )
    )
    active = await manager.create(
        AnnouncementCreate(
            title="Сейчас",
            body="x",
            starts_at=now - timedelta(hours=1),
            expires_at=now + timedelta(hours=1),
        )
    )

    items = await manager.list_active()
    assert [item.id for item in items] == [active.id]


@pytest.mark.asyncio
async def test_kind_filter(manager):
    """Фильтр по виду включает объявления «везде»."""
    ticker = await manager.create(
        AnnouncementCreate(title="Бегущая", body="x", kind=AnnouncementKind.TICKER)
    )
    feed = await manager.create(
        AnnouncementCreate(title="Лента", body="x", kind=AnnouncementKind.FEED)
    )
    both = await manager.create(
        AnnouncementCreate(title="Везде", body="x", kind=AnnouncementKind.BOTH)
    )

    ticker_ids = {
        item.id for item in await manager.list_active(AnnouncementKind.TICKER)
    }
    assert ticker_ids == {ticker.id, both.id}

    feed_ids = {item.id for item in await manager.list_active(AnnouncementKind.FEED)}
    assert feed_ids == {feed.id, both.id}

    both_ids = {item.id for item in await manager.list_active(AnnouncementKind.BOTH)}
    assert both_ids == {both.id}


@pytest.mark.asyncio
async def test_invalid_window_rejected(manager):
    """Дата окончания должна быть позже даты начала."""
    now = datetime.now(UTC)
    with pytest.raises(HTTPException) as exc:
        await manager.create(
            AnnouncementCreate(
                title="x",
                body="x",
                starts_at=now,
                expires_at=now,
            )
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_and_delete(manager):
    """Обновление и удаление объявления."""
    created = await manager.create(AnnouncementCreate(title="Старое", body="x"))
    updated = await manager.update(
        created.id,
        AnnouncementUpdate(title="Новое", is_active=False),
    )
    assert updated.title == "Новое"
    assert updated.is_active is False

    await manager.delete(created.id)
    with pytest.raises(HTTPException) as exc:
        await manager.get(created.id)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_missing_raises(manager):
    """Несуществующее объявление даёт 404."""
    with pytest.raises(HTTPException) as exc:
        await manager.get(uuid.uuid4())
    assert exc.value.status_code == 404
