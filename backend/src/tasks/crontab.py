"""Регистрация периодических задач (fastapi-crons)."""

from fastapi_crons import Crons

from src.tasks.file_sync import run_local_schedules_sync

# Периодическая синхронизация локального файла расписания — каждые 5 минут.
PERIODIC_FILE_SYNC_CRON = "*/2 * * * *"
# Имя джоба (также используется для проверки идемпотентности регистрации).
PERIODIC_FILE_SYNC_JOB_NAME = "periodic_local_schedules_sync"


def register_cron_jobs(crons: Crons) -> None:
    """Регистрирует периодические задачи на переданном планировщике."""
    if PERIODIC_FILE_SYNC_JOB_NAME in {job.name for job in crons.jobs}:
        return
    crons.cron(
        PERIODIC_FILE_SYNC_CRON,
        name=PERIODIC_FILE_SYNC_JOB_NAME,
        tags=["maintenance"],
    )(run_local_schedules_sync)
