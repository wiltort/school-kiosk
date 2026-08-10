import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from src.core.database import get_db_engine
from src.main import app
from src.models.base import Base
from src.models.schedule import Lesson, ScheduleRow, ScheduleTable


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

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db_engine] = override_get_db

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def schedule_table_sample(session: Session):
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
    return schedule.__dict__
