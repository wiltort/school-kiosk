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

import json
import threading
from pathlib import Path
from typing import Any

APP_SETTINGS_FILE = "settings.json"

# Сентинел: поле не передано в update() — значение не меняется.
_UNSET: Any = object()

_DEFAULTS: dict[str, Any] = {
    "static_dir": None,
    "autostart": False,
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
        if self._legacy_file is not None and self._legacy_file.is_file():
            legacy = self._read(self._legacy_file)
            if legacy.get("static_dir"):
                data = {"static_dir": legacy["static_dir"], "autostart": False}
                self._write(self._path, data)
                return data
        return dict(_DEFAULTS)

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

    def update(
        self,
        *,
        static_dir: str | None = _UNSET,
        autostart: bool = _UNSET,
    ) -> dict[str, Any]:
        """Обновляет переданные поля и атомарно сохраняет файл.

        Непереданные поля (по умолчанию ``_UNSET``) не меняются.
        Пустая строка для ``static_dir`` нормализуется в ``None`` (дефолт).
        """
        with self._lock:
            data = dict(self._data)
            if static_dir is not _UNSET:
                data["static_dir"] = (static_dir or "").strip() or None
            if autostart is not _UNSET:
                data["autostart"] = bool(autostart)
            self._data = data
            self._write(self._path, data)
        return dict(data)
