from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.notification import NotificationDelivery
from app.models.workspace import Workspace
from app.services.notifications import (
    _send_custom_webhook,
    _send_opsgenie,
    _send_pagerduty,
    dispatch_alert_notifications,
)


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


async def test_dispatch_alert_notifications_respects_workspace(
    db_session: AsyncSession,
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    sent: list[str] = []

    async def fake_send(channel_type, config, payload):
        sent.append(payload["alert_id"])

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)
    ws_a = Workspace(name="Notify A", slug="notify-a")
    ws_b = Workspace(name="Notify B", slug="notify-b")
    db_session.add_all([ws_a, ws_b])
    await db_session.commit()
    await db_session.refresh(ws_a)
    await db_session.refresh(ws_b)

    await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Workspace A channel",
            "type": "discord_webhook",
            "config": {"webhook_url": "https://discord.com/api/webhooks/123/secret"},
        },
        headers={"X-Workspace-ID": str(ws_a.id)},
    )
    alert = Alert(
        title="Workspace B alert",
        message="boom",
        severity="error",
        workspace_id=ws_b.id,
    )
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)

    deliveries = await dispatch_alert_notifications(db_session, alert)
    assert deliveries == []
    assert sent == []


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


async def test_create_pagerduty_channel_masks_routing_key(
    async_client: AsyncClient,
) -> None:
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Ops PagerDuty",
            "type": "pagerduty",
            "config": {"routing_key": "r1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6"},
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["type"] == "pagerduty"
    assert "r1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6" not in str(data)
    assert data["config_masked"]["routing_key"] == "***"


async def test_create_opsgenie_channel_masks_api_key(
    async_client: AsyncClient,
) -> None:
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Ops OpsGenie",
            "type": "opsgenie",
            "config": {"api_key": "og-secret-key-abc123", "region": "eu"},
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["type"] == "opsgenie"
    assert "og-secret-key-abc123" not in str(data)
    assert data["config_masked"]["api_key"] == "***"
    assert data["config_masked"]["region"] == "eu"


async def test_send_pagerduty_channel_success(
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    captured: dict = {}

    async def fake_send(channel_type, config, payload):
        assert channel_type == "pagerduty"
        captured["routing_key"] = config["routing_key"]

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)

    created = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "PD test",
            "type": "pagerduty",
            "config": {"routing_key": "rk-test-key"},
        },
    )
    channel_id = created.json()["id"]
    r = await async_client.post(f"/api/notification-channels/{channel_id}/test")
    assert r.status_code == 200
    assert r.json()["delivery"]["status"] == "success"
    assert captured["routing_key"] == "rk-test-key"


async def test_send_opsgenie_channel_success(
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    captured: dict = {}

    async def fake_send(channel_type, config, payload):
        assert channel_type == "opsgenie"
        captured["api_key"] = config["api_key"]
        captured["region"] = config.get("region")

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)

    created = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "OG test",
            "type": "opsgenie",
            "config": {"api_key": "og-key", "region": "us"},
        },
    )
    channel_id = created.json()["id"]
    r = await async_client.post(f"/api/notification-channels/{channel_id}/test")
    assert r.status_code == 200
    assert r.json()["delivery"]["status"] == "success"
    assert captured["api_key"] == "og-key"


async def test_opsgenie_invalid_region_rejected(
    async_client: AsyncClient,
) -> None:
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "OG bad region",
            "type": "opsgenie",
            "config": {"api_key": "key", "region": "invalid"},
        },
    )
    assert r.status_code == 422


async def test_pagerduty_missing_routing_key_rejected(
    async_client: AsyncClient,
) -> None:
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "PD no key",
            "type": "pagerduty",
            "config": {},
        },
    )
    assert r.status_code == 422


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


# ---------------------------------------------------------------------------
# Provider extension tests
# ---------------------------------------------------------------------------


async def test_pagerduty_dedup_key_template_sent(monkeypatch) -> None:
    captured: dict = {}

    async def fake_post(self, url, **kwargs):
        captured["body"] = kwargs.get("json", {})

        class FakeResp:
            def raise_for_status(self):
                pass

        return FakeResp()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    config = {
        "routing_key": "rk-test",
        "dedup_key_template": "{source_type}-{source_id}",
    }
    payload = {
        "title": "Job failed",
        "severity": "error",
        "message": "timeout",
        "alert_id": "aaa",
        "source_type": "job",
        "source_id": "bbb",
    }
    await _send_pagerduty(config, payload)
    assert captured["body"]["dedup_key"] == "job-bbb"


async def test_pagerduty_no_dedup_key_when_template_absent(monkeypatch) -> None:
    captured: dict = {}

    async def fake_post(self, url, **kwargs):
        captured["body"] = kwargs.get("json", {})

        class FakeResp:
            def raise_for_status(self):
                pass

        return FakeResp()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    config = {"routing_key": "rk-test"}
    payload = {
        "title": "Job failed",
        "severity": "error",
        "message": "timeout",
        "alert_id": "aaa",
        "source_type": "job",
        "source_id": "bbb",
    }
    await _send_pagerduty(config, payload)
    assert "dedup_key" not in captured["body"]


async def test_pagerduty_invalid_dedup_template_rejected(async_client: AsyncClient) -> None:  # noqa: E501
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "PD dedup bad",
            "type": "pagerduty",
            "config": {"routing_key": "rk-test", "dedup_key_template": "{unknown_var}"},
        },
    )
    assert r.status_code == 422


async def test_pagerduty_dedup_key_template_in_masked_config(async_client: AsyncClient) -> None:  # noqa: E501
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "PD dedup",
            "type": "pagerduty",
            "config": {
                "routing_key": "rk-test",
                "dedup_key_template": "{source_type}-{source_id}",
            },
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["config_masked"]["dedup_key_template"] == "{source_type}-{source_id}"
    assert data["config_masked"]["routing_key"] == "***"


async def test_opsgenie_priority_sent(monkeypatch) -> None:
    captured: dict = {}

    async def fake_post(self, url, **kwargs):
        captured["body"] = kwargs.get("json", {})

        class FakeResp:
            def raise_for_status(self):
                pass

        return FakeResp()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    config = {"api_key": "og-key", "priority": "P1"}
    payload = {
        "title": "Critical",
        "severity": "error",
        "message": "down",
        "alert_id": "aaa",
        "source_type": "job",
        "source_id": "bbb",
    }
    await _send_opsgenie(config, payload)
    assert captured["body"]["priority"] == "P1"


async def test_opsgenie_priority_auto_mapped_from_severity(monkeypatch) -> None:
    captured: dict = {}

    async def fake_post(self, url, **kwargs):
        captured["body"] = kwargs.get("json", {})

        class FakeResp:
            def raise_for_status(self):
                pass

        return FakeResp()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    config = {"api_key": "og-key"}
    payload = {
        "title": "Warning",
        "severity": "warning",
        "message": "slow",
        "alert_id": "aaa",
        "source_type": "job",
        "source_id": "bbb",
    }
    await _send_opsgenie(config, payload)
    assert captured["body"]["priority"] == "P3"


async def test_opsgenie_invalid_priority_rejected(async_client: AsyncClient) -> None:
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "OG bad priority",
            "type": "opsgenie",
            "config": {"api_key": "key", "priority": "P6"},
        },
    )
    assert r.status_code == 422


async def test_opsgenie_priority_in_masked_config(async_client: AsyncClient) -> None:
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "OG priority",
            "type": "opsgenie",
            "config": {"api_key": "og-key", "priority": "P2"},
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["config_masked"]["priority"] == "P2"
    assert data["config_masked"]["api_key"] == "***"


async def test_custom_webhook_payload_template_rendered(monkeypatch) -> None:
    captured: dict = {}

    async def fake_post(self, url, **kwargs):
        captured["body"] = kwargs.get("json", {})

        class FakeResp:
            def raise_for_status(self):
                pass

        return FakeResp()

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    template = '{{"event": "alert", "id": "{alert_id}", "sev": "{severity}"}}'
    config = {"url": "https://example.com/hook", "payload_template": template}
    payload = {
        "title": "Job failed",
        "severity": "error",
        "message": "timeout",
        "alert_id": "abc-123",
        "source_type": "job",
        "source_id": "xyz",
    }
    await _send_custom_webhook(config, payload)
    assert captured["body"] == {"event": "alert", "id": "abc-123", "sev": "error"}


async def test_custom_webhook_invalid_payload_template_rejected(async_client: AsyncClient) -> None:  # noqa: E501
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "CW bad template",
            "type": "custom_webhook",
            "config": {
                "url": "https://example.com/hook",
                "payload_template": "{unknown_var}",
            },
        },
    )
    assert r.status_code == 422


async def test_custom_webhook_non_json_payload_template_rejected(async_client: AsyncClient) -> None:  # noqa: E501
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "CW bad json",
            "type": "custom_webhook",
            "config": {
                "url": "https://example.com/hook",
                "payload_template": "not json {alert_id}",
            },
        },
    )
    assert r.status_code == 422


async def test_custom_webhook_payload_template_in_masked_config(async_client: AsyncClient) -> None:  # noqa: E501
    template = '{{"id": "{alert_id}"}}'
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": "CW template",
            "type": "custom_webhook",
            "config": {"url": "https://example.com/hook", "payload_template": template},
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["config_masked"]["payload_template"] == template
