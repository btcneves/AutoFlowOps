import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import Execution
from app.models.job import Job


async def _create_job(session: AsyncSession) -> Job:
    job = Job(name="test-job", url="http://example.com", method="GET")
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def _create_execution(
    session: AsyncSession, job: Job, status: str = "success"
) -> Execution:
    exc = Execution(
        id=uuid.uuid4(),
        job_id=job.id,
        trigger_type="manual",
        status=status,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration_ms=123,
        request_method="GET",
        request_url=job.url,
    )
    session.add(exc)
    await session.commit()
    await session.refresh(exc)
    return exc


@pytest.mark.asyncio
async def test_list_executions_empty(async_client: AsyncClient):
    response = await async_client.get("/api/executions")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_executions(async_client: AsyncClient, db_session: AsyncSession):
    job = await _create_job(db_session)
    await _create_execution(db_session, job, "success")
    await _create_execution(db_session, job, "failure")

    response = await async_client.get("/api/executions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_executions_filter_by_status(
    async_client: AsyncClient, db_session: AsyncSession
):
    job = await _create_job(db_session)
    await _create_execution(db_session, job, "success")
    await _create_execution(db_session, job, "failure")

    response = await async_client.get("/api/executions?status=failure")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "failure"


@pytest.mark.asyncio
async def test_list_executions_filter_by_job(
    async_client: AsyncClient, db_session: AsyncSession
):
    job1 = await _create_job(db_session)
    job2 = await _create_job(db_session)
    await _create_execution(db_session, job1)
    await _create_execution(db_session, job2)

    response = await async_client.get(f"/api/executions?job_id={job1.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["job_id"] == str(job1.id)


@pytest.mark.asyncio
async def test_get_execution(async_client: AsyncClient, db_session: AsyncSession):
    job = await _create_job(db_session)
    exc = await _create_execution(db_session, job)

    response = await async_client.get(f"/api/executions/{exc.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(exc.id)
    assert data["status"] == "success"


@pytest.mark.asyncio
async def test_get_execution_not_found(async_client: AsyncClient):
    response = await async_client.get(f"/api/executions/{uuid.uuid4()}")
    assert response.status_code == 404
