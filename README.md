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
