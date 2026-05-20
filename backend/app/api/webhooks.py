import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_active_workspace, get_current_user, require_operator
from app.models.user import User
from app.models.webhook import Webhook, WebhookEvent
from app.models.workspace import Workspace
from app.schemas.webhook import (
    WebhookCreate,
    WebhookEventRead,
    WebhookRead,
    WebhookUpdate,
)
from app.services.audit import client_ip, log_action

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _get_or_404(session: AsyncSession, webhook_id: uuid.UUID) -> Webhook:
    result = await session.execute(select(Webhook).where(Webhook.id == webhook_id))
    wh = result.scalar_one_or_none()
    if wh is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return wh


@router.post("", response_model=WebhookRead, status_code=201)
async def create_webhook(
    payload: WebhookCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> WebhookRead:
    existing = await session.execute(
        select(Webhook).where(Webhook.slug == payload.slug)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Slug already in use")

    token_hash = _hash_token(payload.secret_token) if payload.secret_token else None
    wh = Webhook(
        name=payload.name,
        slug=payload.slug,
        secret_token_hash=token_hash,
    )
    session.add(wh)
    await session.flush()
    await log_action(
        session,
        action="webhooks.create",
        resource_type="webhook",
        resource_id=str(wh.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"name": wh.name, "slug": wh.slug},
    )
    await session.commit()
    await session.refresh(wh)
    return WebhookRead.model_validate(wh)


@router.get("", response_model=list[WebhookRead])
async def list_webhooks(
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> list[WebhookRead]:
    stmt = select(Webhook).order_by(Webhook.created_at.desc())
    if workspace is not None:
        stmt = stmt.where(Webhook.workspace_id == workspace.id)
    result = await session.execute(stmt)
    return [WebhookRead.model_validate(w) for w in result.scalars().all()]


@router.get("/{webhook_id}", response_model=WebhookRead)
async def get_webhook(
    webhook_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> WebhookRead:
    wh = await _get_or_404(session, webhook_id)
    return WebhookRead.model_validate(wh)


@router.patch("/{webhook_id}", response_model=WebhookRead)
async def update_webhook(
    webhook_id: uuid.UUID,
    payload: WebhookUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> WebhookRead:
    wh = await _get_or_404(session, webhook_id)
    updates = payload.model_dump(exclude_unset=True)
    if "secret_token" in updates:
        raw = updates.pop("secret_token")
        wh.secret_token_hash = _hash_token(raw) if raw else None
    for field, value in updates.items():
        setattr(wh, field, value)
    await log_action(
        session,
        action="webhooks.update",
        resource_type="webhook",
        resource_id=str(wh.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"updated_fields": list(updates.keys())},
    )
    await session.commit()
    await session.refresh(wh)
    return WebhookRead.model_validate(wh)


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> None:
    wh = await _get_or_404(session, webhook_id)
    await log_action(
        session,
        action="webhooks.delete",
        resource_type="webhook",
        resource_id=str(wh.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"name": wh.name},
    )
    await session.delete(wh)
    await session.commit()


@router.get("/{webhook_id}/events", response_model=list[WebhookEventRead])
async def list_events(
    webhook_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[WebhookEventRead]:
    await _get_or_404(session, webhook_id)
    result = await session.execute(
        select(WebhookEvent)
        .where(WebhookEvent.webhook_id == webhook_id)
        .order_by(WebhookEvent.received_at.desc())
    )
    return [WebhookEventRead.model_validate(e) for e in result.scalars().all()]


@router.post(
    "/{webhook_id}/events/{event_id}/reprocess",
    response_model=WebhookEventRead,
)
async def reprocess_event(
    webhook_id: uuid.UUID,
    event_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> WebhookEventRead:
    await _get_or_404(session, webhook_id)
    result = await session.execute(
        select(WebhookEvent).where(
            WebhookEvent.id == event_id,
            WebhookEvent.webhook_id == webhook_id,
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event.status = "reprocessed"
    event.processed_at = datetime.now(UTC)
    event.error_message = None
    await log_action(
        session,
        action="webhooks.reprocess_event",
        resource_type="webhook_event",
        resource_id=str(event.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    await session.refresh(event)
    return WebhookEventRead.model_validate(event)
