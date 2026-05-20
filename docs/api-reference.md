# API Reference

Base URL in local development: `http://localhost:8000/api`

Interactive documentation is also available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

The MVP does not require authentication. All examples assume the backend is running via `make up` or `uvicorn app.main:app --reload`.

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
  "env": "development"
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
  "version": "0.1.0",
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

Trigger a manual execution immediately.

```bash
curl -X POST http://localhost:8000/api/jobs/550e8400-e29b-41d4-a716-446655440000/run
```

Response `202 Accepted`:

```json
{
  "execution_id": "661e8400-e29b-41d4-a716-446655440001",
  "status": "success",
  "duration_ms": 243,
  "response_status_code": 200
}
```

If the target responds with an error status or the request fails, the execution is saved with `status: "failure"` and an alert is created.

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

## Error Responses

| Status | Condition |
| --- | --- |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | Duplicate webhook slug; alert already resolved |
| `422 Unprocessable Entity` | Invalid request body, invalid report format or `period_start > period_end` |
| `403 Forbidden` | Invalid webhook token or paused webhook |
