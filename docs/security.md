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

## Known Limitations (v0.2.0)

| Limitation | Detail |
| --- | --- |
| **Rate limiting is in-process** | Resets on restart; not shared across replicas. Replace with Redis-backed limiter for HA deployments. |
| **No token revocation** | JWT tokens remain valid until expiry. Logout only clears the client-side token. |
| **No refresh tokens** | Users must re-authenticate when the access token expires. |
| **Scheduler is in-process** | APScheduler runs inside the backend. A single crashed process stops all scheduled jobs. |
| **Response preview is truncated** | Only the first 500 bytes of the response body are stored. |
| **No audit log** | There is no immutable audit trail of resource changes. |

---

## Production Recommendations

1. **Deploy behind a reverse proxy** — use nginx, Caddy or Traefik with HTTPS and restrict access to trusted IPs or a VPN.
2. **Change all placeholder secrets** — update `APP_SECRET_KEY`, `JWT_SECRET_KEY` and database credentials in `.env` before the first run.
3. **Use strong database credentials** — change the default `autoflowops/autoflowops` PostgreSQL user and password.
4. **Restrict the Docker network** — do not expose PostgreSQL (port 5432) to the public internet.
5. **Do not use real tokens in examples** — never include real API keys, tokens or secrets in job configurations used for demos, screenshots or documentation.
6. **Review job URLs** — before activating a job that targets an internal service, verify the URL is intentional to prevent accidental SSRF.

---

## Reporting Vulnerabilities

Do not open a public issue to report a security vulnerability.

Follow the process described in [SECURITY.md](../SECURITY.md).
