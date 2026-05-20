# Security Policy

## Reporting a Vulnerability

**Do not open a public GitHub issue to report a security vulnerability.**

Send a private report to the maintainer:

1. Open a [GitHub Security Advisory](https://github.com/btcneves/autoflowops/security/advisories/new) (recommended — kept private by default).
2. Or send a detailed message to the maintainer via GitHub profile contact.

Include in your report:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

We will acknowledge the report within 72 hours and aim to release a fix within 14 days for critical issues.

---

## Supported Versions

| Version | Supported |
| --- | --- |
| 0.x (current) | ✅ Yes |

---

## Scope

This policy covers vulnerabilities in:

- The FastAPI backend (`backend/`)
- The React frontend (`frontend/`)
- The Docker Compose configuration
- The dependency chain (transitive dependencies)

Out of scope:

- Issues in third-party hosted services used as targets by jobs
- Security of the host environment or operating system
- Denial-of-service attacks that require authenticated access

---

## Secret Masking Policy

AutoFlowOps masks sensitive fields in all logs and stored execution records before any database write.

**Masked HTTP headers** (case-insensitive, matched by substring):

- `authorization`, `x-api-key`, `api-key`, `token`, `secret`, `password`, `cookie`, `set-cookie`

**Masked JSON body fields** (case-insensitive, recursive):

- `password`, `passwd`, `pwd`, `token`, `access_token`, `refresh_token`
- `secret`, `api_key`, `apikey`, `private_key`, `authorization`, `credential`

See [docs/security.md](docs/security.md) for full details, examples and production recommendations.

---

## Important Notices

- **Never use real tokens or credentials in demo mode or public examples.**
- **Never commit `.env` or `.env.production` files** — only templates such as `.env.example` and `.env.production.example` are version-controlled.
- **Webhook secret tokens are stored as SHA-256 hashes**, never in plain text.
- **Authorization headers are never stored in full** in execution logs.
- JWT authentication protects API routes except `/api/health`, `/api/version`, `/api/auth/login` and webhook receive. Deploy with HTTPS and strong bootstrap admin credentials before exposing the service publicly.

---

## `.env` Security

All secrets must be kept in local environment files (never committed to version control).

```bash
cp .env.example .env
# Edit .env and set strong unique values for:
# APP_SECRET_KEY, JWT_SECRET_KEY, DATABASE_URL credentials
```

For production, copy `.env.production.example` to `.env.production`, replace all placeholders, and verify `git status` never shows real environment files before pushing.
