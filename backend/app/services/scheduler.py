import logging
import uuid
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()


def get_scheduler() -> AsyncIOScheduler:
    return _scheduler


def _parse_trigger(schedule_type: str, schedule_expression: str):
    if schedule_type == "interval":
        try:
            seconds = int(schedule_expression)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"interval schedule_expression must be an integer (seconds),"
                f" got: {schedule_expression!r}"
            ) from exc
        return IntervalTrigger(seconds=seconds)
    if schedule_type == "cron":
        return CronTrigger.from_crontab(schedule_expression)
    raise ValueError(f"Unsupported schedule_type: {schedule_type!r}")


async def _run_scheduled_job(job_id_str: str) -> None:
    from app.database import async_session_factory
    from app.services.http_runner import run_job_http

    job_id = uuid.UUID(job_id_str)
    async with async_session_factory() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job is None or job.status != "active":
            logger.info(
                "Skipping scheduled run for job %s (not found or not active)", job_id
            )
            return
        await run_job_http(job, session, trigger_type="scheduled")

    aps_job = _scheduler.get_job(job_id_str)
    if aps_job and getattr(aps_job, "next_run_time", None):
        async with async_session_factory() as session:
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.next_run_at = aps_job.next_run_time
                await session.commit()


def schedule_job(job: Job) -> datetime | None:
    """Add or replace a job in the scheduler.

    Returns the next scheduled run time if the scheduler is running, else None.
    Calling this with a manual/paused/invalid job is always safe (unschedules).
    """
    job_id_str = str(job.id)

    if job.schedule_type not in ("interval", "cron") or not job.schedule_expression:
        unschedule_job(job.id)
        return None

    if job.status != "active":
        unschedule_job(job.id)
        return None

    try:
        trigger = _parse_trigger(job.schedule_type, job.schedule_expression)
    except ValueError:
        logger.exception("Invalid schedule for job %s — skipping", job.id)
        return None

    _scheduler.add_job(
        _run_scheduled_job,
        trigger=trigger,
        id=job_id_str,
        args=[job_id_str],
        replace_existing=True,
        name=job.name,
    )
    logger.info(
        "Scheduled job %s (%s) type=%s expr=%s",
        job.id,
        job.name,
        job.schedule_type,
        job.schedule_expression,
    )

    aps_job = _scheduler.get_job(job_id_str)
    return getattr(aps_job, "next_run_time", None) if aps_job else None


def unschedule_job(job_id: uuid.UUID) -> None:
    job_id_str = str(job_id)
    if _scheduler.get_job(job_id_str):
        _scheduler.remove_job(job_id_str)
        logger.info("Unscheduled job %s", job_id)


async def load_scheduled_jobs(session: AsyncSession) -> None:
    result = await session.execute(
        select(Job).where(
            Job.status == "active",
            Job.schedule_type.in_(["interval", "cron"]),
        )
    )
    jobs = result.scalars().all()
    for job in jobs:
        schedule_job(job)
    logger.info("Loaded %d scheduled job(s) from database", len(jobs))
