"""Тесты HTTP-эндпоинтов админ-панели (src/apps/admin/routes.py)."""

from src.core.config import settings


def test_login_with_wrong_credentials(client):
    response = client.post(
        "/api/v1/admin/login",
        json={"login": "admin", "password": "wrong"},
    )
    assert response.status_code == 401


def test_settings_requires_auth(client):
    assert client.get("/api/v1/admin/settings").status_code == 401
    assert client.put("/api/v1/admin/settings", json={}).status_code == 401


def test_login_and_settings_flow(client, monkeypatch, tmp_path):
    # Направляем каталог данных в temp, чтобы не трогать реальный data_dir.
    monkeypatch.setenv("SCHOOL_KIOSK_DATA_DIR", str(tmp_path))

    # Вход.
    login = client.post(
        "/api/v1/admin/login",
        json={
            "login": settings.default_admin_login,
            "password": settings.default_admin_password,
        },
    )
    assert login.status_code == 200
    token = login.json()["token"]
    assert token

    headers = {"Authorization": f"Bearer {token}"}

    # Изначальные значения по умолчанию.
    initial = client.get("/api/v1/admin/settings", headers=headers)
    assert initial.status_code == 200
    body = initial.json()
    assert body["static_dir"] is None
    assert body["autostart"] is False
    assert "autostart_supported" in body

    # Обновляем папку изображений и автозагрузку.
    updated = client.put(
        "/api/v1/admin/settings",
        headers=headers,
        json={"static_dir": "D:/KioskStatic", "autostart": True},
    )
    assert updated.status_code == 200
    assert updated.json()["static_dir"] == "D:/KioskStatic"
    assert updated.json()["autostart"] is True

    # Значение сохранилось и читается повторно.
    reloaded = client.get("/api/v1/admin/settings", headers=headers)
    assert reloaded.json()["static_dir"] == "D:/KioskStatic"

    # Файл настроек реально создан в data_dir.
    assert (tmp_path / "settings.json").is_file()

    # Пустая строка сбрасывает папку на значение по умолчанию.
    reset = client.put(
        "/api/v1/admin/settings",
        headers=headers,
        json={"static_dir": "", "autostart": False},
    )
    assert reset.json()["static_dir"] is None

    # Выход инвалидирует токен.
    assert client.post("/api/v1/admin/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/admin/settings", headers=headers).status_code == 401
