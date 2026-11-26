"""Идемпотентный seed настроек и реестра сервисов при первом запуске.

Порядок источников значений:

1. таблица ``app_settings`` — основной источник после первого запуска;
2. legacy-файл ``settings.json`` — переносится только если таблица пуста;
3. значения по умолчанию из :data:`SETTINGS_SCHEMA`.

Реестр ``app_units`` заполняется недостающими сервисами независимо от
настроек: так новые плитки появляются после обновления приложения.
"""

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import DBDependency
from src.core.settings_schema import (
    DEFAULT_APP_UNITS,
    SETTINGS_BY_KEY,
    SETTINGS_SCHEMA,
    SettingsKey,
)
from src.models import AppSetting, AppUnit
from src.utils.retry import with_retry_commit

logger = logging.getLogger(__name__)

#: Соответствие полей legacy ``settings.json`` ключам новой схемы.
LEGACY_SETTINGS_MAP: dict[str, SettingsKey] = {
    "static_dir": SettingsKey.SYSTEM_STATIC_DIR,
    "local_image_dir": SettingsKey.SYSTEM_LOCAL_IMAGE_DIR,
    "autostart": SettingsKey.SYSTEM_AUTOSTART,
    "schedule_mode": SettingsKey.SCHEDULE_MODE,
    "current_local_schedule_image_filename": SettingsKey.SCHEDULE_CURRENT_LOCAL_IMAGE,
    "welcome_message": SettingsKey.UI_WELCOME_MESSAGE,
    "use_weather": SettingsKey.WEATHER_ENABLED,
    "use_weather_app": SettingsKey.WEATHER_ENABLED,
    "weather_api": SettingsKey.WEATHER_API,
    "location": SettingsKey.WEATHER_LOCATION,
}


def read_legacy_settings(path: Path | None) -> dict[str, Any]:
    """Читает legacy ``settings.json``; при ошибке возвращает пустой словарь."""
    if path is None or not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError, OSError:
        logger.warning("Не удалось прочитать legacy-настройки: %s", path)
        return {}
    return raw if isinstance(raw, dict) else {}


def _coerce_legacy(legacy: dict[str, Any]) -> dict[str, Any]:
    """Приводит legacy-значения к новой схеме, пропуская некорректные."""
    values: dict[str, Any] = {}
    for legacy_key, key in LEGACY_SETTINGS_MAP.items():
        if legacy_key not in legacy:
            continue
        spec = SETTINGS_BY_KEY[key.value]
        try:
            values[key.value] = spec.coerce(legacy[legacy_key])
        except ValueError:
            logger.warning(
                "Пропускаю некорректное legacy-значение %s=%r",
                legacy_key,
                legacy[legacy_key],
            )
    return values


async def seed_app_settings(
    session: AsyncSession,
    *,
    legacy_settings: dict[str, Any] | None = None,
) -> int:
    """Заполняет ``app_settings``, если таблица пуста.

    Returns:
        Количество вставленных настроек.
    """
    count = (
        await session.execute(select(func.count()).select_from(AppSetting))
    ).scalar_one()
    if count:
        return 0

    values = _coerce_legacy(legacy_settings or {})
    for spec in SETTINGS_SCHEMA:
        values.setdefault(spec.key.value, spec.default)

    for key, value in values.items():
        session.add(AppSetting(key=key, value=value))
    await session.flush()
    return len(values)


async def seed_app_units(session: AsyncSession) -> int:
    """Добавляет недостающие сервисы из :data:`DEFAULT_APP_UNITS`.

    Returns:
        Количество созданных сервисов.
    """
    existing = set((await session.execute(select(AppUnit.key))).scalars().all())
    created = 0
    for unit in DEFAULT_APP_UNITS:
        if unit["key"] in existing:
            continue
        session.add(AppUnit(**unit))
        created += 1
    await session.flush()
    return created


async def seed_all(
    db: DBDependency,
    *,
    legacy_file: Path | None,
) -> None:
    """Выполняет seed настроек и сервисов в одной транзакции."""
    legacy_settings = read_legacy_settings(legacy_file)
    async with db.db_session() as session:
        settings_created = await seed_app_settings(
            session, legacy_settings=legacy_settings
        )
        units_created = await seed_app_units(session)
        await with_retry_commit(session)

    if settings_created or units_created:
        logger.info(
            "Seed настроек: добавлено %s настроек и %s сервисов",
            settings_created,
            units_created,
        )
