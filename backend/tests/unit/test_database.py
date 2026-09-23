"""Тесты для синглтона зависимости базы данных."""

import types

import pytest
from src.core import database as database_module
from src.core.database import DBDependency, get_db_dependency, reset_db_dependency


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Сбрасывает синглтон до и после теста для изоляции."""
    reset_db_dependency()
    yield
    reset_db_dependency()


def test_get_db_dependency_returns_singleton():
    """Повторные вызовы возвращают один и тот же экземпляр DBDependency."""
    first = get_db_dependency()
    second = get_db_dependency()
    assert first is second
    assert isinstance(first, DBDependency)


def test_db_dependency_engine_is_shared():
    """Движок внутри синглтона не пересоздаётся между вызовами."""
    first = get_db_dependency().db_engine
    second = get_db_dependency().db_engine
    assert first is second
    assert first is not None


def test_reset_db_dependency_clears_singleton():
    """После сброса создаётся новый экземпляр."""
    first = get_db_dependency()
    reset_db_dependency()
    second = get_db_dependency()
    assert first is not second


@pytest.mark.asyncio
async def test_engine_applies_sqlite_pragmas(tmp_path, monkeypatch):
    """Прагмы (foreign_keys, WAL, synchronous) применяются на соединении.

    database_url у Settings — property, поэтому подменяем модульную ссылку
    src.core.database.settings целиком.
    """
    db_path = tmp_path / "pragma_test.db"
    monkeypatch.setattr(
        database_module,
        "settings",
        types.SimpleNamespace(
            database_url=f"sqlite+aiosqlite:///{db_path.as_posix()}",
            db_echo=False,
        ),
    )
    dep = get_db_dependency()
    engine = dep.db_engine
    assert engine is not None
    try:
        async with engine.connect() as conn:
            foreign_keys = (
                await conn.exec_driver_sql("PRAGMA foreign_keys")
            ).fetchone()
            assert foreign_keys[0] == 1

            journal_mode = (
                await conn.exec_driver_sql("PRAGMA journal_mode")
            ).fetchone()
            assert journal_mode[0] == "wal"

            synchronous = (await conn.exec_driver_sql("PRAGMA synchronous")).fetchone()
            assert synchronous[0] == 1  # NORMAL
    finally:
        await engine.dispose()
