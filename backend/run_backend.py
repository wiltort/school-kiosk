"""Точка входа standalone-сборки Python-бэкенда (PyInstaller).

В dev-режиме бэкенд запускается через `poetry run uvicorn src.main:app`.
При упаковке в один `.exe` импорт по строке `"src.main:app"` ненадёжен,
поэтому здесь используется явный импорт объекта `app` и вызов uvicorn
программно — это гарантирует корректную работу внутри PyInstaller.

Параметры (порт/хост/каталог данных) приходят через переменные окружения,
которые задаёт Rust-оболочка Tauri (`BACKEND_*`, `SCHOOL_KIOSK_DATA_DIR`).
"""

import uvicorn
from src.core.config import settings
from src.main import app


def main() -> None:
    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
