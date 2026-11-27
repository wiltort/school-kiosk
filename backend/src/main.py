import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi_crons import Crons, SQLiteStateBackend

from src.apps import apps_router
from src.apps.admin import autostart
from src.apps.settings.managers import SettingsManager
from src.apps.settings.repositories import SettingsRepository
from src.apps.settings.seed import seed_all
from src.core.app_settings import APP_SETTINGS_FILE
from src.core.config import runtime_paths, settings
from src.core.database import DBDependency, get_db_dependency
from src.core.logging_setup import setup_logging
from src.core.migrations import _resource_dir, apply_schema
from src.core.settings_schema import SettingsKey
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


_runtime_initialized = False


async def _resolve_runtime_path(
    manager: SettingsManager,
    key: SettingsKey,
    fallback: Path,
) -> Path:
    """Возвращает путь из настроек либо фолбэк, если значение не задано."""
    stored = await manager.get_str(key)
    return Path(stored).expanduser() if stored else fallback


async def _bootstrap_runtime(app: FastAPI, db: DBDependency) -> None:
    """Загружает настройки из БД и применяет их к процессу.

    Выполняется после ``apply_schema``: таблицы уже существуют, а legacy
    ``settings.json`` перенесён в ``app_settings``. Монтирование статики
    вынесено сюда, потому что каталог теперь задаётся настройкой в БД.
    """
    # Приоритет источников: текущий файл настроек бэкенда (обновление с
    # предыдущей версии), затем seed-файл установщика Tauri (чистая установка).
    legacy_file = settings.data_dir / APP_SETTINGS_FILE
    if not legacy_file.is_file():
        legacy_file = settings.legacy_settings_file
    await seed_all(db, legacy_file=legacy_file)
    manager = SettingsManager(db=db, repo=SettingsRepository())
    await manager.ensure_defaults()

    runtime_paths.static_dir = None
    runtime_paths.local_image_dir = None
    static_dir = await _resolve_runtime_path(
        manager, SettingsKey.SYSTEM_STATIC_DIR, settings.static_dir
    )
    local_image_dir = await _resolve_runtime_path(
        manager, SettingsKey.SYSTEM_LOCAL_IMAGE_DIR, settings.local_image_dir
    )
    runtime_paths.static_dir = static_dir
    runtime_paths.local_image_dir = local_image_dir
    static_dir.mkdir(parents=True, exist_ok=True)
    local_image_dir.mkdir(parents=True, exist_ok=True)

    global _runtime_initialized
    if not _runtime_initialized:
        app.mount(
            settings.upload_url,
            StaticFiles(directory=str(static_dir)),
            name="uploads",
        )
        _runtime_initialized = True

    if autostart.is_supported() and await manager.get_bool(
        SettingsKey.SYSTEM_AUTOSTART
    ):
        autostart.set_enabled(True)


@asynccontextmanager
async def lifespan(app: FastAPI):
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
        await _bootstrap_runtime(app, db)
    if settings.cron_enabled:
        register_cron_jobs(crons)
        await crons.start()
    try:
        yield
    finally:
        if settings.cron_enabled:
            await crons.stop()
        if db.db_engine is not None:
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

    @app.middleware("http")
    async def _log_api_requests(request: Request, call_next):
        """Диагностика: логирует все API-запросы (метод, путь, статус, origin).

        Нужен, чтобы отличать «запрос не дошёл до бэкенда» от «дошёл и получил
        404/503». Без этого uvicorn access-log в ``backend.log`` не попадает.
        """
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            logger.info(
                "HTTP %s %s -> %s origin=%s ua=%s",
                request.method,
                request.url.path,
                response.status_code,
                request.headers.get("origin"),
                request.headers.get("user-agent", "")[:80],
            )
        return response

    app.include_router(apps_router)

    settings.data_dir.mkdir(parents=True, exist_ok=True)

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
