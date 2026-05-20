import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_active_workspace, get_current_user, require_admin
from app.models.escalation import EscalationEvent, EscalationPolicy, EscalationStep
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.escalation import (
    EscalationEventRead,
    EscalationPolicyCreate,
    EscalationPolicyRead,
    EscalationPolicyUpdate,
    EscalationStepCreate,
    EscalationStepRead,
)
from app.services.audit import client_ip, log_action

router = APIRouter(prefix="/escalation-policies", tags=["escalation-policies"])


async def _get_policy_or_404(
    session: AsyncSession, policy_id: uuid.UUID
) -> EscalationPolicy:
    result = await session.execute(
        select(EscalationPolicy).where(EscalationPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=404, detail="Escalation policy not found")
    return policy


async def _load_steps(
    session: AsyncSession, policy_id: uuid.UUID
) -> list[EscalationStep]:
    result = await session.execute(
        select(EscalationStep)
        .where(EscalationStep.policy_id == policy_id)
        .order_by(EscalationStep.step_order.asc())
    )
    return list(result.scalars().all())


def _policy_to_read(
    policy: EscalationPolicy, steps: list[EscalationStep]
) -> EscalationPolicyRead:
    return EscalationPolicyRead(
        id=policy.id,
        name=policy.name,
        is_active=policy.is_active,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
        steps=[EscalationStepRead.model_validate(s) for s in steps],
    )


@router.post("", response_model=EscalationPolicyRead, status_code=201)
async def create_policy(
    payload: EscalationPolicyCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> EscalationPolicyRead:
    policy = EscalationPolicy(name=payload.name, is_active=payload.is_active)
    session.add(policy)
    await session.flush()

    steps: list[EscalationStep] = []
    for step_data in payload.steps:
        step = EscalationStep(
            policy_id=policy.id,
            step_order=step_data.step_order,
            channel_id=step_data.channel_id,
            delay_minutes=step_data.delay_minutes,
        )
        session.add(step)
        steps.append(step)

    await log_action(
        session,
        action="escalation.create",
        resource_type="escalation_policy",
        resource_id=str(policy.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"name": policy.name, "steps": len(steps)},
    )
    await session.commit()
    await session.refresh(policy)
    loaded_steps = await _load_steps(session, policy.id)
    return _policy_to_read(policy, loaded_steps)


@router.get("", response_model=list[EscalationPolicyRead])
async def list_policies(
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> list[EscalationPolicyRead]:
    stmt = select(EscalationPolicy).order_by(EscalationPolicy.created_at.desc())
    if workspace is not None:
        stmt = stmt.where(EscalationPolicy.workspace_id == workspace.id)
    result = await session.execute(stmt)
    policies = result.scalars().all()
    out: list[EscalationPolicyRead] = []
    for policy in policies:
        steps = await _load_steps(session, policy.id)
        out.append(_policy_to_read(policy, steps))
    return out


@router.get("/{policy_id}", response_model=EscalationPolicyRead)
async def get_policy(
    policy_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> EscalationPolicyRead:
    policy = await _get_policy_or_404(session, policy_id)
    steps = await _load_steps(session, policy.id)
    return _policy_to_read(policy, steps)


@router.patch("/{policy_id}", response_model=EscalationPolicyRead)
async def update_policy(
    policy_id: uuid.UUID,
    payload: EscalationPolicyUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> EscalationPolicyRead:
    policy = await _get_policy_or_404(session, policy_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(policy, field, value)
    await log_action(
        session,
        action="escalation.update",
        resource_type="escalation_policy",
        resource_id=str(policy.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"updated_fields": list(updates.keys())},
    )
    await session.commit()
    await session.refresh(policy)
    steps = await _load_steps(session, policy.id)
    return _policy_to_read(policy, steps)


@router.post("/{policy_id}/steps", response_model=EscalationStepRead, status_code=201)
async def add_step(
    policy_id: uuid.UUID,
    payload: EscalationStepCreate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
) -> EscalationStepRead:
    await _get_policy_or_404(session, policy_id)
    step = EscalationStep(
        policy_id=policy_id,
        step_order=payload.step_order,
        channel_id=payload.channel_id,
        delay_minutes=payload.delay_minutes,
    )
    session.add(step)
    await session.commit()
    await session.refresh(step)
    return EscalationStepRead.model_validate(step)


@router.delete("/{policy_id}/steps/{step_id}", status_code=204)
async def delete_step(
    policy_id: uuid.UUID,
    step_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_admin),
) -> None:
    result = await session.execute(
        select(EscalationStep).where(
            EscalationStep.id == step_id,
            EscalationStep.policy_id == policy_id,
        )
    )
    step = result.scalar_one_or_none()
    if step is None:
        raise HTTPException(status_code=404, detail="Escalation step not found")
    await session.delete(step)
    await session.commit()


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(
    policy_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    policy = await _get_policy_or_404(session, policy_id)
    await log_action(
        session,
        action="escalation.delete",
        resource_type="escalation_policy",
        resource_id=str(policy.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"name": policy.name},
    )
    await session.delete(policy)
    await session.commit()


@router.get("/{policy_id}/events", response_model=list[EscalationEventRead])
async def list_policy_events(
    policy_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[EscalationEventRead]:
    await _get_policy_or_404(session, policy_id)
    result = await session.execute(
        select(EscalationEvent)
        .where(EscalationEvent.policy_id == policy_id)
        .order_by(EscalationEvent.created_at.desc())
        .limit(50)
    )
    return [EscalationEventRead.model_validate(e) for e in result.scalars().all()]
