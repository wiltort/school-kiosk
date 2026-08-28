from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = {"env_prefix": "BACKEND_"}

    app_name: str = "School Kiosk API"
    app_description: str = "API backend for School Kiosk"
    app_version: str = "0.1.0"

    debug: bool = False
    log_level: str = "INFO"
    log_format: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    api_prefix: str = "/api/v1"

    server_host: str = "0.0.0.0"  # noqa: S104 — intentional for dev server
    server_port: int = 8765

    database_url: str = "sqlite+aiosqlite:///school_kiosk.db"
    db_echo: bool = False

    default_admin_login: str = "admin"
    default_admin_password: str = "admin"  # noqa: S105

    upload_dir: Path = BASE_DIR / "uploads"
    upload_url: str = "/uploads"
    max_image_size: int = 10 * 1024 * 1024


settings = Settings()
