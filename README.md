# AutoFlowOps

**Open-source automation platform for scheduled HTTP jobs, API integrations, webhooks, alerts and operational reports.**

AutoFlowOps helps developers and small teams replace fragile manual processes with reliable, observable and documented automation workflows — self-hosted, reproducible and fully open source.

[![Backend CI](https://github.com/btcneves/autoflowops/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/btcneves/autoflowops/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/btcneves/autoflowops/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/btcneves/autoflowops/actions/workflows/frontend-ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## The Problem

Teams and developers often have routines scattered across isolated scripts, spreadsheets, improvised automations and paid tools with no visibility:

- Periodic API polling with no execution history
- Webhooks received with no audit trail
- Cron jobs that fail silently
- Manual repetitive tasks with no trace
- Integrations that break with no alert

## The Solution

AutoFlowOps centralises these routines in a single self-hosted platform:

- **Jobs** — create HTTP jobs via API, run manually or on interval/cron schedules
- **Executions** — persistent history with status, timings, response previews and masked secrets
- **Webhooks** — receive external events, store payloads with token validation, reprocess events
- **Alerts** — automatic alerts on job failures, with acknowledge and resolve workflows
- **Reports** — export operational history as JSON, Markdown or CSV
- **Dashboard** — real-time metrics: active jobs, executions, failure rate and 7-day chart

---

## Features

- Self-hosted, runs on any server or Docker environment
- REST API backend (FastAPI + PostgreSQL) and React frontend
- Scheduled jobs with interval (seconds) and cron expressions
- HTTP job runner with configurable timeout
- Webhook receiver with secret token validation (SHA-256)
- Execution history with masked secrets and response previews
- Internal alerting system for failed executions
- Operational reports exportable as JSON, Markdown or CSV
- One-command startup via Docker Compose
- GitHub Actions CI for backend and frontend
- Open-source under MIT License

---

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic |
| Database | PostgreSQL 16 |
| Scheduler | APScheduler (in-process, MVP) |
| HTTP client | httpx |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| State/Fetch | TanStack Query v5 |
| Charts | Recharts |
| Testing | pytest (backend), Vitest + Testing Library (frontend) |
| Lint | ruff (backend), ESLint + Prettier (frontend) |
| DevOps | Docker, Docker Compose, GitHub Actions, Makefile |

---

## Architecture Overview

```text
Browser
  └─> React/Vite frontend (port 3000)
        └─> FastAPI REST API (port 8000)
              ├─> SQLAlchemy async session
              │     └─> PostgreSQL (port 5432)
              ├─> APScheduler (in-process)
              │     └─> HTTP runner (executes jobs, creates executions + alerts)
              └─> Webhook receiver (validates token, stores events)
```

For a detailed breakdown of each component and data flow, see [docs/architecture.md](docs/architecture.md).

---

## Screenshots

![Dashboard](docs/assets/screenshots/dashboard.png)

More screenshots: [Webhooks](docs/assets/screenshots/webhooks.png) · [Alerts](docs/assets/screenshots/alerts.png) · [Reports](docs/assets/screenshots/reports.png) · [API docs](docs/assets/screenshots/api-docs.png)

---

## Quick Start

### Requirements

- Docker + Docker Compose

### 1. Clone and configure

```bash
git clone https://github.com/btcneves/autoflowops.git
cd autoflowops
cp .env.example .env
```

Edit `.env` and change `APP_SECRET_KEY` and `JWT_SECRET_KEY` before deploying to production.

### 2. Start

```bash
make dev
# or
docker compose up --build
```

| Service | URL |
| --- | --- |
| Frontend | <http://localhost:3000> |
| Backend API | <http://localhost:8000> |
| API docs (Swagger) | <http://localhost:8000/docs> |
| API docs (ReDoc) | <http://localhost:8000/redoc> |

### 3. Verify

```bash
curl http://localhost:8000/api/health
```

Expected:

```json
{"status": "ok", "app": "AutoFlowOps", "env": "development"}
```

### 4. Seed demo data (optional)

```bash
make seed
```

This creates a set of demo jobs, executions, webhooks and alerts so the dashboard renders with data immediately.

---

## Local Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

See [docs/development.md](docs/development.md) for the full local development guide, including environment variables and database setup.

---

## Testing

```bash
# Backend
cd backend
PYTHONPATH=. pytest

# Frontend
cd frontend
npm test

# Both (via Makefile)
make test
```

**Current test status:**

| Suite | Tests | Status |
| --- | --- | --- |
| Backend | 109 | Passing |
| Frontend | 31 | Passing |

---

## Lint and Format

```bash
# Backend
cd backend
ruff check .
ruff format .

# Frontend
cd frontend
npm run lint
npm run format

# Both (via Makefile)
make lint
make format
```

---

## Makefile Targets

```bash
make dev      # docker compose up --build (foreground)
make up       # docker compose up -d --build (background)
make down     # docker compose down
make logs     # docker compose logs -f
make test     # run backend + frontend tests
make lint     # run backend + frontend lint
make format   # run backend + frontend format
make seed     # seed demo data into running Docker containers
make setup    # copy .env.example to .env
```

---

## Project Structure

```text
autoflowops/
├── backend/         FastAPI application, models, services, tests
├── frontend/        React application, components, pages, tests
├── docs/            Documentation
├── examples/        Usage examples (curl recipes)
├── scripts/         Utility scripts
├── .github/         CI workflows and PR/issue templates
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Documentation

| Document | Description |
| --- | --- |
| [Architecture](docs/architecture.md) | Components, data model, scheduling and security model |
| [API Reference](docs/api-reference.md) | All endpoints with request/response examples |
| [Development Guide](docs/development.md) | Local setup, environment variables, project structure |
| [Security](docs/security.md) | Masking policy, webhook tokens, .env best practices |
| [Roadmap](docs/roadmap.md) | Completed features, next steps and future plans |
| [Deployment](docs/deployment.md) | Docker Compose, migrations and production checklist |
| [Screenshots](docs/screenshots.md) | Screenshot index and regeneration instructions |

---

## Roadmap

| Feature | Status |
| --- | --- |
| FastAPI backend + REST API | ✅ Done |
| PostgreSQL + SQLAlchemy + Alembic | ✅ Done |
| HTTP job runner with secret masking | ✅ Done |
| APScheduler (interval + cron) | ✅ Done |
| Dashboard with real metrics + chart | ✅ Done |
| Webhook CRUD + token validation + events | ✅ Done |
| Internal alerts + acknowledge/resolve | ✅ Done |
| Reports (JSON, Markdown, CSV) | ✅ Done |
| Docker Compose + GitHub Actions CI | ✅ Done |
| Authentication (JWT/session) | Planned |
| Celery + Redis worker | Planned |
| External notifications (Discord, Telegram, email) | Planned |
| Real-time logs via WebSocket | Planned |
| RBAC (role-based access control) | Planned |
| VPS deployment guide | Planned |

See [docs/roadmap.md](docs/roadmap.md) for the full roadmap.

---

## Security

- Secrets are masked in all logs and stored execution records
- Webhook tokens are stored as SHA-256 hashes, never in plain text
- `.env` is never version-controlled; only `.env.example` is committed
- There is no authentication layer in the MVP — deploy behind a private network, VPN or reverse proxy for production use

See [SECURITY.md](SECURITY.md) for the vulnerability reporting policy and full masking rules.

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

For security vulnerabilities, follow [SECURITY.md](SECURITY.md) — do not open public issues.

---

## License

[MIT](LICENSE) © 2026 AutoFlowOps Contributors
