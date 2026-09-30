import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi_crons import Crons, SQLiteStateBackend

from src.apps import apps_router
from src.apps.admin import autostart
from src.core.config import settings
from src.core.database import get_db_dependency
from src.core.logging_setup import setup_logging
from src.core.migrations import _resource_dir, apply_schema
from src.tasks.crontab import register_cron_jobs

logger = logging.getLogger(__name__)


def _init_logging():
    """Инициализирует логирование: консоль + файл `<data_dir>/logs/backend.log`."""
    setup_logging(
        data_dir=settings.data_dir,
        level=settings.log_level,
        log_format=settings.log_format,
        datefmt=settings.date_format,
    )


_init_logging()
logger.info("=== School Kiosk backend: запуск ===")
logger.info(
    "version=%s debug=%s frozen=%s py=%s",
    settings.app_version,
    settings.debug,
    getattr(sys, "frozen", False),
    sys.version.split()[0],
)
logger.info("data_dir=%s", settings.data_dir)
logger.info("database_url=%s", settings.database_url)
logger.info("frontend_dir=%s", settings.frontend_dir)
logger.info("migrations_resources=%s", _resource_dir())

crons = Crons(
    state_backend=SQLiteStateBackend(db_path=str(settings.data_dir / "cron_state.db"))
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001 — required by FastAPI lifespan signature
    db = get_db_dependency()
    if db.db_engine is not None:
        try:
            await apply_schema(db.db_engine)
        except Exception:
            logger.exception(
                "Ошибка применения схемы БД при старте — бэкенд завершает работу"
            )
            raise
        finally:
            _init_logging()
    if settings.cron_enabled:
        await crons.start()
    try:
        yield
    finally:
        if settings.cron_enabled:
            await crons.stop()
        await db.db_engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app: FastAPI = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(apps_router)

    settings.static_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.upload_url,
        StaticFiles(directory=str(settings.static_dir)),
        name="uploads",
    )
    if autostart.is_supported() and settings.app_settings.autostart():
        autostart.set_enabled(True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    if settings.cron_enabled:
        register_cron_jobs(crons)

    _mount_spa(app)

    return app


def _mount_spa(app: FastAPI) -> None:
    """Раздаёт собранный фронтенд (SPA) по HTTP, если он собран."""
    index_file = settings.frontend_dir / "index.html"
    if not index_file.is_file():

        @app.get("/", tags=["root"])
        def root():
            return {"message": "Backend service is running."}

        return

    assets_dir = settings.frontend_dir / "assets"
    if assets_dir.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="assets",
        )
    spa_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    @app.get("/", include_in_schema=False)
    def root_spa():
        return FileResponse(index_file, headers=spa_headers)

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        return FileResponse(index_file, headers=spa_headers)


app = create_app()


def start():
    import uvicorn

    uvicorn.run(
        app="src.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug,
    )
