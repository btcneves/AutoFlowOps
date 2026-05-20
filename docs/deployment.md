# Deployment Guide

The recommended MVP deployment path is Docker Compose on a single host.

## Requirements

- Docker
- Docker Compose
- A private network, VPN or reverse proxy access control for production-like use

## Quick Deploy

```bash
cp .env.example .env
```

Edit `.env` and replace placeholder secrets and database credentials.

```bash
docker compose up -d --build
```

The backend container runs `alembic upgrade head` before starting the API, so a fresh PostgreSQL volume gets the initial schema automatically.

Services:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Verify

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/stats
```

Seed demo data for review:

```bash
make seed
```

## Environment Variables

| Variable | Required | Notes |
|---|---|---|
| `APP_NAME` | No | Display name returned by health endpoints |
| `APP_ENV` | No | `development` or `production` |
| `APP_DEBUG` | No | Keep `false` outside local debugging to avoid verbose SQL logs |
| `APP_SECRET_KEY` | Yes | Replace the example value before deployment |
| `DATABASE_URL` | Yes | SQLAlchemy URL used by backend and migrations |
| `FRONTEND_URL` | Yes | Allowed CORS origin |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING` |
| `DEFAULT_TIMEZONE` | No | Default operational timezone |
| `ENABLE_DEMO_MODE` | No | Reserved for demo behavior |

Some `.env.example` values are reserved for future phases, including Redis/JWT settings.

## Production Notes

- Run one backend replica while using the in-process APScheduler.
- Put the app behind TLS and private access control.
- Change default database passwords.
- Keep `.env` out of Git.
- Back up the PostgreSQL volume before upgrades.
- Review `SECURITY.md` before exposing the service to a network.

## Publishing Checklist

- `make lint`
- `make test`
- `cd frontend && npm run build`
- `docker compose up -d --build`
- Verify `/api/health`, `/api/stats` and frontend pages.
- Capture screenshots or refresh existing screenshots.
- Commit changes and publish the repository when ready.
