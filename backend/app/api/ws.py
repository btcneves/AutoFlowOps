"""WebSocket endpoint for real-time event streaming.

Endpoint:  ws[s]://<host>/ws/events?token=<JWT>

Authentication is performed via the `token` query parameter because the
WebSocket handshake does not support HTTP Authorization headers in browsers.
The server accepts the connection first and immediately closes with code 1008
(Policy Violation) if the token is missing or invalid.

All authenticated users (viewer, operator, admin) receive the same event
stream.  The stream carries only safe, pre-masked fields — no secrets are
ever forwarded to clients.

Fan-out architecture:
  - A single long-running asyncio task subscribes to the Redis Pub/Sub
    channel `autoflowops:events` and re-broadcasts each message to every
    connected WebSocket via the in-process ConnectionManager singleton.
  - This task is started in the FastAPI lifespan and is cancelled on
    shutdown.  If Redis is unavailable the task exits gracefully; the WS
    endpoint still accepts connections but clients will not receive events
    until Redis becomes available again.
"""
import asyncio
import json
import logging
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings
from app.database import async_session_factory
from app.models.user import User
from app.services.auth import decode_access_token
from app.services.event_publisher import CHANNEL

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Thread-safe in-process registry of active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, conn_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[conn_id] = ws
        logger.debug("WS connected: %s (total=%d)", conn_id, len(self._connections))

    def disconnect(self, conn_id: str) -> None:
        self._connections.pop(conn_id, None)
        logger.debug(
            "WS disconnected: %s (total=%d)", conn_id, len(self._connections)
        )

    async def broadcast(self, message: str) -> None:
        dead: list[str] = []
        for cid, ws in list(self._connections.items()):
            try:
                await ws.send_text(message)
            except Exception:  # noqa: BLE001
                dead.append(cid)
        for cid in dead:
            self._connections.pop(cid, None)

    @property
    def count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Redis subscriber (started in lifespan, not called directly)
# ---------------------------------------------------------------------------


async def redis_subscriber() -> None:
    """Subscribe to Redis and fan out messages to all WS clients."""
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(CHANNEL)
        logger.info("Redis WS subscriber ready on channel %s", CHANNEL)
        async for raw in pubsub.listen():
            if raw["type"] != "message":
                continue
            if manager.count > 0:
                await manager.broadcast(raw["data"])
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Redis WS subscriber exited (%s) — real-time push disabled", exc
        )


# ---------------------------------------------------------------------------
# Authentication helper
# ---------------------------------------------------------------------------


async def _authenticate_ws(token: str | None) -> User | None:
    """Validate JWT and return the active user, or None on failure."""
    if not token:
        return None
    try:
        import uuid as _uuid

        payload = decode_access_token(token)
        user_id = _uuid.UUID(payload["sub"])
    except Exception:  # noqa: BLE001
        return None

    from sqlalchemy import select

    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return None
    return user


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.websocket("/ws/events")
async def ws_events(ws: WebSocket, token: str | None = None) -> None:
    """
    Real-time event stream.

    Query params:
        token (str): Valid JWT access token (required).

    Close codes:
        1008 — Policy Violation: missing or invalid token.
        1000 — Normal closure initiated by client.
    """
    await ws.accept()

    user = await _authenticate_ws(token)
    if user is None:
        await ws.send_text(
            json.dumps({"type": "error", "data": {"detail": "Unauthorized"}})
        )
        await ws.close(code=1008)
        return

    conn_id = str(uuid.uuid4())
    # The connection is already accepted above; register it directly.
    manager._connections[conn_id] = ws  # noqa: SLF001
    logger.debug("WS connected: %s (total=%d)", conn_id, manager.count)

    try:
        await ws.send_text(
            json.dumps({"type": "connected", "data": {"user": user.email}})
        )
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(conn_id)
