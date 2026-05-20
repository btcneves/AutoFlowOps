# Release Notes — AutoFlowOps v0.4.0

**Release date:** 2026-05-20

---

## Summary

AutoFlowOps v0.4.0 separates job execution from the API process. Manual and scheduled HTTP jobs are now queued in Redis and executed by a dedicated Celery worker, improving reliability and preparing the platform for heavier self-hosted workloads.

---

## Main Features

### Celery Worker

- New worker process runs HTTP job executions outside FastAPI
- Worker reuses the existing HTTP runner, SSRF protection, masking, timeout handling and alert creation
- Final failures and timeouts still create internal alerts

### Redis Queue

- Redis is configured as Celery broker and result backend via `REDIS_URL`
- Development and production Compose files include Redis and worker services
- Redis remains internal in production and is not published to the host

### Queued Execution Flow

- Manual runs now create an execution with `status: "queued"` and return immediately
- APScheduler still owns schedule timing but dispatches scheduled work to the queue
- Worker updates the same execution through `running`, `retrying`, `success`, `failure` or `timeout`

### Retry Preparation

- Existing `retry_count` and `retry_delay_seconds` job fields now drive Celery retries
- Failed or timed-out attempts move to `retrying` until attempts are exhausted
- Alerts are created only after the final failed attempt

---

## Upgrade Notes

1. Rebuild containers so the backend image includes Celery and Redis dependencies.
2. Ensure `REDIS_URL=redis://redis:6379/0` is present in `.env` or `.env.production`.
3. Start the full stack with `docker compose up --build` or `make prod-up`.
4. Verify backend, Redis and worker containers are healthy.
5. Trigger a manual job and confirm the execution appears first as `queued`, then as a terminal status.

No database migration is required. The existing `executions.status` string column stores the new queue statuses.

---

## Known Limitations

- APScheduler still runs in the API process and should be kept to one API replica.
- Redis-backed rate limiting is not implemented; webhook rate limiting remains in-memory per API process.
- The frontend shows queue statuses but does not yet expose detailed retry history.
- Published container images remain future work.
