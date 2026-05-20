import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import Job
from app.schemas.execution import ExecutionRead
from app.schemas.job import JobCreate, JobRead, JobUpdate
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
    session: AsyncSession = Depends(get_db),
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
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    next_run = schedule_job(job)
    if next_run is not None:
        job.next_run_at = next_run
        await session.commit()
        await session.refresh(job)
    return _job_to_read(job)


@router.get("", response_model=list[JobRead])
async def list_jobs(session: AsyncSession = Depends(get_db)) -> list[JobRead]:
    result = await session.execute(select(Job).order_by(Job.created_at.desc()))
    jobs = result.scalars().all()
    return [_job_to_read(j) for j in jobs]


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> JobRead:
    job = await _get_or_404(session, job_id)
    return _job_to_read(job)


@router.patch("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    session: AsyncSession = Depends(get_db),
) -> JobRead:
    job = await _get_or_404(session, job_id)

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
    session: AsyncSession = Depends(get_db),
) -> None:
    job = await _get_or_404(session, job_id)
    await session.delete(job)
    await session.commit()
    unschedule_job(job_id)


@router.post("/{job_id}/run", response_model=ExecutionRead, status_code=202)
async def run_job(
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> ExecutionRead:
    job = await _get_or_404(session, job_id)
    if job.type != "http":
        raise HTTPException(status_code=501, detail="Only HTTP jobs are supported")
    execution = await enqueue_job_execution(job, session, trigger_type="manual")
    return ExecutionRead.model_validate(execution)


async def _get_or_404(session: AsyncSession, job_id: uuid.UUID) -> Job:
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
