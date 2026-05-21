"""Observability: Prometheus business metrics and structured logging configuration."""

from __future__ import annotations

import logging
import sys

import structlog
from prometheus_client import Counter

# ---------------------------------------------------------------------------
# Business metrics
# ---------------------------------------------------------------------------

job_executions_total = Counter(
    "autoflowops_job_executions_total",
    "Total job executions by final status and trigger type.",
    ["status", "trigger_type"],
)

alerts_created_total = Counter(
    "autoflowops_alerts_created_total",
    "Total internal alerts created by severity.",
    ["severity"],
)

# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------


def configure_logging(log_level: str = "INFO", env: str = "development") -> None:
    """Configure structlog for the application.

    Production (APP_ENV=production): JSON output, one object per line.
    Development: human-readable coloured console output.

    Every log line automatically merges request_id, user_id and workspace_id
    when bound via structlog.contextvars in the request middleware and
    auth/workspace dependencies.
    """
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
    ]

    if env == "production":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=[*shared_processors, renderer],
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level.upper())

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
