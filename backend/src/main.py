import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

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
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
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

    app.include_router(apps_router)

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
