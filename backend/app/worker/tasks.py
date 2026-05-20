import asyncio
import uuid

from celery.exceptions import Retry
from sqlalchemy import select

from app.database import async_session_factory
from app.models.execution import Execution
from app.models.job import Job
from app.services.http_runner import (
    FAILED_EXECUTION_STATUSES,
    create_failure_alert,
    run_job_http,
)
from app.worker.celery_app import celery_app


@celery_app.task(bind=True, name="app.worker.tasks.execute_http_job")
def execute_http_job(
    self,
    job_id: str,
    execution_id: str,
    trigger_type: str = "manual",
) -> dict[str, str]:
    return asyncio.run(
        _execute_http_job(
            celery_task=self,
            job_id=uuid.UUID(job_id),
            execution_id=uuid.UUID(execution_id),
            trigger_type=trigger_type,
        )
    )


async def _execute_http_job(
    celery_task,
    job_id: uuid.UUID,
    execution_id: uuid.UUID,
    trigger_type: str,
) -> dict[str, str]:
    async with async_session_factory() as session:
        job_result = await session.execute(select(Job).where(Job.id == job_id))
        job = job_result.scalar_one_or_none()
        execution_result = await session.execute(
            select(Execution).where(Execution.id == execution_id)
        )
        execution = execution_result.scalar_one_or_none()

        if execution is None:
            return {"execution_id": str(execution_id), "status": "missing"}

        if job is None:
            execution.status = "failure"
            execution.error_message = "Job not found"
            await session.commit()
            return {"execution_id": str(execution.id), "status": execution.status}

        attempt = int(getattr(celery_task.request, "retries", 0) or 0)
        execution = await run_job_http(
            job=job,
            session=session,
            trigger_type=trigger_type,
            execution=execution,
            create_alert=False,
            retry_attempt=attempt,
        )

        if execution.status in FAILED_EXECUTION_STATUSES and attempt < job.retry_count:
            execution.status = "retrying"
            session.add(execution)
            await session.commit()
            try:
                raise celery_task.retry(
                    countdown=job.retry_delay_seconds,
                    max_retries=job.retry_count,
                    exc=Exception(execution.error_message or execution.status),
                )
            except Retry:
                raise

        if job.alert_on_failure and execution.status in FAILED_EXECUTION_STATUSES:
            session.add(create_failure_alert(job, execution))
            await session.commit()

        return {"execution_id": str(execution.id), "status": execution.status}
