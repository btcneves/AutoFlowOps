BACKEND_PYTEST ?= $(shell if [ -x backend/.venv/bin/pytest ]; then echo .venv/bin/pytest; else echo pytest; fi)
BACKEND_RUFF ?= $(shell if [ -x backend/.venv/bin/ruff ]; then echo .venv/bin/ruff; else echo ruff; fi)

.PHONY: dev up down logs worker-logs test lint format setup seed prod-up prod-down prod-logs prod-validate

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

worker-logs:
	docker compose logs -f worker

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

prod-up:
	docker compose -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

prod-validate:
	docker compose -f docker-compose.prod.yml config --quiet && echo "docker-compose.prod.yml is valid"
	docker run --rm -v "$$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile
	@echo "Caddyfile is valid"
