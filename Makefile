BACKEND := backend
POETRY  := cd $(BACKEND) && poetry run

.PHONY: install
install: ## Установить все зависимости (включая dev)
	cd $(BACKEND) && poetry install

.PHONY: run
run: ## Запустить сервер (uvicorn с hot-reload)
	$(POETRY) app

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

.PHONY: migration
migration: ## Создать новую миграцию (использование: make migration m="описание")
	$(POETRY) alembic revision --autogenerate -m "$(m)"

.PHONY: migrate
migrate: ## Применить все миграции
	$(POETRY) alembic upgrade head

.PHONY: migrate-downgrade
migrate-downgrade: ## Откатить последнюю миграцию
	$(POETRY) alembic downgrade -1

.PHONY: pre-commit
pre-commit: ## Запустить pre-commit для всех файлов
	$(POETRY) pre-commit run --all-files

.PHONY: help
help: ## Показать все доступные команды
	@python -X utf8 scripts/make_help.py
