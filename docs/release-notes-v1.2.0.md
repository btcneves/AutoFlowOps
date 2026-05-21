# Release Notes — v1.2.0

**Release date:** 2026-05-20

## Overview

v1.2.0 introduces conditional alert rules for per-job operational thresholds, hardens workspace isolation on resource-specific endpoints and notification dispatch, expands the deployment documentation for the notification encryption key, and ships a production-ready observability stack (Prometheus metrics, structured JSON logging, and an optional Prometheus + Grafana compose stack with a pre-built dashboard).

All changes are backward-compatible. Deployments that do not use the `X-Workspace-ID` header are unaffected by the membership enforcement.

---

## What's New

### Conditional alert rules

Jobs can now define enabled/disabled alert rules that create internal alerts from:

- HTTP status thresholds (`http_status_gte`)
- Execution duration thresholds (`duration_ms_gte`)
- Response body text matches (`response_body_contains`)
- Consecutive failure counts (`consecutive_failures_gte`)

Rules are managed through `GET`, `POST`, `PATCH` and `DELETE /api/jobs/{job_id}/alert-rules`, and the job detail page includes a rules section for operators and admins. The Celery worker evaluates these rules after final retry handling so queued/scheduled jobs behave the same as inline executions.

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

### Log aggregation

Structured logs can now be shipped directly to Loki or Elasticsearch in addition to printing to stdout.

- `LOG_SINK` selects the active shipping mode: `stdout` (default), `loki`, `elasticsearch`, or a comma-separated combination for dual shipping.
- `LOKI_URL` and `ELASTICSEARCH_URL` configure target endpoints for direct-push mode.
- `docker-compose.observability.yml` updated with a Loki + Promtail stack for agent-based log collection from Docker container stdout — the recommended mode for standard self-hosted deployments.
- All log streams carry a consistent label schema (`app`, `service`, `env`, `level`, `logger`) plus structured metadata fields (`job_id`, `execution_id`, `workspace_id`, `request_id`).
- Direct-push and agent-based modes can be active simultaneously.
- Full configuration reference and local setup instructions in `docs/log-aggregation.md`.

### Notification provider extensions

PagerDuty and OpsGenie delivery now supports additional provider-specific fields.

- `dedup_key` on PagerDuty channels for alert deduplication across the Events API v2 lifecycle.
- `priority` on OpsGenie channels (`P1`–`P5`) for routing to on-call schedules by severity.
- `payload_template` on both channel types for fully custom JSON payloads when the built-in format does not match provider expectations.

### Prometheus + Grafana stack

A ready-to-run observability compose stack is provided in `docker-compose.observability.yml`.

- Prometheus v2.53.0 scrapes `/metrics` every 15 seconds.
- Grafana v11.1.0 with a pre-configured Prometheus datasource and an auto-provisioned dashboard.
- The AutoFlowOps dashboard (uid: `autoflowops-main`) ships with 7 panels: HTTP Request Rate, HTTP Latency P95, HTTP Error Rate (5xx), Job Executions rate, Alerts Created rate, Total Job Executions (stat), and Total Alerts Created (stat).
- Data is persisted in Docker volumes `prometheus_data` and `grafana_data`.
- Three new Makefile targets: `obs-up`, `obs-down`, `obs-logs`.

---

## Upgrade Steps

Run the database migration included in this release. It creates the `alert_rules` table.

```bash
cd backend
alembic upgrade head
```

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
- Backend tests: `cd backend && PYTHONPATH=. pytest` (260 tests)
- Frontend lint: `cd frontend && npm run lint`
- Frontend tests: `cd frontend && npm test` (76 tests)
- Frontend build: `cd frontend && npm run build`
- Full local lint/test: `make lint && make test`
- Local Docker build: `docker compose build`
- Smoke tests: send a request with an unknown `X-Workspace-ID` from a non-member user and verify `403`; start the observability stack and confirm metrics appear in Grafana.

---

## Known Limitations

- Workspace membership enforcement is applied at the API layer. Direct database access is not affected.
- The observability stack requires the main `autoflowops_default` Docker network to exist (created by `docker compose up`). If the project name differs in your deployment, update `networks.autoflowops_default.name` in `docker-compose.observability.yml` or set `COMPOSE_PROJECT_NAME=autoflowops` before starting the main stack.
- Prometheus data retention defaults to 15 days. Adjust `--storage.tsdb.retention.time` in `docker-compose.observability.yml` if longer retention is required.
