"""Observability: Prometheus business metrics and structured logging configuration."""

from __future__ import annotations

import json
import logging
import queue
import sys
import threading
from datetime import UTC, datetime
from typing import Any

import httpx
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


# ---------------------------------------------------------------------------
# Remote log shippers (optional, activated via LOKI_URL / ELASTICSEARCH_URL)
# ---------------------------------------------------------------------------

_log = structlog.get_logger(__name__)

_JSON_FORMATTER = structlog.stdlib.ProcessorFormatter(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.processors.JSONRenderer(),
    ]
)


class _LokiHandler(logging.Handler):
    """Batched push handler for Grafana Loki's HTTP push API.

    Runs a background daemon thread that drains a queue and flushes
    entries every FLUSH_INTERVAL seconds or when BATCH_SIZE is reached.
    Uses synchronous httpx so the handler never touches the asyncio loop.
    Network errors are silently swallowed to avoid log recursion.
    """

    FLUSH_INTERVAL: float = 2.0
    BATCH_SIZE: int = 20

    def __init__(self, url: str, labels: dict[str, str]) -> None:
        super().__init__()
        self._push_url = url.rstrip("/") + "/loki/api/v1/push"
        self._labels = labels
        self._queue: queue.SimpleQueue[tuple[str, str]] = queue.SimpleQueue()
        self._client = httpx.Client(timeout=5.0)
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="loki-shipper"
        )
        self._thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ns = str(int(record.created * 1_000_000_000))
            self._queue.put_nowait((ns, self.format(record)))
        except Exception:  # noqa: BLE001
            self.handleError(record)

    def _run(self) -> None:
        while True:
            batch: list[tuple[str, str]] = []
            try:
                batch.append(self._queue.get(timeout=self.FLUSH_INTERVAL))
            except queue.Empty:
                continue
            while len(batch) < self.BATCH_SIZE:
                try:
                    batch.append(self._queue.get_nowait())
                except queue.Empty:
                    break
            self._push(batch)

    def _push(self, entries: list[tuple[str, str]]) -> None:
        payload: dict[str, Any] = {
            "streams": [
                {
                    "stream": self._labels,
                    "values": [[ts, line] for ts, line in entries],
                }
            ]
        }
        try:
            self._client.post(self._push_url, json=payload)
        except Exception:  # noqa: BLE001
            pass


class _ElasticsearchHandler(logging.Handler):
    """Batched bulk-index handler for Elasticsearch.

    Indexes documents into ``{index_prefix}-YYYY.MM.DD`` using the
    ``_bulk`` API.  Network errors are silently swallowed.
    """

    FLUSH_INTERVAL: float = 2.0
    BATCH_SIZE: int = 20

    def __init__(self, url: str, index_prefix: str = "autoflowops") -> None:
        super().__init__()
        self._bulk_url = url.rstrip("/") + "/_bulk"
        self._index_prefix = index_prefix
        self._queue: queue.SimpleQueue[tuple[str, dict[str, Any]]] = queue.SimpleQueue()
        self._client = httpx.Client(timeout=5.0)
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="es-shipper"
        )
        self._thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            doc: dict[str, Any] = json.loads(self.format(record))
            now = datetime.now(UTC)
            doc["@timestamp"] = doc.pop("timestamp", now.isoformat())
            date_str = now.strftime("%Y.%m.%d")
            self._queue.put_nowait((date_str, doc))
        except Exception:  # noqa: BLE001
            self.handleError(record)

    def _run(self) -> None:
        while True:
            batch: list[tuple[str, dict[str, Any]]] = []
            try:
                batch.append(self._queue.get(timeout=self.FLUSH_INTERVAL))
            except queue.Empty:
                continue
            while len(batch) < self.BATCH_SIZE:
                try:
                    batch.append(self._queue.get_nowait())
                except queue.Empty:
                    break
            self._push(batch)

    def _push(self, entries: list[tuple[str, dict[str, Any]]]) -> None:
        lines: list[str] = []
        for date_str, doc in entries:
            idx = f"{self._index_prefix}-{date_str}"
            lines.append(json.dumps({"index": {"_index": idx}}))
            lines.append(json.dumps(doc))
        body = "\n".join(lines) + "\n"
        try:
            self._client.post(
                self._bulk_url,
                content=body.encode(),
                headers={"Content-Type": "application/x-ndjson"},
            )
        except Exception:  # noqa: BLE001
            pass


def configure_log_shippers(
    *,
    loki_url: str = "",
    elasticsearch_url: str = "",
    labels: dict[str, str] | None = None,
    index_prefix: str = "autoflowops",
) -> None:
    """Attach optional remote log shippers to the root logger.

    Both shippers use ``_JSON_FORMATTER`` so log lines are always shipped
    as JSON regardless of the console renderer configured by
    ``configure_logging()``.

    Args:
        loki_url: Full base URL of the Loki instance
            (e.g. ``http://loki:3100``).  Leave blank to disable.
        elasticsearch_url: Full base URL of the Elasticsearch cluster
            (e.g. ``http://es:9200``).  Leave blank to disable.
        labels: Loki stream labels attached to every pushed entry.
            Defaults to ``{"app": "autoflowops"}``.
        index_prefix: Prefix for Elasticsearch daily indices.
    """
    if not loki_url and not elasticsearch_url:
        return

    effective_labels = labels if labels is not None else {"app": "autoflowops"}
    root = logging.getLogger()

    if loki_url:
        loki_handler = _LokiHandler(url=loki_url, labels=effective_labels)
        loki_handler.setFormatter(_JSON_FORMATTER)
        root.addHandler(loki_handler)
        _log.info("loki log shipping enabled", loki_url=loki_url)

    if elasticsearch_url:
        es_handler = _ElasticsearchHandler(
            url=elasticsearch_url, index_prefix=index_prefix
        )
        es_handler.setFormatter(_JSON_FORMATTER)
        root.addHandler(es_handler)
        _log.info("elasticsearch log shipping enabled", es_url=elasticsearch_url)
