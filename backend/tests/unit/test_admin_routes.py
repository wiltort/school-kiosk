"""Тесты HTTP-эндпоинтов админ-панели (src/apps/admin/routes.py)."""

import pytest
from src.apps.admin.repositories import AdminRepository
from src.core.config import settings
from src.core.security import hash_password


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


def test_changing_schedule_mode_inactivates_all_schedules(
    client, monkeypatch, tmp_path
):
    # Направляем каталог данных в temp, чтобы не трогать реальный data_dir.
    monkeypatch.setenv("SCHOOL_KIOSK_DATA_DIR", str(tmp_path))

    response = client.post(
        "/api/v1/schedule-images/",
        data={"name": "Расписание 1", "day_of_week": 1, "is_active": True},
        files={"image": ("image.png", b"x", "image/png")},
    )
    assert response.status_code == 201
    schedule = response.json()
    assert schedule["is_active"] is True

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
    assert body["schedule_mode"] == "single"

    # Обновляем настройки: папку локальных расписаний, режим, приветствие, автозапуск.
    updated = client.put(
        "/api/v1/admin/settings",
        headers=headers,
        json={
            "local_image_dir": "C:/KioskLocal",
            "schedule_mode": "single",
            "welcome_message": "Добро пожаловать!",
            "autostart": True,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["schedule_mode"] == "single"
    response = client.get(f"/api/v1/schedule-images/{schedule['id']}")
    assert response.status_code == 200
    assert response.json()["is_active"] is True

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
    assert updated.json()["schedule_mode"] == "week"
    response = client.get(f"/api/v1/schedule-images/{schedule['id']}")
    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_default_admin_login_blocked_when_non_default_exists(
    client, async_session_maker
):
    """Вход под дефолтным админом невозможен, если есть недефолтные админы."""
    # Недефолтный админ добавляется напрямую в БД (через API его не создать).
    repo = AdminRepository()
    async with async_session_maker() as session:
        await repo.create(
            session,
            {
                "login": "custom-admin",
                "password_hash": hash_password("custom-pass"),
                "email": None,
                "fullname": "Пользовательский админ",
                "is_active": True,
                "is_default": False,
            },
        )
        await session.commit()

    response = client.post(
        "/api/v1/admin/login",
        json={
            "login": settings.default_admin_login,
            "password": settings.default_admin_password,
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный логин или пароль"


def _login_default_admin(client) -> dict[str, str]:
    """Входит под дефолтным админом и возвращает заголовок авторизации."""
    login = client.post(
        "/api/v1/admin/login",
        json={
            "login": settings.default_admin_login,
            "password": settings.default_admin_password,
        },
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


def _create_admin_via_api(
    client, headers: dict[str, str], login: str, password: str, fullname: str
) -> dict:
    """Создаёт админа через API и возвращает тело ответа."""
    response = client.post(
        "/api/v1/admin/",
        headers=headers,
        json={"login": login, "password": password, "fullname": fullname},
    )
    assert response.status_code == 201
    return response.json()


def test_me_and_create_admin_require_auth(client):
    """Новые роуты недоступны без Bearer-токена."""
    assert client.get("/api/v1/admin/me").status_code == 401
    assert client.patch("/api/v1/admin/me", json={}).status_code == 401
    assert client.post("/api/v1/admin/", json={}).status_code == 401


def test_get_me_returns_current_admin_profile(client):
    """GET /me возвращает данные админа, выдавшего токен."""
    headers = _login_default_admin(client)

    response = client.get("/api/v1/admin/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["login"] == settings.default_admin_login
    assert body["is_default"] is True
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


def test_get_me_invalid_token(client):
    """GET /me с несуществующим токеном возвращает 401."""
    response = client.get(
        "/api/v1/admin/me", headers={"Authorization": "Bearer no-such-token"}
    )
    assert response.status_code == 401


def test_create_admin_profile(client):
    """POST / создаёт нового админа, и он может войти."""
    headers = _login_default_admin(client)

    created = _create_admin_via_api(
        client,
        headers,
        login="deputy",
        password="deputy-pass",  # noqa S106
        fullname="Заместитель директора",
    )
    assert created["login"] == "deputy"
    assert created["fullname"] == "Заместитель директора"
    assert created["email"] is None
    assert created["is_default"] is False
    assert created["is_active"] is True

    # Новый админ может войти и увидеть свой профиль.
    deputy_login = client.post(
        "/api/v1/admin/login",
        json={"login": "deputy", "password": "deputy-pass"},
    )
    assert deputy_login.status_code == 200
    deputy_headers = {"Authorization": f"Bearer {deputy_login.json()['token']}"}
    me = client.get("/api/v1/admin/me", headers=deputy_headers)
    assert me.status_code == 200
    assert me.json()["id"] == created["id"]
    assert me.json()["login"] == "deputy"


def test_create_admin_without_required_fields(client):
    """POST / без обязательных полей (логин/пароль/имя) возвращает 422."""
    headers = _login_default_admin(client)

    assert client.post("/api/v1/admin/", headers=headers, json={}).status_code == 422
    assert (
        client.post(
            "/api/v1/admin/",
            headers=headers,
            json={"login": "no-password", "fullname": "Без пароля"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/admin/",
            headers=headers,
            json={"login": "no-name", "password": "pass"},
        ).status_code
        == 422
    )


def test_create_admin_with_duplicate_login(client):
    """POST / с уже занятым логином возвращает 400."""
    headers = _login_default_admin(client)

    response = client.post(
        "/api/v1/admin/",
        headers=headers,
        json={
            "login": settings.default_admin_login,
            "password": "any-pass",
            "fullname": "Дубликат",
        },
    )
    assert response.status_code == 400


def test_patch_me_rejected_for_default_admin(client):
    """PATCH /me для дефолтного админа запрещён (404)."""
    headers = _login_default_admin(client)

    response = client.patch(
        "/api/v1/admin/me",
        headers=headers,
        json={"fullname": "Новое имя"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Админ не найден"


def test_patch_me_updates_profile(client):
    """PATCH /me меняет логин и имя недефолтного админа."""
    headers = _login_default_admin(client)
    created = _create_admin_via_api(
        client,
        headers,
        login="teacher",
        password="teacher-pass",  # noqa S106
        fullname="Учитель",
    )

    deputy_login = client.post(
        "/api/v1/admin/login",
        json={"login": "teacher", "password": "teacher-pass"},
    )
    deputy_headers = {"Authorization": f"Bearer {deputy_login.json()['token']}"}

    updated = client.patch(
        "/api/v1/admin/me",
        headers=deputy_headers,
        json={"login": "teacher2", "fullname": "Учитель обновлённый"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["id"] == created["id"]
    assert body["login"] == "teacher2"
    assert body["fullname"] == "Учитель обновлённый"

    # Обновлённый логин может войти, старый — нет.
    assert (
        client.post(
            "/api/v1/admin/login", json={"login": "teacher", "password": "teacher-pass"}
        ).status_code
        == 401
    )
    relogin = client.post(
        "/api/v1/admin/login", json={"login": "teacher2", "password": "teacher-pass"}
    )
    assert relogin.status_code == 200


def test_patch_me_duplicate_login(client):
    """PATCH /me не позволяет занять чужой логин (400)."""
    headers = _login_default_admin(client)
    _create_admin_via_api(
        client,
        headers,
        login="teacher",
        password="teacher-pass",  # noqa S106
        fullname="Учитель",
    )

    deputy_login = client.post(
        "/api/v1/admin/login",
        json={"login": "teacher", "password": "teacher-pass"},
    )
    deputy_headers = {"Authorization": f"Bearer {deputy_login.json()['token']}"}

    response = client.patch(
        "/api/v1/admin/me",
        headers=deputy_headers,
        json={"login": settings.default_admin_login},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Админ с таким логином уже существует"


def test_patch_me_empty_payload(client):
    """PATCH /me с пустым телом возвращает 400."""
    headers = _login_default_admin(client)
    _create_admin_via_api(
        client,
        headers,
        login="teacher",
        password="teacher-pass",  # noqa S106
        fullname="Учитель",
    )

    deputy_login = client.post(
        "/api/v1/admin/login",
        json={"login": "teacher", "password": "teacher-pass"},
    )
    deputy_headers = {"Authorization": f"Bearer {deputy_login.json()['token']}"}

    response = client.patch("/api/v1/admin/me", headers=deputy_headers, json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Нет данных для обновления"


def test_patch_me_password_change_revokes_tokens(client):
    """Смена пароля через PATCH /me отзывает старые токены."""
    headers = _login_default_admin(client)
    _create_admin_via_api(
        client,
        headers,
        login="teacher",
        password="teacher-pass",  # noqa S106
        fullname="Учитель",
    )

    old_login = client.post(
        "/api/v1/admin/login",
        json={"login": "teacher", "password": "teacher-pass"},
    )
    old_headers = {"Authorization": f"Bearer {old_login.json()['token']}"}

    updated = client.patch(
        "/api/v1/admin/me",
        headers=old_headers,
        json={"password": "new-pass"},
    )
    assert updated.status_code == 200

    # Старый токен больше не работает.
    assert client.get("/api/v1/admin/me", headers=old_headers).status_code == 401

    # Со старым паролем вход невозможен, с новым — возможен.
    assert (
        client.post(
            "/api/v1/admin/login", json={"login": "teacher", "password": "teacher-pass"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/admin/login", json={"login": "teacher", "password": "new-pass"}
        ).status_code
        == 200
    )


def test_delete_me_requires_auth(client):
    """DELETE /me недоступен без Bearer-токена."""
    assert client.delete("/api/v1/admin/me").status_code == 401


def test_delete_me_rejected_for_default_admin(client):
    """DELETE /me для дефолтного админа запрещён (404), профиль сохраняется."""
    headers = _login_default_admin(client)

    response = client.delete("/api/v1/admin/me", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Админ не найден"

    # Дефолтный админ не удалён и продолжает работать.
    assert client.get("/api/v1/admin/me", headers=headers).status_code == 200


def test_delete_me_removes_admin_and_blocks_his_tokens(client):
    """DELETE /me удаляет недефолтного админа и делает его токен/пароль недействительными."""
    headers = _login_default_admin(client)
    _create_admin_via_api(
        client,
        headers,
        login="teacher",
        password="teacher-pass",  # noqa S106
        fullname="Учитель",
    )

    teacher_login = client.post(
        "/api/v1/admin/login",
        json={"login": "teacher", "password": "teacher-pass"},
    )
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['token']}"}
    assert client.get("/api/v1/admin/me", headers=teacher_headers).status_code == 200

    deleted = client.delete("/api/v1/admin/me", headers=teacher_headers)
    assert deleted.status_code == 204

    # Токен удалённого админа больше не даёт доступа к профилю.
    assert client.get("/api/v1/admin/me", headers=teacher_headers).status_code != 200

    # Вход под удалённым админом невозможен.
    assert (
        client.post(
            "/api/v1/admin/login", json={"login": "teacher", "password": "teacher-pass"}
        ).status_code
        == 401
    )

    # После удаления единственного недефолтного админа дефолтный снова может войти.
    assert (
        client.post(
            "/api/v1/admin/login",
            json={
                "login": settings.default_admin_login,
                "password": settings.default_admin_password,
            },
        ).status_code
        == 200
    )
