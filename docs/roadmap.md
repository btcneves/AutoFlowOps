# Roadmap

This document tracks the feature status of AutoFlowOps across completed, planned and future phases.

---

## Completed (v1.0.0)

| Feature | Details |
| --- | --- |
| **Stable self-hosted release** | Consolidates the complete AutoFlowOps feature set into the first major release: jobs, executions, webhooks, alerts, reports, notifications, RBAC, audit log, real-time events, worker queue, Docker Compose and GHCR distribution |
| **Version alignment** | Backend package metadata, `/api/version`, frontend package metadata and lockfile report `1.0.0` |
| **Release packaging** | Dedicated v1.0.0 release notes, setup examples pinned to `v1.0.0`, and Docker publish workflow producing both `vX.Y.Z` and semver image tags |

---

## Completed (v0.9.0)

| Feature | Details |
| --- | --- |
| **Docker image registry** | Backend and frontend images published to GHCR on every version tag; OCI labels, build cache via GitHub Actions cache; tags: `vX.Y.Z`, `X.Y`, `latest` |
| **Improved Dockerfiles** | Backend: added `curl`, `HEALTHCHECK` instruction, OCI labels, non-root user created early, dependency cache layer isolated; `.dockerignore` extended to exclude tests, eggs, SQLite files |
| **Frontend Dockerfile** | Added OCI labels; `.dockerignore` extended to exclude `src/tests/` and `coverage/` |
| **`docker-compose.registry.yml`** | Drop-in compose file that uses `ghcr.io/btcneves/autoflowops-backend` and `ghcr.io/btcneves/autoflowops-frontend` images; `IMAGE_TAG` environment variable selects the version |
| **`scripts/setup.sh`** | Interactive (or non-interactive via `IMAGE_TAG`) setup script: checks prerequisites, copies `.env.example`, pulls images from GHCR, starts the stack, waits for health endpoints and prints service URLs |
| **Makefile targets** | `pull` — pull images from GHCR; `registry-up` — start with GHCR images; `registry-down` — stop; `registry-logs` — stream logs; `IMAGE_TAG` variable controls the version |
| **`docker-publish.yml` workflow** | GitHub Actions workflow triggered on `v*.*.*` tag push; builds and pushes backend and frontend images to GHCR; uses build cache (`type=gha`) for fast rebuilds; separate jobs for each service |

---

## Completed (v0.8.0)

| Feature | Details |
| --- | --- |
| **WebSocket endpoint** | `GET /ws/events?token=<JWT>` — upgrades to a persistent connection; JWT validated against DB on each connect; rejected connections receive code 1008 |
| **ConnectionManager** | In-process registry of active WebSocket connections; dead connections removed on next broadcast |
| **Redis Pub/Sub fan-out** | Single asyncio subscriber task per backend process; forwards `autoflowops:events` channel messages to all connected clients; fails gracefully when Redis is unavailable |
| **`event_publisher` service** | `publish_event()` (sync, Celery) and `publish_event_async()` (async, FastAPI); swallows publish errors so the primary execution path is never blocked |
| **`execution.started` event** | Published by `http_runner` when an execution transitions to `running` |
| **`execution.completed` event** | Published by both `http_runner` and the Celery worker on every terminal state, including `retrying` |
| **`alert.created` event** | Published when a job failure creates an alert, from both the APScheduler and Celery paths |
| **`useWebSocket` hook** | Exponential-backoff reconnect (max 30s); stops reconnecting on code 1008; closes on unmount; no reconnect when access token is absent |
| **`LiveIndicator` component** | Pulsing green dot when connected; grey dot when connecting; invisible when closed or auth-failed (polling fallback still active) |
| **Real-time Executions page** | Invalidates query cache on `execution.started` / `execution.completed`; shows `LiveIndicator` |
| **Real-time Jobs page** | Invalidates jobs cache on `execution.completed` (updates `last_run_at`); shows `LiveIndicator` |
| **Real-time Alerts page** | Invalidates alerts cache on `alert.created`; shows `LiveIndicator` |
| **WS backend tests** | 7 tests: no token, invalid token, ghost-user token, valid admin, ping/pong, broadcast, dead-connection cleanup |
| **WS frontend tests** | 10 tests in `useWebSocket.test.ts`: connection, initial status, auth_error (no token), open, lastEvent, pong/connected filtering, 1008 no-reconnect, reconnect on normal close, close on unmount |

---

## Completed (v0.7.0)

| Feature | Details |
| --- | --- |
| **RBAC** | Three roles — `admin`, `operator`, `viewer` — enforced server-side on every endpoint via FastAPI dependencies |
| **Role hierarchy** | `admin` (level 3) ≥ `operator` (level 2) ≥ `viewer` (level 1); `require_admin` and `require_operator` dependencies applied per endpoint |
| **User management API** | `GET /api/users`, `POST /api/users`, `PATCH /api/users/{id}`, `POST /api/users/{id}/reset-password`, `DELETE /api/users/{id}` — admin only |
| **Last-admin protection** | Cannot deactivate or delete the last active admin account |
| **Audit log model** | `audit_logs` table: `user_id`, `action`, `resource_type`, `resource_id`, `status`, `ip_address`, `user_agent`, masked `metadata`, `created_at` |
| **Audit log API** | `GET /api/audit-logs` with filters (user_id, action, resource_type, status, since, until, limit) — admin only |
| **Audit coverage** | Login success/failure, jobs CRUD + run, webhooks CRUD + reprocess, alerts ack/resolve, notification channels CRUD + test, templates CRUD, escalation policies CRUD, reports generate, user management |
| **Sensitive metadata masking** | Passwords, tokens, API keys, webhook URLs and encryption keys scrubbed from audit metadata before persistence |
| **`last_login_at` tracking** | User model records last successful login timestamp |
| **Frontend: Users page** | Admin-only page with user table, create form, inline role selector, activate/deactivate, password reset and delete |
| **Frontend: Audit Logs page** | Admin-only page with filter controls (action, resource type, status, date range) and paginated log table |
| **Frontend: AdminRoute** | Route guard that redirects non-admins to `/`; non-authenticated users to `/login` |
| **Frontend: `isAdmin` / `isOperator`** | Computed booleans in `AuthContext`; sidebar hides admin nav items from non-admins |
| **RBAC tests** | 20 backend tests covering viewer/operator/admin permission boundaries |
| **Audit log tests** | 5 backend tests: login events, job audit, metadata masking, filter queries |
| **User management tests** | 9 backend tests: full CRUD, last-admin guard, no `password_hash` exposure |
| **Frontend tests** | 8 new frontend tests (UsersPage and AuditLogsPage) — total 65 passing |

---

## Completed (v0.6.0)

| Feature | Details |
| --- | --- |
| **Slack webhook channel** | `slack_webhook` type with Slack attachments format and severity colour coding |
| **Telegram channel** | `telegram_message` type with Bot API and Markdown formatting |
| **Notification templates** | Severity-specific or catch-all templates with title/body customisation and built-in fallback |
| **Escalation policies** | Multi-step policies: step 0 dispatches immediately; later steps fire on a 60-second APScheduler cycle |
| **Credential encryption** | Fernet AES encryption for all channel configs; `NOTIFICATION_ENCRYPTION_KEY` env var; legacy plain-JSON migration |
| **Frontend: Templates page** | Create, edit and delete notification templates from the UI |
| **Frontend: Escalation page** | Multi-step policy builder with channel selector and delay per step |
| **Credential masking** | Slack URL, Telegram token and SMTP password scrubbed before any API response, log or delivery error record |

---

## Completed (v0.5.0)

| Feature | Details |
| --- | --- |
| **Notification channels** | CRUD API and frontend page for Discord webhook, SMTP email and custom webhook channels |
| **Channel testing** | Protected test endpoint sends a sample notification and records the delivery result |
| **Alert delivery integration** | Critical job and webhook alerts dispatch notifications through active channels |
| **Delivery history** | Notification delivery records store success/failure, channel metadata, timestamps and masked errors |
| **Secret masking** | API responses and UI show masked channel configuration; delivery errors are scrubbed before persistence |
| **Notification tests** | Backend tests cover channel CRUD, test sends, alert dispatch and masked failures; frontend tests cover the channels page |

---

## Completed (v0.4.0)

| Feature | Details |
| --- | --- |
| **Celery worker** | Dedicated worker process executes HTTP jobs outside the API process |
| **Redis queue** | Redis broker/result backend configured with `REDIS_URL` |
| **Queued manual runs** | `POST /api/jobs/{id}/run` creates a `queued` execution and dispatches a Celery task |
| **Queued scheduled runs** | APScheduler keeps schedule timing but dispatches work to the queue |
| **Retry states** | Executions can move through `queued`, `running`, `retrying`, `success`, `failure` and `timeout` |
| **Worker healthchecks** | Development and production Compose files include Redis and worker healthchecks |
| **Worker tests** | Backend tests cover enqueue, worker execution, final failure alerts and retrying state |

---

## Completed (v0.3.0)

| Feature | Details |
| --- | --- |
| **Production deployment guide** | Step-by-step VPS deployment with Docker Compose, domain, HTTPS and production checklist |
| **Caddy reverse proxy** | `Caddyfile` template with automatic HTTPS, security headers and path-based routing |
| **`docker-compose.prod.yml`** | Separate production compose: Caddy on 80/443, backend/frontend unexposed, PostgreSQL on internal network only |
| **Container healthchecks** | Healthchecks on all services (backend, frontend, db, Caddy) with `restart: always` |
| **`.env.production.example`** | Production environment template with all required variables documented |
| **Backup and restore guide** | PostgreSQL dump/restore commands and cron example |
| **Update procedure** | Git pull + rebuild + auto-migration documented |
| **Logs and troubleshooting guide** | Common issues, container exec, log streaming |
| **`prod-*` Makefile targets** | `prod-up`, `prod-down`, `prod-logs`, `prod-validate` |
| **Production Config CI** | GitHub Actions workflow validates `docker-compose.prod.yml` and `Caddyfile` syntax |
| **Enhanced health endpoint** | `/api/health` now reports `database: "ok"/"error"` for observability |

---

## Completed (v0.2.0)

| Feature | Details |
| --- | --- |
| **JWT authentication** | Login endpoint, Bootstrap admin, Bearer token validation on all protected routes |
| **Jobs management UI** | Create, edit, pause, activate, run and delete jobs from the frontend |
| **Executions UI** | History list with status/job filters, detail view with masked request/response data |
| **SSRF protection** | Block job URLs targeting private/internal ranges; DNS resolution check; configurable |
| **Webhook rate limiting** | Per-IP and per-slug in-memory rate limiter; HTTP 429 on excess; configurable limit |

---

## Completed (v0.1.0)

These features are implemented, tested and validated in the current MVP.

| Feature | Details |
| --- | --- |
| **FastAPI backend** | REST API, CORS, structured logging, async SQLAlchemy sessions |
| **PostgreSQL + Alembic** | Schema versioning, initial migration covering all domain tables |
| **HTTP job runner** | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` with configurable timeout; sensitive data masked before storage |
| **APScheduler** | In-process interval (seconds) and cron (five-field expression) scheduling; schedule updated on job changes |
| **Execution history** | Every execution stored with status, timings, masked request metadata and response preview |
| **Dashboard + stats API** | Real-time metrics: active jobs, executions/failures in 24 h, success rate, 7-day chart (Recharts) |
| **Webhook receiver** | CRUD, slug-based endpoints, SHA-256 token validation, event history, manual reprocessing |
| **Internal alerts** | Auto-created on job failure; acknowledge and resolve workflows; filter by status |
| **Operational reports** | Generate for any period; export as JSON, Markdown or CSV; stable historical snapshots |
| **React frontend** | Dashboard, Webhooks, Alerts and Reports pages; TanStack Query, React Router, Tailwind CSS |
| **Docker Compose** | Backend, frontend and PostgreSQL with health check; migrations run on backend startup |
| **GitHub Actions CI** | Backend (ruff + pytest) and frontend (ESLint + Vitest + build) pipelines |
| **Test suites** | 109 backend tests, 31 frontend tests — all passing |
| **Secret masking** | Headers and JSON body fields masked before any DB write; dedicated test coverage |
| **Demo seed script** | `make seed` populates demo data for screenshots and local exploration |

---

## Future (planned, not yet scheduled)

These features are planned but not yet in active development.

| Feature | Description |
| --- | --- |
| **Additional notification providers** | PagerDuty, OpsGenie and richer provider-specific delivery options |
| **Real-time logs** | ~~Delivered in v0.8.0~~ |
| **RBAC** | ~~Delivered in v0.7.0~~ |
| **Advanced retry policy UI** | Expose retry policy controls and retry history in the frontend |
| **PDF reports** | Export operational reports as PDF in addition to JSON, Markdown and CSV |
| **Multi-workspace** | Namespace isolation for teams or projects within a single instance |
| **Docker image registry** | ~~Delivered in v0.9.0~~ |
| **Audit log** | ~~Delivered in v0.7.0~~ |

---

## Out of Scope for This Project

The following are not goals for AutoFlowOps:

- SaaS multi-tenant platform with billing
- Visual low-code / no-code workflow builder
- Desktop or mobile application
- Replacement for full-featured platforms like n8n, Zapier or Temporal
