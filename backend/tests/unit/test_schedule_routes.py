"""Юнит-тесты для проверки эндпойнтов."""

import uuid

from src.apps.schedule.routes import schedule_image_router
from src.enums.schedule import DayOfWeek


def schedule_image_valid_payload(**overrides) -> dict:
    payload = {
        "name": "Расписание 1",
        "image": "schedule.png",
        "is_active": True,
        "day_of_week": DayOfWeek.MONDAY.value,
    }
    payload.update(overrides)
    return payload


def _create_schedule_image_record(client) -> dict:
    """Создание записи в базе данных."""
    response = client.post(
        "/api/v1/schedule_images", json=schedule_image_valid_payload()
    )
    assert response.status_code == 201
    return response.json()


def test_create_returns_201_and_record(client):
    """Тест создания расписания."""
    body = _create_schedule_image_record(client)

    assert body["name"] == "Расписание 1"
    assert body["image"] == "schedule.png"
    assert body["is_active"] is True
    assert body["day_of_week"] == DayOfWeek.MONDAY.value
    uuid.UUID(body["id"])
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_create_with_omitted_optional_fields(client):
    """Тест создания расписания с опущенными опциональными полями."""
    payload = {"image": "image.png"}

    response = client.post("/api/v1/schedule_images", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Untitled"
    assert body["is_active"] is False
    assert body["day_of_week"] == DayOfWeek.MONDAY.value


def test_create_without_required_image_returns_422(client):
    """Тест создания расписания без обязательного поля image."""
    response = client.post("/api/v1/schedule_images", json={"name": "No image"})

    assert response.status_code == 422


def test_get_returns_record(client):
    """Тест получения расписания по id."""
    created = _create_schedule_image_record(client)

    response = client.get(f"/api/v1/schedule_images/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["name"] == created["name"]


def test_get_missing_returns_404(client):
    """Тест получения расписания по несуществующему id."""
    response = client.get(f"/api/v1/schedule_images/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_with_invalid_uuid_returns_422(client):
    """Тест получения расписания по невалидному uuid."""
    response = client.get("/api/v1/schedule_images/not-a-uuid")

    assert response.status_code == 422


def test_update_returns_updated_record(client):
    """Тест обновления расписания."""
    created = _create_schedule_image_record(client)

    response = client.patch(
        f"/api/v1/schedule_images/{created['id']}", json={"name": "Updated"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["name"] == "Updated"
    assert body["image"] == created["image"]  # unchanged
    assert body["is_active"] == created["is_active"]  # unchanged


def test_update_missing_returns_404(client):
    """Тест обновления расписания по несуществующему id."""
    response = client.patch(
        f"/api/v1/schedule_images/{uuid.uuid4()}", json={"name": "Updated"}
    )

    assert response.status_code == 404


def test_update_with_empty_payload_returns_400(client):
    """Тест обновления расписания с пустым payload."""
    created = _create_schedule_image_record(client)

    response = client.patch(f"/api/v1/schedule_images/{created['id']}", json={})

    assert response.status_code == 400


def test_delete_returns_204(client):
    """Тест удаления расписания."""
    created = _create_schedule_image_record(client)

    response = client.delete(f"/api/v1/schedule_images/{created['id']}")

    assert response.status_code == 204


def test_delete_missing_returns_404(client):
    """Тест удаления расписания по несуществующему id."""
    response = client.delete(f"/api/v1/schedule_images/{uuid.uuid4()}")

    assert response.status_code == 404


def test_router_prefix_and_tags():
    """Тест префикса и тегов роутера."""
    assert schedule_image_router.prefix == "/schedule_images"
    assert schedule_image_router.tags == ["schedule_images"]
