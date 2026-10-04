"""Тесты миграции создания дефолтного администратора.

Проверяют цепочку из двух новых миграций:
``dc9b10c40f1a`` (создание всех таблиц) → ``5b857b4a2e4c`` (создание
дефолтного администратора), а также автоприменение через ``apply_schema``
на свежей и «старой» (без alembic_version) БД.
"""

import sqlite3

import pytest
from alembic import command
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.core import migrations
from src.core.config import settings
from src.core.security import verify_password
from src.enums.schedule import DayOfWeek
from src.models import ScheduleImage
from src.models.base import Base

# Ревизия миграции, создающей таблицы (до создания дефолтного админа).
BASE_REVISION = "dc9b10c40f1a"


def _point_data_dir(tmp_path, monkeypatch) -> None:
    """Направляет settings.database_url на БД в tmp_path/data."""
    monkeypatch.setenv("SCHOOL_KIOSK_DATA_DIR", str(tmp_path / "data"))


def _head() -> str:
    return migrations._head_revision(migrations._make_config())


def _connect(data_dir):
    conn = sqlite3.connect(data_dir / "school_kiosk.db")
    return conn


# ---------------------------------------------------------------------------
# Миграция напрямую (alembic upgrade/downgrade)
# ---------------------------------------------------------------------------


def test_upgrade_head_creates_default_admin(tmp_path, monkeypatch):
    """После upgrade head появляются все таблицы и дефолтный админ."""
    _point_data_dir(tmp_path, monkeypatch)
    cfg = migrations._make_config()
    command.upgrade(cfg, "head")

    conn = _connect(tmp_path / "data")
    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "admin_profiles" in tables
        assert "alembic_version" in tables
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        row = conn.execute(
            "SELECT login, password_hash, is_active, is_default FROM admin_profiles"
        ).fetchone()
    finally:
        conn.close()

    assert version == _head()
    assert row is not None, "Дефолтный администратор не создан миграцией"
    login, password_hash, is_active, is_default = row
    assert login == settings.default_admin_login
    assert is_active == 1
    assert is_default == 1
    assert verify_password(settings.default_admin_password, password_hash)


def test_upgrade_head_is_idempotent(tmp_path, monkeypatch):
    """Повторный upgrade head не дублирует дефолтного администратора."""
    _point_data_dir(tmp_path, monkeypatch)
    cfg = migrations._make_config()
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")  # второй вызов — no-op

    conn = _connect(tmp_path / "data")
    try:
        count = conn.execute("SELECT COUNT(*) FROM admin_profiles").fetchone()[0]
    finally:
        conn.close()
    assert count == 1


def test_downgrade_removes_default_admin(tmp_path, monkeypatch):
    """Downgrade до базовой ревизии удаляет дефолтного администратора."""
    _point_data_dir(tmp_path, monkeypatch)
    cfg = migrations._make_config()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, BASE_REVISION)

    conn = _connect(tmp_path / "data")
    try:
        count = conn.execute("SELECT COUNT(*) FROM admin_profiles").fetchone()[0]
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    finally:
        conn.close()
    assert count == 0
    assert version == BASE_REVISION


# ---------------------------------------------------------------------------
# Автоприменение схемы через apply_schema (как при старте бэкенда)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fresh_install_apply_schema_creates_default_admin(tmp_path, monkeypatch):
    """Свежая БД: apply_schema применяет миграции и создаёт админа."""
    _point_data_dir(tmp_path, monkeypatch)
    db_path = tmp_path / "data" / "school_kiosk.db"

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    try:
        await migrations.apply_schema(engine)
    finally:
        await engine.dispose()

    conn = _connect(tmp_path / "data")
    try:
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        row = conn.execute(
            "SELECT login, password_hash FROM admin_profiles WHERE is_default = 1"
        ).fetchone()
    finally:
        conn.close()

    assert version == _head()
    assert row is not None, "На свежей БД дефолтный администратор не создан"
    assert row[0] == settings.default_admin_login
    assert verify_password(settings.default_admin_password, row[1])


@pytest.mark.asyncio
async def test_legacy_db_upgrade_keeps_data_and_creates_default_admin(
    tmp_path, monkeypatch
):
    """«Старая» БД (create_all, без alembic_version): данные сохраняются,
    схема помечается head, дефолтный администратор появляется."""
    data = tmp_path / "data"
    data.mkdir(parents=True)
    _point_data_dir(tmp_path, monkeypatch)
    db_path = data / "school_kiosk.db"

    # Создаём БД так, как её создавали старые версии: только create_all.
    legacy = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    try:
        async with legacy.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(legacy, expire_on_commit=False)() as session:
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
        await legacy.dispose()

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    try:
        await migrations.apply_schema(engine)
    finally:
        await engine.dispose()

    conn = _connect(data)
    try:
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        names = [row[0] for row in conn.execute("SELECT name FROM schedule_images")]
        admin = conn.execute(
            "SELECT login, password_hash FROM admin_profiles WHERE is_default = 1"
        ).fetchone()
    finally:
        conn.close()

    assert version == _head()
    assert names == ["legacy-запись"], "Данные старой БД потеряны"
    assert admin is not None, "При апгрейде старой БД админ не создан"
    assert admin[0] == settings.default_admin_login
    assert verify_password(settings.default_admin_password, admin[1])
