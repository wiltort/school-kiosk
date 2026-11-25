"""API-тесты новых разделов: kiosk config, объявления, сервисы, настройки."""

import pytest
from src.core.config import settings
from src.core.settings_schema import DEFAULT_APP_UNITS
from src.models import AppUnit


def _login_default_admin(client) -> dict[str, str]:
    """Входит под дефолтным админом и возвращает заголовок авторизации."""
    response = client.post(
        "/api/v1/admin/login",
        json={
            "login": settings.default_admin_login,
            "password": settings.default_admin_password,
        },
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _seed_units() -> list[AppUnit]:
    return [AppUnit(**unit) for unit in DEFAULT_APP_UNITS]


@pytest.mark.asyncio
async def test_kiosk_config_contains_units(client, async_session_maker):
    """Публичный конфиг отдаёт включённые сервисы и флаги."""
    async with async_session_maker() as session:
        session.add_all(_seed_units())
        await session.commit()

    response = client.get("/api/v1/kiosk/config")
    assert response.status_code == 200
    body = response.json()
    assert [unit["key"] for unit in body["units"]] == [
        "schedule",
        "weather",
        "announcements",
    ]
    assert body["announcements_ticker_enabled"] is True
    assert body["weather_location"] == "Москва"


@pytest.mark.asyncio
async def test_announcements_public_and_admin_flow(client):
    """Создание, публикация, выключение и удаление объявления."""
    headers = _login_default_admin(client)

    created = client.post(
        "/api/v1/admin/announcements/",
        headers=headers,
        json={"title": "Важно", "body": "Линейка в 8:00"},
    )
    assert created.status_code == 201
    announcement_id = created.json()["id"]

    public = client.get("/api/v1/announcements/active")
    assert public.status_code == 200
    assert [item["id"] for item in public.json()] == [announcement_id]

    hidden = client.patch(
        f"/api/v1/admin/announcements/{announcement_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert hidden.status_code == 200
    assert hidden.json()["is_active"] is False
    assert client.get("/api/v1/announcements/active").json() == []

    deleted = client.delete(
        f"/api/v1/admin/announcements/{announcement_id}",
        headers=headers,
    )
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_announcements_require_auth(client):
    """Админские операции с объявлениями требуют токен."""
    assert client.get("/api/v1/admin/announcements/").status_code == 401
    assert (
        client.post(
            "/api/v1/admin/announcements/",
            json={"title": "x", "body": "y"},
        ).status_code
        == 401
    )


@pytest.mark.asyncio
async def test_units_admin_flow(client, async_session_maker):
    """Список, выключение и переупорядочивание сервисов."""
    async with async_session_maker() as session:
        session.add_all(_seed_units())
        await session.commit()

    headers = _login_default_admin(client)

    listed = client.get("/api/v1/admin/units/", headers=headers)
    assert listed.status_code == 200
    assert [unit["key"] for unit in listed.json()] == [
        "schedule",
        "weather",
        "announcements",
    ]

    updated = client.patch(
        "/api/v1/admin/units/weather",
        headers=headers,
        json={"is_enabled": False},
    )
    assert updated.status_code == 200
    assert updated.json()["is_enabled"] is False

    reordered = client.put(
        "/api/v1/admin/units/order",
        headers=headers,
        json={"keys": ["announcements", "weather", "schedule"]},
    )
    assert reordered.status_code == 200
    assert [unit["key"] for unit in reordered.json()] == [
        "announcements",
        "weather",
        "schedule",
    ]


@pytest.mark.asyncio
async def test_admin_settings_weather_and_announcements_fields(client):
    """Новые поля настроек сохраняются и читаются."""
    headers = _login_default_admin(client)

    response = client.put(
        "/api/v1/admin/settings",
        headers=headers,
        json={
            "local_image_dir": None,
            "schedule_mode": "single",
            "welcome_message": None,
            "autostart": False,
            "weather_enabled": True,
            "weather_api": "wttr.in",
            "weather_location": "Казань",
            "weather_refresh_interval_minutes": 30,
            "announcements_enabled": True,
            "announcements_ticker_enabled": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["weather_enabled"] is True
    assert body["weather_location"] == "Казань"
    assert body["weather_refresh_interval_minutes"] == 30
    assert body["announcements_ticker_enabled"] is False

    reloaded = client.get("/api/v1/admin/settings", headers=headers)
    assert reloaded.json()["weather_location"] == "Казань"
    assert reloaded.json()["announcements_ticker_enabled"] is False
