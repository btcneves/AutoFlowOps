"""Tests for /api/stats endpoint."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.execution import Execution
from app.models.job import Job


async def _create_job(session: AsyncSession, **kwargs) -> Job:
    defaults = {"name": "Test", "type": "http", "method": "GET", "url": "http://x.com"}
    defaults.update(kwargs)
    job = Job(**defaults)
    session.add(job)
    await session.flush()
    return job


async def test_stats_empty_db(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_jobs"] == 0
    assert data["active_jobs"] == 0
    assert data["paused_jobs"] == 0
    assert data["total_executions"] == 0
    assert data["executions_24h"] == 0
    assert data["failures_24h"] == 0
    assert data["success_rate_24h"] == 0.0
    assert len(data["daily_stats"]) == 7


async def test_stats_daily_stats_has_seven_days(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/stats")
    data = response.json()
    dates = [d["date"] for d in data["daily_stats"]]
    assert len(dates) == 7
    assert len(set(dates)) == 7


async def test_stats_counts_jobs(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_job(db_session, name="Active", status="active")
    await _create_job(db_session, name="Paused", status="paused")
    await db_session.commit()

    response = await async_client.get("/api/stats")
    data = response.json()
    assert data["total_jobs"] == 2
    assert data["active_jobs"] == 1
    assert data["paused_jobs"] == 1


async def test_stats_counts_executions(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    job = await _create_job(db_session)
    db_session.add_all([
        Execution(job_id=job.id, status="success", trigger_type="manual"),
        Execution(job_id=job.id, status="error", trigger_type="manual"),
    ])
    await db_session.commit()

    response = await async_client.get("/api/stats")
    data = response.json()
    assert data["total_executions"] == 2
    assert data["executions_24h"] == 2
    assert data["failures_24h"] == 1


async def test_stats_counts_failure_status(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    job = await _create_job(db_session)
    db_session.add_all([
        Execution(job_id=job.id, status="success", trigger_type="manual"),
        Execution(job_id=job.id, status="failure", trigger_type="manual"),
    ])
    await db_session.commit()

    response = await async_client.get("/api/stats")
    data = response.json()
    assert data["executions_24h"] == 2
    assert data["failures_24h"] == 1
    assert data["success_rate_24h"] == 50.0


async def test_stats_success_rate_mixed(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    job = await _create_job(db_session)
    db_session.add_all([
        Execution(job_id=job.id, status="success", trigger_type="manual"),
        Execution(job_id=job.id, status="error", trigger_type="manual"),
    ])
    await db_session.commit()

    response = await async_client.get("/api/stats")
    data = response.json()
    assert data["success_rate_24h"] == 50.0


async def test_stats_success_rate_all_success(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    job = await _create_job(db_session)
    db_session.add(Execution(job_id=job.id, status="success", trigger_type="manual"))
    await db_session.commit()

    response = await async_client.get("/api/stats")
    data = response.json()
    assert data["success_rate_24h"] == 100.0


async def test_stats_success_rate_all_failures(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    job = await _create_job(db_session)
    db_session.add(Execution(job_id=job.id, status="error", trigger_type="manual"))
    await db_session.commit()

    response = await async_client.get("/api/stats")
    data = response.json()
    assert data["success_rate_24h"] == 0.0


async def test_stats_daily_stats_fields(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/stats")
    day = response.json()["daily_stats"][0]
    assert "date" in day
    assert "success" in day
    assert "failure" in day
    assert isinstance(day["success"], int)
    assert isinstance(day["failure"], int)
