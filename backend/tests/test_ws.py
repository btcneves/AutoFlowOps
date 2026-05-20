"""WebSocket endpoint tests.

Tests cover:
- Unauthenticated connection (no token)      → error message + close 1008
- Invalid token                              → error message + close 1008
- JWT for non-existent DB user              → error message + close 1008
- Valid admin token (real DB user)           → connected message
- Ping/pong keepalive
- Connection manager broadcast
- Connection manager dead-connection cleanup
"""
import json
import uuid as _uuid

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.ws import manager
from app.config import settings
from app.main import app
from app.services.auth import create_access_token

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _admin_token(client: TestClient) -> str:
    """Log in as the bootstrap admin and return a real JWT."""
    resp = client.post(
        "/api/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ws_no_token_rejected():
    """Connection without token receives error message and is closed 1008."""
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/events") as ws:
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "error"
                ws.receive_text()
        assert exc_info.value.code == 1008


def test_ws_invalid_token_rejected():
    """Connection with a garbage token receives error and is closed 1008."""
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/events?token=not-a-valid-jwt") as ws:
                msg = json.loads(ws.receive_text())
                assert msg["type"] == "error"
                ws.receive_text()
        assert exc_info.value.code == 1008


def test_ws_nonexistent_user_rejected():
    """A JWT whose sub points to no DB row is rejected with 1008."""
    ghost_token = create_access_token(str(_uuid.uuid4()), "admin")
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws/events?token={ghost_token}") as ws:
                ws.receive_text()
                ws.receive_text()
        assert exc_info.value.code == 1008


def test_ws_valid_admin_connects():
    """Bootstrap admin token is accepted; server sends connected message."""
    with TestClient(app) as client:
        token = _admin_token(client)
        with client.websocket_connect(f"/ws/events?token={token}") as ws:
            msg = json.loads(ws.receive_text())
    assert msg["type"] == "connected"
    assert "user" in msg["data"]
    assert msg["data"]["user"] == settings.admin_email


def test_ws_ping_pong():
    """Client can send 'ping' and receives a 'pong' response."""
    with TestClient(app) as client:
        token = _admin_token(client)
        with client.websocket_connect(f"/ws/events?token={token}") as ws:
            ws.receive_text()  # consume connected message
            ws.send_text("ping")
            msg = json.loads(ws.receive_text())
    assert msg["type"] == "pong"


@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    """ConnectionManager.broadcast sends to all registered connections."""
    received: list[str] = []

    class _FakeWS:
        async def send_text(self, msg: str) -> None:
            received.append(msg)

    conn_id = str(_uuid.uuid4())
    manager._connections[conn_id] = _FakeWS()  # type: ignore[assignment]
    try:
        await manager.broadcast('{"type":"test"}')
    finally:
        manager._connections.pop(conn_id, None)

    assert received == ['{"type":"test"}']


@pytest.mark.asyncio
async def test_connection_manager_removes_dead_connections():
    """Broadcast silently removes connections that raise on send."""

    class _DeadWS:
        async def send_text(self, _: str) -> None:
            raise RuntimeError("closed")

    conn_id = str(_uuid.uuid4())
    manager._connections[conn_id] = _DeadWS()  # type: ignore[assignment]
    await manager.broadcast('{"type":"test"}')
    assert conn_id not in manager._connections
