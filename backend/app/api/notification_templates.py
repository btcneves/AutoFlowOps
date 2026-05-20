import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models.notification_template import NotificationTemplate
from app.models.user import User
from app.schemas.notification_template import (
    NotificationTemplateCreate,
    NotificationTemplateRead,
    NotificationTemplateUpdate,
)
from app.services.audit import client_ip, log_action

router = APIRouter(prefix="/notification-templates", tags=["notification-templates"])


async def _get_or_404(
    session: AsyncSession, template_id: uuid.UUID
) -> NotificationTemplate:
    result = await session.execute(
        select(NotificationTemplate).where(NotificationTemplate.id == template_id)
    )
    tmpl = result.scalar_one_or_none()
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Notification template not found")
    return tmpl


@router.post("", response_model=NotificationTemplateRead, status_code=201)
async def create_template(
    payload: NotificationTemplateCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> NotificationTemplateRead:
    tmpl = NotificationTemplate(
        name=payload.name,
        severity_filter=payload.severity_filter,
        title_template=payload.title_template,
        body_template=payload.body_template,
        is_default=payload.is_default,
    )
    session.add(tmpl)
    await session.flush()
    await log_action(
        session,
        action="templates.create",
        resource_type="notification_template",
        resource_id=str(tmpl.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"name": tmpl.name},
    )
    await session.commit()
    await session.refresh(tmpl)
    return NotificationTemplateRead.model_validate(tmpl)


@router.get("", response_model=list[NotificationTemplateRead])
async def list_templates(
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[NotificationTemplateRead]:
    result = await session.execute(
        select(NotificationTemplate).order_by(NotificationTemplate.created_at.desc())
    )
    return [NotificationTemplateRead.model_validate(t) for t in result.scalars().all()]


@router.get("/{template_id}", response_model=NotificationTemplateRead)
async def get_template(
    template_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> NotificationTemplateRead:
    tmpl = await _get_or_404(session, template_id)
    return NotificationTemplateRead.model_validate(tmpl)


@router.patch("/{template_id}", response_model=NotificationTemplateRead)
async def update_template(
    template_id: uuid.UUID,
    payload: NotificationTemplateUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> NotificationTemplateRead:
    tmpl = await _get_or_404(session, template_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(tmpl, field, value)
    await log_action(
        session,
        action="templates.update",
        resource_type="notification_template",
        resource_id=str(tmpl.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"updated_fields": list(updates.keys())},
    )
    await session.commit()
    await session.refresh(tmpl)
    return NotificationTemplateRead.model_validate(tmpl)


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    tmpl = await _get_or_404(session, template_id)
    await log_action(
        session,
        action="templates.delete",
        resource_type="notification_template",
        resource_id=str(tmpl.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"name": tmpl.name},
    )
    await session.delete(tmpl)
    await session.commit()
