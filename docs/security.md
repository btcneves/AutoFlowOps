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

## MVP Security Limitations

The following are known limitations of the current MVP. They are intentional scope decisions, not overlooked risks.

| Limitation | Detail |
| --- | --- |
| **No authentication** | All API endpoints are open. There are no user accounts, sessions or API keys in the MVP. |
| **No rate limiting** | The backend does not limit request rates per IP or per endpoint. |
| **No SSRF protection** | HTTP jobs can target any URL including internal network addresses. Validate job URLs manually in production. |
| **Scheduler is in-process** | APScheduler runs inside the backend. A single crashed process stops all scheduled jobs. |
| **Response preview is truncated** | Only a limited preview of the response body is stored; full responses are not persisted. |
| **No audit log** | There is no immutable audit trail of who created, modified or deleted resources. |

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
