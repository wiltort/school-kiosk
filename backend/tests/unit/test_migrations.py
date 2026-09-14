"""Тесты автоприменения миграций Alembic (src/core/migrations.py)."""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from src.core import migrations
from src.core.config import settings

# ---------------------------------------------------------------------------
# Резолвинг ресурсов и конфигурации Alembic
# ---------------------------------------------------------------------------


def test_resource_dir_points_to_backend_in_dev():
    """В dev-сборке ресурсы лежат в каталоге backend/ рядом с исходниками."""
    assert migrations._resource_dir() == migrations.BACKEND_DIR
    assert (migrations._resource_dir() / "alembic.ini").is_file()
    assert (migrations._resource_dir() / "alembic" / "env.py").is_file()


def test_make_config_sets_script_location_and_url():
    """Конфиг Alembic указывает на каталог миграций и URL БД из настроек."""
    cfg = migrations._make_config()
    script_location = cfg.get_main_option("script_location")
    assert Path(script_location).is_dir()
    assert (Path(script_location) / "versions").is_dir()
    assert cfg.get_main_option("sqlalchemy.url") == settings.database_url


def test_head_revision_resolves():
    """Head-ревизия определяется по скриптам миграций."""
    cfg = migrations._make_config()
    head = migrations._head_revision(cfg)
    assert head is not None
    assert len(head) == 12  # например 68b6052c3c03


def test_sqlite_file_memory_returns_none():
    """Для in-memory БД файл не определяется."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    try:
        assert migrations._sqlite_file(engine) is None
    finally:
        engine.sync_engine.dispose()


def test_sqlite_file_file_backed(tmp_path):
    """Для файловой БД возвращается путь к файлу."""
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    try:
        assert migrations._sqlite_file(engine) == db_path
    finally:
        engine.sync_engine.dispose()


# ---------------------------------------------------------------------------
# Резервное копирование БД
# ---------------------------------------------------------------------------


def test_backup_creates_copy_when_db_exists(tmp_path):
    """При наличии файла БД создаётся резервная копия."""
    db_path = tmp_path / "test.db"
    db_path.write_bytes(b"sqlite-content")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    try:
        backup = migrations._backup_database_if_exists(engine)
        assert backup is not None
        assert backup.exists()
        assert backup.read_bytes() == b"sqlite-content"
        assert backup != db_path
    finally:
        engine.sync_engine.dispose()


def test_backup_noop_for_missing_db(tmp_path):
    """Если файла БД нет — резервная копия не создаётся."""
    db_path = tmp_path / "missing.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    try:
        assert migrations._backup_database_if_exists(engine) is None
        assert not list(tmp_path.glob("*.backup-*"))
    finally:
        engine.sync_engine.dispose()


def test_backup_noop_for_memory():
    """Для in-memory БД резервная копия не создаётся."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    try:
        assert migrations._backup_database_if_exists(engine) is None
    finally:
        engine.sync_engine.dispose()


# ---------------------------------------------------------------------------
# Запросы к схеме БД
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_table_exists_and_current_revision():
    """Проверка вспомогательных запросов к alembic_version."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)

    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
            )
            await conn.execute(text("INSERT INTO alembic_version VALUES ('abc123')"))

        assert await migrations._table_exists(engine, "alembic_version") is True
        assert await migrations._table_exists(engine, "no_such_table") is False
        assert await migrations._current_revision(engine) == "abc123"
    finally:
        engine.sync_engine.dispose()
