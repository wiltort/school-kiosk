from src.core.config import settings
from src.main import create_app


def test_app_starts_and_responds_to_root(client):
    """Проверка запуска приложения и ответа на корневой маршрут."""
    app = create_app()

    assert app.title == settings.app_name
    assert app.version == settings.app_version
    assert app.description == settings.app_description

    with client as test_client:
        response = test_client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Backend service is running."}
