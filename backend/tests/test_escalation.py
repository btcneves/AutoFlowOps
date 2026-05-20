"""Tests for escalation policies, steps and event processing."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.escalation import EscalationEvent, EscalationPolicy
from app.models.notification import NotificationChannel
from app.services.escalation import (
    cancel_pending_escalations_for_alert,
    process_pending_escalation_events,
)
from app.services.notifications import dispatch_alert_notifications


async def _create_channel(async_client: AsyncClient, name: str = "Test Channel") -> str:
    r = await async_client.post(
        "/api/notification-channels",
        json={
            "name": name,
            "type": "custom_webhook",
            "config": {"url": "https://example.com/hook", "headers": {}},
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


async def test_create_escalation_policy(async_client: AsyncClient) -> None:
    channel_id = await _create_channel(async_client)
    r = await async_client.post(
        "/api/escalation-policies",
        json={
            "name": "Ops escalation",
            "is_active": True,
            "steps": [
                {"channel_id": channel_id, "step_order": 0, "delay_minutes": 0},
                {"channel_id": channel_id, "step_order": 1, "delay_minutes": 10},
            ],
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Ops escalation"
    assert data["is_active"] is True
    assert len(data["steps"]) == 2


async def test_list_escalation_policies(async_client: AsyncClient) -> None:
    channel_id = await _create_channel(async_client)
    await async_client.post(
        "/api/escalation-policies",
        json={
            "name": "P1",
            "steps": [{"channel_id": channel_id, "step_order": 0, "delay_minutes": 0}],
        },
    )
    r = await async_client.get("/api/escalation-policies")
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_update_escalation_policy(async_client: AsyncClient) -> None:
    r = await async_client.post(
        "/api/escalation-policies",
        json={"name": "Old policy"},
    )
    policy_id = r.json()["id"]
    r2 = await async_client.patch(
        f"/api/escalation-policies/{policy_id}",
        json={"name": "New policy", "is_active": False},
    )
    assert r2.status_code == 200
    assert r2.json()["name"] == "New policy"
    assert r2.json()["is_active"] is False


async def test_step0_dispatched_immediately(
    db_session: AsyncSession,
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    """Step 0 (delay=0) fires immediately; step 1 (delay>0) creates a pending event."""
    dispatched: list[str] = []

    async def fake_send(channel_type, config, payload):
        dispatched.append(payload["alert_id"])

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)

    channel_id = await _create_channel(async_client, "Ch-A")
    await async_client.post(
        "/api/escalation-policies",
        json={
            "name": "Two-step",
            "steps": [
                {"channel_id": channel_id, "step_order": 0, "delay_minutes": 0},
                {"channel_id": channel_id, "step_order": 1, "delay_minutes": 30},
            ],
        },
    )

    alert = Alert(title="Critical failure", message="disk full", severity="error")
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)

    deliveries = await dispatch_alert_notifications(db_session, alert)
    # Step 0 dispatched immediately
    assert len(deliveries) == 1
    assert dispatched[0] == str(alert.id)

    # Step 1 created as pending EscalationEvent
    pending = await db_session.execute(
        select(EscalationEvent).where(
            EscalationEvent.alert_id == alert.id,
            EscalationEvent.status == "pending",
        )
    )
    assert pending.scalar_one() is not None


async def test_deferred_step_dispatched_on_schedule(
    db_session: AsyncSession,
    async_client: AsyncClient,
    monkeypatch,
) -> None:
    """process_pending_escalation_events dispatches overdue events."""
    dispatched: list = []

    async def fake_send(channel_type, config, payload):
        dispatched.append(payload)

    monkeypatch.setattr("app.services.notifications._send_channel", fake_send)

    await _create_channel(async_client, "Ch-B")

    alert = Alert(title="Disk full", message="90%", severity="error")
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)

    # Inject a pending event already past its scheduled_at
    channel_result = await db_session.execute(
        select(NotificationChannel).where(NotificationChannel.name == "Ch-B")
    )
    channel = channel_result.scalar_one()
    policy = EscalationPolicy(name="Direct policy")
    db_session.add(policy)
    await db_session.flush()
    event = EscalationEvent(
        policy_id=policy.id,
        alert_id=alert.id,
        step_order=1,
        channel_id=channel.id,
        status="pending",
        scheduled_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    db_session.add(event)
    await db_session.commit()

    processed = await process_pending_escalation_events(db_session)
    assert processed == 1
    assert len(dispatched) == 1
    await db_session.refresh(event)
    assert event.status == "dispatched"


async def test_deferred_event_cancelled_when_alert_resolved(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    await _create_channel(async_client, "Ch-C")
    channel_result = await db_session.execute(
        select(NotificationChannel).where(NotificationChannel.name == "Ch-C")
    )
    channel = channel_result.scalar_one()

    alert = Alert(
        title="Resolved alert", message="fixed", severity="error", status="resolved"
    )
    db_session.add(alert)
    policy = EscalationPolicy(name="Resolved policy")
    db_session.add(policy)
    await db_session.flush()
    event = EscalationEvent(
        policy_id=policy.id,
        alert_id=alert.id,
        step_order=1,
        channel_id=channel.id,
        status="pending",
        scheduled_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(event)
    await db_session.commit()

    processed = await process_pending_escalation_events(db_session)
    assert processed == 1
    await db_session.refresh(event)
    assert event.status == "cancelled"


async def test_cancel_pending_escalations(
    db_session: AsyncSession,
    async_client: AsyncClient,
) -> None:
    await _create_channel(async_client, "Ch-D")
    channel_result = await db_session.execute(
        select(NotificationChannel).where(NotificationChannel.name == "Ch-D")
    )
    channel = channel_result.scalar_one()

    alert = Alert(title="Ack alert", message="acked", severity="error")
    db_session.add(alert)
    policy = EscalationPolicy(name="Cancel policy")
    db_session.add(policy)
    await db_session.flush()

    for i in range(3):
        db_session.add(
            EscalationEvent(
                policy_id=policy.id,
                alert_id=alert.id,
                step_order=i + 1,
                channel_id=channel.id,
                status="pending",
                scheduled_at=datetime.now(UTC) + timedelta(minutes=10),
            )
        )
    await db_session.commit()

    cancelled = await cancel_pending_escalations_for_alert(db_session, str(alert.id))
    assert cancelled == 3
