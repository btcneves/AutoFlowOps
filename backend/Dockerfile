FROM python:3.12-slim

LABEL org.opencontainers.image.title="AutoFlowOps Backend" \
      org.opencontainers.image.description="FastAPI backend for AutoFlowOps — scheduled HTTP jobs, webhooks, alerts and real-time events" \
      org.opencontainers.image.source="https://github.com/btcneves/autoflowops" \
      org.opencontainers.image.licenses="MIT"

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e . && rm -rf /root/.cache/pip

COPY app/ app/
COPY alembic.ini .
COPY alembic/ alembic/
COPY scripts/ scripts/

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
