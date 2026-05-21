# Deployment Guide

This guide covers three ways to run AutoFlowOps:

1. **Pull from registry** — fastest; downloads pre-built images from GHCR. No build step.
2. **Build from source** — full local build using Docker Compose.
3. **Production on a VPS** — Caddy reverse proxy with automatic HTTPS.

---

## Option 1 — Pull from GitHub Container Registry (GHCR)

AutoFlowOps publishes versioned Docker images to GHCR on every release tag. No local build is required.

### Images

| Image | Registry path |
| --- | --- |
| Backend | `ghcr.io/btcneves/autoflowops-backend` |
| Frontend | `ghcr.io/btcneves/autoflowops-frontend` |

Available tags: `latest`, `vX.Y.Z`, `X.Y.Z`, `X.Y` (e.g. `v1.0.0`, `1.0.0`, `1.0`).

### Quick setup (interactive)

```bash
git clone https://github.com/btcneves/autoflowops.git
cd autoflowops
bash scripts/setup.sh
```

The script:

1. Checks that Docker and Docker Compose are installed
2. Copies `.env.example` to `.env` if it does not exist
3. Asks for an image tag (default: `latest`)
4. Pulls `autoflowops-backend` and `autoflowops-frontend` from GHCR
5. Starts the stack with `docker-compose.registry.yml`
6. Waits for the backend health endpoint and the frontend to respond
7. Prints service URLs

### Non-interactive (CI / scripted environments)

```bash
IMAGE_TAG=v1.1.0 bash scripts/setup.sh
```

### Makefile shortcuts

```bash
# Pull images (IMAGE_TAG defaults to latest)
make pull

# Start stack using GHCR images
IMAGE_TAG=v1.1.0 make registry-up

# Stop
make registry-down

# Stream logs
make registry-logs
```

### Pinning a specific version

```bash
IMAGE_TAG=v1.1.0 docker compose -f docker-compose.registry.yml up -d
```

### Updating to a new version

```bash
IMAGE_TAG=v1.1.0 make pull
IMAGE_TAG=v1.1.0 make registry-down
IMAGE_TAG=v1.1.0 make registry-up
```

The backend container runs `alembic upgrade head` on startup and applies any pending migrations automatically.

---

## Option 2 — Build from source (local Docker Compose)

---

## Local Development

### Requirements

- Docker + Docker Compose

### Start

```bash
cp .env.example .env
docker compose up --build
```

The backend runs `alembic upgrade head` automatically before starting. Services:

| Service | URL |
| --- | --- |
| Frontend | <http://localhost:3000> |
| Backend API | <http://localhost:8000> |
| Swagger docs | <http://localhost:8000/docs> |
| ReDoc | <http://localhost:8000/redoc> |
| Redis | `localhost:6379` |

### Verify

```bash
curl http://localhost:8000/api/health
```

Expected: `{"status":"ok","app":"AutoFlowOps","env":"development","database":"ok"}`

### Seed demo data

```bash
make seed
```

---

## Production Deployment on a VPS

This section covers deploying AutoFlowOps on a Linux VPS with a custom domain and automatic HTTPS via Caddy.

### Architecture

```text
Internet
  └─> Caddy (ports 80 / 443, TLS)
        ├─> /api/* → backend:8000  (FastAPI)
        └─> /*     → frontend:3000 (Vite preview)
              ├─> worker (Celery, internal only)
              ├─> Redis (internal only)
              └─> PostgreSQL (internal network only, not exposed)
```

Caddy handles TLS certificate provisioning and renewal automatically via Let's Encrypt. The backend and frontend are not reachable directly from the internet — only Caddy is exposed.

### Server Requirements

| Requirement | Minimum |
| --- | --- |
| OS | Ubuntu 22.04 LTS (or any modern Debian-based distro) |
| RAM | 1 GB |
| CPU | 1 vCPU |
| Disk | 10 GB |
| Docker | 24+ |
| Docker Compose | v2.20+ |

Ports 80 and 443 must be open in the server firewall (UFW, iptables, or cloud security group).

### 1. DNS Setup

Create an A record pointing your domain to the server's public IP:

```text
autoflowops.yourdomain.com → <server-public-ip>
```

Verify propagation before proceeding (Caddy needs to resolve the domain to obtain a certificate):

```bash
dig +short autoflowops.yourdomain.com
```

### 2. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
```

### 3. Clone the Repository

```bash
git clone https://github.com/btcneves/autoflowops.git
cd autoflowops
```

### 4. Configure the Production Environment

```bash
cp .env.production.example .env.production
```

Edit `.env.production` and replace every `REPLACE_WITH_*` placeholder with real values. Generate strong secrets with:

```bash
openssl rand -hex 32
```

Key variables to set:

| Variable | Example | Notes |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | *(random)* | PostgreSQL database password |
| `POSTGRES_USER` | `autoflowops` | PostgreSQL username |
| `POSTGRES_DB` | `autoflowops` | PostgreSQL database name |
| `DATABASE_URL` | `postgresql+psycopg://autoflowops:<password>@db:5432/autoflowops` | Must match POSTGRES_* values |
| `REDIS_URL` | `redis://redis:6379/0` | Internal Redis broker/backend URL |
| `APP_SECRET_KEY` | *(64-char hex)* | General application secret |
| `JWT_SECRET_KEY` | *(64-char hex)* | Signs JWT tokens — use a different value than APP_SECRET_KEY |
| `FRONTEND_URL` | `https://autoflowops.yourdomain.com` | Allowed CORS origin |
| `ADMIN_EMAIL` | `admin@yourdomain.com` | Initial admin account email |
| `ADMIN_PASSWORD` | *(strong password)* | Initial admin account password — change after first login |

### 5. Configure Caddy

Edit `Caddyfile` and replace `autoflowops.yourdomain.com` with your domain, and `webmaster@yourdomain.com` with a real email address (used by Let's Encrypt for certificate notifications):

```caddyfile
{
    email webmaster@yourdomain.com
}

autoflowops.yourdomain.com {
    ...
}
```

### 6. Start the Production Stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

On first start, the backend:

1. Runs `alembic upgrade head` to apply database migrations
2. Creates the admin account from `ADMIN_EMAIL` / `ADMIN_PASSWORD`
3. Loads scheduled jobs from the database
4. Starts the worker so queued manual and scheduled jobs can execute
5. Loads notification channels from the database when alerts are dispatched

### 7. Verify

```bash
# API health check (expect database: "ok")
curl https://autoflowops.yourdomain.com/api/health

# Frontend (expect 200)
curl -I https://autoflowops.yourdomain.com
```

If the certificate is not yet provisioned (Caddy takes ~30 seconds on first start), wait and retry.

### 8. First Login

1. Open `https://autoflowops.yourdomain.com` in a browser.
2. Log in with `ADMIN_EMAIL` and `ADMIN_PASSWORD`.
3. Change the admin password immediately via the API or by updating `ADMIN_PASSWORD` in `.env.production` and restarting — note that `ADMIN_PASSWORD` is only used on first startup, so to change the password after bootstrapping you need to use the API or update the database directly.

---

## Makefile Targets (Production)

```bash
make prod-up        # Start the production stack in the background
make prod-down      # Stop the production stack
make prod-logs      # Stream logs from all production services
make prod-validate  # Validate docker-compose.prod.yml and Caddyfile syntax
```

---

## Environment Variables Reference

| Variable | Default | Required in Prod | Notes |
| --- | --- | --- | --- |
| `POSTGRES_DB` | — | Yes | PostgreSQL database name |
| `POSTGRES_USER` | — | Yes | PostgreSQL username |
| `POSTGRES_PASSWORD` | — | Yes | PostgreSQL password |
| `APP_NAME` | `AutoFlowOps` | No | Display name |
| `APP_ENV` | `development` | Yes (`production`) | Controls debug/logging behaviour |
| `APP_DEBUG` | `false` | No | Keep `false` in production |
| `APP_SECRET_KEY` | `change-me` | Yes | Replace before any deployment |
| `DATABASE_URL` | SQLite fallback | Yes | Must use the `db` hostname |
| `REDIS_URL` | `redis://redis:6379/0` | Yes | Must use the `redis` hostname in Compose |
| `JOB_EXECUTION_MODE` | `celery` | No | Use `celery` in normal deployments; `inline` is for isolated tests |
| `FRONTEND_URL` | `http://localhost:3000` | Yes | Allowed CORS origin |
| `JWT_SECRET_KEY` | `change-me` | Yes | Replace before any deployment |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | No | Token lifetime in minutes |
| `NOTIFICATION_ENCRYPTION_KEY` | *(derived)* | Yes | Fernet key for notification channel credentials. Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. If absent, a key is derived from `APP_SECRET_KEY` (not production-safe). Back up this value — losing it makes stored notification credentials unrecoverable. |
| `ADMIN_EMAIL` | `admin@autoflowops.local` | Yes | Bootstrap admin email |
| `ADMIN_PASSWORD` | `changeme` | Yes | Bootstrap admin password |
| `ADMIN_NAME` | `Admin` | No | Bootstrap admin display name |
| `ENABLE_SSRF_PROTECTION` | `true` | No | Keep `true` in production |
| `ALLOW_PRIVATE_NETWORK_TARGETS` | `false` | No | Keep `false` in production |
| `WEBHOOK_RATE_LIMIT_PER_MINUTE` | `60` | No | Per-IP webhook rate limit |
| `LOG_LEVEL` | `INFO` | No | `DEBUG`, `INFO`, `WARNING` |
| `DEFAULT_TIMEZONE` | `America/Sao_Paulo` | No | Operational timezone |

Notification channels are configured in the UI or API after login. No provider
credentials are required in `.env.production`; store only dedicated webhook URLs
or SMTP credentials created for AutoFlowOps.

---

## Backup and Restore

### Backup PostgreSQL

```bash
# Create a timestamped dump
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U autoflowops autoflowops \
  > backup_$(date +%Y%m%d_%H%M%S).sql
```

Store the dump in a location outside the server (S3, object storage, remote host). For automated backups, schedule the command with cron:

```bash
# crontab -e
0 3 * * * cd /srv/autoflowops && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U autoflowops autoflowops > /srv/backups/autoflowops_$(date +\%Y\%m\%d).sql
```

### Restore PostgreSQL

```bash
# Stop the backend first to avoid active connections
docker compose -f docker-compose.prod.yml stop backend

# Restore from dump
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U autoflowops autoflowops < backup_20260101_030000.sql

# Restart
docker compose -f docker-compose.prod.yml start backend
```

---

## Updating to a New Version

```bash
# 1. Pull the latest code
git pull origin main

# 2. Rebuild and restart with zero-downtime rolling restart
docker compose -f docker-compose.prod.yml up -d --build

# The backend entrypoint runs "alembic upgrade head" automatically before starting.
# If migrations fail, the container exits — check logs before proceeding.

# 3. Verify
curl https://autoflowops.yourdomain.com/api/health
```

If a migration fails:

```bash
# Inspect migration logs
docker compose -f docker-compose.prod.yml logs backend

# Run migrations manually inside the container
docker compose -f docker-compose.prod.yml run --rm backend \
  sh -c "alembic upgrade head"
```

---

## Logs and Troubleshooting

### View logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f worker
docker compose -f docker-compose.prod.yml logs -f caddy
docker compose -f docker-compose.prod.yml logs -f db
docker compose -f docker-compose.prod.yml logs -f redis
```

### Check container status

```bash
docker compose -f docker-compose.prod.yml ps
```

### Common issues

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `502 Bad Gateway` from Caddy | Backend container not healthy | `logs backend` — check for DB connection error or migration failure |
| TLS certificate not issued | DNS not propagated or port 80 blocked | Verify DNS A record; check firewall |
| `database: "error"` in `/api/health` | DB container down or credentials mismatch | `logs db`; verify `DATABASE_URL` matches `POSTGRES_*` vars |
| Manual jobs stay `queued` | Worker or Redis unavailable | `logs worker`; `logs redis`; check `REDIS_URL` |
| Backend keeps restarting | Migration error on startup | `logs backend`; fix migration, then `docker compose -f docker-compose.prod.yml up -d --build` |
| `403 Forbidden` on webhook receive | Token mismatch or webhook paused | Check `X-Webhook-Token` header; check webhook status |
| `429 Too Many Requests` | Rate limit exceeded | Wait a minute or increase `WEBHOOK_RATE_LIMIT_PER_MINUTE` |
| Notification test fails | Provider URL, SMTP credentials or outbound firewall issue | Check channel config, provider credentials and backend logs |
| WS badge stays "Connecting…" | Backend unavailable or wrong `VITE_API_BASE_URL` | Verify `VITE_API_BASE_URL` is set correctly; check browser console for WS errors |
| WS events not received | Redis not running | `logs redis`; verify `REDIS_URL`; backend logs show "Redis WS subscriber exited" if disconnected |
| `docker pull` fails with 403 | GHCR package is private | Go to repository → Packages → make package public, or `docker login ghcr.io` with a token |
| Stack starts but shows old version | IMAGE_TAG not set or `latest` cached | Run `make pull IMAGE_TAG=v1.1.0` then `make registry-up IMAGE_TAG=v1.1.0` |

### Exec into a container

```bash
docker compose -f docker-compose.prod.yml exec backend sh
docker compose -f docker-compose.prod.yml exec worker sh
docker compose -f docker-compose.prod.yml exec db psql -U autoflowops autoflowops
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
```

---

## Production Checklist

Run through this list before exposing the instance to users.

- [ ] `POSTGRES_PASSWORD` set to a strong random value
- [ ] `APP_SECRET_KEY` set to a 64-character random hex string
- [ ] `JWT_SECRET_KEY` set to a different 64-character random hex string
- [ ] `NOTIFICATION_ENCRYPTION_KEY` set to a Fernet key and **backed up securely** (losing it makes stored notification credentials unrecoverable)
- [ ] `ADMIN_EMAIL` and `ADMIN_PASSWORD` set to real values (not defaults)
- [ ] `FRONTEND_URL` set to the public HTTPS domain
- [ ] `DATABASE_URL` credentials match `POSTGRES_USER` / `POSTGRES_PASSWORD`
- [ ] `REDIS_URL` is set to `redis://redis:6379/0`
- [ ] `.env.production` is **not** committed to version control
- [ ] Caddyfile domain updated (not `yourdomain.com`)
- [ ] Caddyfile email updated (not `webmaster@yourdomain.com`)
- [ ] DNS A record points to the server's public IP
- [ ] Ports 80 and 443 open in the server firewall
- [ ] Port 5432 (PostgreSQL) **not** exposed publicly (not in `docker-compose.prod.yml`)
- [ ] Port 6379 (Redis) **not** exposed publicly (not in `docker-compose.prod.yml`)
- [ ] `curl https://yourdomain.com/api/health` returns `{"status":"ok",...,"database":"ok"}`
- [ ] Worker healthcheck is passing and manual jobs leave `queued`
- [ ] First login successful; admin password changed or noted
- [ ] Backup strategy in place (cron job or manual schedule)
