"""Integration tests for the HTTP runner service."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.services.http_runner import run_job_http


def _make_job(**kwargs) -> Job:
    defaults = {
        "id": uuid.uuid4(),
        "name": "Runner Test Job",
        "type": "http",
        "method": "GET",
        "url": "http://example.com/ping",
        "timeout_seconds": 10,
        "retry_count": 0,
        "retry_delay_seconds": 60,
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


async def test_run_job_http_success(db_session: AsyncSession) -> None:
    job = _make_job()
    db_session.add(job)
    await db_session.flush()

    mock_resp = _mock_httpx_response(200, '{"ok": true}', True)

    with patch("httpx.AsyncClient") as mock_cls:
        inst = AsyncMock()
        inst.__aenter__ = AsyncMock(return_value=inst)
        inst.__aexit__ = AsyncMock(return_value=None)
        inst.request = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = inst

        execution = await run_job_http(job, db_session)

    assert execution.status == "success"
    assert execution.response_status_code == 200
    assert execution.response_body_preview == '{"ok": true}'
    assert execution.duration_ms is not None and execution.duration_ms >= 0
    assert execution.finished_at is not None
    assert execution.error_message is None


async def test_run_job_http_failure_status(db_session: AsyncSession) -> None:
    job = _make_job(url="http://example.com/fail")
    db_session.add(job)
    await db_session.flush()

    mock_resp = _mock_httpx_response(500, "Internal Server Error", False)

    with patch("httpx.AsyncClient") as mock_cls:
        inst = AsyncMock()
        inst.__aenter__ = AsyncMock(return_value=inst)
        inst.__aexit__ = AsyncMock(return_value=None)
        inst.request = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = inst

        execution = await run_job_http(job, db_session)

    assert execution.status == "failure"
    assert execution.response_status_code == 500


async def test_run_job_http_network_error(db_session: AsyncSession) -> None:
    job = _make_job(url="http://unreachable.invalid/")
    db_session.add(job)
    await db_session.flush()

    with patch("httpx.AsyncClient") as mock_cls:
        inst = AsyncMock()
        inst.__aenter__ = AsyncMock(return_value=inst)
        inst.__aexit__ = AsyncMock(return_value=None)
        inst.request = AsyncMock(side_effect=Exception("Connection refused"))
        mock_cls.return_value = inst

        execution = await run_job_http(job, db_session)

    assert execution.status == "failure"
    assert "Connection refused" in execution.error_message
    assert execution.duration_ms is not None


async def test_run_job_http_timeout(db_session: AsyncSession) -> None:
    job = _make_job(url="http://slow.example.com/")
    db_session.add(job)
    await db_session.flush()

    with patch("httpx.AsyncClient") as mock_cls:
        inst = AsyncMock()
        inst.__aenter__ = AsyncMock(return_value=inst)
        inst.__aexit__ = AsyncMock(return_value=None)
        inst.request = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_cls.return_value = inst

        execution = await run_job_http(job, db_session)

    assert execution.status == "timeout"
    assert "timed out" in execution.error_message
    assert execution.duration_ms is not None


async def test_run_job_masks_auth_header(db_session: AsyncSession) -> None:
    headers = {
        "Authorization": "Bearer super_secret",
        "Content-Type": "application/json",
    }
    job = _make_job(headers_encrypted=json.dumps(headers))
    db_session.add(job)
    await db_session.flush()

    mock_resp = _mock_httpx_response(200, "ok", True)

    with patch("httpx.AsyncClient") as mock_cls:
        inst = AsyncMock()
        inst.__aenter__ = AsyncMock(return_value=inst)
        inst.__aexit__ = AsyncMock(return_value=None)
        inst.request = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = inst

        execution = await run_job_http(job, db_session)

    stored = json.loads(execution.request_headers_masked)  # type: ignore[arg-type]
    assert stored["Authorization"] == "***"
    assert stored["Content-Type"] == "application/json"


async def test_run_job_via_api(async_client: AsyncClient) -> None:
    create = await async_client.post(
        "/api/jobs",
        json={
            "name": "API Run Job",
            "url": "http://example.com/test",
            "method": "POST",
        },
    )
    assert create.status_code == 201
    job_id = create.json()["id"]

    with patch("app.worker.tasks.execute_http_job.delay") as delay:
        response = await async_client.post(f"/api/jobs/{job_id}/run")

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["job_id"] == job_id
    assert data["trigger_type"] == "manual"
    delay.assert_called_once()
