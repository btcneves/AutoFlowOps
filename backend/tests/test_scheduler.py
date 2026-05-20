"""Unit and integration tests for the scheduler service."""

import uuid
from unittest.mock import MagicMock

import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.services.scheduler import (
    _parse_trigger,
    get_scheduler,
    load_scheduled_jobs,
    schedule_job,
    unschedule_job,
)


def _make_mock_job(**kwargs) -> MagicMock:
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test Scheduled Job",
        "type": "http",
        "status": "active",
        "schedule_type": "interval",
        "schedule_expression": "60",
    }
    defaults.update(kwargs)
    job = MagicMock(spec=Job)
    for k, v in defaults.items():
        setattr(job, k, v)
    return job


# --- _parse_trigger ---


def test_parse_trigger_interval_returns_interval_trigger():
    trigger = _parse_trigger("interval", "300")
    assert isinstance(trigger, IntervalTrigger)


def test_parse_trigger_cron_returns_cron_trigger():
    trigger = _parse_trigger("cron", "*/5 * * * *")
    assert isinstance(trigger, CronTrigger)


def test_parse_trigger_interval_invalid_expression():
    with pytest.raises(ValueError, match="integer"):
        _parse_trigger("interval", "not-a-number")


def test_parse_trigger_unsupported_type():
    with pytest.raises(ValueError, match="Unsupported"):
        _parse_trigger("webhook", "*/5 * * * *")


# --- schedule_job / unschedule_job ---


def test_schedule_job_interval_adds_to_scheduler():
    job = _make_mock_job(schedule_type="interval", schedule_expression="120")
    schedule_job(job)
    assert get_scheduler().get_job(str(job.id)) is not None


def test_schedule_job_cron_adds_to_scheduler():
    job = _make_mock_job(schedule_type="cron", schedule_expression="0 * * * *")
    schedule_job(job)
    assert get_scheduler().get_job(str(job.id)) is not None


def test_schedule_job_manual_is_noop():
    job = _make_mock_job(schedule_type="manual", schedule_expression=None)
    schedule_job(job)
    assert get_scheduler().get_job(str(job.id)) is None


def test_schedule_job_paused_unschedules_existing():
    job = _make_mock_job()
    schedule_job(job)
    assert get_scheduler().get_job(str(job.id)) is not None

    job.status = "paused"
    schedule_job(job)
    assert get_scheduler().get_job(str(job.id)) is None


def test_schedule_job_changed_to_manual_unschedules():
    job = _make_mock_job(schedule_type="interval", schedule_expression="60")
    schedule_job(job)
    assert get_scheduler().get_job(str(job.id)) is not None

    job.schedule_type = "manual"
    job.schedule_expression = None
    schedule_job(job)
    assert get_scheduler().get_job(str(job.id)) is None


def test_schedule_job_invalid_expression_is_safe():
    job = _make_mock_job(schedule_type="interval", schedule_expression="bad")
    result = schedule_job(job)
    assert result is None
    assert get_scheduler().get_job(str(job.id)) is None


def test_unschedule_nonexistent_job_is_noop():
    unschedule_job(uuid.uuid4())


def test_schedule_job_replaces_existing():
    job = _make_mock_job(schedule_type="interval", schedule_expression="60")
    schedule_job(job)
    job.schedule_expression = "120"
    schedule_job(job)
    assert get_scheduler().get_job(str(job.id)) is not None


# --- load_scheduled_jobs ---


async def test_load_scheduled_jobs_schedules_active_jobs(
    db_session: AsyncSession,
) -> None:
    active_job = Job(
        name="Active Interval Job",
        type="http",
        method="GET",
        url="http://example.com/tick",
        status="active",
        schedule_type="interval",
        schedule_expression="300",
    )
    paused_job = Job(
        name="Paused Job",
        type="http",
        method="GET",
        url="http://example.com/pause",
        status="paused",
        schedule_type="interval",
        schedule_expression="60",
    )
    manual_job = Job(
        name="Manual Job",
        type="http",
        method="GET",
        url="http://example.com/manual",
        status="active",
        schedule_type="manual",
    )
    db_session.add_all([active_job, paused_job, manual_job])
    await db_session.flush()

    await load_scheduled_jobs(db_session)

    assert get_scheduler().get_job(str(active_job.id)) is not None
    assert get_scheduler().get_job(str(paused_job.id)) is None
    assert get_scheduler().get_job(str(manual_job.id)) is None


async def test_load_scheduled_jobs_cron(db_session: AsyncSession) -> None:
    job = Job(
        name="Cron Job",
        type="http",
        method="GET",
        url="http://example.com/cron",
        status="active",
        schedule_type="cron",
        schedule_expression="*/10 * * * *",
    )
    db_session.add(job)
    await db_session.flush()

    await load_scheduled_jobs(db_session)

    assert get_scheduler().get_job(str(job.id)) is not None
