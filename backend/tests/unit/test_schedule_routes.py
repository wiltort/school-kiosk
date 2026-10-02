"""Юнит-тесты для проверки эндпойнтов расписаний."""

import uuid

from freezegun import freeze_time
from src.apps.schedule.routes import (
    local_schedule_image_router,
    schedule_image_router,
)
from src.enums.schedule import DayOfWeek

CREATE_URL = "/api/v1/schedule-images/"
GET_TODAY_URL = "/api/v1/schedule-images/get-today-schedule"
GET_NEXT_URL = "/api/v1/schedule-images/get-next-schedule"
GET_SINGLE_URL = "/api/v1/schedule-images/get-single-schedule"
CREATE_LOCAL_URL = "/api/v1/schedule-images/create-local"
LOCAL_SCHEDULE_URL = "/api/v1/schedule-images-local/"
RESET_SCHEDULES_URL = "/api/v1/schedule-images/reset-schedules"


def schedule_image_valid_payload(**overrides) -> dict:
    payload = {
        "name": "Расписание 1",
        "is_active": True,
        "day_of_week": DayOfWeek.MONDAY.value,
    }
    payload.update(overrides)
    return payload


def _post_schedule_image(client, filename="schedule.png", **overrides):
    """Отправляет multipart-запрос на создание расписания."""
    data = schedule_image_valid_payload(**overrides)
    return client.post(
        CREATE_URL,
        data=data,
        files={"image": (filename, b"image-bytes", "image/png")},
    )


def _create_schedule_image_record(client, filename="schedule.png", **overrides) -> dict:
    """Создание записи в базе данных через API."""
    response = _post_schedule_image(client, filename=filename, **overrides)
    assert response.status_code == 201
    return response.json()


def test_create_returns_201_and_record(client):
    """Тест создания расписания."""
    body = _create_schedule_image_record(client)

    assert body["name"] == "Расписание 1"
    assert body["image"]  # путь к сохранённому файлу
    assert body["is_active"] is True
    assert body["day_of_week"] == DayOfWeek.MONDAY.value
    uuid.UUID(body["id"])
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_create_with_omitted_optional_fields(client):
    """Тест создания расписания с опущенным опциональным полем is_active."""
    response = client.post(
        CREATE_URL,
        data={
            "name": "Расписание 1",
            "day_of_week": DayOfWeek.MONDAY.value,
        },
        files={"image": ("image.png", b"x", "image/png")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Расписание 1"
    assert body["is_active"] is True  # дефолт формы
    assert body["image"] == "stored/image.png"


def test_create_without_required_image_returns_422(client):
    """Тест создания расписания без обязательного файла image."""
    response = client.post(
        CREATE_URL,
        data=schedule_image_valid_payload(),
    )

    assert response.status_code == 422


def test_create_missing_required_form_field_returns_422(client):
    """Тест создания расписания без обязательного поля day_of_week."""
    response = client.post(
        CREATE_URL,
        data={"name": "Расписание 1"},
        files={"image": ("image.png", b"x", "image/png")},
    )

    assert response.status_code == 422


def test_get_returns_record(client):
    """Тест получения расписания по id."""
    created = _create_schedule_image_record(client)

    response = client.get(f"{CREATE_URL}{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["name"] == created["name"]


def test_get_missing_returns_404(client):
    """Тест получения расписания по несуществующему id."""
    response = client.get(f"{CREATE_URL}{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_with_invalid_uuid_returns_422(client):
    """Тест получения расписания по невалидному uuid."""
    response = client.get(f"{CREATE_URL}not-a-uuid")

    assert response.status_code == 422


def test_update_returns_updated_record(client):
    """Тест обновления расписания."""
    created = _create_schedule_image_record(client)

    response = client.patch(f"{CREATE_URL}{created['id']}", json={"name": "Updated"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["name"] == "Updated"
    assert body["image"] == created["image"]  # unchanged
    assert body["is_active"] == created["is_active"]  # unchanged


def test_update_missing_returns_404(client):
    """Тест обновления расписания по несуществующему id."""
    response = client.patch(f"{CREATE_URL}{uuid.uuid4()}", json={"name": "Updated"})

    assert response.status_code == 404


def test_update_with_empty_payload_returns_400(client):
    """Тест обновления расписания с пустым payload."""
    created = _create_schedule_image_record(client)

    response = client.patch(f"{CREATE_URL}{created['id']}", json={})

    assert response.status_code == 400


def test_delete_returns_204(client):
    """Тест удаления расписания."""
    created = _create_schedule_image_record(client)

    response = client.delete(f"{CREATE_URL}{created['id']}")

    assert response.status_code == 204


def test_delete_missing_returns_404(client):
    """Тест удаления расписания по несуществующему id."""
    response = client.delete(f"{CREATE_URL}{uuid.uuid4()}")

    assert response.status_code == 404


def test_router_prefix_and_tags():
    """Тест префиксов и тегов роутеров."""
    assert schedule_image_router.prefix == "/schedule-images"
    assert schedule_image_router.tags == ["schedule_images"]
    assert local_schedule_image_router.prefix == "/schedule-images-local"
    assert local_schedule_image_router.tags == ["local_schedule_images"]


def test_set_single_active(client):
    """Тест установки единственного расписания."""
    created_1 = _create_schedule_image_record(client)
    created_2 = _create_schedule_image_record(
        client, filename="image2.png", name="Расписание 2"
    )
    assert created_2["is_active"] is True
    response = client.post(f"{CREATE_URL}{created_1['id']}/set-single-active")
    assert response.status_code == 202
    created_1 = response.json()
    assert created_1["is_active"] is True
    response = client.get(f"{CREATE_URL}{created_2['id']}")
    assert response.status_code == 200
    created_2 = response.json()
    assert created_2["is_active"] is False


def test_get_single_schedule(client):
    """Тест получения единственного активного расписания."""
    created_1 = _create_schedule_image_record(client)
    _create_schedule_image_record(
        client, filename="image2.png", name="Расписание 2", is_active=False
    )
    response = client.get(GET_SINGLE_URL)
    assert response.status_code == 200
    assert response.json() == created_1


def test_get_single_schedule_no_active_returns_400(client):
    """Тест получения сингл-расписания без активных записей — 400."""
    _create_schedule_image_record(client, is_active=False)
    response = client.get(GET_SINGLE_URL)
    assert response.status_code == 400


def test_get_single_schedule_multiple_active_returns_400(client):
    """Тест получения сингл-расписания с несколькими активными записями — 400."""
    _create_schedule_image_record(client, filename="image1.png")
    _create_schedule_image_record(client, filename="image2.png", name="Расписание 2")
    response = client.get(GET_SINGLE_URL)
    assert response.status_code == 400


def test_create_local_schedule(client):
    """Тест создания локального расписания."""
    response = client.post(
        CREATE_LOCAL_URL,
        data={
            "name": "local schedule",
            "day_of_week": DayOfWeek.FRIDAY.value,
            "is_active": False,
            "filename": "1.jpg",
        },
    )
    assert response.status_code == 201
    schedule = response.json()
    assert schedule["name"] == "local schedule"
    assert schedule["day_of_week"] == DayOfWeek.FRIDAY.value
    assert schedule["is_active"] is False
    assert schedule["image"] == "local/1.jpg"
    assert schedule["is_local"] is True


@freeze_time("2026-10-01 12:00:00")  # Четверг
def test_get_today_schedule(client):
    """GET get-today-schedule возвращает активное расписание на сегодня."""
    created = _create_schedule_image_record(
        client, name="Today", day_of_week=DayOfWeek.THURSDAY.value
    )
    response = client.get(GET_TODAY_URL)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


@freeze_time("2026-10-01 12:00:00")  # Четверг
def test_get_today_schedule_missing_returns_404(client):
    """GET get-today-schedule без расписания на сегодня — 404."""
    _create_schedule_image_record(client, day_of_week=DayOfWeek.MONDAY.value)
    response = client.get(GET_TODAY_URL)
    assert response.status_code == 404


@freeze_time("2026-10-01 12:00:00")  # Четверг
def test_get_today_schedule_multiple_returns_400(client):
    """GET get-today-schedule с несколькими активными расписаниями — 400."""
    _create_schedule_image_record(
        client,
        name="Thu 1",
        filename="thu1.png",
        day_of_week=DayOfWeek.THURSDAY.value,
    )
    _create_schedule_image_record(
        client,
        name="Thu 2",
        filename="thu2.png",
        day_of_week=DayOfWeek.THURSDAY.value,
    )
    response = client.get(GET_TODAY_URL)
    assert response.status_code == 400


@freeze_time("2026-10-01 12:00:00")  # Четверг
def test_get_next_schedule(client):
    """GET get-next-schedule возвращает ближайшее активное расписание."""
    created = _create_schedule_image_record(
        client,
        name="Friday",
        filename="fri.png",
        day_of_week=DayOfWeek.FRIDAY.value,
    )
    response = client.get(GET_NEXT_URL)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_next_schedule_missing_returns_404(client):
    """GET get-next-schedule без активных расписаний — 404."""
    _create_schedule_image_record(client, is_active=False)
    response = client.get(GET_NEXT_URL)
    assert response.status_code == 404


def test_set_active_at_day(client):
    """POST {id}/set-active-at-day активирует расписание своего дня недели."""
    created_1 = _create_schedule_image_record(
        client, name="Mon A", filename="mon-a.png", day_of_week=DayOfWeek.MONDAY.value
    )
    created_2 = _create_schedule_image_record(
        client,
        name="Mon B",
        filename="mon-b.png",
        day_of_week=DayOfWeek.MONDAY.value,
    )
    other = _create_schedule_image_record(
        client,
        name="Tue",
        filename="tue.png",
        day_of_week=DayOfWeek.TUESDAY.value,
    )

    response = client.post(f"{CREATE_URL}{created_1['id']}/set-active-at-day")

    assert response.status_code == 202
    body = response.json()
    assert body["id"] == created_1["id"]
    assert body["is_active"] is True

    # Второе расписание того же дня деактивировано
    response = client.get(f"{CREATE_URL}{created_2['id']}")
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Расписание другого дня не затронуто
    response = client.get(f"{CREATE_URL}{other['id']}")
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_set_active_at_day_missing_returns_404(client):
    """POST {id}/set-active-at-day для несуществующего id — 404."""
    response = client.post(f"{CREATE_URL}{uuid.uuid4()}/set-active-at-day")
    assert response.status_code == 404


def test_get_local_schedule(client):
    """GET /api/v1/schedule-images-local/ возвращает локальное расписание."""
    response = client.get(LOCAL_SCHEDULE_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Локальное расписание"
    assert body["image"] == "1.jpg"
    assert body["is_active"] is True
    assert body["is_local"] is True


def test_set_all_inactive(client):
    """POST /reset-schedules деактивирует все расписания."""
    created_1 = _create_schedule_image_record(
        client, name="Mon A", filename="mon-a.png", day_of_week=DayOfWeek.MONDAY.value
    )
    created_2 = _create_schedule_image_record(
        client,
        name="Mon B",
        filename="mon-b.png",
        day_of_week=DayOfWeek.MONDAY.value,
    )
    other = _create_schedule_image_record(
        client,
        name="Tue",
        filename="tue.png",
        day_of_week=DayOfWeek.TUESDAY.value,
    )
    response = client.post(RESET_SCHEDULES_URL)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "OK"
    assert body["count"] == 3
    for schedule in [created_1, created_2, other]:
        response = client.get(f"{CREATE_URL}{schedule['id']}")
        assert response.status_code == 200
        assert response.json()["is_active"] is False
