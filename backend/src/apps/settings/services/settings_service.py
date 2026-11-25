"""Типизированный доступ к настройкам приложения в БД.

Настройки хранятся в таблице ``app_settings`` (key-value). Сервис
объединяет сохранённые значения со схемой :data:`SETTINGS_SCHEMA`
(значения по умолчанию, типы и валидация) и кеширует результат в памяти
процесса. Кеш сбрасывается после каждой записи.
"""

import threading
from enum import StrEnum
from typing import Annotated, Any

from fastapi import Depends

from src.apps.settings.repositories import SettingsRepository
from src.core.database import DBDependency, get_db_dependency
from src.core.settings_schema import (
    SETTINGS_BY_KEY,
    SETTINGS_SCHEMA,
    SettingsKey,
    SettingSpec,
)
from src.utils.retry import with_retry_commit

_caches: dict[int, dict[str, Any]] = {}
_cache_lock = threading.Lock()


def invalidate_settings_cache(cache_key: int | None = None) -> None:
    """Сбрасывает кеш настроек.

    Без аргумента очищает кеши всех БД (используется в тестах), с аргументом —
    только кеш конкретного движка.
    """
    with _cache_lock:
        if cache_key is None:
            _caches.clear()
        else:
            _caches.pop(cache_key, None)


class SettingsService:
    """Читает и пишет настройки приложения с валидацией по схеме."""

    def __init__(
        self,
        db: Annotated[DBDependency, Depends(get_db_dependency)],
        repo: Annotated[SettingsRepository, Depends()],
    ) -> None:
        self.db = db
        self.repo = repo

    @staticmethod
    def spec(key: SettingsKey | str) -> SettingSpec:
        """Возвращает описание настройки по ключу.

        Raises:
            ValueError: если ключ отсутствует в реестре.
        """
        try:
            return SETTINGS_BY_KEY[str(key)]
        except KeyError as exc:
            raise ValueError(f"Неизвестная настройка: {key!r}") from exc

    def _cache_key(self) -> int:
        """Идентификатор БД для кеша: один движок — один кеш."""
        bind = self.db.db_session.kw.get("bind")
        return id(bind) if bind is not None else id(self.db.db_session)

    async def _load(self) -> dict[str, Any]:
        """Возвращает все настройки, объединяя БД со значениями по умолчанию."""
        cache_key = self._cache_key()
        with _cache_lock:
            cached = _caches.get(cache_key)
            if cached is not None:
                return dict(cached)

        async with self.db.db_session() as session:
            rows = await self.repo.list_all(session)
        stored = {row.key: row.value for row in rows}
        data = {
            spec.key.value: stored.get(spec.key.value, spec.default)
            for spec in SETTINGS_SCHEMA
        }
        with _cache_lock:
            _caches[cache_key] = data
        return dict(data)

    async def as_dict(self) -> dict[str, Any]:
        """Возвращает все известные настройки."""
        return await self._load()

    async def get(self, key: SettingsKey | str) -> Any:
        """Возвращает значение настройки."""
        return (await self._load())[str(key)]

    async def get_bool(self, key: SettingsKey | str) -> bool:
        """Возвращает настройку как ``bool``."""
        return bool(await self.get(key))

    async def get_int(self, key: SettingsKey | str) -> int:
        """Возвращает настройку как ``int``."""
        return int(await self.get(key))

    async def get_str(self, key: SettingsKey | str) -> str | None:
        """Возвращает настройку как ``str`` либо ``None``."""
        value = await self.get(key)
        return None if value is None else str(value)

    async def get_enum(self, key: SettingsKey | str) -> StrEnum:
        """Возвращает enum-значение настройки.

        Raises:
            ValueError: если настройка не является enum-типом.
        """
        spec = self.spec(key)
        if spec.enum_type is None:
            raise ValueError(f"Настройка {spec.key.value!r} не является enum")
        return spec.enum_type(await self.get(key))

    async def set(self, key: SettingsKey | str, value: Any) -> Any:
        """Сохраняет одну настройку и возвращает её новое значение."""
        return (await self.set_many({str(key): value}))[str(key)]

    async def set_many(self, values: dict[str, Any]) -> dict[str, Any]:
        """Сохраняет набор настроек с валидацией по схеме.

        Raises:
            ValueError: если ключ неизвестен или значение не проходит валидацию.
        """
        normalized: dict[str, Any] = {}
        for key, value in values.items():
            spec = self.spec(key)
            normalized[spec.key.value] = spec.coerce(value)

        async with self.db.db_session() as session:
            await self.repo.upsert_many(session, normalized)
            await with_retry_commit(session)
        invalidate_settings_cache(self._cache_key())
        return await self._load()

    async def ensure_defaults(self) -> None:
        """Добавляет отсутствующие в БД ключи со значениями по умолчанию."""
        async with self.db.db_session() as session:
            rows = await self.repo.list_all(session)
            existing = {row.key for row in rows}
            missing = {
                spec.key.value: spec.default
                for spec in SETTINGS_SCHEMA
                if spec.key.value not in existing
            }
            if not missing:
                return
            await self.repo.upsert_many(session, missing)
            await with_retry_commit(session)
        invalidate_settings_cache(self._cache_key())
