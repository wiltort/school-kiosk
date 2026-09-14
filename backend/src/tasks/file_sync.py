import logging
from typing import Annotated

from fastapi import Depends

from src.apps.schedule.managers import ScheduleImageManager
from src.core.config import settings

logger = logging.getLogger(__name__)


async def run_periodic_file_sincronization(
    manager: Annotated[ScheduleImageManager, Depends()],
):
    logger.info("Starting periodic file sincronization")

    paths = [
        settings.current_local_schedule_image_filename,
    ]
    for path in paths:
        await manager.local_sync(path)
    logger.info("Periodic file sincronization completed")
