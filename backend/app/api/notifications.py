import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.notification import NotificationChannel, NotificationDelivery
from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelRead,
    NotificationChannelUpdate,
    NotificationDeliveryRead,
    NotificationTestResult,
)
from app.services.notifications import (
    channel_to_read,
    dump_channel_config,
    send_channel_notification,
)

router = APIRouter(prefix="/notification-channels", tags=["notification-channels"])


async def _get_or_404(
    session: AsyncSession, channel_id: uuid.UUID
) -> NotificationChannel:
    result = await session.execute(
        select(NotificationChannel).where(NotificationChannel.id == channel_id)
    )
    channel = result.scalar_one_or_none()
    if channel is None:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    return channel


@router.post("", response_model=NotificationChannelRead, status_code=201)
async def create_channel(
    payload: NotificationChannelCreate,
    session: AsyncSession = Depends(get_db),
) -> NotificationChannelRead:
    channel = NotificationChannel(
        name=payload.name,
        type=payload.type,
        status=payload.status,
        config_encrypted=dump_channel_config(payload.config),
    )
    session.add(channel)
    await session.commit()
    await session.refresh(channel)
    return channel_to_read(channel)


@router.get("", response_model=list[NotificationChannelRead])
async def list_channels(
    session: AsyncSession = Depends(get_db),
) -> list[NotificationChannelRead]:
    result = await session.execute(
        select(NotificationChannel).order_by(NotificationChannel.created_at.desc())
    )
    return [channel_to_read(channel) for channel in result.scalars().all()]


@router.get("/deliveries", response_model=list[NotificationDeliveryRead])
async def list_deliveries(
    session: AsyncSession = Depends(get_db),
) -> list[NotificationDeliveryRead]:
    result = await session.execute(
        select(NotificationDelivery).order_by(NotificationDelivery.created_at.desc())
    )
    return [
        NotificationDeliveryRead.model_validate(delivery)
        for delivery in result.scalars().all()
    ]


@router.get("/{channel_id}", response_model=NotificationChannelRead)
async def get_channel(
    channel_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> NotificationChannelRead:
    channel = await _get_or_404(session, channel_id)
    return channel_to_read(channel)


@router.patch("/{channel_id}", response_model=NotificationChannelRead)
async def update_channel(
    channel_id: uuid.UUID,
    payload: NotificationChannelUpdate,
    session: AsyncSession = Depends(get_db),
) -> NotificationChannelRead:
    channel = await _get_or_404(session, channel_id)
    updates = payload.model_dump(exclude_unset=True)
    new_type = updates.get("type", channel.type)
    type_changed = "type" in updates and updates["type"] != channel.type
    if type_changed and "config" not in updates:
        raise HTTPException(
            status_code=422,
            detail="config is required when changing notification channel type",
        )
    if "name" in updates:
        channel.name = updates["name"]
    if "type" in updates:
        channel.type = updates["type"]
    if "status" in updates:
        channel.status = updates["status"]
    if "config" in updates:
        channel.type = new_type
        channel.config_encrypted = dump_channel_config(updates["config"])
    await session.commit()
    await session.refresh(channel)
    return channel_to_read(channel)


@router.post("/{channel_id}/test", response_model=NotificationTestResult)
async def test_channel(
    channel_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> NotificationTestResult:
    channel = await _get_or_404(session, channel_id)
    delivery = await send_channel_notification(session, channel, test=True)
    await session.refresh(channel)
    return NotificationTestResult(
        channel=channel_to_read(channel),
        delivery=NotificationDeliveryRead.model_validate(delivery),
    )


@router.patch("/{channel_id}/deactivate", response_model=NotificationChannelRead)
async def deactivate_channel(
    channel_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> NotificationChannelRead:
    channel = await _get_or_404(session, channel_id)
    channel.status = "paused"
    await session.commit()
    await session.refresh(channel)
    return channel_to_read(channel)


@router.patch("/{channel_id}/activate", response_model=NotificationChannelRead)
async def activate_channel(
    channel_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> NotificationChannelRead:
    channel = await _get_or_404(session, channel_id)
    channel.status = "active"
    await session.commit()
    await session.refresh(channel)
    return channel_to_read(channel)


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    channel = await _get_or_404(session, channel_id)
    await session.delete(channel)
    await session.commit()
