# API Reference

Base URL in local development: `http://localhost:8000/api`

Interactive documentation is also available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

All examples assume the backend is running via `make up` or `uvicorn app.main:app --reload`. Routes other than `/api/health`, `/api/version`, `/api/auth/login` and webhook receive require a JWT Bearer token; examples omit the `Authorization` header for brevity unless authentication is the focus.

---

## Health

### GET /api/health

Returns the backend health status.

```bash
curl http://localhost:8000/api/health
```

Response `200 OK`:

```json
{
  "status": "ok",
  "app": "AutoFlowOps",
  "env": "development",
  "database": "ok"
}
```

### GET /api/version

Returns the current application version.

```bash
curl http://localhost:8000/api/version
```

Response `200 OK`:

```json
{
  "version": "0.5.0",
  "app": "AutoFlowOps"
}
```

---

## Stats

### GET /api/stats

Returns dashboard metrics.

```bash
curl http://localhost:8000/api/stats
```

Response `200 OK`:

```json
{
  "total_jobs": 5,
  "active_jobs": 3,
  "paused_jobs": 1,
  "total_executions": 142,
  "executions_24h": 18,
  "failures_24h": 2,
  "success_rate_24h": 88.9,
  "daily_stats": [
    { "date": "2026-05-13", "success": 12, "failure": 1 },
    { "date": "2026-05-14", "success": 15, "failure": 0 }
  ]
}
```

`daily_stats` contains the last 7 days grouped by date. `success_rate_24h` is `null` when there are no executions in the last 24 hours.

---

## Jobs

### GET /api/jobs

List all jobs.

```bash
curl http://localhost:8000/api/jobs
```

Response `200 OK` — array of job objects:

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Health check",
    "method": "GET",
    "url": "https://httpbin.org/status/200",
    "schedule_type": "interval",
    "schedule_expression": "300",
    "status": "active",
    "timeout_seconds": 30,
    "last_run_at": "2026-05-19T10:00:00Z",
    "next_run_at": "2026-05-19T10:05:00Z",
    "created_at": "2026-05-18T08:00:00Z",
    "updated_at": "2026-05-19T10:00:00Z"
  }
]
```

### POST /api/jobs

Create a new HTTP job.

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Health check",
    "method": "GET",
    "url": "https://httpbin.org/status/200",
    "schedule_type": "interval",
    "schedule_expression": "300",
    "timeout_seconds": 30
  }'
```

Request body fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | string | Yes | Human-readable job name |
| `method` | string | Yes | HTTP method: `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `url` | string | Yes | Target URL |
| `schedule_type` | string | Yes | `manual`, `interval` or `cron` |
| `schedule_expression` | string | No | Seconds (interval) or crontab (cron) |
| `headers` | object | No | Request headers (sensitive values masked before storage) |
| `body` | string | No | Request body (sensitive fields masked before storage) |
| `timeout_seconds` | integer | No | Default: 30 |
| `description` | string | No | Free-text description |

Response `201 Created` — the created job object.

### GET /api/jobs/{job_id}

Get a single job by ID.

```bash
curl http://localhost:8000/api/jobs/550e8400-e29b-41d4-a716-446655440000
```

Response `200 OK` — job object. `404` if not found.

### PATCH /api/jobs/{job_id}

Update job fields. Only provided fields are changed.

```bash
curl -X PATCH http://localhost:8000/api/jobs/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{"status": "paused"}'
```

Response `200 OK` — updated job object.

### DELETE /api/jobs/{job_id}

Delete a job and remove it from the scheduler.

```bash
curl -X DELETE http://localhost:8000/api/jobs/550e8400-e29b-41d4-a716-446655440000
```

Response `204 No Content`.

### POST /api/jobs/{job_id}/run

Queue a manual execution immediately.

```bash
curl -X POST http://localhost:8000/api/jobs/550e8400-e29b-41d4-a716-446655440000/run
```

Response `202 Accepted`:

```json
{
  "id": "661e8400-e29b-41d4-a716-446655440001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "trigger_type": "manual",
  "status": "queued",
  "duration_ms": null,
  "response_status_code": null
}
```

The worker updates the same execution to `running`, then to `success`, `failure` or `timeout`. If retries are configured and an attempt fails, the execution is marked `retrying` until the next attempt starts. Alerts are created only after the final failed or timed-out attempt.

---

## Webhooks

### GET /api/webhooks

List all webhooks.

```bash
curl http://localhost:8000/api/webhooks
```

Response `200 OK` — array of webhook objects:

```json
[
  {
    "id": "aaaa-1111-...",
    "name": "Order Events",
    "slug": "order-events",
    "status": "active",
    "last_received_at": "2026-05-19T12:30:00Z",
    "created_at": "2026-05-18T09:00:00Z",
    "updated_at": "2026-05-18T09:00:00Z"
  }
]
```

### POST /api/webhooks

Create a new webhook endpoint.

```bash
curl -X POST http://localhost:8000/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Order Events",
    "slug": "order-events",
    "secret_token": "my-secret-token"
  }'
```

Request body fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | string | Yes | Human-readable name |
| `slug` | string | Yes | URL-safe identifier, unique across all webhooks |
| `secret_token` | string | Yes | Token senders must include in `X-Webhook-Token`; stored as a SHA-256 hash |

Response `201 Created` — the created webhook object. `409 Conflict` if slug already exists.

### GET /api/webhooks/{webhook_id}

Get a single webhook by ID.

Response `200 OK` — webhook object. `404` if not found.

### PATCH /api/webhooks/{webhook_id}

Update webhook fields.

```bash
curl -X PATCH http://localhost:8000/api/webhooks/aaaa-1111-... \
  -H "Content-Type: application/json" \
  -d '{"status": "paused"}'
```

Response `200 OK` — updated webhook object.

### DELETE /api/webhooks/{webhook_id}

Delete a webhook and its events.

Response `204 No Content`.

### POST /api/webhooks/{slug}/receive

Receive an inbound event from an external system.

```bash
curl -X POST http://localhost:8000/api/webhooks/order-events/receive \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: my-secret-token" \
  -d '{"event": "order.created", "order_id": "1001"}'
```

| Status code | Reason |
| --- | --- |
| `200 OK` | Event accepted and stored |
| `403 Forbidden` | Invalid token or webhook is paused |
| `404 Not Found` | No webhook with this slug |

Response `200 OK`:

```json
{
  "event_id": "bbbb-2222-...",
  "status": "received"
}
```

### GET /api/webhooks/{webhook_id}/events

List received events for a webhook.

```bash
curl http://localhost:8000/api/webhooks/aaaa-1111-.../events
```

Response `200 OK` — array of event objects including `headers_masked`, `payload`, `source_ip`, `received_at` and `status`.

### POST /api/webhooks/{webhook_id}/events/{event_id}/reprocess

Replay a stored event through the pipeline without re-validating the token.

```bash
curl -X POST http://localhost:8000/api/webhooks/aaaa-1111-.../events/bbbb-2222-.../reprocess
```

Response `200 OK` — updated event object with `status: "reprocessed"`. `404` if webhook or event not found.

---

## Alerts

### GET /api/alerts

List all alerts, optionally filtered by status.

```bash
# All alerts
curl http://localhost:8000/api/alerts

# Open alerts only
curl "http://localhost:8000/api/alerts?status=open"

# Acknowledged alerts
curl "http://localhost:8000/api/alerts?status=acknowledged"

# Resolved alerts
curl "http://localhost:8000/api/alerts?status=resolved"
```

Response `200 OK` — array of alert objects:

```json
[
  {
    "id": "cccc-3333-...",
    "title": "Job 'Health check' failed",
    "message": "HTTP 503",
    "severity": "error",
    "source_type": "job_execution",
    "source_id": "661e8400-...",
    "status": "open",
    "created_at": "2026-05-19T10:05:30Z",
    "acknowledged_at": null,
    "resolved_at": null
  }
]
```

### PATCH /api/alerts/{alert_id}/acknowledge

Mark an alert as acknowledged.

```bash
curl -X PATCH http://localhost:8000/api/alerts/cccc-3333-.../acknowledge
```

Response `200 OK` — updated alert object with `status: "acknowledged"` and `acknowledged_at` set. `409` if already resolved. `404` if not found.

### PATCH /api/alerts/{alert_id}/resolve

Mark an alert as resolved.

```bash
curl -X PATCH http://localhost:8000/api/alerts/cccc-3333-.../resolve
```

Response `200 OK` — updated alert object with `status: "resolved"` and `resolved_at` set. `409` if already resolved. `404` if not found.

---

## Notification Channels

Notification channel routes are protected. Channel configuration is returned only
as `config_masked`; full webhook URLs, SMTP passwords and sensitive headers are
not returned by the API.

### GET /api/notification-channels

List configured notification channels.

```bash
curl http://localhost:8000/api/notification-channels
```

Response `200 OK`:

```json
[
  {
    "id": "eeee-5555-...",
    "name": "Ops Discord",
    "type": "discord_webhook",
    "status": "active",
    "config_masked": {
      "webhook_url": "https://discord.com/***"
    },
    "created_at": "2026-05-20T10:00:00Z",
    "updated_at": "2026-05-20T10:00:00Z",
    "last_tested_at": null
  }
]
```

### POST /api/notification-channels

Create a channel. Supported `type` values are `discord_webhook`,
`smtp_email` and `custom_webhook`.

Discord webhook:

```json
{
  "name": "Ops Discord",
  "type": "discord_webhook",
  "config": {
    "webhook_url": "https://discord.com/api/webhooks/..."
  }
}
```

SMTP email:

```json
{
  "name": "Ops Email",
  "type": "smtp_email",
  "config": {
    "host": "smtp.example.com",
    "port": 587,
    "username": "alerts@example.com",
    "password": "REPLACE_WITH_SMTP_PASSWORD",
    "from_email": "alerts@example.com",
    "to_email": "ops@example.com",
    "use_tls": true,
    "use_ssl": false
  }
}
```

Custom webhook:

```json
{
  "name": "Ops Webhook",
  "type": "custom_webhook",
  "config": {
    "url": "https://hooks.example.com/autoflowops",
    "headers": {
      "Authorization": "Bearer REPLACE_WITH_TOKEN"
    }
  }
}
```

Response `201 Created` — created channel with masked configuration.

### PATCH /api/notification-channels/{channel_id}

Update name, status or configuration. Changing `type` requires a replacement
`config` object.

### PATCH /api/notification-channels/{channel_id}/activate

Set channel status to `active`.

### PATCH /api/notification-channels/{channel_id}/deactivate

Set channel status to `paused`.

### POST /api/notification-channels/{channel_id}/test

Send a sample notification and record a delivery result.

Response `200 OK`:

```json
{
  "channel": {
    "id": "eeee-5555-...",
    "name": "Ops Discord",
    "type": "discord_webhook",
    "status": "active",
    "config_masked": {
      "webhook_url": "https://discord.com/***"
    },
    "created_at": "2026-05-20T10:00:00Z",
    "updated_at": "2026-05-20T10:00:00Z",
    "last_tested_at": "2026-05-20T10:05:00Z"
  },
  "delivery": {
    "id": "ffff-6666-...",
    "alert_id": null,
    "channel_id": "eeee-5555-...",
    "channel_name": "Ops Discord",
    "channel_type": "discord_webhook",
    "status": "success",
    "error_message": null,
    "sent_at": "2026-05-20T10:05:00Z",
    "created_at": "2026-05-20T10:05:00Z"
  }
}
```

### GET /api/notification-channels/deliveries

List recent notification delivery records.

### DELETE /api/notification-channels/{channel_id}

Delete a channel. Existing delivery records keep the channel name and type.

---

## Reports

### GET /api/reports

List all generated reports (metadata only, no content).

```bash
curl http://localhost:8000/api/reports
```

Response `200 OK` — array of report summary objects:

```json
[
  {
    "id": "dddd-4444-...",
    "name": "Last 7 days",
    "format": "json",
    "period_start": "2026-05-12T00:00:00Z",
    "period_end": "2026-05-19T23:59:59Z",
    "created_at": "2026-05-19T11:00:00Z",
    "created_by": null
  }
]
```

### POST /api/reports/generate

Generate a new operational report for a given period.

```bash
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Last 7 days",
    "period_start": "2026-05-12T00:00:00Z",
    "period_end": "2026-05-19T23:59:59Z"
  }'
```

Request body fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | string | Yes | Human-readable report name |
| `period_start` | datetime | Yes | ISO 8601 UTC datetime (start of period, inclusive) |
| `period_end` | datetime | Yes | ISO 8601 UTC datetime (end of period, inclusive) |

The report is computed from live DB data and saved as canonical JSON. Response `201 Created` — the created report metadata object. `422` if `period_start > period_end`.

### GET /api/reports/{report_id}

Get a single report including its full canonical JSON content.

```bash
curl http://localhost:8000/api/reports/dddd-4444-...
```

Response `200 OK` — report metadata plus `content` field containing the full JSON payload.

### GET /api/reports/{report_id}/download

Download a report in the requested format.

```bash
# JSON download
curl -OJ "http://localhost:8000/api/reports/dddd-4444-.../download?format=json"

# Markdown download
curl -OJ "http://localhost:8000/api/reports/dddd-4444-.../download?format=markdown"

# CSV download
curl -OJ "http://localhost:8000/api/reports/dddd-4444-.../download?format=csv"
```

Supported `format` values: `json`, `markdown`, `csv`.

Downloads are derived from the saved canonical JSON — historical reports are stable and do not change after generation. `404` if report not found. `422` if format is invalid.

---

## Users

All endpoints require admin role.

### GET /api/users

Returns all user accounts.

```bash
curl http://localhost:8000/api/users \
  -H "Authorization: Bearer <token>"
```

Response `200 OK` (array of user objects):

```json
[
  {
    "id": "aaaa-1111-...",
    "email": "admin@example.com",
    "name": "Admin",
    "role": "admin",
    "is_active": true,
    "created_at": "2026-05-20T10:00:00Z",
    "updated_at": "2026-05-20T10:00:00Z",
    "last_login_at": "2026-05-20T11:00:00Z"
  }
]
```

`password_hash` is never included in any user response.

### POST /api/users

Creates a new user account.

```bash
curl -X POST http://localhost:8000/api/users \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"email": "ops@example.com", "name": "Ops User", "password": "changeme", "role": "operator"}'
```

Request body:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `email` | string | Yes | Unique email address |
| `name` | string | Yes | Display name |
| `password` | string | Yes | Plain password (bcrypt-hashed on write) |
| `role` | string | No | `admin`, `operator` or `viewer` (default: `viewer`) |

Response `201 Created`: the created user object.

`409 Conflict` if the email address is already registered. `400` if the role value is invalid.

### PATCH /api/users/{id}

Updates a user's role, active status or name. Admin-only.

```bash
curl -X PATCH http://localhost:8000/api/users/aaaa-1111-... \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "viewer", "is_active": false}'
```

Request body (all fields optional):

| Field | Type | Description |
| --- | --- | --- |
| `name` | string | New display name |
| `role` | string | `admin`, `operator` or `viewer` |
| `is_active` | boolean | Activate or deactivate the account |

`400` if the operation would leave zero active admin accounts.

### POST /api/users/{id}/reset-password

Sets a new password for a user. Admin-only.

```bash
curl -X POST http://localhost:8000/api/users/aaaa-1111-.../reset-password \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "new-secure-pw"}'
```

Response `200 OK`:

```json
{"ok": true}
```

### DELETE /api/users/{id}

Deletes a user account. Admin-only.

```bash
curl -X DELETE http://localhost:8000/api/users/aaaa-1111-... \
  -H "Authorization: Bearer <token>"
```

Response `204 No Content`.

`400` if the operation would delete the last active admin account.

---

## Audit Logs

All endpoints require admin role.

### GET /api/audit-logs

Returns audit log entries, newest first.

```bash
curl "http://localhost:8000/api/audit-logs?action=job.create&limit=50" \
  -H "Authorization: Bearer <token>"
```

Query parameters (all optional):

| Parameter | Type | Description |
| --- | --- | --- |
| `user_id` | UUID | Filter by actor |
| `action` | string | Filter by action string (exact match) |
| `resource_type` | string | Filter by resource type |
| `status` | string | `success` or `failure` |
| `since` | ISO 8601 datetime | Entries created at or after this timestamp |
| `until` | ISO 8601 datetime | Entries created before or at this timestamp |
| `limit` | integer | Maximum results (default: 100, max: 1000) |

Response `200 OK`:

```json
[
  {
    "id": "bbbb-2222-...",
    "user_id": "aaaa-1111-...",
    "action": "job.create",
    "resource_type": "job",
    "resource_id": "cccc-3333-...",
    "status": "success",
    "ip_address": "192.0.2.1",
    "user_agent": "Mozilla/5.0 ...",
    "metadata_": {"name": "My Job"},
    "created_at": "2026-05-20T10:05:00Z"
  }
]
```

Sensitive metadata fields (`password`, `token`, `api_key`, etc.) are replaced with `"[redacted]"` and never returned in responses.

---

## WebSocket — Real-Time Events

### `GET /ws/events`

Upgrades to a WebSocket connection and streams domain events as JSON frames.

**Authentication** — pass the JWT as a query parameter (HTTP headers are not supported in browser WebSocket APIs):

```text
ws://localhost:8000/ws/events?token=<access_token>
```

Use `wss://` in any deployment with TLS (see Security notes).

### Connection lifecycle

1. Server accepts the connection.
2. Token is validated: if missing, malformed or the user does not exist, the server sends an error frame and closes with code 1008 (Policy Violation).
3. On success the server sends a `connected` frame:

```json
{"type": "connected", "data": {"user": "admin@example.com"}}
```

4. The server pushes events asynchronously. The client may send `"ping"` to receive `{"type": "pong"}`.
5. The connection remains open until the client closes it or the server restarts.

### Event types

| Type | Trigger |
| --- | --- |
| `execution.started` | HTTP runner transitions execution to `running` |
| `execution.completed` | Execution reaches a terminal state (`success`, `failure`, `timeout`) or `retrying` |
| `alert.created` | A new alert is created by job failure |

### `execution.started` frame

```json
{
  "type": "execution.started",
  "data": {
    "execution_id": "uuid",
    "job_id": "uuid",
    "job_name": "My Job",
    "trigger_type": "manual",
    "status": "running"
  },
  "ts": "2026-05-20T10:00:00.123456+00:00"
}
```

### `execution.completed` frame

```json
{
  "type": "execution.completed",
  "data": {
    "execution_id": "uuid",
    "job_id": "uuid",
    "job_name": "My Job",
    "status": "success",
    "duration_ms": 312,
    "response_status_code": 200,
    "trigger_type": "scheduled"
  },
  "ts": "2026-05-20T10:00:00.456789+00:00"
}
```

### `alert.created` frame

```json
{
  "type": "alert.created",
  "data": {
    "alert_id": "uuid",
    "title": "Job \"My Job\" failed",
    "severity": "error",
    "status": "open",
    "source_type": "job_execution"
  },
  "ts": "2026-05-20T10:00:00.789012+00:00"
}
```

### Close codes

| Code | Meaning |
| --- | --- |
| `1000` | Normal closure initiated by client |
| `1008` | Policy Violation — authentication failed (missing token, invalid JWT, inactive user) |

**Fallback:** If the WebSocket is unavailable or Redis is not running, the frontend falls back to TanStack Query polling (30s interval on executions, jobs and alerts pages).

---

## Error Responses

| Status | Condition |
| --- | --- |
| `400 Bad Request` | Last-admin protection triggered; invalid role value |
| `401 Unauthorized` | Missing or invalid JWT token |
| `403 Forbidden` | Insufficient role; invalid webhook token; paused webhook |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | Duplicate webhook slug; alert already resolved; duplicate email |
| `422 Unprocessable Entity` | Invalid request body, invalid report format or `period_start > period_end` |
