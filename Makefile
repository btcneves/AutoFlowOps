BACKEND_PYTEST ?= $(shell if [ -x backend/.venv/bin/pytest ]; then echo .venv/bin/pytest; else echo pytest; fi)
BACKEND_RUFF ?= $(shell if [ -x backend/.venv/bin/ruff ]; then echo .venv/bin/ruff; else echo ruff; fi)

.PHONY: dev up down logs test lint format setup seed

setup:
	@test -f .env || cp .env.example .env && echo ".env created from .env.example"

dev: setup
	docker compose up --build

up: setup
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

test:
	cd backend && PYTHONPATH=. $(BACKEND_PYTEST)
	cd frontend && npm test

lint:
	cd backend && $(BACKEND_RUFF) check .
	cd frontend && npm run lint

format:
	cd backend && $(BACKEND_RUFF) format .
	cd frontend && npm run format

seed:
	docker compose exec backend sh -c 'PYTHONPATH=. python scripts/seed_demo_data.py'
