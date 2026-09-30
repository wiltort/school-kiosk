import logging

from src.apps.schedule.managers import ScheduleImageManager
from src.apps.schedule.repositories import ScheduleImageRepository
from src.core.database import get_db_dependency
from src.core.storage import ImageStorage

logger = logging.getLogger(__name__)


def _build_manager() -> ScheduleImageManager:
    """Собирает ``ScheduleImageManager`` вне FastAPI-DI.

    Планировщик (fastapi-crons) вызывает функцию задачи напрямую, без
    внедрения зависимостей, поэтому граф зависимостей строится вручную.
    """
    return ScheduleImageManager(
        db=get_db_dependency(),
        image_repo=ScheduleImageRepository(),
        storage=ImageStorage(),
    )


async def run_local_schedules_sync() -> None:
    """Периодическая синхронизация активных локальных расписаний расписания."""
    logger.info("Starting periodic file synchronization")
    manager = _build_manager()
    n = await manager.all_local_schedules_sync()
    if n > 0:
        logger.info("Periodic file synchronization completed")
        logger.info(f"Local schedules synced: {n}")
    else:
        logger.warning("No local schedules synced")
