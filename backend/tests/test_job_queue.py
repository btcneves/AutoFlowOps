import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import Retry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.execution import Execution
from app.models.job import Job
from app.services.job_queue import enqueue_job_execution
from app.worker import tasks


def _make_job(**kwargs) -> Job:
    defaults = {
        "id": uuid.uuid4(),
        "name": "Queued Job",
        "type": "http",
        "method": "GET",
        "url": "http://example.com/ping",
        "timeout_seconds": 10,
        "retry_count": 0,
        "retry_delay_seconds": 1,
        "alert_on_failure": True,
        "headers_encrypted": None,
        "body_encrypted": None,
        "status": "active",
        "schedule_type": "manual",
    }
    defaults.update(kwargs)
    return Job(**defaults)


def _mock_httpx_response(status_code: int, text: str, is_success: bool):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.is_success = is_success
    mock_resp.text = text
    return mock_resp


class _FakeRequest:
    retries = 0


class _FakeTask:
    request = _FakeRequest()

    def retry(self, **kwargs):  # noqa: ARG002
        raise Retry("retry requested")


def _session_factory(session: AsyncSession):
    @asynccontextmanager
    async def factory():
        yield session

    return factory


async def test_enqueue_job_execution_creates_queued_execution(
    db_session: AsyncSession,
) -> None:
    job = _make_job()
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    with patch("app.worker.tasks.execute_http_job.delay") as delay:
        execution = await enqueue_job_execution(job, db_session)

    assert execution.status == "queued"
    assert execution.job_id == job.id
    assert execution.request_url == job.url
    delay.assert_called_once_with(str(job.id), str(execution.id), "manual")


async def test_worker_task_executes_queued_job(
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    job = _make_job()
    execution = Execution(
        id=uuid.uuid4(),
        job_id=job.id,
        trigger_type="manual",
        status="queued",
        started_at=datetime.now(UTC),
    )
    db_session.add_all([job, execution])
    await db_session.commit()

    monkeypatch.setattr(tasks, "async_session_factory", _session_factory(db_session))
    mock_resp = _mock_httpx_response(200, "pong", True)

    with patch("httpx.AsyncClient") as mock_cls:
        inst = AsyncMock()
        inst.__aenter__ = AsyncMock(return_value=inst)
        inst.__aexit__ = AsyncMock(return_value=None)
        inst.request = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = inst

        result = await tasks._execute_http_job(
            _FakeTask(), job.id, execution.id, "manual"
        )

    assert result["status"] == "success"
    refreshed = await db_session.get(Execution, execution.id)
    assert refreshed is not None
    assert refreshed.status == "success"
    assert refreshed.response_status_code == 200


async def test_worker_task_creates_alert_on_final_failure(
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    job = _make_job(name="Failing Queue Job")
    execution = Execution(
        id=uuid.uuid4(),
        job_id=job.id,
        trigger_type="manual",
        status="queued",
        started_at=datetime.now(UTC),
    )
    db_session.add_all([job, execution])
    await db_session.commit()
    monkeypatch.setattr(tasks, "async_session_factory", _session_factory(db_session))

    with patch("httpx.AsyncClient") as mock_cls:
        inst = AsyncMock()
        inst.__aenter__ = AsyncMock(return_value=inst)
        inst.__aexit__ = AsyncMock(return_value=None)
        inst.request = AsyncMock(side_effect=Exception("Connection refused"))
        mock_cls.return_value = inst

        result = await tasks._execute_http_job(
            _FakeTask(), job.id, execution.id, "manual"
        )

    assert result["status"] == "failure"
    alerts = (await db_session.execute(select(Alert))).scalars().all()
    assert len(alerts) == 1
    assert alerts[0].source_id == execution.id
    assert "Connection refused" in alerts[0].message


async def test_worker_task_marks_retrying_before_retry(
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    job = _make_job(retry_count=1)
    execution = Execution(
        id=uuid.uuid4(),
        job_id=job.id,
        trigger_type="manual",
        status="queued",
        started_at=datetime.now(UTC),
    )
    db_session.add_all([job, execution])
    await db_session.commit()
    monkeypatch.setattr(tasks, "async_session_factory", _session_factory(db_session))

    async def fail_run(**kwargs):
        exc = kwargs["execution"]
        exc.status = "failure"
        exc.error_message = "boom"
        exc.retry_attempt = 0
        db_session.add(exc)
        await db_session.commit()
        await db_session.refresh(exc)
        return exc

    monkeypatch.setattr(tasks, "run_job_http", fail_run)

    with pytest.raises(Retry):
        await tasks._execute_http_job(_FakeTask(), job.id, execution.id, "manual")

    refreshed = await db_session.get(Execution, execution.id)
    assert refreshed is not None
    assert refreshed.status == "retrying"
