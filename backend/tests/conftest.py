"""Общие фикстуры для тестирования бэкенда."""

import sys
from pathlib import Path

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.core.database import DBDependency, get_db_dependency
from src.main import app
from src.models.base import Base

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Создаёт асинхронный движок SQLite in-memory и создаёт все таблицы."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session_maker(async_engine):
    """Возвращает фабрику асинхронных сессий (для каждого теста своя)."""
    return async_sessionmaker(async_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def async_session(async_session_maker):
    """Создаёт конкретную сессию для использования в тестах (опционально)."""
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
def client(async_session_maker):
    """Тестовый клиент FastAPI с подменой зависимости БД на асинхронную."""

    def override_get_db():
        return DBDependency(async_session_maker)

    app.dependency_overrides[get_db_dependency] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def clean_db(async_session_maker):
    """Автоматически очищает все таблицы после каждого теста."""
    yield
    async with async_session_maker() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest_asyncio.fixture
async def schedule_table_sample(async_session_maker):
    """Создаёт пример расписания в БД и возвращает объект ScheduleTable."""
    from src.models.schedule import Lesson, ScheduleRow, ScheduleTable

    schedule = ScheduleTable(
        schedule_rows=[
            ScheduleRow(
                number=1,
                header="1",
                lessons=[
                    Lesson(number=1, name="History"),
                    Lesson(number=2, name="Math"),
                ],
            ),
            ScheduleRow(
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


@pytest_asyncio.fixture
def manager_factory(async_session_maker):
    """Фабрика менеджеров для тестирования."""

    def _create_manager(manager_cls):
        db_dependency = DBDependency(async_session_maker)
        return manager_cls(db=db_dependency)

    return _create_manager
