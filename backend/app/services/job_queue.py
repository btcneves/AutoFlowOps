import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.execution import Execution
from app.models.job import Job
from app.services.http_runner import create_queued_execution, run_job_http


async def enqueue_job_execution(
    job: Job,
    session: AsyncSession,
    trigger_type: str = "manual",
) -> Execution:
    execution = await create_queued_execution(job, session, trigger_type=trigger_type)

    if settings.job_execution_mode == "inline":
        return await run_job_http(
            job,
            session,
            trigger_type=trigger_type,
            execution=execution,
        )

    from app.worker.tasks import execute_http_job

    execute_http_job.delay(str(job.id), str(execution.id), trigger_type)
    return execution


async def enqueue_job_by_id(
    job_id: uuid.UUID,
    session: AsyncSession,
    trigger_type: str = "scheduled",
) -> Execution | None:
    from sqlalchemy import select

    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None or job.status != "active":
        return None
    return await enqueue_job_execution(job, session, trigger_type=trigger_type)
