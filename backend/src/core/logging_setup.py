"""Настройка логирования бэкенда.

В dev-режиме достаточно вывода в stderr, но в релизе (PyInstaller) бэкенд
запускается Rust-оболочкой Tauri с перенаправлением stdout/stderr в каналы,
которые никто не читает:

* при ошибке до инициализации логов сообщение просто теряется (окно у приложения
  нет, а Rust читает только код возврата процесса);
* при большом объёме вывода канал (64 КБ) переполняется, и процесс блокируется
  на записи — выглядит как «зависший» бэкенд.

Поэтому помимо консоли пишем лог в файл ``<data_dir>/logs/backend.log`` — тот же
каталог, где Rust-оболочка хранит ``update.log``. Файл ротируется по размеру.

Инициализация выполняется на этапе импорта ``src.main`` (до создания FastAPI-
приложения) и повторно внутри lifespan вокруг миграций: ``alembic/env.py``
вызывает ``fileConfig``, который может переопределить корневой логгер.
Повторные вызовы идемпотентны — хендлеры не дублируются.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE_NAME = "backend.log"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3
ENCODING = "utf-8"

# Атрибут-маркер на наших хендлерах: позволяет не добавлять дубликаты при
# повторных вызовах setup_logging() (в том числе после переконфигурации
# logging внутри alembic/env.py).
_MARKER_ATTR = "_school_kiosk_handler"
_MARKER_FILE = "file"
_MARKER_CONSOLE = "console"


def log_file_path(data_dir: Path) -> Path:
    """Полный путь к файлу лога бэкенда."""
    return Path(data_dir) / "logs" / LOG_FILE_NAME


def _install(root: logging.Logger, handler: logging.Handler, marker: str) -> None:
    """Добавляет хендлер, если такого ещё нет (по маркеру)."""
    for existing in root.handlers:
        if getattr(existing, _MARKER_ATTR, None) == marker:
            return
    setattr(handler, _MARKER_ATTR, marker)
    root.addHandler(handler)


def setup_logging(
    *,
    data_dir: Path | None = None,
    level: str | int = logging.INFO,
    log_format: str = "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
) -> None:
    """Конфигурирует корневой логгер: файл + консоль (stderr).

    Args:
        data_dir: Каталог данных приложения (в него пишется ``logs/backend.log``).
            Если ``None`` — файловый лог не создаётся (только консоль).
        level: Уровень логирования (строка или константа logging).
        log_format: Формат сообщений.
        datefmt: Формат даты/времени.
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    formatter = logging.Formatter(log_format, datefmt=datefmt)

    # Файловый лог — главный источник диагностики в релизе.
    if data_dir is not None:
        path = log_file_path(data_dir)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            logging.getLogger(__name__).exception(
                "Не удалось создать каталог для файла лога %s", path.parent
            )
        else:
            try:
                handler = RotatingFileHandler(
                    path,
                    maxBytes=MAX_BYTES,
                    backupCount=BACKUP_COUNT,
                    encoding=ENCODING,
                )
                handler.setFormatter(formatter)
                _install(root, handler, _MARKER_FILE)
            except OSError:
                logging.getLogger(__name__).exception(
                    "Не удалось открыть файл лога %s", path
                )

    # Консоль (stderr): видна в dev; в релизе uvicorn также пишет туда.
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    _install(root, console, _MARKER_CONSOLE)

    # Умеряем шум от библиотек: SQLAlchemy сам пишет в свой логгер.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
