# Release Notes — v0.9.0

**Release date:** 2026-05-20

## Overview

v0.9.0 adds a Docker image registry to AutoFlowOps. Backend and frontend images are now published to GitHub Container Registry (GHCR) on every release tag. A new setup script and a dedicated `docker-compose.registry.yml` let anyone run the full stack from a single command — no local build or clone required.

All existing features (RBAC, audit log, WebSocket real-time stream, notifications, Celery worker) remain unchanged.

---

## What's New

### Docker images on GHCR

Two images are published on every `v*.*.*` tag:

| Image | Registry path |
| --- | --- |
| Backend | `ghcr.io/btcneves/autoflowops-backend` |
| Frontend | `ghcr.io/btcneves/autoflowops-frontend` |

Each release produces three tags:

| Tag | Example | Meaning |
| --- | --- | --- |
| `vX.Y.Z` | `v0.9.0` | Exact release — pinned, immutable |
| `X.Y` | `0.9` | Minor stream — updates on patch releases |
| `latest` | `latest` | Latest stable release |

Images include OCI metadata labels (`title`, `description`, `source`, `licenses`, `version`, `revision`).

### `docker-compose.registry.yml`

A new compose file that starts the full stack — backend, worker, frontend, PostgreSQL, Redis — using GHCR images. The `IMAGE_TAG` environment variable controls the version (default: `latest`).

```bash
# Start with latest
docker compose -f docker-compose.registry.yml up -d

# Pin to a specific release
IMAGE_TAG=v0.9.0 docker compose -f docker-compose.registry.yml up -d
```

### `scripts/setup.sh`

An interactive setup script for first-time installation:

1. Checks that Docker and Docker Compose are installed
2. Copies `.env.example` to `.env` (if not already present)
3. Prompts for an image tag (default: `latest`; skipped when `IMAGE_TAG` is set)
4. Pulls backend and frontend images from GHCR
5. Starts the stack via `docker-compose.registry.yml`
6. Waits for the backend health endpoint (`/api/health`) and frontend to respond
7. Prints service URLs and credentials reminder

```bash
# Interactive
bash scripts/setup.sh

# Non-interactive (CI / scripted environments)
IMAGE_TAG=v0.9.0 bash scripts/setup.sh
```

### Makefile targets

| Target | Description |
| --- | --- |
| `make pull` | Pull backend + frontend images from GHCR (`IMAGE_TAG=latest`) |
| `make registry-up` | Start stack using GHCR images |
| `make registry-down` | Stop registry-based stack |
| `make registry-logs` | Stream logs from registry-based stack |

Override the tag: `IMAGE_TAG=v0.9.0 make registry-up`

### `docker-publish.yml` workflow

A new GitHub Actions workflow (`publish-backend` + `publish-frontend` jobs) triggered on `v*.*.*` tag push:

- Logs in to GHCR using `GITHUB_TOKEN` (no secrets to configure)
- Builds each image with `docker/build-push-action@v5`
- Uses GitHub Actions build cache (`type=gha`) — subsequent builds of unchanged layers complete in seconds
- Applies OCI metadata labels automatically via `docker/metadata-action@v5`
- Can also be triggered manually via `workflow_dispatch`

### Dockerfile improvements

**Backend:**

- Added `curl` to the image (required for the `HEALTHCHECK` instruction)
- Added `HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3` using `/api/health`
- Added OCI labels
- Non-root user (`appuser`, UID 1000) created early in the build
- `.dockerignore` extended: `tests/`, `*.egg-info/`, `*.sqlite`, `*.pyd`, `.env.*`

**Frontend:**

- Added OCI labels
- `.dockerignore` extended: `src/tests/`, `coverage/`

---

## Upgrade Steps

No database migration is required. No new environment variables are required.

### From v0.8.0 (build from source)

1. Pull the latest code: `git pull origin main`
2. Rebuild: `docker compose up -d --build`

### Switch to registry images

```bash
# Pull the v0.9.0 images
make pull IMAGE_TAG=v0.9.0

# Stop any existing stack
docker compose down

# Start from registry
make registry-up IMAGE_TAG=v0.9.0
```

---

## Known Limitations

- **GHCR packages start private** — after the first `docker-publish.yml` run, go to the repository → Packages → make the packages public (or authenticate with `docker login ghcr.io` using a personal access token with `read:packages` scope).
- **`vite preview` in production** — the frontend image uses `vite preview` to serve the built assets. For high-traffic deployments, replace with a dedicated static server (nginx, Caddy). The production `docker-compose.prod.yml` flow (with Caddy) is unaffected and recommended for production.
- **`IMAGE_TAG` not propagated to `docker-compose.registry.yml` automatically** — always pass it explicitly (`IMAGE_TAG=v0.9.0 make registry-up`) or export it in the shell.
- **No Windows support for `scripts/setup.sh`** — the setup script is a Bash script and requires WSL2 or Git Bash on Windows.
