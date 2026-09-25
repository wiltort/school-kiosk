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
    assert body["local_image_dir"] is None
    assert body["schedule_mode"] == "single"
    assert body["welcome_message"] is None
    assert body["autostart"] is False
    assert "autostart_supported" in body

    # Обновляем настройки: папку локальных расписаний, режим, приветствие, автозапуск.
    updated = client.put(
        "/api/v1/admin/settings",
        headers=headers,
        json={
            "local_image_dir": "C:/KioskLocal",
            "schedule_mode": "week",
            "welcome_message": "Добро пожаловать!",
            "autostart": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["local_image_dir"] == "C:/KioskLocal"
    assert updated.json()["schedule_mode"] == "week"
    assert updated.json()["welcome_message"] == "Добро пожаловать!"
    assert updated.json()["autostart"] is True

    # Значения сохранились и читаются повторно.
    reloaded = client.get("/api/v1/admin/settings", headers=headers)
    assert reloaded.json()["local_image_dir"] == "C:/KioskLocal"
    assert reloaded.json()["schedule_mode"] == "week"
    assert reloaded.json()["welcome_message"] == "Добро пожаловать!"

    # Файл настроек реально создан в data_dir.
    assert (tmp_path / "settings.json").is_file()

    # Пустые строки сбрасывают папку и приветствие на значение по умолчанию.
    reset = client.put(
        "/api/v1/admin/settings",
        headers=headers,
        json={
            "local_image_dir": "",
            "schedule_mode": "single",
            "welcome_message": "",
            "autostart": False,
        },
    )
    assert reset.json()["local_image_dir"] is None
    assert reset.json()["welcome_message"] is None
    assert reset.json()["schedule_mode"] == "single"

    # Выход инвалидирует токен.
    assert client.post("/api/v1/admin/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/admin/settings", headers=headers).status_code == 401


def test_kiosk_config_is_public(client, monkeypatch, tmp_path):
    """Публичная конфигурация киоска доступна без авторизации."""
    monkeypatch.setenv("SCHOOL_KIOSK_DATA_DIR", str(tmp_path))

    response = client.get("/api/v1/kiosk/config")
    assert response.status_code == 200
    body = response.json()
    assert body["welcome_message"] is None
    assert body["schedule_mode"] == "single"

    # Сохранённое приветствие отдаётся публичному эндпоинту.
    login = client.post(
        "/api/v1/admin/login",
        json={
            "login": settings.default_admin_login,
            "password": settings.default_admin_password,
        },
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    client.put(
        "/api/v1/admin/settings",
        headers=headers,
        json={
            "local_image_dir": None,
            "schedule_mode": "week",
            "welcome_message": "Привет, школа!",
            "autostart": False,
        },
    )
    refreshed = client.get("/api/v1/kiosk/config")
    assert refreshed.json()["welcome_message"] == "Привет, школа!"
    assert refreshed.json()["schedule_mode"] == "week"
