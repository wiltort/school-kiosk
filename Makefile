BACKEND := backend
POETRY  := cd $(BACKEND) && poetry run
FEATURE_BRANCH_FROM := dev
TAURI := src-tauri
FRONTEND := frontend
NPM := cd $(FRONTEND) && npm run

.PHONY: help
help: ## Показать все доступные команды
	@python -X utf8 scripts/make_help.py

.PHONY: install
install: install-backend install-frontend install-tauri ## Установить всё (backend+frontend+Tauri)

.PHONY: install-frontend
install-frontend: ## Установить зависимости frontend (npm)
	cd $(FRONTEND) && npm install

.PHONY: install-tauri
install-tauri: ## Установить Tauri CLI (cargo install tauri-cli)
	cargo install tauri-cli

.PHONY: build-backend
build-backend: ## Собрать Python-бэкенд в standalone .exe (PyInstaller)
	$(POETRY) pyinstaller --noconfirm --clean --onefile --name python-backend \
		--collect-submodules uvicorn \
		--hidden-import aiosqlite \
		run_backend.py
	mkdir -p $(TAURI)/binaries
	@host=$$(rustc -vV | sed -n 's/^host: //p'); \
	rm -f $(TAURI)/binaries/python-backend-*.exe; \
	echo "Tauri externalBin target: $$host"; \
	cp $(BACKEND)/dist/python-backend.exe $(TAURI)/binaries/python-backend-$${host}.exe

.PHONY: build
build: build-backend ## Собрать установщик (frontend + backend exe + Tauri)
	cd $(TAURI) && cargo tauri build

.PHONY: run
run: ## Запустить проект
	cd $(TAURI) && cargo tauri dev

.PHONY: run-frontend
run-frontend: ## Запустить frontend (dev-сервер)
	$(NPM) dev

.PHONY: install-backend
install-backend: ## Установить все зависимости (включая dev)
	cd $(BACKEND) && poetry install

.PHONY: run-backend
run-backend: ## Запустить сервер backend (uvicorn с hot-reload)
	$(POETRY) app

.PHONY: lint-frontend
lint-frontend: ## Линт + проверка типов + форматирования frontend
	cd $(FRONTEND) && npm run lint
	cd $(FRONTEND) && npm run typecheck
	cd $(FRONTEND) && npm run format:check

.PHONY: format-frontend
format-frontend: ## Автофикс форматирования frontend (prettier)
	cd $(FRONTEND) && npm run format

.PHONY: lint-rust
lint-rust: ## Формат + clippy для Rust (src-tauri)
	cd $(TAURI) && cargo fmt --check
	cd $(TAURI) && cargo clippy --all-targets -- -D warnings

.PHONY: test
test: ## Запустить все тесты
	$(POETRY) pytest

.PHONY: test-unit
test-unit: ## Запустить только unit-тесты
	$(POETRY) pytest tests/unit

.PHONY: test-integration
test-integration: ## Запустить только integration-тесты
	$(POETRY) pytest tests/integration

.PHONY: test-coverage
test-coverage: ## Запустить тесты с отчётом о покрытии
	$(POETRY) pytest --cov=src --cov-report=term-missing

.PHONY: lint
lint: ## Проверить код линтером (ruff)
	$(POETRY) ruff check src tests

.PHONY: format
format: ## Отформатировать код (ruff format)
	$(POETRY) ruff format src tests

.PHONY: check
check: ## Полная проверка: линт + проверка форматирования
	$(POETRY) ruff check src tests
	$(POETRY) ruff format --check src tests

.PHONY: update-keys
update-keys: ## Сгенерировать minisign-ключи для автообновления (обязательный шаг перед сборкой)
	powershell -ExecutionPolicy Bypass -File scripts/gen_update_keys.ps1

.PHONY: update-version
update-version: ## Проставить версию релиза (исп.: make update-version v="0.1.0-dev.42")
	python scripts/set_release_version.py --version "$(v)"

.PHONY: db-migration
db-migration: ## Создать новую миграцию (использование: make migration m="описание")
	$(POETRY) alembic revision --autogenerate -m "$(m)"

.PHONY: db-migrate
db-migrate: ## Применить все миграции
	$(POETRY) alembic upgrade head

.PHONY: db-migrate-downgrade
db-migrate-downgrade: ## Откатить последнюю миграцию
	$(POETRY) alembic downgrade -1

.PHONY: db-current
db-current: ## Показать текущую миграцию
	$(POETRY) alembic current

.PHONY: pre-commit-install
pre-commit-install: ## Установить pre-commit (конфиг в корне репозитория)
	poetry -C $(BACKEND) run pre-commit install

.PHONY: pre-commit
pre-commit: ## Запустить pre-commit для всех файлов
	poetry -C $(BACKEND) run pre-commit run --all-files

.PHONY: new-branch
new-branch: ## Создать новую ветку (использование: make new-branch n="Имя-ветки")
	git checkout $(FEATURE_BRANCH_FROM)
	git fetch origin
	git pull origin $(FEATURE_BRANCH_FROM)
	git checkout -b "$(n)"
