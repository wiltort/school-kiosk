"""Общие фикстуры для тестирования бэкенда."""

import asyncio
import os
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault(
    "SCHOOL_KIOSK_FRONTEND_DIR",
    str(Path(__file__).resolve().parent / "__no_frontend_build__"),
)

os.environ.setdefault("BACKEND_CRON_ENABLED", "0")

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from src.core import migrations
from src.core.database import DBDependency, get_db_dependency
from src.core.storage import get_image_storage
from src.main import app
from src.models.base import Base

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class FakeImageStorage:
    """Заглушка хранилища изображений для тестов (без работы с диском)."""

    saved_path = "stored/schedule.png"

    def __init__(self) -> None:
        self.saved: list[tuple[bytes, str]] = []
        self.deleted: list[str] = []
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def save(
        self,
        data: bytes,
        filename: str,
        subdir: str = "",  # noqa: ARG002
        is_local: bool = False,  # noqa: ARG002
    ) -> str:
        self.saved.append((data, filename))
        subdir = subdir or "stored"
        return f"{subdir}/{filename}"

    def delete(self, path: str) -> None:
        self.deleted.append(path)

    def read_file_metadata(self, path: str, *args, **kwargs) -> dict:  # noqa: ARG002
        return {"file_hash": f"{path}", "file_size": len(path), "mtime": 0.2}

    def restore_file(self, path: str) -> bool:  # noqa: ARG002
        return True

    def lock(self, key: str) -> asyncio.Lock:
        return self._locks[key]

    def read_file(self, path: str, is_local: bool = False):
        if is_local:
            return b"image"
        try:
            file = filter(lambda x: x[1] == path, self.saved)
        except Exception:
            return None
        if file:
            return list(file)[0][0]


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Создаёт асинхронный движок SQLite in-memory и создаёт все таблицы."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session_maker(async_engine):
    """Возвращает фабрику асинхронных сессий (для каждого теста своя)."""
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture(scope="function")
async def async_session(async_session_maker):
    """Создаёт конкретную сессию для использования в тестах (опционально)."""
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(async_engine, async_session_maker):
    """Тестовый клиент FastAPI с подменой зависимости БД на асинхронную."""

    def override_get_db():
        """Возвращает зависимость БД с асинхронной фабрикой сессий."""
        return DBDependency(async_session_maker)

    def override_image_storage():
        """Подменяет хранилище файлов заглушкой."""
        return FakeImageStorage()

    # In-memory тестовая БД создаётся через Base.metadata.create_all, поэтому
    # дефолтного администратора в ней нет (в проде его создаёт миграция
    # 5b857b4a2e4c / apply_schema; до реальной файловой БД миграции на старте
    # тестов действительно применяются, но запросы идут в in-memory БД).
    # Добавляем админа здесь, иначе POST /api/v1/admin/login с дефолтными
    # учётными данными вернёт 401. Фикстура function-scope: clean_db стирает
    # строки после каждого теста, а репозиторные тесты (count == 0) не
    # используют client и остаются с пустой таблицей.
    await migrations._ensure_default_admin(async_engine)

    app.dependency_overrides[get_db_dependency] = override_get_db
    app.dependency_overrides[get_image_storage] = override_image_storage
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def clean_db(async_session_maker):
    """Автоматически очищает все таблицы после каждого теста."""
    yield
    async with async_session_maker() as session:
        try:
            for table in reversed(Base.metadata.sorted_tables):
                await session.execute(table.delete())
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


@pytest_asyncio.fixture
async def schedule_table_sample(async_session_maker):
    """Создаёт пример расписания в БД и возвращает объект ScheduleTable."""
    from src.models import Lesson, ScheduleColumn, ScheduleTable

    schedule = ScheduleTable(
        schedule_columns=[
            ScheduleColumn(
                number=1,
                header="1",
                lessons=[
                    Lesson(number=1, name="History"),
                    Lesson(number=2, name="Math"),
                ],
            ),
            ScheduleColumn(
                number=2,
                header="2",
                lessons=[
                    Lesson(number=1, name="History"),
                    Lesson(number=2, name="Math"),
                ],
            ),
        ]
    )
    async with async_session_maker() as session:
        session.add(schedule)
        await session.flush()
        await session.commit()
        await session.refresh(schedule)

        return schedule


@pytest_asyncio.fixture()
def manager_factory(async_session_maker):
    """Фабрика менеджеров для тестирования."""

    def _create_manager(manager_cls, *args, **kwargs):
        """Создаёт экземпляр менеджера с подменённой зависимостью БД."""
        db_dependency = DBDependency(async_session_maker)
        return manager_cls(*args, db=db_dependency, **kwargs)

    return _create_manager


@pytest.fixture()
def fake_image_storage() -> FakeImageStorage:
    """Возвращает новый экземпляр заглушки хранилища изображений."""
    return FakeImageStorage()


@pytest.fixture()
def sync_session():
    """Провайдер синхронной сессии SQLAlchemy."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()
