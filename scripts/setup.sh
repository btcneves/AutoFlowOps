#!/usr/bin/env bash
# AutoFlowOps setup script
# Downloads pre-built images from GHCR, configures environment and starts the stack.
#
# Usage:
#   bash scripts/setup.sh              # interactive, asks for image tag
#   IMAGE_TAG=v1.0.0 bash scripts/setup.sh   # non-interactive, use specific tag
#   IMAGE_TAG=latest  bash scripts/setup.sh   # non-interactive, use latest

set -euo pipefail

REGISTRY="ghcr.io/btcneves"
BACKEND_IMAGE="${REGISTRY}/autoflowops-backend"
FRONTEND_IMAGE="${REGISTRY}/autoflowops-frontend"
TAG="${IMAGE_TAG:-}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

info()    { printf '\033[0;32m[setup]\033[0m %s\n' "$*"; }
warning() { printf '\033[0;33m[setup]\033[0m %s\n' "$*"; }
error()   { printf '\033[0;31m[setup]\033[0m %s\n' "$*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || error "'$1' not found. Install it and re-run."
}

wait_healthy() {
  local url="$1" label="$2" attempts="${3:-30}"
  info "Waiting for ${label} to be healthy…"
  for i in $(seq 1 "${attempts}"); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      info "${label} is ready."
      return 0
    fi
    sleep 2
  done
  error "${label} did not become healthy after $(( attempts * 2 ))s. Check logs: docker compose -f docker-compose.registry.yml logs"
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

require_cmd docker
require_cmd curl

if ! docker compose version >/dev/null 2>&1; then
  error "Docker Compose v2 plugin not found. Install it and re-run."
fi

# ---------------------------------------------------------------------------
# Resolve image tag
# ---------------------------------------------------------------------------

if [ -z "${TAG}" ]; then
  printf '\033[0;32m[setup]\033[0m Image tag to use (e.g. v1.0.0, latest) [latest]: '
  read -r TAG
  TAG="${TAG:-latest}"
fi

info "Using image tag: ${TAG}"

# ---------------------------------------------------------------------------
# Env file
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

if [ ! -f .env ]; then
  cp .env.example .env
  info "Created .env from .env.example"
  warning "Edit .env and change APP_SECRET_KEY and JWT_SECRET_KEY before using in production."
else
  info ".env already exists — skipping copy."
fi

# ---------------------------------------------------------------------------
# Pull images
# ---------------------------------------------------------------------------

info "Pulling backend image (${BACKEND_IMAGE}:${TAG})…"
docker pull "${BACKEND_IMAGE}:${TAG}"

info "Pulling frontend image (${FRONTEND_IMAGE}:${TAG})…"
docker pull "${FRONTEND_IMAGE}:${TAG}"

# ---------------------------------------------------------------------------
# Start stack
# ---------------------------------------------------------------------------

info "Starting stack with docker-compose.registry.yml…"
IMAGE_TAG="${TAG}" docker compose -f docker-compose.registry.yml up -d

# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

wait_healthy "http://localhost:8000/api/health" "backend API" 40
wait_healthy "http://localhost:3000" "frontend" 20

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

printf '\n'
info "AutoFlowOps is running."
printf '\n'
printf '  Frontend  → http://localhost:3000\n'
printf '  API       → http://localhost:8000\n'
printf '  Swagger   → http://localhost:8000/docs\n'
printf '\n'
info "Default credentials: ADMIN_EMAIL / ADMIN_PASSWORD from .env"
info "Stop the stack: docker compose -f docker-compose.registry.yml down"
