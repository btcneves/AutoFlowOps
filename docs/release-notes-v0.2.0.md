# Release Notes — AutoFlowOps v0.2.0

**Release date:** 2026-05-19

---

## Summary

AutoFlowOps v0.2.0 turns the MVP into an authenticated operations tool. It adds JWT login, protected API routes, jobs management in the frontend, execution history pages, SSRF protection and webhook rate limiting.

---

## Main Features

### Authentication

- `POST /api/auth/login` issues JWT access tokens
- `GET /api/auth/me` returns the current authenticated user
- Protected routers require `Authorization: Bearer <token>`
- The first admin user is bootstrapped from `ADMIN_EMAIL`, `ADMIN_PASSWORD` and `ADMIN_NAME`

### Jobs UI

- List, create, edit and inspect HTTP jobs from the browser
- Run jobs manually from the UI
- Pause, activate and delete jobs without using curl

### Executions UI

- Browse execution history with status and job filters
- Inspect individual execution details
- View masked request and response data without exposing stored secrets

### Security Hardening

- SSRF guard blocks loopback, private, link-local and reserved network ranges by default
- DNS resolution is checked before HTTP jobs execute
- Webhook receive endpoints are rate-limited per IP and slug
- bcrypt password hashing is used for stored user credentials

---

## Validation

| Suite | Result |
| --- | --- |
| Backend tests (pytest) | 140+ passing |
| Frontend tests (Vitest) | 38+ passing |
| Backend lint (ruff) | Clean |
| Frontend lint (ESLint) | Clean |
| Frontend build (Vite) | Success |

---

## Known Limitations

- Access tokens have no refresh-token flow or server-side revocation.
- Rate limiting is in-process and resets on backend restart.
- APScheduler still runs inside the backend process, so one backend replica is recommended.
- Role-based access control is not implemented yet.

See [docs/roadmap.md](roadmap.md) for planned follow-up work.
