"""Фикстуры интеграционных тестов собранного билда бэкенда.

Проверяют именно упакованный ``python-backend.exe`` из GitHub-релизов: тесты
спавнят его как отдельный процесс и проверяют поведение «как у пользователя».
"""

from pathlib import Path

import pytest

from tests.integration.smoke import (
    BackendProcess,
    free_port,
    resolve_backend_exe,
    spawn_backend,
    stop_all_spawned,
)


@pytest.fixture(scope="session", autouse=True)
def cleanup_spawned_backends():
    """Финализатор сессии: гарантированно останавливает все бэкенды.

    Срабатывает и при прерывании прогона (Ctrl+C), когда teardown отдельных
    фикстур может не выполниться, — чтобы не копить осиротевшие
    ``python-backend.exe`` в системе.
    """
    yield
    stop_all_spawned()


@pytest.fixture(scope="session")
def backend_exe() -> Path:
    """Путь к собранному бэкенду; пропускает тесты, если он не собран."""
    exe = resolve_backend_exe()
    if exe is None:
        pytest.skip(
            "python-backend.exe не собран. Соберите его (make build-backend) "
            "или укажите путь через KIOSK_BACKEND_EXE.",
        )
    return exe


@pytest.fixture
def run_backend(backend_exe):
    """Фабрика запуска бэкенда в заданном каталоге данных.

    Останавливает все запущенные процессы после теста. Каждый запуск использует
    новый свободный порт.
    """

    started: list[BackendProcess] = []

    def _run(data_dir: Path) -> BackendProcess:
        bp = spawn_backend(backend_exe, data_dir, free_port())
        started.append(bp)
        return bp

    yield _run
    for bp in started:
        bp.stop()
