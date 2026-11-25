"""Регистрация периодических задач (fastapi-crons)."""

from fastapi_crons import Crons

from src.tasks.file_sync import run_local_schedules_sync
from src.tasks.token_cleanup import run_expired_tokens_cleanup
from src.tasks.weather_refresh import run_weather_refresh

# Периодическая синхронизация локального файла расписания — каждые 2 минуты.
PERIODIC_FILE_SYNC_CRON = "*/2 * * * *"
# Имя джоба (также используется для проверки идемпотентности регистрации).
PERIODIC_FILE_SYNC_JOB_NAME = "periodic_local_schedules_sync"

TOKEN_CLEANUP_CRON = "0 * * * *"  # noqa S105
TOKEN_CLEANUP_JOB_NAME = "periodic_tokens_cleanup"  # noqa S105

# Проверка TTL прогноза погоды — каждые 5 минут. Фактический запрос
# к провайдеру выполняется только когда кеш устарел (см. настройку
# weather.refresh_interval_minutes).
WEATHER_REFRESH_CRON = "*/5 * * * *"
WEATHER_REFRESH_JOB_NAME = "periodic_weather_refresh"

JOBS_DICT = {
    PERIODIC_FILE_SYNC_JOB_NAME: (
        PERIODIC_FILE_SYNC_CRON,
        ["maintenance"],
        run_local_schedules_sync,
    ),
    TOKEN_CLEANUP_JOB_NAME: (
        TOKEN_CLEANUP_CRON,
        ["maintenance", "tokens"],
        run_expired_tokens_cleanup,
    ),
    WEATHER_REFRESH_JOB_NAME: (
        WEATHER_REFRESH_CRON,
        ["maintenance", "weather"],
        run_weather_refresh,
    ),
}


def register_cron_jobs(crons: Crons) -> None:
    """Регистрирует периодические задачи на переданном планировщике."""
    existing = {job.name for job in crons.jobs}
    for name, (cron, tags, func) in JOBS_DICT.items():
        if name in existing:
            continue
        crons.cron(
            cron,
            name=name,
            tags=tags,
        )(func)
