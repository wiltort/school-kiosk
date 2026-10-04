"""Тесты репозитория администраторов (src/apps/admin/repositories.py)."""

import pytest
from src.apps.admin.repositories import AdminRepository
from src.core.security import hash_password


def _admin_data(login: str, password: str = "secret") -> dict:  # noqa: S107
    """Данные для создания AdminProfile через репозиторий."""
    return {
        "login": login,
        "password_hash": hash_password(password),
        "email": None,
        "is_active": True,
        "is_default": False,
    }


@pytest.mark.asyncio
async def test_create_and_get_by_login(async_session):
    """create() сохраняет администратора, get_by_login() находит его."""
    repo = AdminRepository()
    admin = await repo.create(async_session, _admin_data("admin-1"))

    assert admin.id is not None
    assert admin.created_at is not None

    found = await repo.get_by_login(async_session, "admin-1")
    assert found is not None
    assert found.id == admin.id
    assert found.login == "admin-1"
    assert found.password_hash != "secret"  # noqa: S105 — пароль не хранится в открытом виде


@pytest.mark.asyncio
async def test_get_by_login_missing_returns_none(async_session):
    """get_by_login() возвращает None для несуществующего логина."""
    repo = AdminRepository()
    assert await repo.get_by_login(async_session, "no-such-login") is None


@pytest.mark.asyncio
async def test_update_changes_fields(async_session):
    """update() изменяет поля и сохраняет изменения."""
    repo = AdminRepository()
    admin = await repo.create(async_session, _admin_data("admin-2"))

    updated = await repo.update(
        async_session,
        admin,
        {"is_active": False, "email": "admin2@example.com"},
    )
    assert updated.is_active is False
    assert updated.email == "admin2@example.com"

    reloaded = await repo.get_by_login(async_session, "admin-2")
    assert reloaded.is_active is False
    assert reloaded.email == "admin2@example.com"


@pytest.mark.asyncio
async def test_delete_removes_admin(async_session):
    """delete() удаляет администратора из БД."""
    repo = AdminRepository()
    admin = await repo.create(async_session, _admin_data("admin-3"))

    await repo.delete(async_session, admin)

    assert await repo.get_by_login(async_session, "admin-3") is None


@pytest.mark.asyncio
async def test_count_counts_all_admins(async_session):
    """count() возвращает количество администраторов."""
    repo = AdminRepository()
    assert await repo.count(async_session) == 0

    await repo.create(async_session, _admin_data("count-1"))
    await repo.create(async_session, _admin_data("count-2"))

    assert await repo.count(async_session) == 2
