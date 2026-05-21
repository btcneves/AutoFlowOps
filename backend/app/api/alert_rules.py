import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_active_workspace, get_current_user, require_operator
from app.models.alert_rule import AlertRule
from app.models.job import Job
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.alert_rule import (
    AlertRuleConditionType,
    AlertRuleCreate,
    AlertRuleRead,
    AlertRuleUpdate,
    validate_alert_rule_condition_value,
)
from app.services.audit import client_ip, log_action

router = APIRouter(prefix="/jobs/{job_id}/alert-rules", tags=["alert-rules"])


async def _get_job_or_404(
    session: AsyncSession,
    job_id: uuid.UUID,
    workspace: Workspace | None = None,
) -> Job:
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None or (workspace is not None and job.workspace_id != workspace.id):
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def _get_rule_or_404(
    session: AsyncSession,
    job_id: uuid.UUID,
    rule_id: uuid.UUID,
    workspace: Workspace | None = None,
) -> AlertRule:
    stmt = select(AlertRule).where(
        AlertRule.id == rule_id, AlertRule.job_id == job_id
    )
    if workspace is not None:
        stmt = stmt.where(AlertRule.workspace_id == workspace.id)
    result = await session.execute(stmt)
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


def _ensure_valid_condition_value(
    condition_type: AlertRuleConditionType | str,
    condition_value: str,
) -> None:
    try:
        validate_alert_rule_condition_value(
            condition_type,  # type: ignore[arg-type]
            condition_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[AlertRuleRead])
async def list_alert_rules(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> list[AlertRuleRead]:
    await _get_job_or_404(session, job_id, workspace)
    result = await session.execute(
        select(AlertRule)
        .where(AlertRule.job_id == job_id)
        .order_by(AlertRule.created_at.asc())
    )
    rules = result.scalars().all()
    return [AlertRuleRead.model_validate(r) for r in rules]


@router.post("", response_model=AlertRuleRead, status_code=201)
async def create_alert_rule(
    job_id: uuid.UUID,
    payload: AlertRuleCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> AlertRuleRead:
    job = await _get_job_or_404(session, job_id, workspace)
    rule = AlertRule(
        job_id=job.id,
        condition_type=payload.condition_type,
        condition_value=payload.condition_value,
        severity=payload.severity,
        message=payload.message,
        is_enabled=payload.is_enabled,
        workspace_id=job.workspace_id,
    )
    session.add(rule)
    await session.flush()
    await log_action(
        session,
        action="alert_rules.create",
        resource_type="alert_rule",
        resource_id=str(rule.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"job_id": str(job_id), "condition_type": rule.condition_type},
    )
    await session.commit()
    await session.refresh(rule)
    return AlertRuleRead.model_validate(rule)


@router.patch("/{rule_id}", response_model=AlertRuleRead)
async def update_alert_rule(
    job_id: uuid.UUID,
    rule_id: uuid.UUID,
    payload: AlertRuleUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> AlertRuleRead:
    await _get_job_or_404(session, job_id, workspace)
    rule = await _get_rule_or_404(session, job_id, rule_id, workspace)
    updates = payload.model_dump(exclude_unset=True)
    next_condition_type = updates.get("condition_type", rule.condition_type)
    next_condition_value = updates.get("condition_value", rule.condition_value)
    _ensure_valid_condition_value(next_condition_type, next_condition_value)
    for field, value in updates.items():
        setattr(rule, field, value)
    await log_action(
        session,
        action="alert_rules.update",
        resource_type="alert_rule",
        resource_id=str(rule_id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"updated_fields": list(updates.keys())},
    )
    await session.commit()
    await session.refresh(rule)
    return AlertRuleRead.model_validate(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_alert_rule(
    job_id: uuid.UUID,
    rule_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> None:
    await _get_job_or_404(session, job_id, workspace)
    rule = await _get_rule_or_404(session, job_id, rule_id, workspace)
    await log_action(
        session,
        action="alert_rules.delete",
        resource_type="alert_rule",
        resource_id=str(rule_id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"job_id": str(job_id)},
    )
    await session.delete(rule)
    await session.commit()
