# Examples

Practical usage examples for AutoFlowOps.

## Runnable API Recipes

Start the stack first:

```bash
make up
```

### Create and run an HTTP job

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "HTTP 200 check",
    "method": "GET",
    "url": "https://httpbin.org/status/200",
    "schedule_type": "manual"
  }'
```

Use the returned `id` to run it manually:

```bash
curl -X POST http://localhost:8000/api/jobs/<job-id>/run
```

### Create and call a webhook

```bash
curl -X POST http://localhost:8000/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{"name": "Order Events", "slug": "order-events", "secret_token": "demo-token"}'

curl -X POST http://localhost:8000/api/webhooks/order-events/receive \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: demo-token" \
  -d '{"event": "order.created", "order_id": "1001"}'
```

### Generate an operational report

```bash
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Last 7 days",
    "period_start": "2026-05-12T00:00:00Z",
    "period_end": "2026-05-19T23:59:59Z"
  }'
```

Download the generated report:

```bash
curl -L "http://localhost:8000/api/reports/<report-id>/download?format=markdown"
```

More example folders can be added later for integrations that need external services.
