r"""Управление автозагрузкой приложения при входе в систему (Windows).

Бэкенд (Python) запускается на машине киоска, поэтому может включать и
выключать автозапуск `kiosk.exe`.

Чтобы не провоцировать срабатывание антивируса (Касперский блокирует прямое
изменение ключа реестра `HKCU\...\CurrentVersion\Run` из процесса Python),
автозагрузка реализована через **ярлык `.lnk` в папке автозагрузки
пользователя (Startup)** — это штатный механизм Windows. Ярлык создаётся
через PowerShell (COM-объект WScript.Shell), т.е. штатным системным
инструментом.

Ярлык: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\School Kiosk.lnk`

Путь к исполняемому файлу приложения передаётся бэкенду через переменную
окружения `SCHOOL_KIOSK_APP_EXE` (её задаёт Rust-оболочка Tauri). На других
ОС автозагрузка не поддерживается — функции возвращают ``False``.
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SHORTCUT_NAME = "School Kiosk.lnk"


def _app_exe() -> str | None:
    return os.environ.get("SCHOOL_KIOSK_APP_EXE")


def _startup_dir() -> Path | None:
    base = os.environ.get("APPDATA")
    if not base:
        return None
    return Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _shortcut_path() -> Path | None:
    directory = _startup_dir()
    if directory is None:
        return None
    return directory / SHORTCUT_NAME


def is_supported() -> bool:
    """Поддерживается ли автозагрузка в текущем окружении."""
    return sys.platform.startswith("win") and _app_exe() is not None


def is_enabled() -> bool:
    """Проверяет, создан ли ярлык автозагрузки в папке Startup."""
    if not is_supported():
        return False
    shortcut = _shortcut_path()
    return shortcut is not None and shortcut.is_file()


def set_enabled(enabled: bool) -> bool:
    """Включает/выключает автозагрузку. Возвращает ``True`` при успехе."""
    if not is_supported():
        logger.info("Автозагрузка не поддерживается на этой ОС")
        return False

    exe = _app_exe()
    shortcut = _shortcut_path()
    if not exe or shortcut is None:
        return False

    logger.info(
        "autostart.set_enabled(%s): EXE=%r shortcut=%r",
        enabled,
        exe,
        str(shortcut),
    )

    try:
        if enabled:
            shortcut.parent.mkdir(parents=True, exist_ok=True)
            _create_shortcut(shortcut, exe)
        else:
            shortcut.unlink(missing_ok=True)
        logger.info(
            "autostart.set_enabled(%s): ярлык %s",
            enabled,
            "создан" if enabled else "удалён",
        )
        return True
    except OSError as e:  # pragma: no cover - зависит от прав/файловой системы
        logger.error("autostart.set_enabled(%s): ошибка: %s", enabled, e)
        return False


def _create_shortcut(shortcut: Path, exe: str) -> None:
    """Создаёт `.lnk` через PowerShell (штатный COM-объект WScript.Shell)."""
    working_dir = Path(exe).parent.as_posix()
    # Экранируем одинарные кавычки для PowerShell-строки.
    shortcut_ps = str(shortcut).replace("'", "''")
    exe_ps = exe.replace("'", "''")
    workdir_ps = working_dir.replace("'", "''")

    command = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('"
        + shortcut_ps
        + "'); $s.TargetPath='"
        + exe_ps
        + "'; $s.WorkingDirectory='"
        + workdir_ps
        + "'; $s.Save()"
    )

    # Используем штатный системный инструмент PowerShell (полный путь через
    # `shutil.which`). Вызов помечен noqa S603 — это намеренный запуск
    # доверенной утилиты Windows для создания ярлыка автозагрузки.
    powershell = shutil.which("powershell.exe") or "powershell"
    completed = subprocess.run(  # noqa: S603
        [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise OSError(
            completed.stderr.strip()
            or f"PowerShell завершился с кодом {completed.returncode}"
        )
