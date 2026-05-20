"""Publishes domain events to the Redis Pub/Sub channel.

Provides both a sync variant (for Celery worker tasks) and an async variant
(for the FastAPI / asyncio context).  Failures are logged and swallowed so
that event publishing never blocks or breaks the primary execution path.
"""
import json
import logging
from datetime import UTC, datetime

import redis
import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

CHANNEL = "autoflowops:events"

_sync_client: redis.Redis | None = None
_async_client: aioredis.Redis | None = None


def _get_sync_client() -> redis.Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _sync_client


def _get_async_client() -> aioredis.Redis:
    global _async_client
    if _async_client is None:
        _async_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _async_client


def _build_message(event_type: str, data: dict) -> str:
    return json.dumps(
        {"type": event_type, "data": data, "ts": datetime.now(UTC).isoformat()}
    )


def publish_event(event_type: str, data: dict) -> None:
    """Synchronous publish — use from Celery worker (non-async context)."""
    try:
        _get_sync_client().publish(CHANNEL, _build_message(event_type, data))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Event publish failed [%s]: %s", event_type, exc)


async def publish_event_async(event_type: str, data: dict) -> None:
    """Async publish — use from FastAPI request handlers and APScheduler callbacks."""
    try:
        await _get_async_client().publish(CHANNEL, _build_message(event_type, data))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Event publish failed [%s]: %s", event_type, exc)
