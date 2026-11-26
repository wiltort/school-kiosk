# Разработка School Kiosk

## Требования

- Python-бэкенд и предустановленный `poetry`.
- Зависимости фронтенда: `cd frontend && npm install`.
- Rust toolchain (`cargo`) для проверок `src-tauri`.
- Tauri CLI (`make install-tauri`).

## Pre-commit (обязательный)

Единый `pre-commit` на весь монорепо: Python-бэкенд (ruff + pytest),
TS/React-фронтенд (tsc + eslint + prettier) и Tauri/Rust
(cargo fmt + clippy). Rust-хуки запускаются только при изменении
`src-tauri/*.rs`; `cargo test` в pre-commit намеренно не добавлен
из-за долгой компиляции (он выполняется в CI).

Установка хуков:

    make pre-commit-install

Ручной запуск по всем файлам:

    make pre-commit

## Сборка установщика

Приложение можно собрать в автономный Windows-инсталлятор.
Конечному пользователю ничего устанавливать не нужно
(Python, Rust, Node не требуются): Tauri-оболочка запускает
Python-бэкенд, упакованный PyInstaller'ом в один `python-backend.exe`.

    make build

## Настройки, сервисы и контент

- Настройки приложения хранятся в таблице `app_settings` (key-value) и описаны
  реестром [`backend/src/core/settings_schema.py`](../backend/src/core/settings_schema.py).
- Реестр плиток главного экрана — таблица `app_units`
  (`backend/src/apps/units`).
- Объявления — `announcements` (`backend/src/apps/announcements`).
- Прогноз погоды кешируется в `weather_forecasts`; провайдер и менеджер —
  `backend/src/apps/weather`, фоновая задача —
  `backend/src/tasks/weather_refresh.py`.
- Legacy `settings.json` импортируется в БД при первом запуске
  (`backend/src/apps/settings/seed.py`).
- Миграция новых таблиц:
  `backend/alembic/versions/9f1c2d3e4a5b_*.py`.

Проверки перед коммитом:

    cd backend && poetry run ruff check src tests && poetry run pytest tests/unit -q
    cd frontend && npm run typecheck && npm run lint

## Автообновление

Приложение обновляется из своей ветки: сборка из `dev` проверяет
только канал `dev`, из `main` — только канал `main`. Обновление
скачивается тихо в фоне и устанавливается при следующем запуске.

Подробности — в [docs/INSTALLATION.md](INSTALLATION.md).
