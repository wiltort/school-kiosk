import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.apps import apps_router
from src.apps.admin import autostart
from src.core.config import settings
from src.core.database import get_db_dependency
from src.core.logging_setup import setup_logging
from src.core.migrations import _resource_dir, apply_schema

logger = logging.getLogger(__name__)


def _init_logging():
    """Инициализирует логирование: консоль + файл `<data_dir>/logs/backend.log`.

    Вызывается при импорте модуля (до создания приложения), в начале lifespan
    (до миграций) и после миграций — `alembic/env.py` переопределяет logging
    через `fileConfig`, из-за чего наши хендлеры могли быть сброшены.
    Повторные вызовы идемпотентны.
    """
    setup_logging(
        data_dir=settings.data_dir,
        level=settings.log_level,
        log_format=settings.log_format,
        datefmt=settings.date_format,
    )


# Логирование настраиваем как можно раньше: падение при импорте или создании
# приложения должно попасть в лог-файл (в релизе stderr уходит в канал, который
# никто не читает — без файлового лога причина была бы невидимой).
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


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001 — required by FastAPI lifespan signature
    db = get_db_dependency()
    if db.db_engine is not None:
        # Автоприменение Alembic-миграций + создание недостающих таблиц. Нужно
        # выполнять до начала обслуживания запросов, чтобы после автообновления
        # (которое меняет только исполняемые файлы) схема БД соответствовала
        # новой версии кода.
        try:
            await apply_schema(db.db_engine)
        except Exception:
            logger.exception(
                "Ошибка применения схемы БД при старте — бэкенд завершает работу"
            )
            raise
        finally:
            # Восстанавливаем наши хендлеры после возможного fileConfig в alembic.
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

    settings.static_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.upload_url,
        StaticFiles(directory=str(settings.static_dir)),
        name="uploads",
    )

    # Самовосстановление автозагрузки: если в настройках она включена,
    # применяем её и после перезапуска бэкенда (ключ в реестре Windows).
    if autostart.is_supported() and settings.app_settings.autostart():
        autostart.set_enabled(True)

    _mount_spa(app)

    return app


def _mount_spa(app: FastAPI) -> None:
    """Раздаёт собранный фронтенд (SPA) по HTTP, если он собран.

    Каталог фронтенда берётся из `settings.frontend_dir` (см. config.py).
    Если `index.html` отсутствует — считаем, что фронтенд не собран
    (например, чистый dev-бэкенд за Vite), и оставляем корень как
    health-ответ JSON.
    """
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

    # index.html не кэшируется: после автообновления WebView должен сразу
    # получить новый бандл с актуальной версией, а не старый из HTTP-кэша.
    # Сами ассеты (assets/*) имеют хеши в имени файла, поэтому их кэширование
    # безопасно — менять его не нужно.
    spa_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    @app.get("/", include_in_schema=False)
    def root_spa():
        return FileResponse(index_file, headers=spa_headers)

    # SPA-fallback: любой не-API путь (история/клиентская навигация) отдаёт
    # index.html. Монтированные ранее маршруты (API, uploads, assets) имеют
    # приоритет и обрабатываются раньше этого catch-all.
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
