import hashlib
import json

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _create_webhook(
    client: AsyncClient,
    name: str = "My Hook",
    slug: str = "my-hook",
    secret_token: str | None = None,
) -> dict:
    body: dict = {"name": name, "slug": slug}
    if secret_token is not None:
        body["secret_token"] = secret_token
    r = await client.post("/api/webhooks", json=body)
    assert r.status_code == 201
    return r.json()


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def test_create_webhook(async_client: AsyncClient) -> None:
    data = await _create_webhook(async_client)
    assert data["name"] == "My Hook"
    assert data["slug"] == "my-hook"
    assert data["status"] == "active"
    assert data["last_received_at"] is None


async def test_create_webhook_duplicate_slug(async_client: AsyncClient) -> None:
    await _create_webhook(async_client)
    r = await async_client.post(
        "/api/webhooks", json={"name": "Other", "slug": "my-hook"}
    )
    assert r.status_code == 409


async def test_list_webhooks(async_client: AsyncClient) -> None:
    await _create_webhook(async_client, name="A", slug="hook-a")
    await _create_webhook(async_client, name="B", slug="hook-b")
    r = await async_client.get("/api/webhooks")
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_get_webhook(async_client: AsyncClient) -> None:
    created = await _create_webhook(async_client)
    r = await async_client.get(f"/api/webhooks/{created['id']}")
    assert r.status_code == 200
    assert r.json()["slug"] == "my-hook"


async def test_get_webhook_not_found(async_client: AsyncClient) -> None:
    r = await async_client.get("/api/webhooks/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


async def test_update_webhook_name(async_client: AsyncClient) -> None:
    created = await _create_webhook(async_client)
    r = await async_client.patch(
        f"/api/webhooks/{created['id']}", json={"name": "Renamed"}
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"


async def test_update_webhook_status(async_client: AsyncClient) -> None:
    created = await _create_webhook(async_client)
    r = await async_client.patch(
        f"/api/webhooks/{created['id']}", json={"status": "paused"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "paused"


async def test_delete_webhook(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    created = await _create_webhook(async_client)
    r = await async_client.delete(f"/api/webhooks/{created['id']}")
    assert r.status_code == 204
    r2 = await async_client.get(f"/api/webhooks/{created['id']}")
    assert r2.status_code == 404


# ── Receive ───────────────────────────────────────────────────────────────────


async def test_receive_webhook_no_token(async_client: AsyncClient) -> None:
    await _create_webhook(async_client, slug="open-hook")
    r = await async_client.post(
        "/api/webhooks/open-hook/receive",
        content=b'{"event":"ping"}',
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "received"
    assert data["payload"] is not None


async def test_receive_webhook_valid_token(async_client: AsyncClient) -> None:
    await _create_webhook(async_client, slug="secure-hook", secret_token="mysecret")
    r = await async_client.post(
        "/api/webhooks/secure-hook/receive",
        content=b"hello",
        headers={"X-Webhook-Token": "mysecret"},
    )
    assert r.status_code == 200


async def test_receive_webhook_invalid_token(async_client: AsyncClient) -> None:
    await _create_webhook(async_client, slug="secure-hook", secret_token="mysecret")
    r = await async_client.post(
        "/api/webhooks/secure-hook/receive",
        content=b"hello",
        headers={"X-Webhook-Token": "wrongtoken"},
    )
    assert r.status_code == 403


async def test_receive_webhook_missing_token(async_client: AsyncClient) -> None:
    await _create_webhook(async_client, slug="secure-hook", secret_token="mysecret")
    r = await async_client.post("/api/webhooks/secure-hook/receive", content=b"hello")
    assert r.status_code == 403


async def test_receive_webhook_not_found(async_client: AsyncClient) -> None:
    r = await async_client.post("/api/webhooks/nonexistent/receive", content=b"x")
    assert r.status_code == 404


async def test_receive_paused_webhook(async_client: AsyncClient) -> None:
    created = await _create_webhook(async_client, slug="paused-hook")
    await async_client.patch(
        f"/api/webhooks/{created['id']}", json={"status": "paused"}
    )
    r = await async_client.post("/api/webhooks/paused-hook/receive", content=b"x")
    assert r.status_code == 403


async def test_receive_updates_last_received_at(async_client: AsyncClient) -> None:
    created = await _create_webhook(async_client, slug="ts-hook")
    assert created["last_received_at"] is None
    await async_client.post("/api/webhooks/ts-hook/receive", content=b"ping")
    r = await async_client.get(f"/api/webhooks/{created['id']}")
    assert r.json()["last_received_at"] is not None


async def test_receive_masks_sensitive_headers(async_client: AsyncClient) -> None:
    await _create_webhook(async_client, slug="mask-hook")
    r = await async_client.post(
        "/api/webhooks/mask-hook/receive",
        content=b"{}",
        headers={
            "Authorization": "Bearer secret123",
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 200
    stored_headers = json.loads(r.json()["headers_masked"])
    assert stored_headers.get("authorization") == "***"


async def test_receive_masks_sensitive_payload(async_client: AsyncClient) -> None:
    await _create_webhook(async_client, slug="mask-payload")
    r = await async_client.post(
        "/api/webhooks/mask-payload/receive",
        content=b'{"password":"s3cr3t","event":"login"}',
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 200
    payload = json.loads(r.json()["payload"])
    assert payload["password"] == "***"
    assert payload["event"] == "login"


# ── Events ────────────────────────────────────────────────────────────────────


async def test_list_events(async_client: AsyncClient) -> None:
    created = await _create_webhook(async_client, slug="evt-hook")
    for _ in range(3):
        await async_client.post("/api/webhooks/evt-hook/receive", content=b"x")
    r = await async_client.get(f"/api/webhooks/{created['id']}/events")
    assert r.status_code == 200
    assert len(r.json()) == 3


async def test_list_events_unknown_webhook(async_client: AsyncClient) -> None:
    r = await async_client.get(
        "/api/webhooks/00000000-0000-0000-0000-000000000000/events"
    )
    assert r.status_code == 404


# ── Reprocess ─────────────────────────────────────────────────────────────────


async def test_reprocess_event(async_client: AsyncClient) -> None:
    created = await _create_webhook(async_client, slug="repr-hook")
    await async_client.post("/api/webhooks/repr-hook/receive", content=b"x")
    events_r = await async_client.get(f"/api/webhooks/{created['id']}/events")
    event_id = events_r.json()[0]["id"]

    r = await async_client.post(
        f"/api/webhooks/{created['id']}/events/{event_id}/reprocess"
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "reprocessed"
    assert data["processed_at"] is not None


async def test_reprocess_event_not_found(async_client: AsyncClient) -> None:
    created = await _create_webhook(async_client, slug="repr-miss")
    r = await async_client.post(
        f"/api/webhooks/{created['id']}/events/"
        "00000000-0000-0000-0000-000000000000/reprocess"
    )
    assert r.status_code == 404
