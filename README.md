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

> Как поставить dev/main версию на другой компьютер — см.
> [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Автообновление

Приложение обновляется из своей ветки: сборка из `dev` проверяет только канал
`dev`, из `main` — только канал `main`. Обновление скачивается тихо в фоне и
устанавливается при следующем запуске (NSIS, per-user, без UAC). Так как
Python-бэкенд упакован внутрь установщика (`externalBin`), обновляется всё сразу.

Архитектура (см. [`src-tauri/src/updater.rs`](src-tauri/src/updater.rs)):

- **Канал** запекается на этапе сборки через `KIOSK_CHANNEL` (`dev`/`main`),
  который выставляет CI.
- **Фид** `latest.json` на канал лежит в ветке `update-feed` репозитория по
  пути `<channel>/latest.json` и отдаётся через raw.githubusercontent.com.
- **Установщики** публикуются в GitHub Releases с тегом `<channel>-v<version>`.
- **Версия** монотонна внутри канала: `0.1.0-<channel>.<build_number>`.
- Подпись minisign: публичный ключ зашит в
  [`tauri.conf.json`](src-tauri/tauri.conf.json) (`plugins.updater.pubkey`),
  приватный хранится в секретах GitHub (`MINISIGN_PRIVATE_KEY`).

### Подготовка (один раз)

1. Сгенерировать ключи:

   ```bash
   make update-keys
   ```

   Скрипт создаст пару файлов и подскажет шаги.

2. Скопировать **публичный** ключ (строка `RWR...`) из `<name>.pub` в
   [`tauri.conf.json`](src-tauri/tauri.conf.json) → `plugins.updater.pubkey`
   (пока там пусто — автообновление не работает и релизная сборка требует ключа).

3. В секреты GitHub добавить:
   - `MINISIGN_PRIVATE_KEY` — содержимое приватного ключа;
   - `MINISIGN_PRIVATE_KEY_PASSWORD` — пароль, заданный при генерации.

4. Убедиться, что приватный ключ не попал в git (он в `.gitignore`).

### Публикация обновления

Достаточно запушить в `dev` или `main` — workflow
[`.github/workflows/release-build.yml`](.github/workflows/release-build.yml)
соберёт установщик, подпишет его, создаст релиз и обновит фид нужного канала.
Приложение само подтянет и установит новую версию при следующем запуске.

Локальная простановка версии (если нужно вручную):

```bash
make update-version v="0.1.0-dev.42"
```
