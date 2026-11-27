from fastapi.testclient import TestClient
from src.core.config import runtime_paths, settings
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


def test_uploads_served_before_spa_fallback(tmp_path, monkeypatch):
    """`/uploads/...` отдаёт файл, а не `index.html` SPA-fallback.

    Регрессия: когда собранный фронтенд присутствует, catch-all
    ``/{full_path:path}`` регистрировался раньше монтирования ``/uploads`` и
    перехватывал запросы к статике — изображения в киоске не загружались
    (вместо картинки приходил HTML).
    """
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<!doctype html>", encoding="utf-8")

    static_dir = tmp_path / "uploads"
    image = static_dir / "schedule_images" / "lesson.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"\x89PNG\r\n\x1a\n")

    monkeypatch.setenv("SCHOOL_KIOSK_FRONTEND_DIR", str(frontend_dir))
    monkeypatch.setattr(runtime_paths, "static_dir", static_dir)

    app = create_app()
    response = TestClient(app).get(f"{settings.upload_url}/schedule_images/lesson.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == image.read_bytes()


def test_uploads_rejects_path_traversal(tmp_path, monkeypatch):
    """Раздача статики не выпускает за пределы каталога `static_dir`."""
    static_dir = tmp_path / "uploads"
    static_dir.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")

    monkeypatch.setattr(runtime_paths, "static_dir", static_dir)

    app = create_app()
    # `%2E%2E%2F` = `../`: клиент не нормализует путь, проверка остаётся на бэкенде.
    response = TestClient(app).get(f"{settings.upload_url}/%2E%2E%2Fsecret.txt")

    assert response.status_code == 404
