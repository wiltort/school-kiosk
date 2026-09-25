"""Хранилище настроек приложения (без БД).

Владелец настроек — бэкенд. Значения хранятся в JSON-файле
`settings.json` внутри каталога данных (`<data_dir>/settings.json`):

- ``static_dir`` — каталог статики (изображения расписания). ``None``
  означает «использовать значение по умолчанию» (`<data_dir>/uploads`);
- ``autostart`` — включать ли автозагрузку приложения при входе в систему.

При первом запуске (когда своего файла ещё нет) выполняется миграция
«seed»-значения ``static_dir`` из legacy-файла настроек Tauri
(`%APPDATA%\\com.schoolkiosk.app\\settings.json`), который пишет установщик
(см. ``src-tauri/windows/hooks.nsh``). После этого источником истины
становится только этот файл.
"""

import contextlib
import json
import threading
from pathlib import Path
from typing import Any

from src.enums.schedule_modes import ScheduleMode

APP_SETTINGS_FILE = "settings.json"

# Сентинел: поле не передано в update() — значение не меняется.
_UNSET: Any = object()

_DEFAULTS: dict[str, Any] = {
    "static_dir": None,
    "autostart": False,
    "local_image_dir": None,
    "current_local_schedule_image_filename": None,
    "schedule_mode": ScheduleMode.SINGLE,
    "welcome_message": None,
}


class AppSettingsStore:
    """Читает и пишет файл настроек приложения в каталоге данных."""

    def __init__(
        self,
        data_dir: Path,
        legacy_file: Path | None = None,
    ) -> None:
        self._path = data_dir / APP_SETTINGS_FILE
        self._legacy_file = legacy_file
        self._lock = threading.Lock()
        self._data = self._load()

    @property
    def path(self) -> Path:
        """Путь к файлу настроек."""
        return self._path

    def _load(self) -> dict[str, Any]:
        if self._path.is_file():
            return self._read(self._path)
        data = dict(_DEFAULTS)
        if self._legacy_file is not None and self._legacy_file.is_file():
            legacy = self._read(self._legacy_file)
            if legacy.get("static_dir"):
                data["static_dir"] = legacy["static_dir"]
            if legacy.get("local_image_dir"):
                data["local_image_dir"] = legacy["local_image_dir"]
            if legacy.get("autostart"):
                data["autostart"] = bool(legacy["autostart"])
            if legacy.get("current_local_schedule_image_filename"):
                data["current_local_schedule_image_filename"] = legacy[
                    "current_local_schedule_image_filename"
                ]
            if legacy.get("schedule_mode"):
                with contextlib.suppress(ValueError):
                    data["schedule_mode"] = ScheduleMode(legacy["schedule_mode"])
            self._write(self._path, data)
        return data

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError, OSError:
            return {}
        return {key: raw.get(key) for key in _DEFAULTS if key in raw}

    def _write(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)

    def as_dict(self) -> dict[str, Any]:
        """Возвращает копию текущих настроек."""
        with self._lock:
            return dict(self._data)

    def static_dir(self) -> str | None:
        """Каталог статики либо ``None`` (значение по умолчанию)."""
        return self.as_dict().get("static_dir")

    def autostart(self) -> bool:
        """Включена ли автозагрузка."""
        return bool(self.as_dict().get("autostart"))

    def local_image_dir(self) -> str | None:
        """Каталог локальных изображений либо ``None`` (значение по умолчанию)."""
        return self.as_dict().get("local_image_dir")

    def current_local_schedule_image_filename(self) -> str | None:
        """Имя текущего изображения расписания."""
        return self.as_dict().get("current_local_schedule_image_filename")

    def schedule_mode(self) -> ScheduleMode:
        raw = self.as_dict().get("schedule_mode")
        try:
            return ScheduleMode(raw) if raw is not None else ScheduleMode.SINGLE
        except ValueError:
            return ScheduleMode.SINGLE

    def welcome_message(self) -> str | None:
        """Приветственное сообщение на главном экране либо ``None``."""
        return self.as_dict().get("welcome_message")

    def update(
        self,
        *,
        static_dir: str | None = _UNSET,
        autostart: bool = _UNSET,
        local_image_dir: str | None = _UNSET,
        current_local_schedule_image_filename: str | None = _UNSET,
        schedule_mode: str | None = _UNSET,
        welcome_message: str | None = _UNSET,
    ) -> dict[str, Any]:
        """Обновляет переданные поля и атомарно сохраняет файл.

        Непереданные поля (по умолчанию ``_UNSET``) не меняются.
        Пустая строка для ``static_dir``/``local_image_dir``/``welcome_message``
        нормализуется в ``None`` (дефолт).
        """
        with self._lock:
            data = dict(self._data)
            if static_dir is not _UNSET:
                data["static_dir"] = (static_dir or "").strip() or None
            if autostart is not _UNSET:
                data["autostart"] = bool(autostart)
            if local_image_dir is not _UNSET:
                data["local_image_dir"] = (local_image_dir or "").strip() or None
            if current_local_schedule_image_filename is not _UNSET:
                data["current_local_schedule_image_filename"] = (
                    current_local_schedule_image_filename or ""
                ).strip() or None
            if schedule_mode is not _UNSET:
                with contextlib.suppress(ValueError):
                    data["schedule_mode"] = ScheduleMode(schedule_mode)
            if welcome_message is not _UNSET:
                data["welcome_message"] = (welcome_message or "").strip() or None
            self._data = data
            self._write(self._path, data)
        return dict(data)
