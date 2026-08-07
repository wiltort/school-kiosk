from fastapi import APIRouter

from src.apps.schedule.routes import schedule_router

apps_router = APIRouter(prefix="/api/v1")

apps_router.include_router(schedule_router)
