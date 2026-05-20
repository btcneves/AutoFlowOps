import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification_template import NotificationTemplate
from app.schemas.notification_template import (
    NotificationTemplateCreate,
    NotificationTemplateRead,
    NotificationTemplateUpdate,
)

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
    session: AsyncSession = Depends(get_db),
) -> NotificationTemplateRead:
    tmpl = NotificationTemplate(
        name=payload.name,
        severity_filter=payload.severity_filter,
        title_template=payload.title_template,
        body_template=payload.body_template,
        is_default=payload.is_default,
    )
    session.add(tmpl)
    await session.commit()
    await session.refresh(tmpl)
    return NotificationTemplateRead.model_validate(tmpl)


@router.get("", response_model=list[NotificationTemplateRead])
async def list_templates(
    session: AsyncSession = Depends(get_db),
) -> list[NotificationTemplateRead]:
    result = await session.execute(
        select(NotificationTemplate).order_by(NotificationTemplate.created_at.desc())
    )
    return [NotificationTemplateRead.model_validate(t) for t in result.scalars().all()]


@router.get("/{template_id}", response_model=NotificationTemplateRead)
async def get_template(
    template_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> NotificationTemplateRead:
    tmpl = await _get_or_404(session, template_id)
    return NotificationTemplateRead.model_validate(tmpl)


@router.patch("/{template_id}", response_model=NotificationTemplateRead)
async def update_template(
    template_id: uuid.UUID,
    payload: NotificationTemplateUpdate,
    session: AsyncSession = Depends(get_db),
) -> NotificationTemplateRead:
    tmpl = await _get_or_404(session, template_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(tmpl, field, value)
    await session.commit()
    await session.refresh(tmpl)
    return NotificationTemplateRead.model_validate(tmpl)


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    tmpl = await _get_or_404(session, template_id)
    await session.delete(tmpl)
    await session.commit()
