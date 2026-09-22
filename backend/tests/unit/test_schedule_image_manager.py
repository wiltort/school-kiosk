"""Юнит-тесты для ScheduleImageManager CRUD операций."""

import asyncio
import hashlib
import uuid
from collections import defaultdict
from datetime import UTC

import pytest
from sqlalchemy import select
from src.apps.schedule.managers import ScheduleImageManager
from src.apps.schedule.repositories import ScheduleImageRepository
from src.apps.schedule.schemas import (
    ScheduleImageCreate,
    ScheduleImageUpdate,
)
from src.enums.schedule import DayOfWeek
from src.models import ScheduleImage


def _sample_create(**overrides) -> ScheduleImageCreate:
    payload = {
        "name": "Расписание 1",
        "is_active": True,
        "day_of_week": DayOfWeek.MONDAY,
    }
    payload.update(overrides)
    return ScheduleImageCreate(**payload)


def _make_manager(manager_factory, storage):
    return manager_factory(
        ScheduleImageManager,
        image_repo=ScheduleImageRepository(),
        storage=storage,
    )


async def _create(manager, schedule=None):
    return await manager.create(
        schedule or _sample_create(), data=b"image-bytes", filename="schedule.png"
    )


class LocalSyncStorage:
    """Заглушка хранилища для тестов синхронизации локального файла.

    Эмулирует два источника: локальный файл-источник (``local_data``)
    и статическую копию (``static_data``). Позволяет между вызовами менять
    содержимое локального файла или «удалять» его (``local_missing``),
    чтобы проверить сценарии синхронизации.
    """

    def __init__(
        self,
        local_data: bytes = b"local-v1",
        static_data: bytes | None = None,
        local_missing: bool = False,
    ) -> None:
        self.local_data = local_data
        self.static_data = static_data if static_data is not None else local_data
        self.local_missing = local_missing
        self.saved: list[tuple[bytes, str, str, bool]] = []
        self.deleted: list[str] = []
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    @staticmethod
    def _meta(data: bytes) -> dict:
        return {
            "file_hash": hashlib.sha256(data).hexdigest(),
            "file_size": len(data),
            "mtime": 1.0,
        }

    def lock(self, key: str) -> asyncio.Lock:
        return self._locks[key]

    def save(
        self,
        data: bytes,
        filename: str,
        subdir: str = "",
        is_local: bool = False,
    ) -> str:
        self.saved.append((data, filename, subdir, is_local))
        self.static_data = data
        return f"{subdir}/{filename}".lstrip("/")

    def delete(self, path: str) -> None:
        self.deleted.append(path)

    def restore_file(self, path: str) -> bool:  # noqa: ARG002
        return True

    def read_file(self, path: str, is_local: bool = False) -> bytes | None:  # noqa: ARG002
        if is_local:
            return None if self.local_missing else self.local_data
        return self.static_data

    def read_file_metadata(
        self,
        path: str,  # noqa: ARG002
        is_local: bool = False,
    ) -> dict | None:
        if is_local:
            if self.local_missing:
                return None
            return self._meta(self.local_data)
        return self._meta(self.static_data)


class MissingStaticStorage(LocalSyncStorage):
    """Хранилище, в котором статический файл по заданному пути отсутствует."""

    def __init__(self, missing_path: str = "local/ghost.png", **kwargs) -> None:
        super().__init__(**kwargs)
        self.missing_path = missing_path

    def read_file_metadata(self, path: str, is_local: bool = False) -> dict | None:
        if is_local:
            return super().read_file_metadata(path, is_local=True)
        if path == self.missing_path:
            return None
        return self._meta(self.static_data)


async def _create_local(manager, **overrides) -> None:
    return await manager.create_local(
        filename="current_schedule.jpg",
        schedule=_sample_create(name="Локальное", **overrides),
    )


@pytest.mark.asyncio
async def test_create_schedule_image(manager_factory, fake_image_storage):
    """Проверка создания изображения расписания."""
    manager = _make_manager(manager_factory, fake_image_storage)
    created = await _create(manager)

    assert isinstance(created.id, uuid.UUID)
    assert created.name == "Расписание 1"
    assert created.image == fake_image_storage.saved_path
    assert created.is_active is True
    assert created.day_of_week == DayOfWeek.MONDAY
    assert created.created_at is not None
    assert created.updated_at is not None


@pytest.mark.asyncio
async def test_create_saves_file_via_storage(manager_factory, fake_image_storage):
    """Проверка, что файл передаётся в хранилище при создании."""
    manager = _make_manager(manager_factory, fake_image_storage)

    await _create(manager)

    assert fake_image_storage.saved == [(b"image-bytes", "schedule.png")]


@pytest.mark.asyncio
async def test_create_applies_model_defaults_for_none_fields(
    manager_factory, fake_image_storage
):
    """Проверка применения значений по умолчанию для полей."""
    manager = _make_manager(manager_factory, fake_image_storage)
    created = await _create(
        manager, _sample_create(name=None, is_active=None, day_of_week=None)
    )

    assert created.name == "Untitled"
    assert created.is_active is False
    assert created.day_of_week == DayOfWeek.MONDAY


@pytest.mark.asyncio
async def test_get_schedule_image(manager_factory, fake_image_storage):
    """Тест получения изображния из бд."""
    manager = _make_manager(manager_factory, fake_image_storage)
    created = await _create(manager)

    fetched = await manager.get(created.id)

    assert fetched.id == created.id
    assert fetched.name == created.name


@pytest.mark.asyncio
async def test_get_missing_raises_404(manager_factory, fake_image_storage):
    """Тест выброса HTTP 404 при вызове несуществующего ID."""
    missing_id = uuid.uuid4()
    manager = _make_manager(manager_factory, fake_image_storage)

    with pytest.raises(Exception) as excinfo:
        await manager.get(missing_id)

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_get_all_returns_created_records(manager_factory, fake_image_storage):
    """Тест получения всех созданных записей."""
    manager = _make_manager(manager_factory, fake_image_storage)
    await _create(manager, _sample_create(name="A", day_of_week=DayOfWeek.MONDAY))
    await _create(manager, _sample_create(name="B", day_of_week=DayOfWeek.TUESDAY))

    records = await manager.get_all()

    assert len(records) == 2
    assert {r.name for r in records} == {"A", "B"}


@pytest.mark.asyncio
async def test_get_all_orders_by_day_of_week(manager_factory, fake_image_storage):
    """Тест получения всех записей по дню недели."""
    manager = _make_manager(manager_factory, fake_image_storage)

    await _create(manager, _sample_create(name="late", day_of_week=DayOfWeek.FRIDAY))
    await _create(manager, _sample_create(name="early", day_of_week=DayOfWeek.MONDAY))

    records = await manager.get_all()

    assert [r.name for r in records] == ["early", "late"]


@pytest.mark.asyncio
async def test_update_partial_fields(manager_factory, fake_image_storage):
    """Тест частичного обновления полей."""
    manager = _make_manager(manager_factory, fake_image_storage)

    created = await _create(manager, _sample_create(name="Before"))

    updated = await manager.update(created.id, ScheduleImageUpdate(name="After"))

    assert updated.id == created.id
    assert updated.name == "After"
    assert updated.image == created.image  # unchanged
    assert updated.is_active == created.is_active  # unchanged


@pytest.mark.asyncio
async def test_update_missing_raises_404(manager_factory, fake_image_storage):
    """Тест выброса HTTP 404 при редактировании изображения с несуществующим ID."""
    manager = _make_manager(manager_factory, fake_image_storage)
    with pytest.raises(Exception) as excinfo:
        await manager.update(uuid.uuid4(), ScheduleImageUpdate(name="X"))

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_update_with_empty_payload_raises_400(
    manager_factory, fake_image_storage
):
    """Тест выброса HTTP 400 при пустом payload."""
    manager = _make_manager(manager_factory, fake_image_storage)
    created = await _create(manager)

    with pytest.raises(Exception) as excinfo:
        await manager.update(created.id, ScheduleImageUpdate())

    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_removes_record(
    manager_factory, fake_image_storage, async_session_maker
):
    """Тест удаления записи."""
    manager = _make_manager(manager_factory, fake_image_storage)
    created = await _create(manager)

    await manager.delete(created.id)

    with pytest.raises(Exception) as excinfo:
        await manager.get(created.id)

    assert excinfo.value.status_code == 404

    async with async_session_maker() as session:
        result = await session.execute(
            select(ScheduleImage).where(ScheduleImage.id == created.id)
        )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_missing_raises_404(manager_factory, fake_image_storage):
    """Тест выброса HTTP 404 при удалении несуществующего изображения."""
    manager = _make_manager(manager_factory, fake_image_storage)

    with pytest.raises(Exception) as excinfo:
        await manager.delete(uuid.uuid4())

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_update_is_local_syncs_changed_file(manager_factory, async_session_maker):
    """Синхронизация: при изменении локального файла перезаписывается
    статическая копия и обновляются метаданные изображения."""
    storage = LocalSyncStorage(local_data=b"local-v1")
    manager = _make_manager(manager_factory, storage)
    created = await _create_local(manager)

    # Пользователь заменил файл в каталоге локальных изображений.
    storage.local_data = b"local-v2"
    saves_before = len(storage.saved)

    updated = await manager.update(created.id, ScheduleImageUpdate(), is_local=True)

    # Статическая копия перезаписана новым содержимым локального файла.
    assert len(storage.saved) == saves_before + 1
    data, filename, subdir, is_local = storage.saved[-1]
    assert data == b"local-v2"
    assert filename == "current_schedule.jpg"
    assert subdir == "local"
    assert is_local is True

    # Путь и остальные поля записи не изменились.
    assert updated.image == created.image == "local/current_schedule.jpg"
    assert updated.name == created.name

    # Метаданные изображения переписаны из локального файла-источника.
    async with async_session_maker() as session:
        obj = await session.get(ScheduleImage, created.id)
        assert obj.file_hash == hashlib.sha256(b"local-v2").hexdigest()
        assert obj.file_size == len(b"local-v2")


@pytest.mark.asyncio
async def test_update_is_local_noop_when_file_unchanged(manager_factory):
    """Синхронизация не пересохраняет файл, если локальный файл не менялся."""
    storage = LocalSyncStorage(local_data=b"local-v1")
    manager = _make_manager(manager_factory, storage)
    created = await _create_local(manager)

    saves_before = len(storage.saved)

    updated = await manager.update(created.id, ScheduleImageUpdate(), is_local=True)

    assert len(storage.saved) == saves_before
    assert updated.image == created.image


@pytest.mark.asyncio
async def test_update_is_local_missing_source_skips_sync(manager_factory):
    """Синхронизация откатывается с ошибкой, если файл-источник исчез."""
    storage = LocalSyncStorage(local_data=b"local-v1")
    manager = _make_manager(manager_factory, storage)
    created = await _create_local(manager)

    storage.local_missing = True
    saves_before = len(storage.saved)
    with pytest.raises(Exception) as excinfo:
        await manager.update(created.id, ScheduleImageUpdate(), is_local=True)
    assert excinfo.value.status_code == 400

    updated = await manager.get(created.id)
    assert len(storage.saved) == saves_before
    assert updated.image == created.image
    assert updated.updated_at.replace(tzinfo=UTC) == created.updated_at


@pytest.mark.asyncio
async def test_update_is_local_empty_payload_missing_record_raises_404(
    manager_factory, fake_image_storage
):
    """Пустой payload + is_local=True на несуществующей записи — 404."""
    manager = _make_manager(manager_factory, fake_image_storage)

    with pytest.raises(Exception) as excinfo:
        await manager.update(uuid.uuid4(), ScheduleImageUpdate(), is_local=True)

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_update_replaces_image_and_refreshes_metadata(
    manager_factory, fake_image_storage, async_session_maker
):
    """Обновление поля image перечитывает метаданные нового файла."""
    manager = _make_manager(manager_factory, fake_image_storage)
    created = await _create(manager)

    updated = await manager.update(
        created.id, ScheduleImageUpdate(image="stored/new.png")
    )

    assert updated.image == "stored/new.png"
    async with async_session_maker() as session:
        obj = await session.get(ScheduleImage, created.id)
    # fake-хранилище формирует метаданные из пути файла.
    assert obj.file_hash == "stored/new.png"
    assert obj.file_size == len("stored/new.png")


@pytest.mark.asyncio
async def test_update_image_missing_in_storage_raises_400(manager_factory):
    """Указан новый image, отсутствующий в хранилище — 400."""
    storage = MissingStaticStorage(local_data=b"local-v1")
    manager = _make_manager(manager_factory, storage)
    created = await _create_local(manager)

    with pytest.raises(Exception) as excinfo:
        await manager.update(created.id, ScheduleImageUpdate(image="local/ghost.png"))

    assert excinfo.value.status_code == 400


class _DeletingLock:
    """Обёртка над asyncio.Lock, выполняющая побочное действие при захвате."""

    def __init__(self, inner: asyncio.Lock, on_acquire) -> None:
        self._inner = inner
        self._on_acquire = on_acquire

    async def __aenter__(self):
        await self._inner.__aenter__()
        await self._on_acquire()

    async def __aexit__(self, *args):
        return await self._inner.__aexit__(*args)


class ConcurrentDeleteStorage(LocalSyncStorage):
    """Хранилище, удаляющее запись из БД в момент взятия лока."""

    def __init__(self, delete_callback, **kwargs) -> None:
        super().__init__(**kwargs)
        self._delete_callback = delete_callback

    def lock(self, key: str) -> _DeletingLock:
        return _DeletingLock(super().lock(key), self._delete_callback)


class FailingMetaStorage(LocalSyncStorage):
    """Хранилище, возвращающее None для метаданных пути после N-го чтения.

    Позволяет имитировать ошибку сразу после ``save`` и проверить откат
    файловых операций в ``update``.
    """

    def __init__(self, fail_path: str, fail_after: int = 1, **kwargs) -> None:
        super().__init__(**kwargs)
        self.fail_path = fail_path
        self.fail_after = fail_after
        self._meta_reads: dict[str, int] = defaultdict(int)
        self.restored: list[str] = []
        self.deleted: list[str] = []

    def restore_file(self, path: str) -> bool:
        self.restored.append(path)
        return True

    def delete(self, path: str) -> None:
        self.deleted.append(path)

    def read_file_metadata(self, path: str, is_local: bool = False) -> dict | None:
        path = f"local/{path}" if is_local else path
        if path == self.fail_path:
            self._meta_reads[path] += 1
            if self._meta_reads[path] >= self.fail_after:
                return None
        return super().read_file_metadata(path, is_local=is_local)


@pytest.mark.asyncio
async def test_update_rereads_fresh_state_after_lock(
    manager_factory, async_session_maker
):
    """Перечитывание под локом видит изменения других транзакций.

    Если запись удалена между первым чтением и взятием лока, update должен
    вернуть 404, а не продолжать работу с устаревшим объектом из identity map.
    """
    deleted_id = None

    async def delete_record() -> None:
        if deleted_id is None:
            return
        async with async_session_maker() as session:
            obj = await session.get(ScheduleImage, deleted_id)
            if obj is not None:
                await session.delete(obj)
                await session.commit()

    storage = ConcurrentDeleteStorage(delete_record)
    manager = _make_manager(manager_factory, storage)
    created = await _create_local(manager)
    deleted_id = created.id

    with pytest.raises(Exception) as excinfo:
        await manager.update(created.id, ScheduleImageUpdate(), is_local=True)

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_update_new_local_file_failure(manager_factory):
    """Ошибка после сохранения нового файла для локального расписания."""
    storage = FailingMetaStorage(fail_path="local/new_name.jpg")
    manager = _make_manager(manager_factory, storage)
    created = await _create_local(manager)

    with pytest.raises(Exception) as excinfo:
        await manager.update(
            created.id, ScheduleImageUpdate(), is_local=True, filename="new_name.jpg"
        )

    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Невозможно заменить файл у локального расписания"


@pytest.mark.asyncio
async def test_update_local_file_failure(manager_factory):
    """Ошибка после перезаписи того же файла: предыдущая версия восстанавливается
    из backup, новый файл не удаляется."""
    storage = FailingMetaStorage(fail_path="local/current_schedule.jpg", fail_after=2)
    manager = _make_manager(manager_factory, storage)
    created = await _create_local(manager)

    with pytest.raises(Exception) as excinfo:
        await manager.update(
            created.id,
            ScheduleImageUpdate(),
            is_local=True,
        )

    assert excinfo.value.status_code == 400
