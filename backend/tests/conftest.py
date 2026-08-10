import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from src.core.database import get_db_dependency
from src.main import app
from src.models.base import Base
from src.models.schedule import Lesson, ScheduleRow, ScheduleTable

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(scope="session")
def test_engine():
    """Создание тестового движка SQLAlchemy с SQLite в памяти."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def session(test_engine):
    """Создание сессии SQLAlchemy для тестирования."""
    connection = test_engine.connect()
    transaction = connection.begin()

    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
    )

    session = testing_session_local()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(session: Session):
    """Фикстура для тестового клиента FastAPI с переопределенной зависимостью БД."""

    app.dependency_overrides[get_db_dependency] = lambda: _SessionDependency(session)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


class _SessionDependency:
    """DBDependency с замененной синхронной сессией."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def db_session(self):
        return _SyncSessionFactory(self._session)


class _SyncSessionFactory:
    """Фабрика синхронных сессий."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def __call__(self):
        return _SessionContext(self._session)


class _SessionContext:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def __aenter__(self) -> Session:
        return self._session

    async def __aexit__(self, *exc) -> None:
        pass


@pytest.fixture(autouse=True)
def clean_db(session):
    """Очистка БД после каждого теста."""
    yield
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()


@pytest.fixture()
def schedule_table_sample(session: Session):
    """Фикстура для создания примера таблицы расписания."""
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
    session.add(schedule)
    session.flush()
    return schedule
