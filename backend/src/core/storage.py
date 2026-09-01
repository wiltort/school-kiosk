import uuid
from datetime import datetime
from pathlib import Path

from src.core.config import settings


class ImageStorage:
    """Инфраструктурный сервис для работы с файлами изображений.

    Отвечает за сохранение, удаление и получение физических файлов.
    В БД хранится только относительный путь/имя файла.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or settings.upload_dir / "schedule_images"

    async def save(self, data: bytes, filename: str, subdir: str = "") -> str:
        """Сохраняет содержимое файла и возвращает путь для записи в БД."""
        ext = Path(filename or "").suffix.lower() or ".png"
        filename = f"{uuid.uuid4().hex}{ext}"
        subdir = subdir or datetime.now().strftime("%Y/%m")
        dest = self._base / subdir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)

        dest.write_bytes(data)
        return f"{subdir}/{filename}".lstrip("/")

    def delete(self, path: str) -> None:
        """Удаляет файл по пути из БД (только внутри base_dir)."""
        safe = (self._base / path).resolve()
        if safe.is_relative_to(self._base.resolve()):
            safe.unlink(missing_ok=True)
