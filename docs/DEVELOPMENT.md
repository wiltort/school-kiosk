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

## Автообновление

Приложение обновляется из своей ветки: сборка из `dev` проверяет
только канал `dev`, из `main` — только канал `main`. Обновление
скачивается тихо в фоне и устанавливается при следующем запуске.

Подробности — в [docs/INSTALLATION.md](INSTALLATION.md).
