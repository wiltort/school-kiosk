"""Интеграционные тесты собранного билда бэкенда (GitHub-релиз).

Запускают настоящий ``python-backend.exe`` как отдельный процесс и проверяют
сценарии, которые ломались в CI-релизах:

* свежая установка: бэкенд стартует, создаёт БД, применяет Alembic-миграции
  (то есть alembic-ресурсы реально попали в onefile-сборку);
* API отвечает;
* бэкенд пишет лог в ``<data_dir>/logs/backend.log``;
* повторный запуск на существующей БД стабилен (сценарий автообновления);
* апгрейд «старой» БД (созданной только через ``create_all``, без
  ``alembic_version``) проходит без потери данных.

Если ``python-backend.exe`` не собран — модуль пропускается целиком.
"""

import sqlite3

import pytest

from tests.integration.smoke import (
    create_legacy_db,
    head_revision,
    inspect_db,
    resolve_backend_exe,
)

EXPECTED_TABLES = {
    "alembic_version",
    "schedule_images",
    "schedule_tables",
    "schedule_columns",
    "lessons",
}

_EXE = resolve_backend_exe()
if _EXE is None:
    pytest.skip(
        "python-backend.exe не собран (make build-backend) — интеграционные "
        "тесты релизного билда пропущены",
        allow_module_level=True,
    )


def test_fresh_install_starts_and_serves_health(run_backend, tmp_path):
    """Свежая установка: бэкенд стартует и отвечает на health-check."""
    bp = run_backend(tmp_path / "data")
    status, body = bp.get_json("/")
    assert status == 200
    assert isinstance(body, dict)
    assert "message" in body


def test_fresh_install_creates_db_with_full_schema(run_backend, tmp_path):
    """Свежая установка: создаётся БД, все таблицы и alembic_version == head.

    Если alembic-ресурсы не попали в сборку (историческая поломка CI), вместо
    миграций сработал бы фолбэк и ``alembic_version`` отсутствовала бы.
    """
    bp = run_backend(tmp_path / "data")
    _, tables, version = inspect_db(bp.data_dir)
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Отсутствуют таблицы: {sorted(missing)}"
    assert version == head_revision(), (
        f"alembic_version={version!r}, ожидался head {head_revision()!r} — "
        "похоже, alembic-ресурсы не попали в onefile-сборку"
    )


def test_api_endpoints_respond(run_backend, tmp_path):
    """Основные API-эндпоинты отвечают корректно."""
    bp = run_backend(tmp_path / "data")
    status, body = bp.get_json("/api/v1/schedule_images")
    assert status == 200
    assert body == []
    status, _ = bp.get_json("/api/v1/schedule_images_local")
    assert status == 200


def test_backend_log_written_and_migrations_applied(run_backend, tmp_path):
    """Бэкенд пишет лог-файл, миграции применены, а не фолбэк."""
    bp = run_backend(tmp_path / "data")
    log = bp.data_dir / "logs" / "backend.log"
    assert log.is_file(), "Лог-файл не создан"
    text = log.read_text(encoding="utf-8")
    assert "School Kiosk backend: запуск" in text
    # Миграции должны быть ПРИМЕНЕНЫ (alembic-ресурсы в сборке), фолбэка нет.
    assert "Не удалось применить Alembic-миграции" not in text


def test_restart_on_existing_db_is_stable(run_backend, tmp_path):
    """Повторный запуск на существующей БД не ломает её (сценарий апдейта)."""
    data = tmp_path / "data"
    bp = run_backend(data)
    _, tables_first, version_first = inspect_db(data)
    bp.stop()

    bp2 = run_backend(data)
    _, tables_second, version_second = inspect_db(data)
    assert tables_second == tables_first
    assert version_second == version_first
    # На втором запуске БД уже была на актуальной ревизии — это видно в логе.
    log = (data / "logs" / "backend.log").read_text(encoding="utf-8")
    assert "БД на актуальной ревизии миграций" in log
    assert bp2.is_alive()


def test_upgrade_from_legacy_db_without_alembic_version(run_backend, tmp_path):
    """Апгрейд «старой» БД (без alembic_version) проходит без потери данных."""
    data = tmp_path / "data"
    data.mkdir()
    create_legacy_db(data)
    _, tables_before, version_before = inspect_db(data)
    assert "alembic_version" not in tables_before
    assert version_before is None

    bp = run_backend(data)
    _, tables_after, version_after = inspect_db(data)
    assert "alembic_version" in tables_after
    assert version_after == head_revision()

    conn = sqlite3.connect(data / "school_kiosk.db")
    try:
        names = [row[0] for row in conn.execute("SELECT name FROM schedule_images")]
    finally:
        conn.close()
    assert names == ["legacy-запись"], "Данные старой БД потеряны при апгрейде"
    assert bp.is_alive()
