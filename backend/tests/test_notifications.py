from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.notification import NotificationDelivery
from app.services.notifications import dispatch_alert_notifications


async def test_create_notification_channel_masks_secret(
    async_client: AsyncClient,
) -> None:
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Ops Discord",
            "type": "discord_webhook",
            "config": {
                "webhook_url": "https://discord.com/api/webhooks/123/secret-token"
            },
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Ops Discord"
    assert data["type"] == "discord_webhook"
    assert data["status"] == "active"
    assert data["config_masked"]["webhook_url"] == "https://discord.com/***"
    assert "secret-token" not in str(data)


async def test_update_notification_channel_status(
    async_client: AsyncClient,
) -> None:
    created = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Ops Custom",
            "type": "custom_webhook",
            "config": {"url": "https://example.com/hook", "headers": {}},
        },
    )
    channel_id = created.json()["id"]

    r = await async_client.patch(
        f"/api/notification-channels/{channel_id}",
        json={"name": "Paused Custom", "status": "paused"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Paused Custom"
    assert r.json()["status"] == "paused"


async def test_test_notification_channel_records_delivery(
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    async def fake_send(channel_type, config, payload):
        assert channel_type == "custom_webhook"
        assert payload["alert_id"] == "test"

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)
    created = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Ops Custom",
            "type": "custom_webhook",
            "config": {"url": "https://example.com/hook", "headers": {}},
        },
    )
    channel_id = created.json()["id"]

    r = await async_client.post(f"/api/notification-channels/{channel_id}/test")
    assert r.status_code == 200
    data = r.json()
    assert data["delivery"]["status"] == "success"
    assert data["channel"]["last_tested_at"] is not None


async def test_dispatch_alert_notifications_records_success(
    db_session: AsyncSession,
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    async def fake_send(channel_type, config, payload):
        assert payload["severity"] == "error"
        assert payload["title"] == "Job failed"

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)
    await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Ops Discord",
            "type": "discord_webhook",
            "config": {
                "webhook_url": "https://discord.com/api/webhooks/123/secret-token"
            },
        },
    )
    alert = Alert(title="Job failed", message="boom", severity="error")
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)

    deliveries = await dispatch_alert_notifications(db_session, alert)
    assert len(deliveries) == 1
    assert deliveries[0].status == "success"


async def test_dispatch_alert_notifications_records_masked_failure(
    db_session: AsyncSession,
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    async def fake_send(channel_type, config, payload):
        raise RuntimeError(f"failed with {config['headers']['Authorization']}")

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)
    await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Ops Custom",
            "type": "custom_webhook",
            "config": {
                "url": "https://example.com/hook",
                "headers": {"Authorization": "Bearer real-token"},
            },
        },
    )
    alert = Alert(title="Webhook failed", message="bad token", severity="error")
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)

    await dispatch_alert_notifications(db_session, alert)
    result = await db_session.execute(select(NotificationDelivery))
    delivery = result.scalar_one()
    assert delivery.status == "failed"
    assert "real-token" not in (delivery.error_message or "")
    assert "***" in (delivery.error_message or "")


async def test_invalid_webhook_token_creates_notification_delivery(
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    async def fake_send(channel_type, config, payload):
        assert payload["source_type"] == "webhook"

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)
    await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Ops Custom",
            "type": "custom_webhook",
            "config": {"url": "https://example.com/hook", "headers": {}},
        },
    )
    webhook = await async_client.post(
        "/api/webhooks",
        json={"name": "Orders", "slug": "orders", "secret_token": "correct"},
    )
    assert webhook.status_code == 201

    r = await async_client.post(
        "/api/webhooks/orders/receive",
        headers={"X-Webhook-Token": "wrong"},
        json={"event": "order.created"},
    )
    assert r.status_code == 403

    deliveries = await async_client.get("/api/notification-channels/deliveries")
    assert deliveries.status_code == 200
    assert deliveries.json()[0]["status"] == "success"
