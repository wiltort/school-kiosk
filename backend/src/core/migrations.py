"""Автоматическое применение миграций базы данных при старте приложения.

Зачем это нужно: приложение обновляется тихо через автообновление Tauri
(NSIS-инсталлятор заменяет только исполняемые файлы, а БД живёт в каталоге
данных и сохраняется). Если новая версия меняет схему существующих таблиц,
одного ``Base.metadata.create_all`` недостаточно — он только создаёт недостающие
таблицы, но не изменяет уже существующие (не добавляет колонки и т.п.). Поэтому
схема ведётся через Alembic-миграции, которые применяются автоматически перед
обслуживанием запросов.

Стратегия (гибрид create_all + Alembic):
  * ``create_all`` — фолбэк только для создания базовых таблиц (в основном на
    пустой БД), чтобы не полагаться на реплей миграций для начальной схемы.
  * Alembic — единственный источник изменений *существующих* таблиц (ALTER и
    новые таблицы поверх текущего ``head``).

Чтобы они не конфликтовали:
  * если в БД нет таблицы ``alembic_version`` (пустая БД или БД, созданная ранее
    только через ``create_all``), мы *стампим* ``head``, а не реплеим миграции —
    иначе первая миграция попытается создать таблицы, которые уже создаст
    ``create_all``;
  * если версия отстаёт от ``head`` — делаем резервную копию файла БД и
    применяем ``upgrade head``.

Alembic ``env.py`` запускает внутри себя ``asyncio.run()``, поэтому вызывать его
из уже работающего event loop (lifespan) напрямую нельзя — выполняем в отдельном
потоке через ``asyncio.to_thread``.

Файлы миграций (``alembic.ini`` и каталог ``alembic/``) в PyInstaller-сборке
бандлятся как данные (см. target ``build-backend`` в Makefile) и распаковываются
в ``sys._MEIPASS``; в dev-сборке они лежат рядом с исходниками (каталог
``backend/``).
"""

import asyncio
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.config import settings
from src.models.base import Base

logger = logging.getLogger(__name__)

# Каталог `backend/` (родитель каталога `src/core`).
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _resource_dir() -> Path:
    """Каталог, где лежат ``alembic.ini`` и скрипты миграций.

    В dev-сборке — корень ``backend/``. В PyInstaller (onefile) данные лежат в
    ``sys._MEIPASS``, куда их раскладывает распаковщик при старте.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return BACKEND_DIR


def _sqlite_file(engine: AsyncEngine) -> Path | None:
    """Возвращает путь к файлу SQLite из URL движка (или None для :memory:)."""
    url = str(engine.url)
    if "///" not in url:
        return None
    raw = url.split("///", 1)[1]
    if not raw or raw == ":memory:":
        return None
    return Path(raw)


def _make_config() -> Config:
    """Собирает Alembic Config с путями из ресурсного каталога и URL БД."""
    base = _resource_dir()
    cfg = Config(str(base / "alembic.ini"))
    cfg.set_main_option("script_location", str(base / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    return cfg


def _head_revision(cfg: Config) -> str | None:
    """Текущая head-ревизия миграций (или None, если миграций нет)."""
    return ScriptDirectory.from_config(cfg).get_current_head()


async def _table_exists(engine: AsyncEngine, table_name: str) -> bool:
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
                {"name": table_name},
            )
        ).fetchone()
    return row is not None


async def _current_revision(engine: AsyncEngine) -> str | None:
    """Текущая версия БД по таблице ``alembic_version`` (None — нет записи)."""
    async with engine.connect() as conn:
        row = (
            await conn.execute(text("SELECT version_num FROM alembic_version"))
        ).fetchone()
    return row[0] if row else None


def _backup_database_if_exists(engine: AsyncEngine) -> Path | None:
    """Копирует файл БД рядом с собой с меткой времени перед изменениями."""
    db_path = _sqlite_file(engine)
    if db_path is None or not db_path.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = db_path.with_name(f"{db_path.name}.backup-{timestamp}")
    shutil.copy2(db_path, backup)
    logger.info("Создана резервная копия БД перед миграцией: %s", backup)
    return backup


async def run_migrations(engine: AsyncEngine) -> None:
    """Приводит схему БД к актуальному состоянию (миграции Alembic).

    Должна вызываться до ``Base.metadata.create_all`` (внутри ``apply_schema``),
    чтобы ``stamp``/``upgrade`` не конфликтовали с созданием таблиц.
    """
    cfg = _make_config()
    head = _head_revision(cfg)
    if head is None:
        logger.warning("В проекте нет миграций Alembic — пропускаю автозапуск")
        return

    has_version_table = await _table_exists(engine, "alembic_version")

    if not has_version_table:
        # Пустая БД либо БД, созданная ранее только через create_all: схема
        # будет (или уже) создана metadata, поэтому стампим head без реплея,
        # чтобы не наткнуться на "table already exists".
        _backup_database_if_exists(engine)
        await asyncio.to_thread(command.stamp, cfg, head)
        logger.info("БД без alembic_version: схема помечена ревизией %s", head)
        return

    current = await _current_revision(engine)
    if current == head:
        logger.info("БД на актуальной ревизии миграций (%s)", head)
        return

    logger.info("Применяю миграции БД: текущая ревизия %s -> head %s", current, head)
    _backup_database_if_exists(engine)
    # env.py вызывает asyncio.run() внутри себя — из уже работающего event loop
    # это невозможно, поэтому выполняем в отдельном потоке.
    await asyncio.to_thread(command.upgrade, cfg, "head")
    logger.info("Миграции БД применены: %s", head)


async def apply_schema(engine: AsyncEngine) -> None:
    """Приводит БД к актуальному состоянию: миграции + создание недостающих
    таблиц через metadata (фолбэк для пустой БД)."""
    await run_migrations(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
