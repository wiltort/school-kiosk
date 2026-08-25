"""Общие фикстуры для тестирования бэкенда."""

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from src.core.database import DBDependency, get_db_dependency
from src.main import app
from src.models.base import Base

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


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
        autocommit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture(scope="function")
async def async_session(async_session_maker):
    """Создаёт конкретную сессию для использования в тестах (опционально)."""
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(async_session_maker):
    """Тестовый клиент FastAPI с подменой зависимости БД на асинхронную."""

    def override_get_db():
        """Возвращает зависимость БД с асинхронной фабрикой сессий."""
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
def sync_session():
    """Провайдер синхронной сессии SQLAlchemy."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()
