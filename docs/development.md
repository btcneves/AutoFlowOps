# Development Guide

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose

## Quick Start (Docker)

```bash
make dev
```

This runs `docker compose up --build` and starts backend, frontend and database.

- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- API docs (Swagger): http://localhost:8000/docs
- API docs (ReDoc): http://localhost:8000/redoc

## Local Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Copy the environment file:

```bash
cp ../.env.example ../.env
```

Run the development server:

```bash
uvicorn app.main:app --reload
```

Run tests:

```bash
PYTHONPATH=. .venv/bin/pytest
```

Run lint:

```bash
.venv/bin/ruff check .
.venv/bin/ruff format .
```

## Local Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on http://localhost:3000 by default.

Run tests:

```bash
npm test
```

Run lint:

```bash
npm run lint
npm run format
```

Build the production frontend:

```bash
npm run build
```

## Demo Data

When Docker is running, seed a small demo dataset for screenshots or manual review:

```bash
make seed
```

For local backend development without Docker, run migrations first and then seed:

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./autoflowops.db .venv/bin/alembic upgrade head
DATABASE_URL=sqlite+aiosqlite:///./autoflowops.db PYTHONPATH=. .venv/bin/python scripts/seed_demo_data.py
```

## Environment Variables

Copy `.env.example` to `.env` and adjust values for your environment.

| Variable | Description | Default |
|---|---|---|
| `APP_NAME` | Application name | `AutoFlowOps` |
| `APP_ENV` | Environment (`development`, `production`) | `development` |
| `APP_DEBUG` | Enable verbose SQL/debug logging | `false` |
| `APP_SECRET_KEY` | Secret key for session/auth | `change-me` |
| `DATABASE_URL` | PostgreSQL connection string | See `.env.example` |
| `FRONTEND_URL` | Frontend URL for CORS | `http://localhost:3000` |
| `LOG_LEVEL` | Log level (`DEBUG`, `INFO`, `WARNING`) | `INFO` |
| `ENABLE_DEMO_MODE` | Enable demo data | `true` |

**Never commit `.env` to version control.**

## Project Structure

```
backend/
├── app/
│   ├── main.py          # FastAPI app, CORS, startup
│   ├── config.py        # Settings (pydantic-settings)
│   ├── api/             # REST routers
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   └── services/        # Scheduler, runner and masking services
├── alembic/             # Database migrations
├── scripts/             # Utility scripts such as demo data seeding
└── tests/
    ├── conftest.py
    └── test_*.py

frontend/
└── src/
    ├── api/             # HTTP client + typed endpoints
    ├── components/      # Reusable UI components
    ├── hooks/           # Custom React hooks
    ├── pages/           # Route-level page components
    ├── types/           # TypeScript types
    └── tests/           # Vitest test files
```

## Commit Convention

```
feat: add job creation endpoint
fix: mask authorization header in execution logs
docs: update development guide
test: add job execution tests
chore: update docker compose
```
