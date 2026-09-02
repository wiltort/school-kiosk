# school-kiosk
<img src="media/logo-color.jpeg" alt="Логотип" width="200" height="200"><br>
Native information kiosk for schools

## Разработка

### Pre-commit (обязательный)

В репозитории единый [`pre-commit`](.pre-commit-config.yaml) на весь монорепо:
Python-бэкенд (ruff + pytest), TS/React-фронтенд (tsc + eslint + prettier) и
Tauri/Rust (cargo fmt + clippy). Rust-хуки запускаются только при изменении
`src-tauri/*.rs`; `cargo test` в pre-commit намеренно не добавлен из-за долгой
компиляции (он выполняется в CI).

Установка хуков:

```bash
make pre-commit-install   # установит hook в .git/hooks/
```

Ручной запуск по всем файлам:

```bash
make pre-commit
```

Требования:

- Python-бэкенд и предустановленный `poetry` (через `backend/pyproject.toml`);
- зависимости фронтенда: `cd frontend && npm install`;
- Rust toolchain (`cargo`) для проверок `src-tauri`.

Отдельные проверки:

```bash
make lint           # ruff (backend)
make lint-frontend  # eslint + tsc + prettier --check (frontend)
make format-frontend # prettier --write (frontend)
make lint-rust      # cargo fmt --check + cargo clippy (src-tauri)
```

## Сборка установщика (без Python/Rust на целевой машине)

Приложение можно собрать в автономный Windows-инсталлятор. Конечному
пользователю ничего устанавливать не нужно (Python, Rust, Node не требуются):
Tauri-оболочка запускает Python-бэкенд, упакованный PyInstaller'ом в один
`python-backend.exe`.

Сборка:

```bash
make build
```

Что происходит по шагам:

1. `build-backend` — PyInstaller собирает бэкенд из [`backend/run_backend.py`](backend/run_backend.py)
   в standalone-файл и кладёт его в `src-tauri/binaries/python-backend.exe`.
2. `cargo tauri build` — собирает frontend (`npm run build`) и Rust-оболочку,
   включает `python-backend.exe` (через `externalBin` в
   [`tauri.conf.json`](src-tauri/tauri.conf.json)) и формирует NSIS-установщик
   `School Kiosk 0.1.0 Setup.exe`.

Только сборку бэкенда (без Tauri) можно выполнить отдельно:

```bash
make build-backend
```

Важные моменты:

- **Release** (`cargo tauri build`): Rust запускает `python-backend.exe`,
  лежащий рядом с `kiosk.exe`, и передаёт ему каталог данных через
  `SCHOOL_KIOSK_DATA_DIR` (см. [`src-tauri/src/process.rs`](src-tauri/src/process.rs)).
- **Данные** (SQLite-БД и загрузки изображений) хранятся в каталоге данных
  приложения, а не в папке программы (см. [`backend/src/core/config.py`](backend/src/core/config.py)).
- **WebView2 Runtime**: установщик при необходимости сам докачивает и ставит
  WebView2 (`webviewInstallMode: downloadBootstrapper` в
  [`tauri.conf.json`](src-tauri/tauri.conf.json)).
- Перед первым `make build` должен быть установлен Tauri CLI
  (`make install-tauri`) и зависимости (`make install`).
