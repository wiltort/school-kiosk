"""Unit tests for the FastAPI application entrypoint."""

from fastapi.testclient import TestClient
from src.core.config import settings
from src.main import create_app


def test_app_starts_and_responds_to_root():
    """Test that the app starts, applies settings, and answers the root request."""
    app = create_app()

    # Settings are applied to the app instance.
    assert app.title == settings.app_name
    assert app.version == settings.app_version
    assert app.description == settings.app_description

    # Using TestClient as a context manager triggers the lifespan (startup/shutdown),
    # which verifies the app starts successfully.
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Backend service is running."}
