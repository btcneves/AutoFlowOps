"""Public webhook receive endpoint — no authentication required."""

import hashlib
import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alert import Alert
from app.models.webhook import Webhook, WebhookEvent
from app.schemas.webhook import WebhookEventRead
from app.services.masking import mask_sensitive_body, mask_sensitive_headers
from app.services.notifications import dispatch_alert_notifications
from app.services.rate_limiter import webhook_rate_limit

router = APIRouter(tags=["webhooks"])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _create_webhook_alert(
    session: AsyncSession,
    webhook: Webhook,
    message: str,
) -> None:
    alert = Alert(
        title=f'Webhook "{webhook.name}" delivery failed',
        message=message,
        severity="error",
        source_type="webhook",
        source_id=webhook.id,
    )
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    await dispatch_alert_notifications(session, alert)


@router.post("/webhooks/{slug}/receive", response_model=WebhookEventRead)
async def receive_webhook(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> WebhookEventRead:
    webhook_rate_limit(request, slug)

    result = await session.execute(select(Webhook).where(Webhook.slug == slug))
    wh = result.scalar_one_or_none()
    if wh is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if wh.status != "active":
        await _create_webhook_alert(
            session, wh, "Webhook received an event while paused"
        )
        raise HTTPException(status_code=403, detail="Webhook is not active")
    if wh.secret_token_hash is not None:
        token_header = request.headers.get("X-Webhook-Token", "")
        if not token_header or _hash_token(token_header) != wh.secret_token_hash:
            await _create_webhook_alert(session, wh, "Webhook token validation failed")
            raise HTTPException(status_code=403, detail="Invalid webhook token")

    raw_body = await request.body()
    body_str = raw_body.decode("utf-8", errors="replace") if raw_body else None
    masked_headers = mask_sensitive_headers(dict(request.headers))
    masked_payload = mask_sensitive_body(body_str)
    source_ip = request.client.host if request.client else None

    event = WebhookEvent(
        webhook_id=wh.id,
        headers_masked=json.dumps(masked_headers),
        payload=masked_payload,
        source_ip=source_ip,
        status="received",
    )
    session.add(event)
    wh.last_received_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(event)
    return WebhookEventRead.model_validate(event)
