# PaySetu development commands (ADR-011). Run `make help` for the list.
# Requires Python 3.12 and Node.js 20/22 LTS (see .nvmrc). Override the interpreter with
# `make setup PYTHON=/path/to/python3.12` if python3.12 is not on PATH.

PYTHON ?= python3.12
VENV := backend/.venv
VENV_BIN := $(VENV)/bin
API_PORT ?= 8000
WEB_PORT ?= 3000

.DEFAULT_GOAL := help
.PHONY: help api-types setup setup-backend setup-frontend dev dev-api dev-web lint format typecheck \
	test e2e build migrate migrate-status seed

help: ## List available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

setup: setup-backend setup-frontend ## Install backend and frontend dependencies

setup-backend: ## Create the Python venv and install pinned dependencies
	test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(VENV_BIN)/python -m pip install --upgrade pip
	$(VENV_BIN)/python -m pip install -r backend/requirements-dev.txt

setup-frontend: ## Install pinned npm dependencies and the Playwright browser
	cd frontend && npm ci && npx playwright install chromium

dev: ## Run API and web together (Ctrl+C stops both)
	$(MAKE) -j2 dev-api dev-web

dev-api: ## Run FastAPI with reload (default http://localhost:8000)
	cd backend && .venv/bin/uvicorn app.main:create_app --factory --reload --port $(API_PORT)

dev-web: ## Run Next.js (default http://localhost:3000; proxies /api to the API)
	cd frontend && npm run dev -- --port $(WEB_PORT)

lint: ## Lint and format-check backend and frontend
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .
	cd frontend && npm run lint && npm run format:check

format: ## Apply formatters
	cd backend && .venv/bin/ruff format . && .venv/bin/ruff check --fix .
	cd frontend && npm run format

typecheck: ## Type-check backend (mypy strict) and frontend (tsc)
	cd backend && .venv/bin/mypy app tests alembic seed tools
	cd frontend && npm run typecheck

test: ## Run backend tests with the 100% branch-coverage gate on app/domain
	cd backend && .venv/bin/pytest --cov --cov-report=term-missing

e2e: ## Run Playwright end-to-end tests
	cd frontend && npm run e2e

build: ## Production build of the frontend
	cd frontend && npm run build

migrate: ## Apply database migrations to DATABASE_URL (backend/.env)
	cd backend && .venv/bin/alembic upgrade head

migrate-status: ## Show the current and head migration revisions
	cd backend && .venv/bin/alembic current && .venv/bin/alembic heads

seed: ## Load SYNTHETIC demo data (refuses production; run after make migrate)
	cd backend && .venv/bin/python -m seed.demo

api-types: ## Regenerate frontend API types from the backend OpenAPI schema
	cd backend && .venv/bin/python -m tools.export_openapi > ../frontend/openapi.json
	cd frontend && npx openapi-typescript openapi.json -o src/lib/api/schema.d.ts
