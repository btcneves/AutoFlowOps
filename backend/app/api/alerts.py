import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_operator
from app.models.alert import Alert
from app.models.user import User
from app.schemas.alert import AlertRead
from app.services.audit import client_ip, log_action

router = APIRouter(prefix="/alerts", tags=["alerts"])


async def _get_or_404(session: AsyncSession, alert_id: uuid.UUID) -> Alert:
    result = await session.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("", response_model=list[AlertRead])
async def list_alerts(
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[AlertRead]:
    stmt = select(Alert).order_by(Alert.created_at.desc())
    if status is not None:
        stmt = stmt.where(Alert.status == status)
    result = await session.execute(stmt)
    return [AlertRead.model_validate(a) for a in result.scalars().all()]


@router.patch("/{alert_id}/resolve", response_model=AlertRead)
async def resolve_alert(
    alert_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> AlertRead:
    alert = await _get_or_404(session, alert_id)
    if alert.status == "resolved":
        raise HTTPException(status_code=409, detail="Alert is already resolved")
    alert.status = "resolved"
    alert.resolved_at = datetime.now(UTC)
    await log_action(
        session,
        action="alerts.resolve",
        resource_type="alert",
        resource_id=str(alert.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    await session.refresh(alert)
    return AlertRead.model_validate(alert)


@router.patch("/{alert_id}/acknowledge", response_model=AlertRead)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
) -> AlertRead:
    alert = await _get_or_404(session, alert_id)
    if alert.status == "resolved":
        raise HTTPException(status_code=409, detail="Alert is already resolved")
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(UTC)
    await log_action(
        session,
        action="alerts.acknowledge",
        resource_type="alert",
        resource_id=str(alert.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    await session.commit()
    await session.refresh(alert)
    return AlertRead.model_validate(alert)
