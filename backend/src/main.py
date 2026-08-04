from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.core.config import settings
from src.core.database import Base, async_engine


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001 — required by FastAPI lifespan signature
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    await async_engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app: FastAPI = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        lifespan=lifespan,
    )

    # TODO подключить роутеры

    @app.get("/", tags=["root"])
    def root():
        return {"message": "Backend service is running."}

    return app


def run_app():
    app = create_app()
    uvicorn.run(app, host=settings.server_host, port=settings.server_port)


if __name__ == "__main__":
    run_app()
