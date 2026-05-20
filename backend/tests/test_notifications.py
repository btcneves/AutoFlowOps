from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.notification import NotificationDelivery
from app.services.notifications import dispatch_alert_notifications


async def test_create_slack_channel_masks_webhook_url(
    async_client: AsyncClient,
) -> None:
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Ops Slack",
            "type": "slack_webhook",
            "config": {
                "webhook_url": "https://hooks.slack.com/services/T123/B456/secret-token"
            },
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["type"] == "slack_webhook"
    assert "secret-token" not in str(data)
    assert data["config_masked"]["webhook_url"] == "https://hooks.slack.com/***"


async def test_create_telegram_channel_masks_bot_token(
    async_client: AsyncClient,
) -> None:
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Ops Telegram",
            "type": "telegram_message",
            "config": {
                "bot_token": "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi",
                "chat_id": "-100123456789",
            },
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["type"] == "telegram_message"
    # Full token must not appear
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi" not in str(data)
    # Masked token shows numeric prefix + :***
    masked_token = data["config_masked"]["bot_token"]
    assert masked_token.startswith("1234567890:")
    assert "***" in masked_token
    # chat_id may be shown (not a secret)
    assert data["config_masked"]["chat_id"] == "-100123456789"


async def test_send_slack_channel_success(
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    captured: dict = {}

    async def fake_send(channel_type, config, payload):
        assert channel_type == "slack_webhook"
        captured["url"] = config["webhook_url"]
        captured["payload"] = payload

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)

    created = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Slack delivery test",
            "type": "slack_webhook",
            "config": {"webhook_url": "https://hooks.slack.com/services/T/B/secret"},
        },
    )
    channel_id = created.json()["id"]
    r = await async_client.post(f"/api/notification-channels/{channel_id}/test")
    assert r.status_code == 200
    assert r.json()["delivery"]["status"] == "success"
    assert captured["url"] == "https://hooks.slack.com/services/T/B/secret"


async def test_send_telegram_channel_success(
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    captured: dict = {}

    async def fake_send(channel_type, config, payload):
        assert channel_type == "telegram_message"
        captured["bot_token"] = config["bot_token"]
        captured["chat_id"] = config["chat_id"]

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)

    created = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Telegram delivery test",
            "type": "telegram_message",
            "config": {"bot_token": "9999:TTTTT", "chat_id": "-100000000"},
        },
    )
    channel_id = created.json()["id"]
    r = await async_client.post(f"/api/notification-channels/{channel_id}/test")
    assert r.status_code == 200
    assert r.json()["delivery"]["status"] == "success"
    # The real token (from decrypted config) was used but must not appear in response
    assert "9999:TTTTT" not in str(r.json())


async def test_telegram_token_not_in_delivery_error(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    async def fake_send(channel_type, config, payload):
        raise RuntimeError(f"bad token: {config['bot_token']}")

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)

    await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Leaky Telegram",
            "type": "telegram_message",
            "config": {"bot_token": "8888:REAL-SECRET-TOKEN", "chat_id": "-1"},
        },
    )
    alert = Alert(title="Escalation test", message="fail", severity="error")
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)

    await dispatch_alert_notifications(db_session, alert)
    result = await db_session.execute(select(NotificationDelivery))
    delivery = result.scalar_one()
    assert delivery.status == "failed"
    assert "REAL-SECRET-TOKEN" not in (delivery.error_message or "")
    assert "***" in (delivery.error_message or "")


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
