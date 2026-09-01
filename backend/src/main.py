import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.apps import apps_router
from src.core.config import settings
from src.core.database import get_db_dependency
from src.models import Base

logger = logging.getLogger(__name__)


def _init_logging():
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format=settings.log_format,
        datefmt=settings.date_format,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001 — required by FastAPI lifespan signature
    db = get_db_dependency()
    async with db.db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _init_logging()
    yield
    await db.db_engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app: FastAPI = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        lifespan=lifespan,
    )

    # CORS: собранное приложение (Tauri WebView) обращается к бэкенду по
    # абсолютному URL из origin "http://tauri.localhost". Это локальный киоск,
    # поэтому разрешаем все origin. В dev-режиме запросы идут через Vite-прокси
    # (same-origin) и CORS не требуется, но middleware не мешает.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(apps_router)

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.upload_url,
        StaticFiles(directory=str(settings.upload_dir)),
        name="uploads",
    )

    @app.get("/", tags=["root"])
    def root():
        return {"message": "Backend service is running."}

    return app


app = create_app()


def start():
    import uvicorn

    uvicorn.run(
        app="src.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug,
    )
