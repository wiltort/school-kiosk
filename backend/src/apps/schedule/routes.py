import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from src.apps.schedule.managers import ScheduleImageManager
from src.apps.schedule.schemas import (
    ScheduleImageCreate,
    ScheduleImageGet,
    ScheduleImageUpdate,
)
from src.enums.schedule import DayOfWeek

schedule_image_router = APIRouter(prefix="/schedule_images", tags=["schedule_images"])


class ScheduleImageForm:
    """Метаданные расписания из multipart-формы (для чистого Swagger UI)."""

    def __init__(
        self,
        name: Annotated[str, Form(min_length=1, max_length=255)],
        day_of_week: Annotated[DayOfWeek, Form()],
        is_active: Annotated[bool, Form()] = True,
    ) -> None:
        self.name = name
        self.day_of_week = day_of_week
        self.is_active = is_active


@schedule_image_router.post(
    "/", response_model=ScheduleImageGet, status_code=status.HTTP_201_CREATED
)
async def create_schedule(
    data: Annotated[ScheduleImageForm, Depends()],
    image: Annotated[UploadFile, File(...)],
    manager: Annotated[ScheduleImageManager, Depends()],
) -> ScheduleImageGet:
    schedule = ScheduleImageCreate(
        name=data.name,
        is_active=data.is_active,
        day_of_week=data.day_of_week,
    )
    content = await image.read()
    return await manager.create(schedule, content, image.filename)


@schedule_image_router.get("/{id}", response_model=ScheduleImageGet)
async def get_schedule(
    id: uuid.UUID, manager: ScheduleImageManager = Depends()
) -> ScheduleImageGet | None:
    return await manager.get(id)


@schedule_image_router.patch("/{id}", response_model=ScheduleImageGet)
async def update_schedule(
    id: uuid.UUID,
    schedule: ScheduleImageUpdate,
    manager: ScheduleImageManager = Depends(),
) -> ScheduleImageGet:
    return await manager.update(id, schedule)


@schedule_image_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    id: uuid.UUID, manager: ScheduleImageManager = Depends()
) -> None:
    return await manager.delete(id)
