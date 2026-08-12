"""Unit tests for the schedule API routers (HTTP endpoints)."""

import uuid

from src.apps.schedule.routes import schedule_router
from src.enums.schedule import DayOfWeek


def _valid_payload(**overrides) -> dict:
    payload = {
        "name": "Расписание 1",
        "image": "schedule.png",
        "is_active": True,
        "day_of_week": DayOfWeek.MONDAY.value,
    }
    payload.update(overrides)
    return payload


def _create_record(client) -> dict:
    """Create a schedule via the API and return the parsed JSON body."""
    response = client.post("/api/v1/schedule", json=_valid_payload())
    assert response.status_code == 201
    return response.json()


def test_create_returns_201_and_record(client):
    """Test that POST creates a schedule and returns it with status 201."""
    response = client.post("/api/v1/schedule", json=_valid_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Расписание 1"
    assert body["image"] == "schedule.png"
    assert body["is_active"] is True
    assert body["day_of_week"] == DayOfWeek.MONDAY.value
    # The id and timestamps are server-generated.
    uuid.UUID(body["id"])
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_create_with_omitted_optional_fields(client):
    """Test that optional fields fall back to model defaults."""
    payload = {"image": "image.png"}

    response = client.post("/api/v1/schedule", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Untitled"
    assert body["is_active"] is False
    assert body["day_of_week"] == DayOfWeek.MONDAY.value


def test_create_without_required_image_returns_422(client):
    """Test that a missing required field yields HTTP 422."""
    response = client.post("/api/v1/schedule", json={"name": "No image"})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# get (GET /api/v1/schedule/{id})
# ---------------------------------------------------------------------------
def test_get_returns_record(client):
    """Test that GET returns an existing schedule by id."""
    created = _create_record(client)

    response = client.get(f"/api/v1/schedule/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["name"] == created["name"]


def test_get_missing_returns_404(client):
    """Test that GET for a non-existent id returns HTTP 404."""
    response = client.get(f"/api/v1/schedule/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_with_invalid_uuid_returns_422(client):
    """Test that GET with a malformed id returns HTTP 422."""
    response = client.get("/api/v1/schedule/not-a-uuid")

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# update (PATCH /api/v1/schedule/{id})
# ---------------------------------------------------------------------------
def test_update_returns_updated_record(client):
    """Test that PATCH updates the provided fields and returns the record."""
    created = _create_record(client)

    response = client.patch(
        f"/api/v1/schedule/{created['id']}", json={"name": "Updated"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["name"] == "Updated"
    assert body["image"] == created["image"]  # unchanged
    assert body["is_active"] == created["is_active"]  # unchanged


def test_update_missing_returns_404(client):
    """Test that PATCH for a non-existent id returns HTTP 404."""
    response = client.patch(
        f"/api/v1/schedule/{uuid.uuid4()}", json={"name": "Updated"}
    )

    assert response.status_code == 404


def test_update_with_empty_payload_returns_400(client):
    """Test that PATCH with no fields returns HTTP 400."""
    created = _create_record(client)

    response = client.patch(f"/api/v1/schedule/{created['id']}", json={})

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# delete (DELETE /api/v1/schedule/{id})
# ---------------------------------------------------------------------------
def test_delete_returns_204(client):
    """Test that DELETE removes a record and returns HTTP 204."""
    created = _create_record(client)

    response = client.delete(f"/api/v1/schedule/{created['id']}")

    assert response.status_code == 204


def test_delete_missing_returns_404(client):
    """Test that DELETE for a non-existent id returns HTTP 404."""
    response = client.delete(f"/api/v1/schedule/{uuid.uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# router registration
# ---------------------------------------------------------------------------
def test_router_prefix_and_tags():
    """Test that the schedule router is mounted under the expected prefix/tags."""
    assert schedule_router.prefix == "/schedule"
    assert schedule_router.tags == ["schedule"]
