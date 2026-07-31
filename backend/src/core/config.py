from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "School Kiosk API"
    app_description: str = "API backend for School Kiosk"
    app_version: str = "0.1.0"

    debug: bool = False
    api_prefix: str = "/api/v1"

    server_host: str = "0.0.0.0"  # noqa: S104 — intentional for dev server
    server_port: int = 8765

    database_url: str = "sqlite+aiosqlite:///school_kiosk.db"


settings = Settings()
