"""Integration tests for conditional alert rules."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.execution import Execution
from app.models.job import Job
from app.models.workspace import Workspace, WorkspaceMembership
from app.services.http_runner import run_job_http
from app.worker import tasks
from tests.conftest import _FAKE_OPERATOR

_JOB_PAYLOAD = {
    "name": "Rule Target",
    "url": "http://example.com/health",
    "method": "GET",
    "alert_on_failure": False,
}


class _FakeRequest:
    retries = 0


class _FakeTask:
    request = _FakeRequest()


async def _create_job(async_client: AsyncClient) -> str:
    response = await async_client.post("/api/jobs", json=_JOB_PAYLOAD)
    assert response.status_code == 201
    return response.json()["id"]


async def test_create_and_list_alert_rule(async_client: AsyncClient) -> None:
    job_id = await _create_job(async_client)

    create = await async_client.post(
        f"/api/jobs/{job_id}/alert-rules",
        json={
            "condition_type": "http_status_gte",
            "condition_value": "500",
            "severity": "error",
            "message": "High HTTP status",
        },
    )
    assert create.status_code == 201
    created = create.json()
    assert created["job_id"] == job_id
    assert created["condition_type"] == "http_status_gte"
    assert created["condition_value"] == "500"
    assert created["severity"] == "error"

    listed = await async_client.get(f"/api/jobs/{job_id}/alert-rules")
    assert listed.status_code == 200
    assert [rule["id"] for rule in listed.json()] == [created["id"]]


async def test_update_and_delete_alert_rule(async_client: AsyncClient) -> None:
    job_id = await _create_job(async_client)
    create = await async_client.post(
        f"/api/jobs/{job_id}/alert-rules",
        json={
            "condition_type": "duration_ms_gte",
            "condition_value": "1000",
        },
    )
    rule_id = create.json()["id"]

    update = await async_client.patch(
        f"/api/jobs/{job_id}/alert-rules/{rule_id}",
        json={"condition_value": "2500", "is_enabled": False},
    )
    assert update.status_code == 200
    assert update.json()["condition_value"] == "2500"
    assert update.json()["is_enabled"] is False

    delete = await async_client.delete(f"/api/jobs/{job_id}/alert-rules/{rule_id}")
    assert delete.status_code == 204

    listed = await async_client.get(f"/api/jobs/{job_id}/alert-rules")
    assert listed.status_code == 200
    assert listed.json() == []


async def test_alert_rule_requires_numeric_threshold(
    async_client: AsyncClient,
) -> None:
    job_id = await _create_job(async_client)

    response = await async_client.post(
        f"/api/jobs/{job_id}/alert-rules",
        json={
            "condition_type": "http_status_gte",
            "condition_value": "not-a-number",
        },
    )
    assert response.status_code == 422


async def test_viewer_can_read_but_not_create_alert_rules(
    viewer_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    job = Job(
        id=uuid.uuid4(),
        name="Viewer target",
        type="http",
        method="GET",
        url="https://example.com",
        schedule_type="manual",
        timeout_seconds=30,
        retry_count=0,
        retry_delay_seconds=0,
        alert_on_failure=False,
    )
    db_session.add(job)
    await db_session.commit()

    read = await viewer_client.get(f"/api/jobs/{job.id}/alert-rules")
    assert read.status_code == 200

    write = await viewer_client.post(
        f"/api/jobs/{job.id}/alert-rules",
        json={"condition_type": "http_status_gte", "condition_value": "500"},
    )
    assert write.status_code == 403


async def test_alert_rules_respect_workspace_header(
    operator_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    allowed_ws = Workspace(name="Allowed Rules", slug="allowed-rules")
    other_ws = Workspace(name="Other Rules", slug="other-rules")
    db_session.add_all([allowed_ws, other_ws])
    await db_session.flush()
    db_session.add(
        WorkspaceMembership(
            workspace_id=allowed_ws.id,
            user_id=_FAKE_OPERATOR.id,
            role="member",
        )
    )
    job = Job(
        name="Other workspace job",
        type="http",
        method="GET",
        url="https://example.com",
        schedule_type="manual",
        timeout_seconds=30,
        retry_count=0,
        retry_delay_seconds=0,
        alert_on_failure=False,
        workspace_id=other_ws.id,
    )
    db_session.add(job)
    await db_session.commit()

    response = await operator_client.get(
        f"/api/jobs/{job.id}/alert-rules",
        headers={"X-Workspace-ID": str(allowed_ws.id)},
    )
    assert response.status_code == 404


def _mock_httpx_response(status_code: int, text: str, is_success: bool):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.is_success = is_success
    mock_resp.text = text
    return mock_resp


async def test_http_runner_creates_alert_from_matching_rule(
    db_session: AsyncSession,
) -> None:
    job = Job(
        id=uuid.uuid4(),
        name="Runner Rule Target",
        type="http",
        method="GET",
        url="http://example.com/fail",
        timeout_seconds=10,
        retry_count=0,
        retry_delay_seconds=60,
        alert_on_failure=False,
        headers_encrypted=None,
        body_encrypted=None,
        status="active",
        schedule_type="manual",
    )
    db_session.add(job)
    await db_session.flush()
    rule = AlertRule(
        job_id=job.id,
        condition_type="http_status_gte",
        condition_value="500",
        severity="error",
        message="Rule triggered",
    )
    db_session.add(rule)
    await db_session.commit()

    mock_resp = _mock_httpx_response(503, "Service Unavailable", False)
    with patch("httpx.AsyncClient") as mock_cls:
        inst = AsyncMock()
        inst.__aenter__ = AsyncMock(return_value=inst)
        inst.__aexit__ = AsyncMock(return_value=None)
        inst.request = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = inst

        await run_job_http(job, db_session)

    result = await db_session.execute(select(Alert).where(Alert.source_id == rule.id))
    alert = result.scalar_one()
    assert alert.title == "Rule triggered"
    assert alert.message == "HTTP 503 >= 500"
    assert alert.severity == "error"
    assert alert.source_type == "alert_rule"


async def test_worker_creates_alert_from_matching_rule(
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    job = Job(
        id=uuid.uuid4(),
        name="Worker Rule Target",
        type="http",
        method="GET",
        url="http://example.com/fail",
        timeout_seconds=10,
        retry_count=0,
        retry_delay_seconds=60,
        alert_on_failure=False,
        headers_encrypted=None,
        body_encrypted=None,
        status="active",
        schedule_type="manual",
    )
    execution = Execution(
        id=uuid.uuid4(),
        job_id=job.id,
        trigger_type="manual",
        status="queued",
    )
    rule = AlertRule(
        job_id=job.id,
        condition_type="http_status_gte",
        condition_value="500",
        severity="error",
        message="Worker rule triggered",
    )
    db_session.add_all([job, execution, rule])
    await db_session.commit()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def factory():
        yield db_session

    monkeypatch.setattr(tasks, "async_session_factory", factory)

    mock_resp = _mock_httpx_response(503, "Service Unavailable", False)
    with patch("httpx.AsyncClient") as mock_cls:
        inst = AsyncMock()
        inst.__aenter__ = AsyncMock(return_value=inst)
        inst.__aexit__ = AsyncMock(return_value=None)
        inst.request = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = inst

        result = await tasks._execute_http_job(
            _FakeTask(), job.id, execution.id, "manual"
        )

    assert result["status"] == "failure"
    alerts = (await db_session.execute(select(Alert))).scalars().all()
    assert len(alerts) == 1
    assert alerts[0].title == "Worker rule triggered"
    assert alerts[0].source_id == rule.id
