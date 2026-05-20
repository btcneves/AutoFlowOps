"""Escalation policy service.

When an alert fires, active escalation policies take precedence over the
direct "all active channels" dispatch. Each policy's step 0 (delay_minutes=0)
is dispatched immediately; subsequent steps create EscalationEvent records
that are processed by a periodic APScheduler job every 60 seconds.

If the alert is acknowledged or resolved before a deferred step fires, the
pending EscalationEvents for that alert are cancelled.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.escalation import EscalationEvent, EscalationPolicy, EscalationStep
from app.models.notification import NotificationChannel, NotificationDelivery

logger = logging.getLogger(__name__)


async def dispatch_via_escalation_policies(
    session: AsyncSession,
    alert: Alert,
) -> list[NotificationDelivery] | None:
    """Dispatch alert through active escalation policies.

    Returns a list of deliveries created for step-0 channels, or None if no
    active policies exist (signaling caller to fall back to direct dispatch).
    """
    result = await session.execute(
        select(EscalationPolicy)
        .where(EscalationPolicy.is_active.is_(True))
        .order_by(EscalationPolicy.created_at.asc())
    )
    policies = result.scalars().all()
    if not policies:
        return None

    from app.services.notifications import send_channel_notification

    all_deliveries: list[NotificationDelivery] = []
    now = datetime.now(UTC)

    for policy in policies:
        steps_result = await session.execute(
            select(EscalationStep)
            .where(EscalationStep.policy_id == policy.id)
            .order_by(EscalationStep.step_order.asc())
        )
        steps = steps_result.scalars().all()
        if not steps:
            continue

        for step in steps:
            channel_result = await session.execute(
                select(NotificationChannel).where(
                    NotificationChannel.id == step.channel_id,
                    NotificationChannel.status == "active",
                )
            )
            channel = channel_result.scalar_one_or_none()
            if channel is None:
                logger.warning(
                    "Escalation step %s references inactive/missing channel %s",
                    step.id,
                    step.channel_id,
                )
                continue

            if step.delay_minutes == 0:
                # Dispatch immediately
                delivery = await send_channel_notification(session, channel, alert)
                all_deliveries.append(delivery)
                event = EscalationEvent(
                    policy_id=policy.id,
                    alert_id=alert.id,
                    step_order=step.step_order,
                    channel_id=step.channel_id,
                    status="dispatched",
                    scheduled_at=now,
                    dispatched_at=now,
                )
                session.add(event)
            else:
                # Schedule for later
                scheduled_at = now + timedelta(minutes=step.delay_minutes)
                event = EscalationEvent(
                    policy_id=policy.id,
                    alert_id=alert.id,
                    step_order=step.step_order,
                    channel_id=step.channel_id,
                    status="pending",
                    scheduled_at=scheduled_at,
                )
                session.add(event)
                logger.info(
                    "Escalation step %s (policy=%s, channel=%s) scheduled for %s",
                    step.step_order,
                    policy.id,
                    step.channel_id,
                    scheduled_at.isoformat(),
                )

    await session.commit()
    return all_deliveries


async def process_pending_escalation_events(session: AsyncSession) -> int:
    """Process pending escalation events whose scheduled_at has passed.

    Called by the APScheduler periodic job every 60 seconds.
    Returns the number of events processed.
    """
    from app.services.notifications import send_channel_notification

    now = datetime.now(UTC)
    result = await session.execute(
        select(EscalationEvent)
        .where(
            EscalationEvent.status == "pending",
            EscalationEvent.scheduled_at <= now,
        )
        .order_by(EscalationEvent.scheduled_at.asc())
    )
    events = result.scalars().all()
    processed = 0

    for event in events:
        # Check if the alert is still open
        alert_result = await session.execute(
            select(Alert).where(Alert.id == event.alert_id)
        )
        alert = alert_result.scalar_one_or_none()

        if alert is None or alert.status in ("acknowledged", "resolved"):
            event.status = "cancelled"
            session.add(event)
            logger.info(
                "Escalation event %s cancelled — alert %s is %s",
                event.id,
                event.alert_id,
                getattr(alert, "status", "deleted"),
            )
            processed += 1
            continue

        # Alert still open — dispatch to channel
        channel_result = await session.execute(
            select(NotificationChannel).where(
                NotificationChannel.id == event.channel_id,
                NotificationChannel.status == "active",
            )
        )
        channel = channel_result.scalar_one_or_none()

        if channel is None:
            event.status = "cancelled"
            session.add(event)
            logger.warning(
                "Escalation event %s cancelled — channel %s not found or inactive",
                event.id,
                event.channel_id,
            )
            processed += 1
            continue

        try:
            await send_channel_notification(session, channel, alert)
            event.status = "dispatched"
            event.dispatched_at = now
        except Exception:  # noqa: BLE001
            logger.exception(
                "Error dispatching escalation event %s to channel %s",
                event.id,
                event.channel_id,
            )
            event.status = "cancelled"

        session.add(event)
        processed += 1

    if processed:
        await session.commit()
    return processed


async def cancel_pending_escalations_for_alert(
    session: AsyncSession, alert_id: str
) -> int:
    """Cancel all pending escalation events for an alert (call on resolve/ack)."""
    import uuid

    result = await session.execute(
        select(EscalationEvent).where(
            EscalationEvent.alert_id == uuid.UUID(str(alert_id)),
            EscalationEvent.status == "pending",
        )
    )
    events = result.scalars().all()
    for event in events:
        event.status = "cancelled"
        session.add(event)
    if events:
        await session.commit()
    return len(events)
