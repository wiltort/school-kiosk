import uuid

from fastapi import Depends

from src.apps.schedule.managers import ScheduleImageManager
from src.apps.schedule.schemas import (
    ScheduleImageCreate,
    ScheduleImageGet,
    ScheduleImageUpdate,
)


class ScheduleImageService:
    def __init__(self, manager: ScheduleImageManager = Depends(ScheduleImageManager)):
        self.manager = manager

    async def create(self, schedule: ScheduleImageCreate) -> ScheduleImageGet:
        return await self.manager.create(schedule)

    async def update(
        self, id: uuid.UUID, schedule: ScheduleImageUpdate
    ) -> ScheduleImageGet:
        return await self.manager.update(id, schedule)

    async def delete(self, id: uuid.UUID) -> None:
        await self.manager.delete(id)

    async def get(self, id: uuid.UUID) -> ScheduleImageGet | None:
        return await self.manager.get(id)
