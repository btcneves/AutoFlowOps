# Observability

AutoFlowOps exposes Prometheus metrics and emits structured (JSON) logs in production. This guide covers the metrics endpoint, the optional Prometheus + Grafana stack, and the structured logging format.

---

## Metrics endpoint

The backend exposes a `/metrics` endpoint in Prometheus text format.

```bash
curl http://localhost:8000/metrics
```

### HTTP metrics (auto-instrumented)

| Metric | Type | Labels |
| --- | --- | --- |
| `http_request_duration_seconds` | Histogram | `handler`, `method`, `status_code` |

Standard Prometheus histogram names apply: `_bucket`, `_count`, `_sum`.

### Business metrics

| Metric | Type | Labels | Description |
| --- | --- | --- | --- |
| `autoflowops_job_executions_total` | Counter | `status`, `trigger_type` | Total job executions by final status (`success`, `failure`, `timeout`) and trigger type (`manual`, `scheduled`) |
| `autoflowops_alerts_created_total` | Counter | `severity` | Total internal alerts created by severity |

---

## Prometheus + Grafana stack

A ready-to-run observability stack is provided in `docker-compose.observability.yml`. It includes Prometheus (scraping the backend) and Grafana (pre-configured datasource and dashboard).

### Prerequisites

The main AutoFlowOps stack must be running first (the observability compose joins the `autoflowops_default` Docker network created by `docker compose up`).

```bash
# Start main stack
docker compose up -d

# Start observability stack
make obs-up
```

### Services

| Service | URL | Default credentials |
| --- | --- | --- |
| Prometheus | <http://localhost:9090> | — |
| Grafana | <http://localhost:3001> | admin / admin |

Change the Grafana admin password after first login.

### Dashboard

The AutoFlowOps dashboard is provisioned automatically and available in Grafana under **Dashboards → AutoFlowOps**. Panels:

| Panel | Query |
| --- | --- |
| HTTP Request Rate | `sum(rate(http_request_duration_seconds_count[5m])) by (handler)` |
| HTTP Latency P95 | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, handler))` |
| HTTP Error Rate (5xx) | `sum(rate(http_request_duration_seconds_count{status_code=~"5.."}[5m]))` |
| Job Executions (rate) | `sum(rate(autoflowops_job_executions_total[5m])) by (status)` |
| Alerts Created (rate) | `sum(rate(autoflowops_alerts_created_total[5m])) by (severity)` |
| Total Job Executions | `sum(autoflowops_job_executions_total)` |
| Total Alerts Created | `sum(autoflowops_alerts_created_total)` |

### Makefile targets

```bash
make obs-up    # Start Prometheus + Grafana in the background
make obs-down  # Stop the observability stack
make obs-logs  # Stream logs
```

### Stopping

```bash
make obs-down
```

Data is persisted in Docker volumes `prometheus_data` and `grafana_data`. To delete data:

```bash
docker compose -f docker-compose.observability.yml down -v
```

---

## Structured logging

### Development

Human-readable coloured output (default when `APP_ENV != production`):

```
2026-05-20T22:00:00Z [info     ] AutoFlowOps started         env=development version=1.2.0
2026-05-20T22:00:01Z [info     ] GET /api/jobs 200           request_id=abc123 user_id=uuid method=GET path=/api/jobs
```

### Production

JSON output, one object per line (when `APP_ENV=production`):

```json
{"timestamp": "2026-05-20T22:00:01Z", "level": "info", "event": "GET /api/jobs 200", "request_id": "abc123", "user_id": "uuid", "workspace_id": "uuid", "method": "GET", "path": "/api/jobs"}
```

### Context fields

Every log line automatically includes:

| Field | Set by | Present when |
| --- | --- | --- |
| `request_id` | Request middleware | Every HTTP request |
| `user_id` | `get_current_user` dependency | Authenticated requests |
| `workspace_id` | `get_active_workspace` dependency | Requests with `X-Workspace-ID` header |

These fields make it straightforward to filter logs by user or workspace in any log aggregation tool (Loki, Elastic, CloudWatch, etc.).

### Shipping logs to Loki

Add a Loki datasource and log shipper (e.g. Promtail or Alloy) pointed at the backend container's stdout. Example Promtail scrape config targeting Docker:

```yaml
scrape_configs:
  - job_name: autoflowops
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
        filters:
          - name: name
            values: [autoflowops-backend]
    relabel_configs:
      - source_labels: [__meta_docker_container_name]
        target_label: container
    pipeline_stages:
      - json:
          expressions:
            level: level
            request_id: request_id
            user_id: user_id
            workspace_id: workspace_id
      - labels:
          level:
          request_id:
          user_id:
          workspace_id:
```

---

## Production deployment

For VPS deployments using `docker-compose.prod.yml`, the network name may differ. Check the network created by your production stack:

```bash
docker network ls | grep autoflowops
```

Update the `networks.autoflowops_default.name` value in `docker-compose.observability.yml` if needed, or set `COMPOSE_PROJECT_NAME=autoflowops` before starting the main stack.
