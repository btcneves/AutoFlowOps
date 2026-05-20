# Roadmap

This document tracks the feature status of AutoFlowOps across completed, planned and future phases.

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
| **Celery + Redis worker** | Move job execution to a dedicated worker process; enables parallel execution and better scalability |
| **External notifications** | Discord webhooks, Telegram messages, email (SMTP) on job failure or alert creation |
| **Real-time logs** | WebSocket connection for live execution log streaming in the frontend |
| **RBAC** | Role-based access control — admin, operator and read-only roles |
| **Retry logic** | Configurable retry count and delay for failed HTTP jobs |
| **PDF reports** | Export operational reports as PDF in addition to JSON, Markdown and CSV |
| **Multi-workspace** | Namespace isolation for teams or projects within a single instance |
| **Docker image registry** | Publish versioned images to GitHub Container Registry for direct pull |
| **Audit log** | Immutable log of resource changes with actor and timestamp |

---

## Out of Scope for This Project

The following are not goals for AutoFlowOps:

- SaaS multi-tenant platform with billing
- Visual low-code / no-code workflow builder
- Desktop or mobile application
- Replacement for full-featured platforms like n8n, Zapier or Temporal
