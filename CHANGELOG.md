# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-05-21

### Added

- **Conditional alert rules** — per-job rules can create alerts from HTTP status thresholds, execution duration thresholds, response body matches and consecutive failure counts.
- **Alert rules API and UI** — CRUD endpoints under `/api/jobs/{job_id}/alert-rules` plus management controls on the job detail page.
- **Alembic migration `c3d4e5f6a7b8`** — creates the `alert_rules` table with job and workspace foreign keys.
- **Workspace-scoped alert dispatch** — alert notifications and escalation policies now dispatch only through channels/policies in the alert's workspace.
- **Log aggregation** — Loki and Elasticsearch log shipping via `LOG_SINK`, `LOKI_URL` and `ELASTICSEARCH_URL` environment variables; Promtail agent-based shipping for Docker deployments added to `docker-compose.observability.yml`; label schema documented in `docs/log-aggregation.md`.
- **Notification provider extensions** — PagerDuty dedup key (`dedup_key`), OpsGenie alert priority (`priority`) and custom payload template (`payload_template`) for richer provider-specific delivery configuration.

### Changed

- **Workspace isolation hardening** — job detail/update/delete/run, execution detail and alert rule endpoints now honor `X-Workspace-ID` resource scope.
- **Worker parity** — queued Celery executions now evaluate conditional alert rules after final retry handling.
- **Version alignment** — backend package metadata, `/api/version`, frontend package metadata and lockfile report `1.2.0`.

## [1.1.0] - 2026-05-20

### Added

- **PagerDuty notification channel** — `pagerduty` channel type using Events API v2; `routing_key` credential encrypted at rest with Fernet and masked in all API responses and delivery records
- **OpsGenie notification channel** — `opsgenie` channel type with US/EU region support; `api_key` encrypted and masked; optional `responders` list
- **PDF report export** — `GET /api/reports/{id}/download?format=pdf` generates a PDF using reportlab; sections: title, period, summary metrics, top failed jobs, alerts, recommendations
- **Multi-workspace** — `workspaces` and `workspace_memberships` tables; `X-Workspace-ID` header filters all domain resources; workspace CRUD API (`GET`, `POST`, `PATCH`, `DELETE /api/workspaces`) and member management (`GET`, `POST`, `DELETE /api/workspaces/{id}/members`); default workspace bootstrapped on startup; default workspace cannot be deleted
- **Frontend workspace selector** — sidebar dropdown persists active workspace to `localStorage` and injects `X-Workspace-ID` into all API requests; admin-only Workspaces settings page at `/workspaces`
- **`workspace_id` column** — nullable FK (`SET NULL` on workspace delete) added to jobs, executions, alerts, webhooks, notification channels, notification templates, escalation policies and reports
- **Alembic migration `b2c3d4e5f6a7`** — creates `workspaces` and `workspace_memberships` tables and adds `workspace_id` to all domain tables; fully reversible

## [1.0.0] - 2026-05-20

### Added

- **Stable self-hosted release** — consolidates all platform capabilities delivered from v0.1.0 through v0.9.0 into the first production-oriented major release.
- **Version alignment** — backend package metadata, `/api/version`, frontend package metadata and lockfile now report `1.0.0`.
- **Release notes** — `docs/release-notes-v1.0.0.md` documents the full feature set, validation plan, safety checklist, known limitations and next steps for the official release.

### Changed

- **GHCR release tags** — Docker publish workflow now pushes both the exact Git tag (`vX.Y.Z`) and semver aliases (`X.Y.Z`, `X.Y`, `latest`) for backend and frontend images.
- **Registry setup examples** — setup script, Makefile comment, README and deployment guide now use `v1.0.0` as the pinned release example.

## [0.9.0] - 2026-05-20

### Added

- **Docker image registry** — backend and frontend images published to GitHub Container Registry (`ghcr.io/btcneves/autoflowops-backend`, `ghcr.io/btcneves/autoflowops-frontend`) on every `v*.*.*` tag push via `docker-publish.yml` GitHub Actions workflow
- **Versioned image tags** — each release produces `vX.Y.Z`, `X.Y` and `latest` tags with full OCI metadata labels
- **`docker-compose.registry.yml`** — drop-in compose file that starts the full stack using GHCR images; `IMAGE_TAG` environment variable selects the version (defaults to `latest`)
- **`scripts/setup.sh`** — interactive setup script: checks prerequisites, copies `.env.example`, pulls images from GHCR, starts the stack and waits for health checks; supports `IMAGE_TAG` for non-interactive use
- **Makefile targets** — `pull`, `registry-up`, `registry-down`, `registry-logs`; `IMAGE_TAG` variable (default `latest`) controls the image version across all registry targets
- **Build cache** — `docker-publish.yml` uses GitHub Actions cache (`type=gha`) for backend and frontend build stages, reducing repeat-build time significantly
- **Backend Dockerfile** — added `curl` for health checks, `HEALTHCHECK` instruction, OCI labels, non-root user created earlier in build; `.dockerignore` extended to exclude `tests/`, egg-info, `.sqlite` and `.pyd` files
- **Frontend Dockerfile** — added OCI labels; `.dockerignore` extended to exclude `src/tests/` and `coverage/`

## [0.8.0] - 2026-05-20

### Added

- **WebSocket endpoint** — `ws[s]://<host>/ws/events?token=<JWT>`; JWT authentication via query parameter; immediate rejection (close 1008) for missing, invalid or non-existent-user tokens
- **`ConnectionManager`** — in-process singleton that tracks active WebSocket connections and broadcasts messages; dead connections are silently removed on next send
- **Redis Pub/Sub fan-out** — a long-running asyncio task subscribes to the `autoflowops:events` channel and forwards every message to all connected WS clients; started in lifespan, cancelled on shutdown; fails gracefully if Redis is unavailable
- **`event_publisher` service** — `publish_event()` (sync, for Celery) and `publish_event_async()` (async, for FastAPI); events: `execution.started`, `execution.completed`, `alert.created`; failures are logged and swallowed so the primary execution path is never blocked
- **Execution events from `http_runner`** — `execution.started` on status transition to `running`; `execution.completed` and `alert.created` after each execution completes
- **Execution events from Celery worker** — `execution.completed` (including `retrying` transitions) and `alert.created` published synchronously after each task run
- **`useWebSocket` hook** — connects to `ws[s]://<host>/ws/events?token=<JWT>`; parses `WSEvent` frames; exponential-backoff reconnect (max 30s); stops reconnecting on auth failure (code 1008); closes cleanly on unmount; no reconnect when token is absent
- **`LiveIndicator` component** — pulsing green dot ("Live") when WS is connected; neutral grey dot when connecting; renders nothing when closed or auth-failed (polling fallback remains active)
- **Executions page real-time** — invalidates the executions query on `execution.started` / `execution.completed` events; displays `LiveIndicator`
- **Jobs page real-time** — invalidates the jobs query on `execution.completed`; displays `LiveIndicator`
- **Alerts page real-time** — invalidates the alerts query on `alert.created`; displays `LiveIndicator`
- **WS backend tests** — 7 tests: no token, invalid token, ghost-user token, valid admin connects, ping/pong, manager broadcast, manager dead-connection cleanup
- **WS frontend tests** — 10 tests in `useWebSocket.test.ts`: connection creation, initial status, auth_error when no token, open status, lastEvent parsing, pong/connected filtering, code-1008 no-reconnect, reconnect on normal close, socket close on unmount

## [0.7.0] - 2026-05-20

### Added

- **RBAC** — three roles (`admin`, `operator`, `viewer`) enforced server-side via `require_admin` and `require_operator` FastAPI dependencies; applied to every write endpoint across jobs, webhooks, alerts, notifications, templates, escalation policies and reports
- **User management API** — `GET /api/users`, `POST /api/users`, `PATCH /api/users/{id}`, `POST /api/users/{id}/reset-password`, `DELETE /api/users/{id}`; all admin-only; protects against deleting or deactivating the last active admin account
- **Audit log model** — `audit_logs` table with `user_id` (nullable FK, `SET NULL` on delete), `action`, `resource_type`, `resource_id`, `status`, `ip_address`, `user_agent`, masked `metadata`, `created_at`
- **Audit log API** — `GET /api/audit-logs` with filters (`user_id`, `action`, `resource_type`, `status`, `since`, `until`, `limit`); admin-only
- **Audit coverage** — login success/failure, all job CRUD + run, webhook CRUD + reprocess, alert ack/resolve, notification channel CRUD + test, template CRUD, escalation policy CRUD, report generate, user management events
- **Sensitive metadata masking in audit** — `password`, `token`, `api_key`, `webhook_url`, `bot_token`, `smtp_password`, `encryption_key` and related keys replaced with `"[redacted]"` before persistence
- **`last_login_at` tracking** — `User` model now records the timestamp of each successful login
- **`require_admin` / `require_operator` dependencies** — `backend/app/dependencies.py`; role level integer comparison (`admin=3`, `operator=2`, `viewer=1`)
- **`audit.py` service** — async `log_action()` helper; uses `session.flush()` to capture new resource IDs before commit
- **Frontend: Users page** — admin-only; table with name, email, role selector, status badge, last login, created date; inline password reset form; activate/deactivate; delete with self-protection
- **Frontend: Audit Logs page** — admin-only; filter controls for action, resource type, status and date range; sortable log table
- **Frontend: `AdminRoute` component** — redirects unauthenticated users to `/login`, non-admins to `/`
- **Frontend: `isAdmin` / `isOperator`** — computed booleans derived from role level in `AuthContext`; used by `AdminRoute` and `Sidebar`
- **Frontend: admin nav items** — Users and Audit Logs sidebar links visible only to admins
- **RBAC backend tests** — 20 tests across 4 classes (viewer read, viewer blocked write, operator write, admin full access)
- **Audit log backend tests** — 5 tests: login events, job audit, metadata masking, filter queries
- **User management backend tests** — 9 tests: CRUD, last-admin protection, no `password_hash` in responses
- **Frontend tests** — 8 new tests: `UsersPage` (4) and `AuditLogsPage` (4)
- **Release notes** — `docs/release-notes-v0.7.0.md`

### Changed

- Default user role changed from `"user"` to `"viewer"`
- `GET /api/jobs`, `GET /api/jobs/{id}`, `GET /api/executions`, `GET /api/webhooks`, `GET /api/alerts`, `GET /api/reports` now accessible to all authenticated roles (previously operator-only by convention)
- `POST /api/jobs`, `PUT /api/jobs/{id}`, `DELETE /api/jobs/{id}`, `POST /api/jobs/{id}/run` now require `operator` or above (explicit enforcement)
- Webhook, alert, notification channel, template, escalation policy and report write operations now carry explicit role checks
- Sidebar footer now displays the authenticated user's role label
- `Base.metadata.create_all` in app lifespan ensures `audit_logs` table is created on startup (no Alembic migration required for new tables)

### Test Results (v0.7.0)

| Suite | Status |
| --- | --- |
| Backend lint (ruff) | Clean |
| Backend tests (pytest) | 209 passing |
| Frontend tests (Vitest) | 65 passing |
| Frontend lint (ESLint) | Clean |
| Frontend TypeScript | No errors |

## [0.6.0] - 2026-05-20

### Added

- **Slack webhook channel** — new `slack_webhook` channel type; sends Slack attachments with severity colour coding
- **Telegram channel** — new `telegram_message` channel type; sends formatted messages via Bot API
- **Notification templates** — `NotificationTemplate` model and CRUD API (`/api/notification-templates`); severity-specific or catch-all templates with `{title}`, `{severity}`, `{message}` variables; built-in fallback when no template matches
- **Escalation policies** — `EscalationPolicy` and `EscalationStep` models; step 0 dispatches immediately, later steps create `EscalationEvent` records dispatched on a 60-second APScheduler cycle; events cancelled automatically on alert resolution
- **Credential encryption at rest** — `credential_cipher.py` wraps Fernet (AES-128-CBC + HMAC); all channel `config_encrypted` values written using `NOTIFICATION_ENCRYPTION_KEY`; legacy plain-JSON records (v0.5.0) detected and handled transparently on read
- **`NOTIFICATION_ENCRYPTION_KEY` setting** — URL-safe base64 Fernet key; if absent, derived from `APP_SECRET_KEY` with a logged WARNING (dev/test only)
- **Frontend: Slack and Telegram channel forms** — `NotificationChannelsPage` now includes input sections for both new channel types
- **Frontend: Notification Templates page** — create, edit and delete templates with severity filter and template variable preview
- **Frontend: Escalation Policies page** — multi-step policy builder with channel selector and delay (minutes) per step
- **Release notes** — `docs/release-notes-v0.6.0.md`

### Changed

- `dispatch_alert_notifications` checks for active escalation policies first; falls back to direct all-channels dispatch when none exist
- Channel config read/write now goes through `encrypt_config`/`decrypt_config`; no plain secrets stored after first write
- Slack and Telegram delivery errors are scrubbed of bot tokens and webhook URLs before persistence
- Sidebar navigation split into **Channels**, **Templates** and **Escalation** entries

### Test Results (v0.6.0)

| Suite | Status |
| --- | --- |
| Backend lint (ruff) | Clean |
| Backend tests (pytest) | 172 passing |
| Frontend tests (Vitest) | 57 passing |
| Frontend lint (ESLint) | Clean |
| Frontend TypeScript | No errors |

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
