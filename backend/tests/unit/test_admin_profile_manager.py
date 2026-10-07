"""Юнит-тесты для AdminProfileManager."""

import uuid

import pytest
from src.apps.admin.auth import AuthManager
from src.apps.admin.managers import AdminProfileManager
from src.apps.admin.repositories import AdminRepository, AdminTokenRepository
from src.apps.admin.schemas import AdminAuth, AdminProfileCreate, AdminProfileUpdate


def _sample_admin_profile(**overrides) -> AdminProfileCreate:
    payload = {
        "login": "admin_1",
        "password": "password",
        "fullname": "Иванов Иван Иванович",
    }
    payload.update(overrides)
    return AdminProfileCreate(**payload)


def _admin_profile_manager(manager_factory):
    token_repo = AdminTokenRepository()
    return manager_factory(
        AdminProfileManager,
        admin_repo=AdminRepository(),
        token_repo=token_repo,
        auth_manager=manager_factory(
            AuthManager,
            token_repo=token_repo,
        ),
    )


@pytest.mark.asyncio
async def test_create_admin_profile(manager_factory):
    """Проверка создания профиля админа."""
    manager = _admin_profile_manager(manager_factory)
    created = await manager.create(_sample_admin_profile())
    created_dict = created.model_dump()
    assert isinstance(created_dict.pop("id"), uuid.UUID)
    assert hasattr(created, "password") is False
    assert hasattr(created, "password_hash") is False
    assert created_dict.pop("created_at") is not None
    assert created_dict.pop("updated_at") is not None
    assert created_dict == {
        "login": "admin_1",
        "fullname": "Иванов Иван Иванович",
        "email": None,
        "is_active": True,
        "is_default": False,
    }


@pytest.mark.asyncio
async def test_update_admin_profile(manager_factory):
    """Проверка редактирования профиля"""

    manager = _admin_profile_manager(manager_factory)
    created = await manager.create(_sample_admin_profile())
    payload = AdminProfileUpdate(login="admin_2", fullname="Петров")

    updated = await manager.update(created.id, payload)
    updated_data = updated.model_dump()
    updated_at = updated_data.pop("updated_at")
    assert created.updated_at != updated_at
    assert bool(updated_at)
    assert updated_data == {
        "id": created.id,
        "login": "admin_2",
        "fullname": "Петров",
        "email": None,
        "is_active": True,
        "is_default": False,
        "created_at": created.created_at,
    }


@pytest.mark.asyncio
async def test_delete_admin(manager_factory):
    """Проверка удаления профиля"""
    manager = _admin_profile_manager(manager_factory)

    created = await manager.create(_sample_admin_profile())

    await manager.delete(created.id)

    with pytest.raises(Exception) as excinfo:
        await manager.delete(created.id)

    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "Админ не найден"


@pytest.mark.asyncio
async def test_authenticate_admin(manager_factory):
    """Проверка аутентификации."""
    manager = _admin_profile_manager(manager_factory)

    await manager.create(_sample_admin_profile())
    auth = AdminAuth(login="admin_1", password="password")  # noqa S106

    token_data = await manager.authenticate(auth)
    token = token_data.token
    assert token is not None
    assert isinstance(token, str)
    assert len(token) == 43


@pytest.mark.asyncio
async def test_auth_after_deleting_admin(manager_factory):
    """Проверка авторизации после удаления админа."""
    manager = _admin_profile_manager(manager_factory)

    created = await manager.create(_sample_admin_profile())
    auth = AdminAuth(login="admin_1", password="password")  # noqa S106

    token_data = await manager.authenticate(auth)
    token = token_data.token
    assert token is not None
    assert isinstance(token, str)
    assert len(token) == 43

    await manager.delete(created.id)
    with pytest.raises(Exception) as excinfo:
        await manager.authenticate(auth)

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Неверный логин или пароль"
