"""Тесты инфраструктурного сервиса хранения изображений (src/core/storage.py).

``ImageStorage`` принимает ``base_dir`` и ``local_dir`` в конструкторе, поэтому
в тестах передаём временные каталоги (``tmp_path``) и не зависим от настроек.
"""

import asyncio
import hashlib
from datetime import datetime

import pytest
from src.core.storage import ImageStorage


@pytest.fixture()
def storage(tmp_path) -> ImageStorage:
    """Хранилище с временными базовым и локальным каталогами."""
    return ImageStorage(
        base_dir=tmp_path / "uploads",
        local_dir=tmp_path / "local",
        backup_dir=tmp_path / "backup",
    )


def test_init_sets_backup_dir(storage: ImageStorage, tmp_path):
    assert storage._base == tmp_path / "uploads"
    assert storage._local_dir == tmp_path / "local"
    assert storage._backup_dir == tmp_path / "backup"


def test_init_defaults_to_settings(tmp_path, monkeypatch):
    """Без явных аргументов каталоги берутся из настроек."""
    from src.core import config

    upload = tmp_path / "settings_uploads"
    local = tmp_path / "settings_local"

    # Подменяем read-only свойства Settings на уровне класса.
    monkeypatch.setattr(
        type(config.settings),
        "static_dir",
        property(lambda self: upload),  # noqa: ARG005
    )
    monkeypatch.setattr(
        type(config.settings),
        "local_image_dir",
        property(lambda self: local),  # noqa: ARG005
    )

    inst = ImageStorage()
    assert inst._base == upload / "schedule_images"
    assert inst._local_dir == local


def test_save_generates_random_filename_with_ext(storage: ImageStorage):
    rel = storage.save(b"hello", "picture.JPG")
    assert rel.endswith(".jpg")
    # Возвращается путь вида "2026/09/uuidhex.jpg".
    filename = rel.rsplit("/", 1)[-1]
    assert len(filename) == 36  # 32 hex + ".jpg"
    assert (storage._base / rel).is_file()
    assert (storage._base / rel).read_bytes() == b"hello"


def test_save_defaults_subdir_to_current_month(storage: ImageStorage):
    expected = datetime.now().strftime("%Y/%m")
    rel = storage.save(b"data", "a.png")
    assert rel.startswith(expected + "/")


def test_save_respects_provided_subdir(storage: ImageStorage):
    rel = storage.save(b"data", "a.png", subdir="custom/folder")
    assert rel == "custom/folder/" + rel.rsplit("/", 1)[-1]
    assert (storage._base / rel).is_file()


def test_save_defaults_extension_to_png_for_empty_name(storage: ImageStorage):
    rel = storage.save(b"data", "")
    assert rel.endswith(".png")
    assert (storage._base / rel).is_file()


def test_save_non_local_ignores_original_filename(storage: ImageStorage):
    """Для не-локального сохранения имя всегда генерируется заново."""
    rel = storage.save(b"data", "secret_name.png")
    assert "secret_name" not in rel


def test_save_is_local_keeps_filename(storage: ImageStorage):
    rel = storage.save(b"data", "current_schedule.jpg", subdir="2026/09", is_local=True)
    assert rel == "2026/09/current_schedule.jpg"
    assert (storage._base / rel).read_bytes() == b"data"


def test_save_is_local_backs_up_existing_file(storage: ImageStorage):
    rel = storage.save(b"new", "current_schedule.jpg", subdir="2026/09", is_local=True)
    # Повторное сохранение того же имени.
    rel2 = storage.save(
        b"newer", "current_schedule.jpg", subdir="2026/09", is_local=True
    )

    assert rel2 == rel
    # Основной файл обновлён.
    assert (storage._base / rel).read_bytes() == b"newer"
    # Старая версия уехала в backup.
    backup_file = storage._backup_dir / "2026/09/current_schedule.jpg"
    assert backup_file.is_file()
    assert backup_file.read_bytes() == b"new"


def test_delete_removes_file(storage: ImageStorage):
    rel = storage.save(b"data", "a.png", subdir="2026/09")
    storage.delete(rel)
    assert not (storage._base / rel).exists()


def test_delete_missing_file_does_not_raise(storage: ImageStorage):
    storage.delete("2026/09/ghost.png")  # не должно падать


def test_delete_ignores_path_outside_base(storage: ImageStorage, tmp_path):
    """Traversal-попытка удалить файл вне base_dir должна игнорироваться."""
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"x")
    storage.delete("../outside.png")
    assert outside.is_file()


def test_read_file_returns_bytes(storage: ImageStorage):
    rel = storage.save(b"\x00\x01payload", "a.png", subdir="2026/09")
    assert storage.read_file(rel) == b"\x00\x01payload"


def test_read_file_returns_none_for_missing(storage: ImageStorage):
    assert storage.read_file("2026/09/missing.png") is None


def test_read_file_is_local_uses_local_dir(storage: ImageStorage):
    local_file = storage._local_dir / "2026/09/current.jpg"
    local_file.parent.mkdir(parents=True)
    local_file.write_bytes(b"local-data")

    assert storage.read_file("2026/09/current.jpg", is_local=True) == b"local-data"
    # Тот же путь в базовом каталоге — там файла нет.
    assert storage.read_file("2026/09/current.jpg") is None


def test_read_file_metadata_returns_dict(storage: ImageStorage):
    rel = storage.save(b"0123456789", "a.png", subdir="2026/09")
    meta = storage.read_file_metadata(rel)

    assert meta is not None
    assert meta["file_size"] == 10
    assert meta["file_hash"] == hashlib.sha256(b"0123456789").hexdigest()
    assert isinstance(meta["mtime"], float)


def test_read_file_metadata_returns_none_for_missing(storage: ImageStorage):
    assert storage.read_file_metadata("2026/09/missing.png") is None


def test_read_file_metadata_is_local_uses_local_dir(storage: ImageStorage):
    local_file = storage._local_dir / "cur.jpg"
    local_file.parent.mkdir(parents=True)
    local_file.write_bytes(b"abc")

    meta = storage.read_file_metadata("cur.jpg", is_local=True)
    assert meta is not None
    assert meta["file_size"] == 3
    assert meta["file_hash"] == hashlib.sha256(b"abc").hexdigest()


def test_get_file_hash_is_sha256_of_content(storage: ImageStorage):
    rel = storage.save(b"hash-me", "a.png", subdir="2026/09")
    path = storage._base / rel
    assert storage._get_file_hash(path) == hashlib.sha256(b"hash-me").hexdigest()


def test_restore_file_moves_from_backup(storage: ImageStorage):
    # Создаём файл, затем даём ему замениться и попасть в backup.
    rel = storage.save(b"old", "current.jpg", subdir="2026/09", is_local=True)
    storage.save(b"new", "current.jpg", subdir="2026/09", is_local=True)

    # Восстановление используется, когда текущий файл уже удалён.
    storage.delete("2026/09/current.jpg")
    restored = storage.restore_file(rel)
    assert restored is True
    # Восстановленная старая версия на месте, в backup она осталась.
    assert (storage._base / "2026/09" / "current.jpg").read_bytes() == b"old"
    assert (storage._backup_dir / "2026/09/current.jpg").exists()
    assert (storage._backup_dir / "2026/09/current.jpg").read_bytes() == b"old"


def test_restore_file_returns_false_when_no_backup(storage: ImageStorage):
    assert storage.restore_file("2026-09/nope.jpg") is False


@pytest.mark.asyncio
async def test_lock_creates_lock_file(storage: ImageStorage):
    """lock() возвращает блокировку, создающую файл в каталоге блокировок."""
    lock = storage.lock("local/current.jpg")
    async with lock:
        digest = hashlib.sha256(b"local/current.jpg").hexdigest()
        assert (storage._locks_dir / f"{digest}.lock").is_file()


@pytest.mark.asyncio
async def test_lock_can_be_reacquired_after_release(storage: ImageStorage):
    """После выхода из контекста блокировка освобождается."""
    lock = storage.lock("local/current.jpg")
    async with lock:
        pass
    # Повторный захват не должен зависнуть.
    async with lock:
        pass


@pytest.mark.asyncio
async def test_lock_serializes_acquisitions_for_same_key(storage: ImageStorage):
    """Два захвата одного ключа не пересекаются во времени."""
    lock = storage.lock("local/current.jpg")
    order: list[str] = []

    async def worker(tag: str) -> None:
        async with lock:
            order.append(f"{tag}-start")
            await asyncio.sleep(0.02)
            order.append(f"{tag}-end")

    await asyncio.gather(worker("a"), worker("b"))

    assert order == ["a-start", "a-end", "b-start", "b-end"]
