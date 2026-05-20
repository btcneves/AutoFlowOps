# Release Notes — AutoFlowOps v0.3.0

**Release date:** 2026-05-20

---

## Summary

AutoFlowOps v0.3.0 focuses on production readiness for single-host VPS deployments. It adds a hardened Docker Compose production stack, Caddy HTTPS reverse proxy, production environment template, config validation CI and complete deployment documentation.

---

## Main Features

### Production Docker Compose

- `docker-compose.prod.yml` runs Caddy, backend, frontend and PostgreSQL
- Only Caddy publishes host ports (`80`, `443` and `443/udp`)
- Backend, frontend and PostgreSQL stay on the private Docker network
- Service healthchecks and `restart: always` are configured for production operations

### Caddy Reverse Proxy

- Automatic HTTPS certificate provisioning and renewal
- `/api/*`, `/docs`, `/redoc` and `/openapi.json` route to the FastAPI backend
- All other paths route to the frontend
- Baseline security headers and JSON logs are enabled

### Production Documentation

- Full VPS guide with DNS, Docker installation, environment setup and Caddy configuration
- Backup and restore commands for PostgreSQL
- Update procedure with migration notes
- Troubleshooting table for common deployment issues
- Production hardening guidance in the security documentation

### Observability and CI

- `/api/health` now reports database connectivity with `database: "ok"` or `database: "error"`
- `make prod-validate` validates the production compose file and Caddyfile
- Production Config CI validates `docker-compose.prod.yml` and `Caddyfile` on pull requests

---

## Upgrade Notes

1. Copy `.env.production.example` to `.env.production`.
2. Replace every placeholder secret and credential.
3. Edit `Caddyfile` with your real domain and email.
4. Run `make prod-validate`.
5. Start with `make prod-up`.

Production deploys should verify:

```bash
curl https://your-domain.example/api/health
```

Expected response includes `"database":"ok"`.

---

## Known Limitations

- The production stack is designed for one backend replica while APScheduler remains in-process.
- Rate limiting remains in memory and is not shared across replicas.
- Caddy is configured from a checked-in template; operators must replace the example domain and email before deployment.
- Published container images are still future work.

See [docs/deployment.md](deployment.md) for the full production guide.
