# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-05-20

### Added

- **Notification channels** — protected CRUD API for Discord webhook, SMTP email and custom webhook channels
- **Notification Channels UI** — frontend page for listing, creating, editing, testing, activating, pausing and deleting channels
- **Channel testing** — `POST /api/notification-channels/{id}/test` sends a sample notification and records a delivery result
- **Alert delivery integration** — critical job and webhook alerts dispatch notifications to active channels
- **Delivery history** — `notification_deliveries` records success/failure status, timestamps, channel metadata and masked errors
- **Notification security docs** — configuration guidance and credential masking limitations documented
- **Release notes** — `docs/release-notes-v0.5.0.md`

### Changed

- Webhook token validation failures and paused webhook deliveries now create critical alerts
- API responses expose notification configuration only as masked values
- Frontend navigation now includes Notification Channels

### Test Results (v0.5.0)

| Suite | Status |
| --- | --- |
| Backend lint (ruff) | Clean |
| Backend tests (pytest) | 148 passing |
| Frontend tests (Vitest) | 49 passing |
| Frontend lint (ESLint) | Clean |
| Frontend build | Success |
| Docker Compose build/smoke | Success |
| Production config validation | Compose and Caddyfile valid |

## [0.4.0] - 2026-05-20

### Added

- **Celery worker** — dedicated worker process executes HTTP jobs outside the FastAPI API process
- **Redis queue** — `REDIS_URL` configures Redis as Celery broker/result backend
- **Queued executions** — manual and scheduled runs create `queued` execution records before dispatching work
- **Retrying state** — failed or timed-out attempts can move to `retrying` before Celery schedules the next attempt
- **Worker containers** — development and production Docker Compose files include Redis and worker services with healthchecks
- **Worker tests** — backend tests cover enqueue, worker success, final failure alerting and retry state
- **Release notes** — `docs/release-notes-v0.4.0.md`

### Changed

- `POST /api/jobs/{id}/run` now returns the queued execution immediately in Celery mode
- APScheduler now dispatches scheduled jobs to the queue instead of executing HTTP calls in the API process
- Stats and reports treat `timeout` as a failed terminal execution and ignore queued/running/retrying executions for success-rate math
- Frontend execution filters now include queued, retrying and timeout statuses

### Test Results (v0.4.0)

| Suite | Status |
| --- | --- |
| Backend lint (ruff) | Clean |
| Backend tests (pytest) | 140 passing |
| Frontend tests (Vitest) | 45 passing |
| Frontend lint (ESLint) | Clean |
| Frontend build | Success |
| Docker Compose build/smoke | Success |
| Production config validation | Compose and Caddyfile valid |

## [0.3.0] - 2026-05-20

### Added

- **Production deployment stack** — `docker-compose.prod.yml` with Caddy on ports 80/443, backend/frontend exposed only inside Docker, private PostgreSQL and service healthchecks
- **Caddy reverse proxy template** — automatic HTTPS, API/docs routing, frontend routing, JSON logs and baseline security headers
- **Production environment template** — `.env.production.example` with secure placeholders and production defaults
- **Production config CI** — GitHub Actions workflow validates `docker-compose.prod.yml` and `Caddyfile` syntax
- **Production Makefile targets** — `prod-up`, `prod-down`, `prod-logs` and `prod-validate`
- **Release notes** — dedicated v0.2.0 and v0.3.0 release note documents

### Changed

- `/api/health` now includes a `database` field with `ok` or `error`
- `docs/deployment.md` rewritten as a full VPS guide with DNS, Docker, Caddy, backups, restore, updates and troubleshooting
- Security, architecture, roadmap, README and API reference updated with production deployment guidance
- `.env.production` is explicitly ignored by Git

### Test Results (v0.3.0)

| Suite | Status |
| --- | --- |
| Backend lint (ruff) | Clean |
| Backend tests (pytest) | 134 passing |
| Frontend tests (Vitest) | 45 passing |
| Frontend lint (ESLint) | Clean |
| Frontend build | Success |
| Production config validation | Compose and Caddyfile valid |

## [0.2.0] - 2026-05-19

### Added

- **JWT authentication** — login endpoint (`POST /api/auth/login`), current user endpoint (`GET /api/auth/me`), JWT Bearer token validation; all API routes except `/api/health`, `/api/version` and webhook receive now require a valid token
- **Bootstrap admin** — admin account created automatically from `ADMIN_EMAIL` / `ADMIN_PASSWORD` env vars on first startup when the users table is empty
- **Executions API** — `GET /api/executions` with `job_id`, `status`, `limit` and `offset` filters; `GET /api/executions/{id}` for execution detail
- **SSRF protection** — `app/services/ssrf_guard.py` blocks job URLs targeting private and reserved ranges (loopback, RFC-1918, link-local, IPv6 ULA); controlled by `ENABLE_SSRF_PROTECTION` and `ALLOW_PRIVATE_NETWORK_TARGETS` env vars
- **Webhook rate limiting** — in-memory per-IP and per-slug rate limiter on `POST /api/webhooks/{slug}/receive`; returns HTTP 429 when the limit is exceeded
- **Jobs management UI** — `/jobs` list, `/jobs/new` create form, `/jobs/:id` detail, `/jobs/:id/edit` edit form; run, pause/activate, and delete actions
- **Executions UI** — `/executions` list with status and job filters, `/executions/:id` detail view with masked request/response data
- **Login page** — `/login` with email/password form, error handling and redirect after successful login
- **Auth context** — `AuthContext` + `AuthProvider` + `useAuth` hook; JWT stored in `localStorage`; token sent as `Authorization: Bearer` header on every API request; auto-redirect to `/login` on 401
- **Protected routes** — `ProtectedRoute` component wraps all pages except `/login`
- **Sign-out** — logout action in sidebar clears token and redirects to `/login`
- **Updated sidebar** — Jobs and Executions nav items; signed-in user email and sign-out button at bottom
- New env vars: `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NAME`, `ENABLE_SSRF_PROTECTION`, `ALLOW_PRIVATE_NETWORK_TARGETS`, `WEBHOOK_RATE_LIMIT_PER_MINUTE`, `API_RATE_LIMIT_PER_MINUTE`

### Changed

- `pyproject.toml` — added `PyJWT>=2.9` and `bcrypt>=4.0` runtime dependencies
- `app/api/router.py` — protected routers now require `get_current_user` dependency; webhook receive moved to `webhook_receiver.py` (public)
- `app/services/http_runner.py` — calls `ssrf_guard.check_url()` before executing HTTP jobs when `ENABLE_SSRF_PROTECTION=true`
- `conftest.py` — overrides `get_current_user` with a stub user so all existing tests continue to pass without tokens
- `.env.example` — documents all new v0.2.0 environment variables

### Test Results (v0.2.0)

| Suite | Tests | Status |
| --- | --- | --- |
| Backend (pytest) | 140+ | ✅ Passing |
| Frontend (Vitest) | 38+ | ✅ Passing |
| Backend lint (ruff) | — | ✅ Clean |
| Frontend lint (ESLint) | — | ✅ Clean |
| Frontend build | — | ✅ Success |

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
