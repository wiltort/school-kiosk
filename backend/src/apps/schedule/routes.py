import uuid

from fastapi import APIRouter, Depends, status

from src.apps.schedule.schemas import (
    ScheduleImageCreate,
    ScheduleImageGet,
    ScheduleImageUpdate,
)
from src.apps.schedule.services import ScheduleImageService

schedule_image_router = APIRouter(prefix="/schedule_images", tags=["schedule_images"])


@schedule_image_router.post(
    "/", response_model=ScheduleImageGet, status_code=status.HTTP_201_CREATED
)
async def create_schedule(
    schedule: ScheduleImageCreate,
    service: ScheduleImageService = Depends(ScheduleImageService),
) -> ScheduleImageGet:
    return await service.create(schedule)


@schedule_image_router.get("/{id}", response_model=ScheduleImageGet)
async def get_schedule(
    id: uuid.UUID, service: ScheduleImageService = Depends(ScheduleImageService)
) -> ScheduleImageGet | None:
    return await service.get(id)


@schedule_image_router.patch("/{id}", response_model=ScheduleImageGet)
async def update_schedule(
    id: uuid.UUID,
    schedule: ScheduleImageUpdate,
    service: ScheduleImageService = Depends(ScheduleImageService),
) -> ScheduleImageGet:
    return await service.update(id, schedule)


@schedule_image_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    id: uuid.UUID, service: ScheduleImageService = Depends(ScheduleImageService)
) -> None:
    return await service.delete(id)
