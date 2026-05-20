"""Tests for notification templates CRUD and rendering."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.services.notifications import dispatch_alert_notifications


async def test_create_template(async_client: AsyncClient) -> None:
    r = await async_client.post(
        "/api/notification-templates",
        json={
            "name": "Error template",
            "severity_filter": "error",
            "title_template": "ALERT: {title}",
            "body_template": "{title}\n\n{message}",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Error template"
    assert data["severity_filter"] == "error"
    assert data["title_template"] == "ALERT: {title}"


async def test_list_templates(async_client: AsyncClient) -> None:
    await async_client.post(
        "/api/notification-templates",
        json={"name": "T1", "severity_filter": "error"},
    )
    await async_client.post(
        "/api/notification-templates",
        json={"name": "T2", "severity_filter": "warning"},
    )
    r = await async_client.get("/api/notification-templates")
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_update_template(async_client: AsyncClient) -> None:
    created = await async_client.post(
        "/api/notification-templates",
        json={"name": "Old name", "severity_filter": "error"},
    )
    tmpl_id = created.json()["id"]
    r = await async_client.patch(
        f"/api/notification-templates/{tmpl_id}",
        json={"name": "New name"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "New name"


async def test_delete_template(async_client: AsyncClient) -> None:
    created = await async_client.post(
        "/api/notification-templates",
        json={"name": "ToDelete"},
    )
    tmpl_id = created.json()["id"]
    r = await async_client.delete(f"/api/notification-templates/{tmpl_id}")
    assert r.status_code == 204
    r2 = await async_client.get(f"/api/notification-templates/{tmpl_id}")
    assert r2.status_code == 404


async def test_template_applied_to_delivery(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    """Template title/body should be used when dispatching a notification."""
    await async_client.post(
        "/api/notification-templates",
        json={
            "name": "Error tmpl",
            "severity_filter": "error",
            "title_template": "CRITICAL: {title}",
            "body_template": "Alert: {title}\nMsg: {message}",
        },
    )

    captured: dict = {}

    async def fake_send(channel_type, config, payload):
        captured.update(payload)

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)

    await async_client.post(
        "/api/notification-channels",
        json={
            "name": "Test Channel",
            "type": "custom_webhook",
            "config": {"url": "https://example.com/hook", "headers": {}},
        },
    )
    alert = Alert(title="Job failed", message="timeout", severity="error")
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)

    await dispatch_alert_notifications(db_session, alert)
    assert captured.get("rendered_title") == "CRITICAL: Job failed"
    assert "timeout" in captured.get("rendered_body", "")


async def test_builtin_fallback_when_no_template(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    captured: dict = {}

    async def fake_send(channel_type, config, payload):
        captured.update(payload)

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)

    await async_client.post(
        "/api/notification-channels",
        json={
            "name": "NoTmpl Channel",
            "type": "custom_webhook",
            "config": {"url": "https://example.com/hook", "headers": {}},
        },
    )
    alert = Alert(title="No template", message="raw msg", severity="error")
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)

    await dispatch_alert_notifications(db_session, alert)
    # Built-in title template is "{title}" → "No template"
    assert captured.get("rendered_title") == "No template"
