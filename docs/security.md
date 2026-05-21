# Security

This document describes the security practices built into AutoFlowOps, the known limitations of the current MVP, and recommendations for production deployments.

---

## Secret Masking

AutoFlowOps masks sensitive data before writing execution records or webhook events to the database. **Secrets are never stored in plain text in logs or execution history.**

### HTTP Headers Masked

Any request header whose name contains one of the following patterns is masked (case-insensitive):

- `authorization`
- `x-api-key`
- `api-key`
- `token`
- `secret`
- `password`
- `cookie`
- `set-cookie`

Stored value example:

```json
{
  "Authorization": "Bearer ***MASKED***",
  "Content-Type": "application/json"
}
```

### JSON Body Fields Masked

Any JSON body field whose key contains one of the following patterns is masked recursively (including nested objects):

- `password`, `passwd`, `pwd`
- `token`, `access_token`, `refresh_token`
- `secret`
- `api_key`, `apikey`
- `private_key`
- `authorization`
- `credential`

Non-JSON bodies (plain text, binary, form data) are stored as-is. Validate that non-JSON job bodies do not contain secrets before configuring a job.

### Masking is tested

The masking service (`backend/app/services/masking.py`) has a dedicated test suite (`backend/tests/test_masking.py`) with 11 tests covering headers, nested JSON, non-JSON bodies and edge cases.

---

## Webhook Token Security

- Each webhook endpoint requires a `secret_token` at creation time.
- The token is **never stored in plain text**. Only its SHA-256 hash is persisted in the database.
- Inbound requests must include the token in the `X-Webhook-Token` header. Requests with a missing or incorrect token receive `403 Forbidden`.
- Paused webhooks reject all inbound requests regardless of the token.

---

## Environment File Security

- `.env` is listed in `.gitignore` and must **never be committed to version control**.
- Only `.env.example` is committed. It contains only fictional placeholder values — no real secrets.
- Before deploying to production, copy `.env.example` to `.env` and set strong unique values for:
  - `APP_SECRET_KEY`
  - `JWT_SECRET_KEY`
  - The database credentials in `DATABASE_URL`
- Never share your `.env` file publicly or include it in Docker images.

---

## SSRF Protection (v0.2.0)

HTTP jobs execute arbitrary URLs configured by the operator. To prevent jobs from
targeting internal services, AutoFlowOps blocks requests to private and reserved
address ranges when `ENABLE_SSRF_PROTECTION=true` (the default).

Blocked ranges:

- `127.0.0.0/8` — loopback
- `0.0.0.0/8` — unspecified
- `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` — RFC-1918 private
- `169.254.0.0/16` — link-local (including cloud metadata endpoints)
- `100.64.0.0/10` — shared address space
- `::1/128`, `fc00::/7`, `fe80::/10` — IPv6 equivalents

The check is applied both to literal IP addresses and after DNS resolution, to
prevent bypass via custom DNS records.

Set `ALLOW_PRIVATE_NETWORK_TARGETS=true` only in controlled local development
environments where you intentionally need to call internal services.

---

## Rate Limiting (v0.2.0)

The webhook receiver (`POST /api/webhooks/{slug}/receive`) is rate-limited
per-IP and per-slug using an in-memory fixed-window counter.

- Default limit: `WEBHOOK_RATE_LIMIT_PER_MINUTE=60` requests per minute
- Responses exceeding the limit receive `429 Too Many Requests` with a
  `Retry-After` header

The current implementation is in-process and resets on backend restart. For
multi-replica or high-volume deployments, replace `app/services/rate_limiter.py`
with a Redis-backed implementation.

---

## Queue Security (v0.4.0)

HTTP job execution is dispatched through Redis and processed by the Celery worker.
Queued task payloads contain database identifiers and trigger metadata; request
headers and bodies are loaded from PostgreSQL by the worker and are masked before
being written to execution history.

Production Compose keeps Redis on the internal Docker network only. Do not expose
Redis to the public internet. If deploying outside the provided Compose files,
bind Redis to a private interface and protect it with network-level access
controls.

---

## Notification Channel Security (v0.5.0)

Notification channels can contain sensitive delivery configuration:

- Discord webhook URLs
- Slack webhook URLs
- Telegram bot tokens
- SMTP usernames and passwords
- Custom webhook URLs and headers

API responses and the frontend never return full notification secrets. Channel
configuration is returned as `config_masked`, and delivery error messages are
scrubbed before they are stored in `notification_deliveries`.

Channel credentials must be available to the backend so notifications can be
sent. They are encrypted at rest with Fernet, returned only as masked values,
and still depend on protecting the configured encryption key, database access
and backups.

Custom notification webhook targets are checked by the same SSRF guard used by
HTTP jobs when `ENABLE_SSRF_PROTECTION=true`.

### Encryption key — backup and rotation

`NOTIFICATION_ENCRYPTION_KEY` is a Fernet key that protects all stored channel
credentials. Losing it means all notification channel credentials become
unrecoverable and channels must be reconfigured.

**Generating a key:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Backup — required before any production deployment:**

Store the key in at least two separate, access-controlled locations (e.g., a
password manager, a secrets manager, an encrypted file on offline media). Do not
store it only in `.env.production` on the server.

**Rotating the key:**

Key rotation requires re-encrypting all existing channel credentials:

1. Generate a new Fernet key.
2. For each notification channel, read the plaintext credentials via the API or
   directly from the database after decrypting with the old key.
3. Re-save each channel (via `PATCH /api/notification-channels/{id}`) with the
   new key active — this re-encrypts credentials at rest.
4. Update `NOTIFICATION_ENCRYPTION_KEY` in `.env.production` and restart the
   backend.
5. Verify channels work with a test dispatch (`POST /api/notification-channels/{id}/test`).

There is no automated rotation command. All steps require intentional operator
action to avoid accidental credential loss.

---

## Role-Based Access Control (v0.7.0)

Three roles are enforced **server-side** on every write endpoint. Role checks are applied as FastAPI dependencies (`require_admin`, `require_operator`) and cannot be bypassed by modifying frontend state.

### Permission Matrix

| Endpoint category | viewer | operator | admin |
| --- | :---: | :---: | :---: |
| Read jobs, executions, webhooks, alerts, reports | ✓ | ✓ | ✓ |
| Read notification channels, templates, escalation policies | ✓ | ✓ | ✓ |
| Create/edit/delete jobs | — | ✓ | ✓ |
| Run jobs manually | — | ✓ | ✓ |
| Create/edit/delete webhooks, reprocess events | — | ✓ | ✓ |
| Acknowledge/resolve alerts | — | ✓ | ✓ |
| Test notification channels | — | ✓ | ✓ |
| Generate reports | — | ✓ | ✓ |
| Create/edit/delete notification channels | — | — | ✓ |
| Create/edit/delete templates | — | — | ✓ |
| Create/edit/delete escalation policies | — | — | ✓ |
| User management | — | — | ✓ |
| View audit logs | — | — | ✓ |

### Last-admin protection

The API prevents the last active `admin` account from being deactivated (`PATCH /api/users/{id}`) or deleted (`DELETE /api/users/{id}`). The check counts active admin accounts before committing the change; the operation is rejected with `400` if it would leave zero active admins.

---

## Audit Log (v0.7.0)

Every sensitive action writes an `AuditLog` record atomically in the same database session as the primary operation. The record cannot be created without also completing the primary operation (and vice versa), because both share a single `session.commit()`.

### What is logged

- **Auth:** login success and failure (includes IP address and user agent)
- **Jobs:** create, update, delete, run
- **Webhooks:** create, update, delete, reprocess
- **Alerts:** acknowledge, resolve
- **Notification channels:** create, update, delete, activate, deactivate, test
- **Templates:** create, update, delete
- **Escalation policies:** create, update, delete, add step, delete step
- **Reports:** generate
- **Users:** create, update, delete, reset password

### Metadata masking in audit

The `log_action` service strips the following keys from the `metadata` dict before writing to `audit_logs.metadata`:

`password`, `password_hash`, `secret`, `token`, `api_key`, `webhook_url`, `bot_token`, `smtp_password`, `encryption_key`, `config`, `config_encrypted`, `config_masked`

Nested keys are not traversed (metadata is expected to be shallow). If a sensitive key is present, its value is replaced with `"[redacted]"`.

### Audit log access

`GET /api/audit-logs` is restricted to admin users. Filters: `user_id`, `action`, `resource_type`, `status`, `since`, `until`, `limit` (max 1000, default 100). Results are ordered by `created_at` descending.

### Known audit limitations

- **Append-only by convention.** No database-level immutability (e.g., PostgreSQL row security) prevents a direct database user from deleting rows.
- **Actor is nullable.** If the `user_id` FK target is deleted, `user_id` becomes `NULL` (`SET NULL` on delete). The action and resource are still recorded.
- **Unauthenticated events.** Login failures record `user_id=NULL` because no validated user is associated at that point.

---

## Authentication (v0.2.0)

All API routes except `/api/health`, `/api/version` and the webhook receiver
require a valid JWT Bearer token in the `Authorization` header.

- Tokens are issued by `POST /api/auth/login` using email and bcrypt-hashed
  password verification
- Passwords are hashed with bcrypt; plain-text passwords are never stored
- Token expiry is controlled by `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60)
- An admin account is bootstrapped from `ADMIN_EMAIL` / `ADMIN_PASSWORD` env
  vars on first startup; change these values before any deployment

**v0.2.0 limitation:** only a single access token is issued (no refresh tokens,
no token revocation). For production use, plan for short expiry values and
change `ADMIN_PASSWORD` immediately after the first login.

---

## Known Limitations (v0.7.0)

| Limitation | Detail |
| --- | --- |
| **Rate limiting is in-process** | Resets on restart; not shared across replicas. Replace with Redis-backed limiter for HA deployments. |
| **No token revocation** | JWT tokens remain valid until expiry. Logout only clears the client-side token. |
| **No refresh tokens** | Users must re-authenticate when the access token expires. |
| **Scheduler timing is in-process** | APScheduler runs inside the backend and dispatches to Redis. Run one scheduler-owning API replica. |
| **Redis rate limiting not implemented** | Redis is used for Celery. Webhook rate limiting remains in-memory per API process. |
| **Notification credentials encrypted at rest** | Channel secrets are encrypted with Fernet (v0.6.0+). The encryption key must be protected and backed up by the operator; database-level key management is not provided. See [Encryption key — backup and rotation](#encryption-key--backup-and-rotation). |
| **Notification retry is simple** | Failed sends are retried briefly and recorded; escalation and provider-specific backoff are not implemented. |
| **Response preview is truncated** | Only the first 500 bytes of the response body are stored. |
| **Audit log is append-only by convention** | No row-level immutability; direct database access bypasses the audit trail. |
| **`last_login_at` requires schema update** | The `last_login_at` column on `users` is added by `create_all` on startup; pre-existing PostgreSQL deployments without Alembic migration must run `ALTER TABLE users ADD COLUMN last_login_at TIMESTAMPTZ` manually. |

---

## WebSocket Authentication

The WebSocket event stream at `/ws/events` uses JWT authentication via a query parameter because browser `WebSocket` APIs do not support custom HTTP headers during the handshake.

### Implications

| Concern | Detail |
| --- | --- |
| **Token in URL** | The JWT appears in server access logs and proxy forwarding headers. Rotate tokens if logs are leaked. |
| **Mitigation** | Use `wss://` (TLS) in production so the query string is encrypted in transit. Caddy handles this automatically. |
| **Token lifetime** | The default token expiry is `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 minutes). Shorter lifetimes reduce the exposure window. |
| **Close on auth failure** | The server closes the connection with code 1008 (Policy Violation) if the token is missing, invalid or the user is inactive. The frontend stops reconnecting on this code. |

### What WS events contain

Event frames carry only identifiers and status values:

- `execution_id`, `job_id`, `job_name`, `trigger_type`, `status`, `duration_ms`, `response_status_code`
- `alert_id`, `title`, `severity`

No request headers, body content, credentials, webhook URLs or SMTP passwords are ever included in WebSocket event payloads.

---

## Production Recommendations

The recommended production path is `docker-compose.prod.yml` + Caddy, documented in [docs/deployment.md](deployment.md). Key security properties of that setup:

- **Caddy terminates TLS** — automatic HTTPS via Let's Encrypt; HTTP redirected to HTTPS.
- **Security headers** — `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` and `Referrer-Policy` set by Caddy.
- **PostgreSQL not exposed** — port 5432 is absent from `docker-compose.prod.yml`; the database is only reachable from other containers on the internal Docker network.
- **Redis not exposed** — port 6379 is absent from `docker-compose.prod.yml`; Redis is only reachable from other containers on the internal Docker network.
- **Backend and frontend not published** — only Caddy (ports 80/443) is reachable from outside Docker.

Additional hardening steps:

1. **Replace all placeholder secrets** — generate strong values for `APP_SECRET_KEY`, `JWT_SECRET_KEY` and `POSTGRES_PASSWORD` using `openssl rand -hex 32` before first run.
2. **Change the bootstrap admin password** — `ADMIN_PASSWORD` is used only on the first startup. After creating the admin account, use a strong password and change it immediately after first login.
3. **Do not commit `.env.production`** — it is listed in `.gitignore`; verify it never appears in `git status` output.
4. **Firewall** — allow only ports 22 (SSH), 80 and 443 from the public internet. Block all other ports at the firewall level.
5. **Keep Docker and the OS updated** — subscribe to security advisories for Ubuntu, Docker, PostgreSQL 16 and Redis.
6. **Review job URLs** — before activating a job that targets an internal service, verify the URL is intentional to prevent accidental SSRF.
7. **Do not use real tokens in demos** — never include real API keys, tokens or secrets in job configurations used for screenshots or documentation.
8. **Protect notification credentials** — use dedicated webhook URLs and SMTP credentials, rotate them periodically and restrict database backup access. Back up `NOTIFICATION_ENCRYPTION_KEY` in a separate, access-controlled location before adding any notification channels; losing it makes all stored channel credentials unrecoverable. See [Encryption key — backup and rotation](#encryption-key--backup-and-rotation) above.
9. **Create a least-privilege operator account** — avoid day-to-day use of the admin account. Create an `operator` role account for operational tasks and reserve `admin` for user management and audit review.
10. **Review audit logs periodically** — `GET /api/audit-logs` provides a full action history. Schedule periodic reviews as part of your security posture, especially after privilege changes or incident response.

---

## Reporting Vulnerabilities

Do not open a public issue to report a security vulnerability.

Follow the process described in [SECURITY.md](../SECURITY.md).
