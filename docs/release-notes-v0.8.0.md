# Release Notes — v0.8.0

**Release date:** 2026-05-20

## Overview

v0.8.0 adds real-time push notifications to the AutoFlowOps frontend via a WebSocket event stream. Job executions and new alerts now appear in the UI as they happen, without waiting for the next polling cycle.

All WebSocket events contain only safe, pre-masked data — no credentials, headers or secrets are ever forwarded to browser clients.

---

## What's New

### WebSocket event stream (`GET /ws/events`)

A new WebSocket endpoint accepts JWT-authenticated connections and pushes domain events in real time:

| Event | Trigger |
| --- | --- |
| `execution.started` | An HTTP execution transitions to `running` |
| `execution.completed` | An execution reaches a terminal state (`success`, `failure`, `timeout`) or `retrying` |
| `alert.created` | A job failure creates a new alert |

Authentication uses the existing JWT access token passed as a query parameter (`?token=<JWT>`). The server rejects missing or invalid tokens with WebSocket close code 1008 (Policy Violation). No new credentials or configuration are required.

### Redis Pub/Sub fan-out

The backend starts a long-running asyncio task at startup that subscribes to the `autoflowops:events` Redis channel and fans out messages to all connected WebSocket clients. The task fails gracefully if Redis is unavailable — the WebSocket endpoint still accepts connections and the frontend falls back to polling.

### `useWebSocket` frontend hook

The hook manages the WebSocket lifecycle:

- Automatic reconnect with exponential backoff (max 30s delay)
- Stops reconnecting on authentication failure (code 1008)
- Cleans up on component unmount
- Falls back silently when no access token is present

### `LiveIndicator` component

A small status badge is shown in the top-right area of the Jobs, Executions and Alerts pages:

- **Green pulsing dot** — WebSocket connected, real-time updates active
- **Grey dot** — Connecting…
- **Nothing** — Closed or auth failure (polling still active)

### Pages updated

| Page | Real-time trigger |
| --- | --- |
| Jobs | `execution.completed` — refreshes `last_run_at` |
| Executions | `execution.started`, `execution.completed` |
| Alerts | `alert.created` |

---

## Test Coverage

| Suite | Before | After |
| --- | --- | --- |
| Backend pytest | 209 | 216 (+7) |
| Frontend Vitest | 65 | 75 (+10) |

### New backend tests (`tests/test_ws.py`)

- No token → rejected (code 1008)
- Invalid token → rejected (code 1008)
- JWT for non-existent user → rejected (code 1008)
- Valid admin token → connected message received
- Ping/pong keepalive
- `ConnectionManager.broadcast` delivers to registered connections
- `ConnectionManager` silently removes dead connections

### New frontend tests (`tests/useWebSocket.test.ts`)

- Connection created on mount
- Initial status is `connecting`
- Auth error when no token stored
- Status transitions to `open` on successful connection
- Incoming messages parsed as `WSEvent`
- `pong` and `connected` frames do not update `lastEvent`
- Code 1008 sets `auth_error` and prevents reconnect
- Normal close schedules reconnect
- Socket closed on unmount

---

## Architecture Changes

### New files

| File | Purpose |
| --- | --- |
| `backend/app/services/event_publisher.py` | `publish_event()` (sync) and `publish_event_async()` — write to Redis Pub/Sub channel `autoflowops:events` |
| `backend/app/api/ws.py` | WebSocket endpoint, `ConnectionManager` singleton, `redis_subscriber` background task |
| `backend/tests/test_ws.py` | WS endpoint and connection manager tests |
| `frontend/src/hooks/useWebSocket.ts` | Hook with auto-reconnect and auth-error detection |
| `frontend/src/components/ui/LiveIndicator.tsx` | Connection status badge |
| `frontend/src/tests/useWebSocket.test.ts` | Hook unit tests |

### Modified files

| File | Change |
| --- | --- |
| `backend/app/main.py` | Includes WS router; starts `redis_subscriber` asyncio task in lifespan |
| `backend/app/services/http_runner.py` | Publishes `execution.started`, `execution.completed`, `alert.created` |
| `backend/app/worker/tasks.py` | Publishes `execution.completed` (incl. `retrying`), `alert.created` synchronously |
| `frontend/src/pages/ExecutionsPage.tsx` | Wires `useWebSocket`; invalidates query on exec events |
| `frontend/src/pages/JobsPage.tsx` | Wires `useWebSocket`; invalidates jobs query on completion |
| `frontend/src/pages/AlertsPage.tsx` | Wires `useWebSocket`; invalidates alerts query on new alert |

---

## Known Limitations

- **Token in URL** — The JWT is sent as a query parameter during the WebSocket handshake. Use HTTPS/WSS in production to keep it encrypted in transit. It will appear in server access logs; use short token lifetimes.
- **Single subscriber per replica** — Each backend replica independently subscribes and fans out. In a multi-replica deployment, a client connected to replica A will not receive events published only on replica B's Redis subscriber (but both subscribers connect to the same Redis channel, so this is not an issue in practice — the event is published once and both subscribers relay it).
- **No history replay** — WebSocket clients only receive events that occur after connection; historical executions are loaded via the REST API.
- **No per-user filtering** — All authenticated users receive the same event stream. Fine-grained filtering (e.g. viewer sees only their own job events) is not yet implemented.

---

## Upgrade Steps

No database migration is required. No new environment variables are required.

1. Pull the latest code.
2. Rebuild Docker images: `docker compose up -d --build`
3. Verify the backend log shows:

   ```text
   INFO  app.api.ws  Redis WS subscriber ready on channel autoflowops:events
   ```

4. Open the Jobs, Executions or Alerts page in the browser; the **Live** indicator should appear within a few seconds.
