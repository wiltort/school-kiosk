"""Тесты для синглтона зависимости базы данных."""

import pytest
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
