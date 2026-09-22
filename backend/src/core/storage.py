import asyncio
import hashlib
import os
import shutil
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from src.core.config import settings


def _lock_file_exclusive(fd: int) -> None:
    """Захватывает эксклюзивную файловую блокировку (межпроцессную).

    На Windows используется ``msvcrt.locking`` (блокировка одного байта),
    на POSIX — ``fcntl.flock``. Функция блокирующая, поэтому вызывается
    через ``asyncio.to_thread``, чтобы не блокировать event loop.
    """
    if os.name == "nt":
        import msvcrt

        os.ftruncate(fd, 1)
        os.lseek(fd, 0, os.SEEK_SET)
        deadline = time.monotonic() + 30.0
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX)


def _unlock_file(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)


class ProcessSafeLock:
    """Асинхронная блокировка по ключу.

    Сочетает внутрипроцессный ``asyncio.Lock`` (быстрый путь без системных
    вызовов) и файловую блокировку (msvcrt/fcntl) для согласованности между
    процессами — например, между HTTP-запросами и задачей синхронизации.

    Реализует протокол асинхронного контекстного менеджера и поэтому может
    использоваться в ``maybe_lock`` вместо обычного ``asyncio.Lock``.
    """

    def __init__(self, local: asyncio.Lock, lock_file: Path) -> None:
        self._local = local
        self._lock_file = lock_file
        self._fd: int | None = None

    async def __aenter__(self) -> ProcessSafeLock:
        await self._local.acquire()
        try:
            self._lock_file.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(self._lock_file, os.O_CREAT | os.O_RDWR)
        except BaseException:
            self._local.release()
            raise
        try:
            await asyncio.to_thread(_lock_file_exclusive, fd)
        except BaseException:
            os.close(fd)
            self._local.release()
            raise
        self._fd = fd
        return self

    async def __aexit__(self, _exc_type, _exc, _tb) -> None:
        fd, self._fd = self._fd, None
        try:
            if fd is not None:
                await asyncio.to_thread(_unlock_file, fd)
        finally:
            if fd is not None:
                os.close(fd)
            self._local.release()


class ImageStorage:
    """Инфраструктурный сервис для работы с файлами изображений.

    Отвечает за сохранение, удаление и получение физических файлов.
    В БД хранится только относительный путь/имя файла.
    """

    def __init__(
        self,
        base_dir: Path | None = None,
        local_dir: Path | None = None,
        backup_dir: Path | None = None,
    ) -> None:
        self._base = (base_dir or settings.static_dir / "schedule_images").resolve()
        self._local_dir = (local_dir or settings.local_image_dir).resolve()
        self._backup_dir = (backup_dir or settings.data_dir / "backup").resolve()
        self._locks_dir = self._backup_dir.parent / "locks"
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def lock(self, key: str) -> ProcessSafeLock:
        """Возвращает блокировку по ключу.

        Один и тот же ключ всегда даёт один и тот же ``asyncio.Lock``
        (сериализация внутри процесса) и один файл блокировки
        (сериализация между процессами).
        """
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return ProcessSafeLock(self._locks[key], self._locks_dir / f"{digest}.lock")

    def _safe_join(self, base: Path, *parts: str | Path) -> Path | None:
        candidate = (base / Path(*parts)).resolve()
        if not candidate.is_relative_to(base):
            return None
        return candidate

    def _backup_existing(self, dest: Path, rel_path: str) -> Path | None:
        if not dest.is_file():
            return None
        backup_path = self._safe_join(self._backup_dir, rel_path)
        if backup_path is None:
            return None
        if backup_path.exists():
            backup_path.unlink(missing_ok=True)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, backup_path)
        return backup_path

    @staticmethod
    def _atomic_write(dest: Path, data: bytes) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(f".{dest.name}.{uuid.uuid4().hex}.tmp")
        try:
            tmp.write_bytes(data)
            tmp.replace(dest)
        finally:
            tmp.unlink(missing_ok=True)

    def save(
        self, data: bytes, filename: str, subdir: str = "", is_local: bool = False
    ) -> str:
        """Сохраняет содержимое файла и возвращает путь для записи в БД."""
        ext = Path(filename or "").suffix.lower() or ".png"
        filename = filename if is_local else f"{uuid.uuid4().hex}{ext}"
        subdir = subdir or datetime.now().strftime("%Y/%m")
        dest = self._safe_join(self._base, subdir, filename)
        if dest is None:
            raise ValueError("Invalid path")
        rel_path = f"{subdir}/{filename}".lstrip("/")
        if is_local:
            self._backup_existing(dest, rel_path)

        self._atomic_write(dest, data)
        return rel_path

    def delete(self, path: str) -> None:
        """Удаляет файл по пути из БД (только внутри base_dir)."""
        safe = self._safe_join(self._base, path)
        if safe is not None:
            safe.unlink(missing_ok=True)

    @staticmethod
    def _get_file_hash(file_path: Path, chunk_size: int = 1 << 20) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()

    def read_file_metadata(self, path: str, is_local: bool = False) -> dict | None:
        """Возвращает метаданные файла по пути."""
        base = self._local_dir if is_local else self._base
        safe = self._safe_join(base, path)
        if safe is None or not safe.is_file():
            return None
        return {
            "file_hash": self._get_file_hash(safe),
            "file_size": safe.stat().st_size,
            "mtime": safe.stat().st_mtime,
        }

    def read_file(self, path: str, is_local: bool = False) -> bytes | None:
        """Возвращает содержимое файла по пути."""
        base = self._local_dir if is_local else self._base
        safe = self._safe_join(base, path)
        if safe is None or not safe.is_file():
            return None
        return safe.read_bytes()

    def restore_file(self, path: str) -> bool:
        """Восстанавливает файл по пути из backup_dir."""
        backup = self._safe_join(self._backup_dir, path)
        if backup is None or not backup.is_file():
            return False

        dest = self._safe_join(self._base, path)
        if dest is None:
            return False

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, dest)
        return True
