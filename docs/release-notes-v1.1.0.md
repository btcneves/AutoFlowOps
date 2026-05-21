# Release Notes — v1.1.0

**Release date:** 2026-05-20

## Overview

v1.1.0 extends the AutoFlowOps platform with two new notification providers (PagerDuty and OpsGenie), PDF export for operational reports, and multi-workspace support for namespace isolation within a single instance.

All changes are backward-compatible. Existing deployments without the `X-Workspace-ID` header continue to operate exactly as before.

---

## What's New

### PagerDuty notification channel

A new `pagerduty` channel type integrates with the PagerDuty Events API v2.

- `routing_key` is the only required credential; encrypted at rest using the existing Fernet mechanism.
- Alerts dispatch a `trigger` event with severity mapped from the internal alert severity.
- The `routing_key` is masked in all API responses and delivery error records.
- The channel can be tested via `POST /api/notification-channels/{id}/test`.

### OpsGenie notification channel

A new `opsgenie` channel type integrates with the OpsGenie Alerts API.

- Supports US (`api.opsgenie.com`) and EU (`api.eu.opsgenie.com`) regions via a `region` field (`us` by default).
- `api_key` is the required credential; encrypted at rest and masked in API responses.
- Optional `responders` list accepts any structure supported by the OpsGenie API (teams, users, escalations, schedules).
- The channel can be tested via `POST /api/notification-channels/{id}/test`.

### PDF report export

Operational reports can now be downloaded as PDF in addition to JSON, Markdown and CSV.

- Endpoint: `GET /api/reports/{id}/download?format=pdf`
- Generated with `reportlab` (pure-Python, no OS-level dependencies).
- PDF sections: title, period, summary metrics, top failed jobs, alerts, recommendations.
- The `ReportFormat` type in the frontend now includes `pdf`; the Reports page exposes a PDF download button alongside the existing format options.

### Multi-workspace

Resources can now be scoped to a workspace using the `X-Workspace-ID` request header.

- New tables: `workspaces`, `workspace_memberships`.
- A default workspace (`Default` / slug `default`) is created automatically on first startup.
- All domain resources (jobs, executions, alerts, webhooks, notification channels, notification templates, escalation policies, reports) accept the header and filter results accordingly.
- When the header is absent, no filtering is applied — full backward compatibility.
- Workspace CRUD: `GET /api/workspaces`, `POST /api/workspaces`, `PATCH /api/workspaces/{id}`, `DELETE /api/workspaces/{id}` (admin-only for write operations).
- Member management: `GET /api/workspaces/{id}/members`, `POST /api/workspaces/{id}/members`, `DELETE /api/workspaces/{id}/members/{user_id}`.
- The default workspace cannot be deleted.
- Frontend workspace selector in the sidebar persists the active workspace to `localStorage` and injects the `X-Workspace-ID` header into all API requests.
- Admin-only Workspaces settings page at `/workspaces`.

---

## Upgrade Steps

A database migration is required to add the `workspaces` and `workspace_memberships` tables and the `workspace_id` column to domain tables.

### Pull from registry

```bash
make pull IMAGE_TAG=v1.1.0
make registry-down
make registry-up IMAGE_TAG=v1.1.0
```

### Build from source

```bash
git pull origin main
docker compose up -d --build
```

The backend applies `Base.metadata.create_all` on startup, which creates new tables automatically in development environments using SQLite or a fresh PostgreSQL instance. For production environments with existing data, run the Alembic migration:

```bash
docker compose exec backend alembic upgrade head
```

---

## Production Safety Checklist

All items from v1.0.0 apply. Additional considerations for v1.1.0:

- **PagerDuty/OpsGenie credentials** — `routing_key` and `api_key` are encrypted at rest. Ensure `NOTIFICATION_ENCRYPTION_KEY` is set and backed up before adding channels.
- **Workspace isolation** — the `X-Workspace-ID` header is trusted as sent by the client; it is not a security boundary. Do not rely on workspace filtering as an access control mechanism. Use RBAC roles for access control.
- **Default workspace** — all resources created before v1.1.0 have `workspace_id = NULL`. They remain visible when no workspace header is sent. Assign them to workspaces explicitly if namespace isolation is required.

---

## Validation Plan

- Backend lint: `cd backend && ruff check .`
- Backend tests: `cd backend && PYTHONPATH=. pytest`
- Frontend lint: `cd frontend && npm run lint`
- Frontend tests: `cd frontend && npm test`
- Frontend build: `cd frontend && npm run build`
- Full local lint/test: `make lint && make test`
- Local Docker build: `docker compose build`
- Smoke tests: create PagerDuty and OpsGenie channels, run channel test, generate a report and download as PDF, create a workspace, set `X-Workspace-ID` header and verify filtered responses.

---

## Known Limitations

- PagerDuty and OpsGenie channel tests require valid credentials; the test endpoint will return a delivery failure for placeholder keys.
- PDF generation uses `reportlab`; the package is included in `pyproject.toml` but must be present in the deployment image. The standard GHCR images built from this release include it.
- Workspace filtering is applied at query time per request. Resources without a `workspace_id` (created before v1.1.0) are only visible when no `X-Workspace-ID` header is sent.
- Workspace isolation does not enforce data access control; it is a convenience filter. RBAC remains the access control mechanism.
