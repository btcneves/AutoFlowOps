# Log Aggregation

AutoFlowOps ships structured JSON logs to external aggregation backends.
Two shipping modes are available:

| Mode | How it works | When to use |
|---|---|---|
| **Agent-based (recommended)** | Promtail scrapes Docker container stdout/stderr and pushes to Loki | Standard self-hosted deployments with Docker |
| **Direct push** | The application pushes each log line over HTTP to Loki or Elasticsearch | Kubernetes / cloud environments where a sidecar agent is not available |

Both modes can be active simultaneously.

---

## Label schema

Every log stream carries a consistent set of labels.

### Stream labels (low cardinality — used for stream selection)

| Label | Source | Example values |
|---|---|---|
| `app` | constant | `autoflowops` |
| `service` | compose service name / `LOG_SERVICE_NAME` env var | `backend`, `worker` |
| `env` | `APP_ENV` environment variable | `production`, `development` |
| `level` | structlog `level` field | `info`, `warning`, `error`, `critical` |
| `logger` | structlog `logger` field (module path) | `app.services.notifications` |

### Structured metadata (high cardinality — available for filtering, not for stream selection)

| Field | Description | Emitted when |
|---|---|---|
| `request_id` | Per-request UUID injected by the ASGI middleware | Inside any HTTP request |
| `workspace_id` | Active workspace UUID | After workspace resolution in the auth dependency |
| `user_id` | Authenticated user UUID | After JWT validation |
| `job_id` | Job UUID | Job execution tasks |
| `execution_id` | Execution UUID | Job execution tasks |

High-cardinality fields (`request_id`, `workspace_id`, `user_id`) are **not** promoted to Loki stream labels. They are extracted by the Promtail pipeline as structured metadata and are queryable with LogQL label filters.

---

## Quick start — Loki (agent-based, recommended)

### Prerequisites

- The main AutoFlowOps stack must be running (`make up`)
- Docker socket access for Promtail (`/var/run/docker.sock`)
- The Docker compose project name must be `autoflowops` (the default when the repo directory is `AutoFlowOps`)

### Start

```bash
make obs-up
```

This starts Prometheus, Grafana, Loki, and Promtail in a single overlay network.

| Service | URL | Credentials |
|---|---|---|
| Grafana | http://localhost:3001 | admin / admin |
| Loki API | http://localhost:3100 | — |
| Prometheus | http://localhost:9090 | — |

Grafana is pre-provisioned with both the Prometheus and Loki datasources.

### Stop

```bash
make obs-down
```

### How Promtail works

Promtail connects to the Docker daemon via `/var/run/docker.sock`, discovers containers belonging to the `autoflowops` compose project, and reads their log files from `/var/lib/docker/containers`. It applies the label pipeline defined in `observability/promtail-config.yml` and pushes streams to Loki.

The JSON fields emitted by structlog in `APP_ENV=production` are parsed by the pipeline stage and promoted to structured metadata.

---

## Quick start — Loki (direct push, optional)

For environments without a sidecar agent, the backend can push logs directly to Loki over HTTP.

Set the following environment variables before starting the backend:

```env
LOKI_URL=http://loki:3100
LOG_SERVICE_NAME=backend   # override to "worker" in the worker container
```

The backend attaches a `_LokiHandler` to the root logger.  
Entries are batched (up to 20) and flushed every 2 seconds by a background daemon thread.

> **Note**: Direct push and agent-based scraping can both be active. Loki deduplicates streams by labels + nanosecond timestamp, so no double-counting occurs.

---

## Quick start — Elasticsearch (direct push)

Set the following environment variable before starting the backend:

```env
ELASTICSEARCH_URL=http://es:9200
```

Logs are indexed into daily indices named `autoflowops-YYYY.MM.DD` using the `_bulk` API. The `timestamp` field from structlog is mapped to `@timestamp` (Kibana-compatible).

No Docker Compose configuration is provided for Elasticsearch, as cluster topologies vary significantly. Configure your own cluster and point `ELASTICSEARCH_URL` at it. A typical Filebeat + Logstash pipeline reading from Docker `json-file` logs works equally well without any code changes (structlog already outputs JSON in production).

---

## Example LogQL queries

```logql
# All backend errors in the last hour
{app="autoflowops", service="backend", level="error"}

# Errors from a specific module
{app="autoflowops", level="error", logger="app.services.notifications"}

# Trace a specific request across backend + worker logs
{app="autoflowops"} | json | request_id="550e8400-e29b-41d4-a716-446655440000"

# All logs for a specific workspace
{app="autoflowops"} | json | workspace_id="<uuid>"

# Job execution failures in the last 24h
{app="autoflowops", service="worker", level="error"} |= "job_id"

# Rate of error logs per minute (for alerting)
sum(rate({app="autoflowops", level="error"}[1m]))
```

---

## Environment variable reference

| Variable | Default | Description |
|---|---|---|
| `LOKI_URL` | `` (disabled) | Base URL of Loki instance for direct push |
| `ELASTICSEARCH_URL` | `` (disabled) | Base URL of Elasticsearch cluster for direct push |
| `LOG_SERVICE_NAME` | `backend` | Value of the `service` Loki stream label. Set to `worker` in the Celery worker container |
| `APP_ENV` | `development` | Controls log renderer (JSON in production, coloured console otherwise) and the `env` label |
| `LOG_LEVEL` | `INFO` | Root log level |

---

## Configuring the Promtail compose project filter

If your Docker compose project name differs from `autoflowops` (e.g. you renamed the repository directory), update the filter in `observability/promtail-config.yml`:

```yaml
filters:
  - name: label
    values: ["com.docker.compose.project=<your-project-name>"]
```

The project name is the lowercase directory name where `docker-compose.yml` lives.
Run `docker compose ps` and look at the container names — the prefix before the first `-` is the project name.
