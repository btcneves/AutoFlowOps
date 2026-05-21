import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_active_workspace, get_current_user, require_operator
from app.models.job import Job
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.execution import ExecutionRead
from app.schemas.job import JobCreate, JobRead, JobUpdate
from app.services.audit import client_ip, log_action
from app.services.job_queue import enqueue_job_execution
from app.services.masking import mask_sensitive_headers
from app.services.scheduler import schedule_job, unschedule_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_to_read(job: Job) -> JobRead:
    headers_raw = json.loads(job.headers_encrypted) if job.headers_encrypted else None
    headers_masked = (
        mask_sensitive_headers(headers_raw) if headers_raw is not None else None
    )
    return JobRead(
        id=job.id,
        name=job.name,
        description=job.description,
        type=job.type,
        status=job.status,
        schedule_type=job.schedule_type,
        schedule_expression=job.schedule_expression,
        method=job.method,
        url=job.url,
        headers_masked=headers_masked,
        timeout_seconds=job.timeout_seconds,
        retry_count=job.retry_count,
        retry_delay_seconds=job.retry_delay_seconds,
        alert_on_failure=job.alert_on_failure,
        created_at=job.created_at,
        updated_at=job.updated_at,
        last_run_at=job.last_run_at,
        next_run_at=job.next_run_at,
    )


@router.post("", response_model=JobRead, status_code=201)
async def create_job(
    payload: JobCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> JobRead:
    job = Job(
        name=payload.name,
        description=payload.description,
        type=payload.type,
        method=payload.method,
        url=payload.url,
        headers_encrypted=json.dumps(payload.headers) if payload.headers else None,
        body_encrypted=payload.body,
        schedule_type=payload.schedule_type,
        schedule_expression=payload.schedule_expression,
        timeout_seconds=payload.timeout_seconds,
        retry_count=payload.retry_count,
        retry_delay_seconds=payload.retry_delay_seconds,
        alert_on_failure=payload.alert_on_failure,
        workspace_id=workspace.id if workspace else None,
    )
    session.add(job)
    await session.flush()
    await log_action(
        session,
        action="jobs.create",
        resource_type="job",
        resource_id=str(job.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"name": job.name, "url": job.url},
    )
    await session.commit()
    await session.refresh(job)
    next_run = schedule_job(job)
    if next_run is not None:
        job.next_run_at = next_run
        await session.commit()
        await session.refresh(job)
    return _job_to_read(job)


@router.get("", response_model=list[JobRead])
async def list_jobs(
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> list[JobRead]:
    stmt = select(Job).order_by(Job.created_at.desc())
    if workspace is not None:
        stmt = stmt.where(Job.workspace_id == workspace.id)
    result = await session.execute(stmt)
    jobs = result.scalars().all()
    return [_job_to_read(j) for j in jobs]


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> JobRead:
    job = await _get_or_404(session, job_id, workspace)
    return _job_to_read(job)


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> JobRead:
    job = await _get_or_404(session, job_id, workspace)

    updates = payload.model_dump(exclude_unset=True)
    if "headers" in updates:
        raw_headers = updates.pop("headers")
        job.headers_encrypted = (
            json.dumps(raw_headers) if raw_headers is not None else None
        )
    if "body" in updates:
        job.body_encrypted = updates.pop("body")

    for field, value in updates.items():
        setattr(job, field, value)

    await log_action(
        session,
        action="jobs.update",
        resource_type="job",
        resource_id=str(job.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"updated_fields": list(updates.keys())},
    )
    await session.commit()
    await session.refresh(job)
    next_run = schedule_job(job)
    if next_run is not None:
        job.next_run_at = next_run
        await session.commit()
        await session.refresh(job)
    return _job_to_read(job)


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> None:
    job = await _get_or_404(session, job_id, workspace)
    await log_action(
        session,
        action="jobs.delete",
        resource_type="job",
        resource_id=str(job.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"name": job.name},
    )
    await session.delete(job)
    await session.commit()
    unschedule_job(job_id)


@router.post("/{job_id}/run", response_model=ExecutionRead, status_code=202)
async def run_job(
    job_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_operator),
    workspace: Workspace | None = Depends(get_active_workspace),
) -> ExecutionRead:
    job = await _get_or_404(session, job_id, workspace)
    if job.type != "http":
        raise HTTPException(status_code=501, detail="Only HTTP jobs are supported")
    execution = await enqueue_job_execution(job, session, trigger_type="manual")
    await log_action(
        session,
        action="jobs.run",
        resource_type="job",
        resource_id=str(job.id),
        user_id=current_user.id,
        ip_address=client_ip(request),
        user_agent=request.headers.get("User-Agent"),
        metadata={"execution_id": str(execution.id)},
    )
    await session.commit()
    return ExecutionRead.model_validate(execution)


async def _get_or_404(
    session: AsyncSession,
    job_id: uuid.UUID,
    workspace: Workspace | None = None,
) -> Job:
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None or (workspace is not None and job.workspace_id != workspace.id):
        raise HTTPException(status_code=404, detail="Job not found")
    return job
