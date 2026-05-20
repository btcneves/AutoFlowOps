# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-19

First stable release of the AutoFlowOps MVP. All core platform features are implemented, tested and validated end-to-end with Docker Compose.

### Added

### Backend

- FastAPI application with `/api/health`, `/api/version` and `/api/stats` endpoints
- pydantic-settings configuration, CORS middleware and structured logging
- SQLAlchemy 2.x async engine with Alembic migrations for all domain tables: `jobs`, `executions`, `webhooks`, `webhook_events`, `alerts`, `reports`, `users`
- HTTP job runner with configurable timeout; sensitive headers and JSON body fields masked before storage
- APScheduler in-process scheduler with `interval` (seconds) and `cron` (five-field expression) support
- Full CRUD API for HTTP jobs with manual execution trigger (`POST /api/jobs/{id}/run`)
- Webhook CRUD, slug-based receiver endpoint, SHA-256 token validation, event history and manual reprocessing
- Internal alert system: auto-created on job failure, with acknowledge and resolve endpoints
- Reports API: generate for any time period, save as canonical JSON, export as JSON, Markdown or CSV
- Demo data seed script (`make seed`) for local exploration and screenshots
- 109 pytest tests covering health, models, jobs CRUD, HTTP runner, masking, scheduler, webhooks, alerts, reports and stats

### Frontend

- React 18 + TypeScript + Vite application with Tailwind CSS
- Dashboard page: backend status badge, four metric cards, 7-day execution chart (Recharts)
- Webhooks page: list, status badges, last received timestamp, Copy URL button
- Alerts page: list with severity and status pills, Acknowledge and Resolve buttons, status filter
- Reports page: generate form, report list, JSON/Markdown/CSV download buttons
- TanStack Query v5 hooks with auto-refresh for all data-fetching pages
- 31 Vitest + Testing Library tests covering all four pages

### Infrastructure

- Docker Compose with backend (port 8000), frontend (port 3000) and PostgreSQL 16 (port 5432)
- Backend Docker image runs `alembic upgrade head` before starting the API server
- GitHub Actions CI: backend (ruff + pytest), frontend (ESLint + Vitest + build), Docker build
- `Makefile` with `dev`, `up`, `down`, `logs`, `test`, `lint`, `format`, `seed` targets
- `.env.example` with all configuration variables documented and safe placeholder values

### Documentation

- `README.md` — project overview, quick start, testing, stack, architecture, roadmap and security
- `docs/architecture.md` — runtime components, data model, scheduling model, job/webhook/alert/report flows, security model and MVP boundaries
- `docs/api-reference.md` — all endpoints with request/response examples and error reference
- `docs/development.md` — local setup, environment variables, project structure and commit conventions
- `docs/security.md` — masking policy, webhook token security, `.env` best practices and MVP limitations
- `docs/roadmap.md` — completed features, next priorities and future plans
- `docs/deployment.md` — Docker Compose deployment, migrations and production checklist
- `docs/screenshots.md` — screenshot index and regeneration instructions
- `docs/assets/screenshots/` — five screenshots captured from the live stack using demo data: dashboard, webhooks, alerts, reports and Swagger API docs
- `SECURITY.md` — vulnerability reporting policy, supported versions, scope and masking rules
- `CONTRIBUTING.md` — development setup, verification checklist, commit style and PR guidelines

### Test Results (v0.1.0)

| Suite | Tests | Status |
| --- | --- | --- |
| Backend (pytest) | 109/109 | ✅ Passing |
| Frontend (Vitest) | 31/31 | ✅ Passing |
| Backend lint (ruff) | — | ✅ Clean |
| Frontend lint (ESLint) | — | ✅ Clean |
| Frontend build | — | ✅ Success |
| Docker end-to-end | 17 flows | ✅ Validated |
