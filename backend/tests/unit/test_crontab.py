"""Юнит-тесты регистрации периодических задач (fastapi-crons)."""

import inspect

from src.tasks.crontab import (
    PERIODIC_FILE_SYNC_CRON,
    PERIODIC_FILE_SYNC_JOB_NAME,
    register_cron_jobs,
)


class _Job:
    """Минимальная модель зарегистрированного джоба (по API fastapi-crons)."""

    def __init__(self, name: str | None, expr: str, func) -> None:
        self.name = name
        self.expr = expr
        self.func = func


class _FakeCrons:
    """Заглушка планировщика: фиксирует вызовы ``crons.cron(...)``."""

    def __init__(self) -> None:
        self.jobs: list[_Job] = []

    def cron(self, expr: str, **kwargs):
        def decorator(func):
            self.jobs.append(_Job(kwargs.get("name"), expr, func))
            return func

        return decorator


def test_register_cron_jobs_registers_periodic_file_sync():
    """Джоб синхронизации регистрируется с ожидаемым расписанием."""
    fake = _FakeCrons()

    register_cron_jobs(fake)

    assert len(fake.jobs) == 2
    job = fake.jobs[0]
    assert job.name == PERIODIC_FILE_SYNC_JOB_NAME
    assert job.expr == PERIODIC_FILE_SYNC_CRON
    assert inspect.iscoroutinefunction(job.func)


def test_register_cron_jobs_is_idempotent():
    """Повторная регистрация не создаёт дубликат джоба."""
    fake = _FakeCrons()

    register_cron_jobs(fake)
    register_cron_jobs(fake)

    assert len(fake.jobs) == 2
    assert fake.jobs[0].name == PERIODIC_FILE_SYNC_JOB_NAME
