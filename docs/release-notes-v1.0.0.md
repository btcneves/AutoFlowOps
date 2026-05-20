# Release Notes — v1.0.0

**Release date:** 2026-05-20

## Overview

v1.0.0 is the first stable self-hosted release of AutoFlowOps. It consolidates the full platform built from v0.1.0 through v0.9.0: FastAPI backend, React/TypeScript frontend, PostgreSQL persistence, Redis and Celery worker execution, Jobs, Executions, Webhooks, Alerts, Reports, Notification Channels, Templates, Escalation Policies, RBAC, Audit Log, WebSocket real-time events, Docker Compose deployment, GHCR image publishing and setup scripts.

This release is intended as the official baseline for self-hosted operation.

---

## Included Capabilities

### Core automation

- Jobs CRUD with HTTP methods, headers, bodies, timeouts and schedule controls.
- Manual, interval and cron execution paths.
- Persistent execution history with statuses, timings, masked request metadata and response previews.
- Redis-backed Celery worker for manual and scheduled job processing.
- Automatic alerts for failed executions and webhook failures.

### Integrations and operations

- Webhook CRUD, token validation, event history and reprocessing.
- Reports exportable as JSON, Markdown and CSV.
- Dashboard metrics for active jobs, recent executions, failures and success rate.
- External notifications through Discord, Telegram, SMTP email and custom webhooks.
- Notification templates and multi-step escalation policies.

### Security and governance

- JWT authentication on protected API routes.
- Admin, operator and viewer roles enforced server-side.
- Admin-only user management.
- Audit log for sensitive actions with actor, resource, IP address, user agent and masked metadata.
- SSRF protection for HTTP job targets.
- Webhook token hashing.
- Notification credentials encrypted at rest with Fernet.
- Secrets masked in execution records, API responses, delivery errors and audit metadata.

### Real-time experience

- WebSocket endpoint at `/ws/events` with JWT validation.
- Redis Pub/Sub fan-out for execution and alert events.
- Frontend live indicators and query invalidation for executions, jobs and alerts.
- Polling fallback remains available when the WebSocket stream is unavailable.

### Distribution and deployment

- Local Docker Compose stack for development and validation.
- Production Docker Compose stack with Caddy reverse proxy.
- Backend and frontend images published to GHCR on release tags.
- Registry compose file for running pre-built images without a local build.
- `scripts/setup.sh` for first-time setup and non-interactive scripted installs.
- Makefile targets for tests, lint, local stack, production stack and registry stack.

---

## Version and Packaging Changes

- Backend package metadata and `/api/version` now report `1.0.0`.
- Frontend package metadata and lockfile now report `1.0.0`.
- GHCR publish workflow now emits:
  - `v1.0.0`
  - `1.0.0`
  - `1.0`
  - `latest`
- Setup examples now use `IMAGE_TAG=v1.0.0`.

---

## Upgrade Steps

No database migration is required for the v0.9.0 to v1.0.0 version consolidation.

### Pull from registry

```bash
make pull IMAGE_TAG=v1.0.0
make registry-down
make registry-up IMAGE_TAG=v1.0.0
```

### Build from source

```bash
git pull origin main
docker compose up -d --build
```

---

## Production Safety Checklist

- Set strong, unique `APP_SECRET_KEY` and `JWT_SECRET_KEY` values before deployment.
- Set `NOTIFICATION_ENCRYPTION_KEY` explicitly for production notification credentials.
- Change the initial admin password immediately after first login.
- Keep `.env`, `.env.production` and database backups outside version control.
- Run behind HTTPS in production, especially when using the WebSocket endpoint.
- Restrict PostgreSQL and Redis to the internal Docker network.
- Keep `ENABLE_SSRF_PROTECTION=true` unless private-network job targets are intentionally required.
- Review RBAC assignments before adding operators or viewers.
- Monitor audit logs for sensitive administrative activity.

---

## Validation Plan

- Backend lint: `cd backend && ruff check .`
- Backend tests: `cd backend && PYTHONPATH=. pytest`
- Frontend lint: `cd frontend && npm run lint`
- Frontend tests: `cd frontend && npm test`
- Frontend build: `cd frontend && npm run build`
- Full local lint/test: `make lint && make test`
- Local Docker build: `docker compose build`
- Local smoke: backend health/version, Redis ping, Celery worker ping, job success/failure, alert creation, RBAC checks, audit log entries, WebSocket event stream.
- Registry smoke after release: pull `v1.0.0` GHCR images, run `IMAGE_TAG=v1.0.0 bash scripts/setup.sh`, verify backend, frontend, worker and health endpoints.

---

## Known Limitations

- The frontend image uses `vite preview`; for high-traffic production environments, prefer the documented production stack with a dedicated reverse proxy.
- WebSocket authentication uses a query parameter because browser WebSocket clients cannot send custom headers during the handshake. Use HTTPS/WSS and short-lived tokens in production.
- Webhook rate limiting is in-memory per API process.
- Audit logs are append-only by application convention; direct database access can bypass application controls.
- Notification credential encryption depends on protecting the configured encryption key.
- Multi-workspace isolation, PDF exports and advanced retry controls remain planned future work.

---

## Next Steps

- Add advanced retry policy controls to the frontend.
- Add optional PDF report export.
- Expand notification providers.
- Document multi-replica deployment patterns for the WebSocket subscriber and worker scaling.
