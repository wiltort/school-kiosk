"""Хелперы интеграционных тестов собранного билда бэкенда.

Эти тесты запускают настоящий ``python-backend.exe`` (PyInstaller-сборка,
которая публикуется в GitHub Releases) как отдельный процесс и проверяют его
работоспособность «как у пользователя»: свежая установка, создание БД,
миграции Alembic, API и лог.

Чтобы тесты заработали, сначала соберите бэкенд (``make build-backend`` или
команда из ``.github/workflows/release-build.yml``). Путь к exe можно
переопределить переменной окружения ``KIOSK_BACKEND_EXE``.
"""

import asyncio
import json
import os
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.enums.schedule import DayOfWeek
from src.models import ScheduleImage
from src.models.base import Base

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_BACKEND_EXE = BACKEND_DIR / "dist" / "python-backend.exe"

# Frozen onefile при первом запуске распаковывает архив в _MEIPASS — даём запас.
STARTUP_TIMEOUT_SEC = 90


def resolve_backend_exe() -> Path | None:
    """Путь к собранному бэкенду либо None, если он не собран."""
    env = os.environ.get("KIOSK_BACKEND_EXE")
    if env:
        candidate = Path(env)
        return candidate if candidate.is_file() else None
    return DEFAULT_BACKEND_EXE if DEFAULT_BACKEND_EXE.is_file() else None


def free_port() -> int:
    """Свободный TCP-порт на loopback."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def head_revision() -> str:
    """Текущая head-ревизия Alembic из репозитория."""
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(cfg).get_current_head()


class BackendProcess:
    """Запущенный процесс ``python-backend.exe`` и хелперы для работы с ним."""

    def __init__(self, proc: subprocess.Popen, data_dir: Path, port: int) -> None:
        self.proc = proc
        self.data_dir = data_dir
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"

    # -- жизненный цикл ------------------------------------------------------

    def is_alive(self) -> bool:
        return self.proc.poll() is None

    def stop(self) -> None:
        """Корректно останавливает процесс (terminate, затем kill)."""
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)

    # -- вывод процесса ------------------------------------------------------

    def _read_log(self, name: str) -> str:
        path = self.data_dir / name
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def output_text(self) -> str:
        """stdout+stderr процесса (для сообщений об ошибках)."""
        return (
            f"--- stdout ({self.data_dir / 'stdout.log'}) ---\n"
            + self._read_log("stdout.log")
            + f"\n--- stderr ({self.data_dir / 'stderr.log'}) ---\n"
            + self._read_log("stderr.log")
        )

    # -- проверки ------------------------------------------------------------

    def wait_health(self, timeout: float = STARTUP_TIMEOUT_SEC) -> None:
        """Ждёт ответа 200 от корневого эндпоинта (health-check)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.is_alive():
                raise AssertionError(
                    "Бэкенд завершился раньше времени "
                    f"(rc={self.proc.returncode}).\n{self.output_text()}"
                )
            try:
                with urllib.request.urlopen(self.base_url + "/", timeout=1) as resp:
                    if resp.status == 200:
                        return
            except urllib.error.URLError, OSError:
                pass
            time.sleep(0.5)
        raise AssertionError(
            f"Бэкенд не ответил на health-check за {timeout:g}с.\n{self.output_text()}"
        )

    def get_json(self, path: str) -> tuple[int, object]:
        """GET по пути; возвращает ``(status, json)``."""
        with urllib.request.urlopen(self.base_url + path, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)


def inspect_db(data_dir: Path) -> tuple[Path, set[str], str | None]:
    """Возвращает (путь к БД, набор таблиц, версия alembic_version).

    Для «старой» БД без alembic_version версия возвращается как None.
    """
    db_path = data_dir / "school_kiosk.db"
    assert db_path.is_file(), f"Файл БД не создан: {db_path}"
    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        try:
            row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
            version = row[0] if row else None
        except sqlite3.OperationalError:
            version = None
    finally:
        conn.close()
    return db_path, tables, version


async def _create_legacy_db_async(db_path: Path) -> None:
    """Создаёт «старую» БД: только create_all, без alembic_version, с данными."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            session.add(
                ScheduleImage(
                    name="legacy-запись",
                    image="legacy.png",
                    is_active=False,
                    day_of_week=DayOfWeek.MONDAY,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()


def create_legacy_db(data_dir: Path) -> None:
    """Создаёт БД так, как её создавали старые версии (без Alembic)."""
    asyncio.run(_create_legacy_db_async(data_dir / "school_kiosk.db"))


def spawn_backend(exe: Path, data_dir: Path, port: int) -> BackendProcess:
    """Запускает собранный бэкенд с каталогом данных и ждёт health-check."""
    # Абсолютный путь: процесс стартует с cwd=data_dir, относительный exe
    # (например, из KIOSK_BACKEND_EXE) там бы не нашёлся.
    exe = exe.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["SCHOOL_KIOSK_DATA_DIR"] = str(data_dir)
    env["BACKEND_SERVER_HOST"] = "127.0.0.1"
    env["BACKEND_SERVER_PORT"] = str(port)
    env["BACKEND_DEBUG"] = "false"
    # Несуществующий каталог SPA: корень отдаёт JSON-health, а не index.html.
    env["SCHOOL_KIOSK_FRONTEND_DIR"] = str(data_dir / "__no_frontend__")

    with (
        open(data_dir / "stdout.log", "wb") as stdout_f,
        open(data_dir / "stderr.log", "wb") as stderr_f,
    ):
        proc = subprocess.Popen(
            [str(exe)],
            env=env,
            stdout=stdout_f,
            stderr=stderr_f,
            cwd=str(data_dir),
        )
    bp = BackendProcess(proc, data_dir, port)
    bp.wait_health()
    return bp
