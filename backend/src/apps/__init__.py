from fastapi import APIRouter

from src.apps.schedule.routes import local_schedule_image_router, schedule_image_router

apps_router = APIRouter(prefix="/api/v1")

apps_router.include_router(schedule_image_router)
apps_router.include_router(local_schedule_image_router)
