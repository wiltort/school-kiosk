import asyncio
import hashlib
import shutil
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from src.core.config import settings


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
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def lock(self, key: str) -> asyncio.Lock:
        return self._locks[key]

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
        safe = (
            (self._local_dir / path).resolve()
            if is_local
            else (self._base / path).resolve()
        )
        if not safe.is_file():
            return None
        return {
            "file_hash": self._get_file_hash(safe),
            "file_size": safe.stat().st_size,
            "mtime": safe.stat().st_mtime,
        }

    def read_file(self, path: str, is_local: bool = False) -> bytes | None:
        """Возвращает содержимое файла по пути."""
        safe = (
            (self._local_dir / path).resolve()
            if is_local
            else (self._base / path).resolve()
        )
        if not safe.is_file():
            return None
        return safe.read_bytes()

    def restore_file(self, subdir: str, filename: str) -> str | None:
        """Восстанавливает файл по пути из backup_dir."""
        safe = (self._backup_dir / subdir / filename).resolve()
        if not safe.is_file():
            return None
        safe.rename(self._base / subdir / filename)
        return f"{subdir}/{filename}".lstrip("/")
