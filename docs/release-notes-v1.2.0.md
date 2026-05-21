# Release Notes — v1.2.0

**Release date:** 2026-05-20

## Overview

v1.2.0 introduces a security fix that enforces workspace membership on all workspace-scoped requests, expands the deployment documentation for the notification encryption key, and ships a production-ready observability stack (Prometheus metrics, structured JSON logging, and an optional Prometheus + Grafana compose stack with a pre-built dashboard).

All changes are backward-compatible. Deployments that do not use the `X-Workspace-ID` header are unaffected by the membership enforcement.

---

## What's New

### Workspace membership enforcement (security)

Prior to this release, any authenticated user could access another workspace's data by supplying an arbitrary workspace UUID in the `X-Workspace-ID` header. Starting with v1.2.0, the `get_active_workspace` dependency validates that the requesting user is a member of the target workspace before returning any data.

- Admin users (role level 3) bypass the check and retain cross-workspace access.
- Non-member requests return `403 Forbidden` with the message `Not a member of this workspace`.
- The workspace object is not returned at all for non-members, preventing information leakage.
- 5 new backend tests cover member access, non-member rejection, and the admin bypass path.

This resolves the known limitation documented in v1.1.0 that stated workspace isolation was not a security boundary.

### Encryption key documentation and rotation guide

The `NOTIFICATION_ENCRYPTION_KEY` Fernet key was absent from the deployment guide's environment variable reference table and production checklist. Both have been updated.

- `docs/deployment.md` now lists `NOTIFICATION_ENCRYPTION_KEY` in the environment variable reference and includes a checklist item requiring the key to be backed up before first use.
- `docs/security.md` now includes an "Encryption key — backup and rotation" section with the key generation command, backup requirements, and a five-step rotation procedure.

### Prometheus metrics endpoint

The backend exposes a `/metrics` endpoint in Prometheus text format, powered by `prometheus-fastapi-instrumentator`.

- HTTP metrics are auto-instrumented: `http_request_duration_seconds` histogram with `handler`, `method`, and `status_code` labels.
- Two business metrics counters:
  - `autoflowops_job_executions_total` — labelled by `status` (`success`, `failure`, `timeout`) and `trigger_type` (`manual`, `scheduled`).
  - `autoflowops_alerts_created_total` — labelled by `severity`.
- The `/metrics` endpoint is excluded from HTTP instrumentation to avoid self-referential noise.

### Structured logging

Application logs now use `structlog` with context-variable injection.

- Development: human-readable coloured output (default when `APP_ENV != production`).
- Production: one JSON object per line when `APP_ENV=production`.
- Every HTTP request automatically binds `request_id` (UUID) to the log context via middleware.
- Authenticated requests bind `user_id`; workspace-scoped requests bind `workspace_id`.
- Fully compatible with existing `logging.getLogger()` usage throughout the codebase.

### Prometheus + Grafana stack

A ready-to-run observability compose stack is provided in `docker-compose.observability.yml`.

- Prometheus v2.53.0 scrapes `/metrics` every 15 seconds.
- Grafana v11.1.0 with a pre-configured Prometheus datasource and an auto-provisioned dashboard.
- The AutoFlowOps dashboard (uid: `autoflowops-main`) ships with 7 panels: HTTP Request Rate, HTTP Latency P95, HTTP Error Rate (5xx), Job Executions rate, Alerts Created rate, Total Job Executions (stat), and Total Alerts Created (stat).
- Data is persisted in Docker volumes `prometheus_data` and `grafana_data`.
- Three new Makefile targets: `obs-up`, `obs-down`, `obs-logs`.

---

## Upgrade Steps

No database migration is required for this release.

### Pull from registry

```bash
make pull IMAGE_TAG=v1.2.0
make registry-down
make registry-up IMAGE_TAG=v1.2.0
```

### Build from source

```bash
git pull origin main
docker compose up -d --build
```

### Optional: start the observability stack

```bash
# The main stack must be running first
docker compose up -d
make obs-up
```

Grafana is available at `http://localhost:3001` (default credentials: `admin` / `admin`). Change the admin password after first login.

---

## Production Safety Checklist

All items from previous releases apply. Additional considerations for v1.2.0:

- **Workspace membership** — users without a `workspace_memberships` row for a given workspace will receive `403` when that workspace is requested. Ensure all workspace members are recorded in the `workspace_memberships` table before deploying.
- **`NOTIFICATION_ENCRYPTION_KEY` backup** — see `docs/security.md` for the backup and rotation procedure. The key must be available for decryption of existing channel credentials; losing it renders all stored channel configurations unrecoverable.
- **Grafana credentials** — the observability stack defaults to `admin`/`admin`. Set a strong password immediately after first login.

---

## Validation Plan

- Backend lint: `cd backend && ruff check .`
- Backend tests: `cd backend && PYTHONPATH=. pytest` (239 tests)
- Frontend lint: `cd frontend && npm run lint`
- Frontend tests: `cd frontend && npm test`
- Frontend build: `cd frontend && npm run build`
- Full local lint/test: `make lint && make test`
- Local Docker build: `docker compose build`
- Smoke tests: send a request with an unknown `X-Workspace-ID` from a non-member user and verify `403`; start the observability stack and confirm metrics appear in Grafana.

---

## Known Limitations

- Workspace membership enforcement is applied at the API layer. Direct database access is not affected.
- The observability stack requires the main `autoflowops_default` Docker network to exist (created by `docker compose up`). If the project name differs in your deployment, update `networks.autoflowops_default.name` in `docker-compose.observability.yml` or set `COMPOSE_PROJECT_NAME=autoflowops` before starting the main stack.
- Prometheus data retention defaults to 15 days. Adjust `--storage.tsdb.retention.time` in `docker-compose.observability.yml` if longer retention is required.
