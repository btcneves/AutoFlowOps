# Release Notes — AutoFlowOps v0.1.0

**Release date:** 2026-05-19

---

## Summary

AutoFlowOps v0.1.0 is the first stable release of the platform. It delivers a fully functional, self-hosted automation dashboard for scheduled HTTP jobs, API integrations, webhooks, alerts and operational reports. The entire stack — backend, frontend, database and CI — is implemented, tested and validated end-to-end with Docker Compose.

---

## Main Features

### HTTP Job Scheduler

- Create HTTP jobs (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) via REST API
- Schedule jobs on a fixed interval (seconds) or a five-field cron expression
- Trigger jobs manually at any time via `POST /api/jobs/{id}/run`
- Pause and resume jobs without losing configuration
- Configurable timeout per job

### Execution History

- Every execution is stored with status, duration, HTTP status code, error message and a preview of the response body
- Sensitive request headers and JSON body fields are masked before storage — tokens, passwords, API keys and similar fields are never persisted in plain text

### Webhooks

- Create inbound webhook endpoints with a unique slug and a secret token
- Incoming requests are validated against the SHA-256 hash of the secret — mismatches return `403 Forbidden`
- All received events are stored with headers and payload; sensitive fields are masked
- Events can be reprocessed manually via API

### Alerts

- A failure alert is created automatically on every failed job execution
- Alerts can be acknowledged and resolved via dedicated endpoints
- Alerts are filterable by status (`open`, `acknowledged`, `resolved`)

### Operational Reports

- Generate a report for any time period: summary of executions, failures, success rate and average duration
- Save reports in canonical JSON format; export as JSON, Markdown or CSV on demand
- Historical reports are stable — they are rendered from saved content, not recomputed from live data

### Dashboard

- Real-time metrics: active jobs, executions in the last 24 hours, failures, success rate
- 7-day execution chart (success vs failure) rendered with Recharts
- Backend connectivity badge visible in the header

---

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x async, Alembic |
| Database | PostgreSQL 16 |
| Scheduler | APScheduler (in-process) |
| HTTP client | httpx |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query v5 |
| Charts | Recharts |
| Testing | pytest (backend), Vitest + Testing Library (frontend) |
| Lint | ruff (backend), ESLint + Prettier (frontend) |
| DevOps | Docker, Docker Compose, GitHub Actions, Makefile |

---

## Validation

All suites were run against the final build before this release.

| Suite | Result |
| --- | --- |
| Backend tests (pytest) | 109 / 109 passing |
| Frontend tests (Vitest) | 31 / 31 passing |
| Backend lint (ruff) | Clean |
| Frontend lint (ESLint) | Clean |
| Frontend build (Vite) | Success |
| Docker Compose end-to-end | Backend, frontend and PostgreSQL running; all API flows verified |

---

## Screenshots

All screenshots were captured from the live stack seeded with `make seed`.

| Screen | File |
| --- | --- |
| Dashboard | `docs/assets/screenshots/dashboard.png` |
| Webhooks | `docs/assets/screenshots/webhooks.png` |
| Alerts | `docs/assets/screenshots/alerts.png` |
| Reports | `docs/assets/screenshots/reports.png` |
| API docs (Swagger) | `docs/assets/screenshots/api-docs.png` |

---

## Known Limitations

- **No authentication.** All API endpoints are open. The MVP is intended for deployment behind a private network, VPN or reverse proxy.
- **In-process scheduler.** APScheduler runs inside the backend process. A single replica is supported. Heavy workloads or high availability require migrating execution to a Celery/Redis worker (planned in a future release).
- **No rate limiting.** The backend does not limit request rates per IP or endpoint.
- **No SSRF protection.** HTTP jobs can target any URL including internal network addresses. Validate job URLs manually before use in production.
- **Frontend is API-first.** The dashboard, webhooks, alerts and reports pages are implemented. Job creation, editing and listing from the UI are planned for the next release cycle.
- **No audit log.** There is no immutable record of who created, modified or deleted resources.

---

## Next Steps

The following are the top priorities for the next development cycle:

1. **Jobs management UI** — create, edit, pause and delete jobs directly from the browser
2. **Executions page** — frontend page with filters for status, job and date range
3. **JWT authentication** — user accounts, login/logout, session tokens and protected endpoints
4. **VPS deployment guide** — step-by-step guide for production on a Linux server with nginx and HTTPS
5. **Celery + Redis worker** — decouple job execution from the API process

See [docs/roadmap.md](roadmap.md) for the full roadmap.

---

## Quick Start

```bash
git clone https://github.com/btcneves/autoflowops.git
cd autoflowops
cp .env.example .env
docker compose up --build
```

The frontend is available at `http://localhost:3000`. The backend API is at `http://localhost:8000`. Seed demo data with `make seed`.

For the full setup guide, see [docs/development.md](development.md).
