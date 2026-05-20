import json
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.execution import Execution
from app.models.job import Job


async def _create_job(session: AsyncSession, name: str = "Job") -> Job:
    job = Job(name=name, type="http", method="GET", url="https://example.com")
    session.add(job)
    await session.flush()
    return job


async def _generate_report(
    async_client: AsyncClient,
    start: datetime,
    end: datetime,
    name: str = "Weekly Ops",
):
    return await async_client.post(
        "/api/reports/generate",
        json={
            "name": name,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
        },
    )


async def test_generate_report_empty(async_client: AsyncClient) -> None:
    now = datetime.now(UTC)
    response = await _generate_report(
        async_client,
        now - timedelta(days=7),
        now,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Weekly Ops"
    assert data["format"] == "json"
    content = json.loads(data["content"])
    assert content["summary"]["total_jobs"] == 0
    assert content["summary"]["executions"] == 0
    assert content["summary"]["failures"] == 0
    assert content["executions"] == []


async def test_generate_report_filters_period(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    job = await _create_job(db_session)
    db_session.add_all([
        Execution(
            job_id=job.id,
            trigger_type="manual",
            status="success",
            started_at=now - timedelta(days=1),
        ),
        Execution(
            job_id=job.id,
            trigger_type="manual",
            status="success",
            started_at=now - timedelta(days=20),
        ),
    ])
    await db_session.commit()

    response = await _generate_report(
        async_client,
        now - timedelta(days=7),
        now,
    )

    assert response.status_code == 201
    content = json.loads(response.json()["content"])
    assert content["summary"]["executions"] == 1


async def test_generate_report_counts_success_failure_and_legacy_error(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    job = await _create_job(db_session)
    db_session.add_all([
        Execution(
            job_id=job.id,
            trigger_type="manual",
            status="success",
            started_at=now - timedelta(hours=3),
            duration_ms=100,
        ),
        Execution(
            job_id=job.id,
            trigger_type="manual",
            status="failure",
            started_at=now - timedelta(hours=2),
            duration_ms=200,
        ),
        Execution(
            job_id=job.id,
            trigger_type="manual",
            status="error",
            started_at=now - timedelta(hours=1),
            duration_ms=300,
        ),
    ])
    await db_session.commit()

    response = await _generate_report(
        async_client,
        now - timedelta(days=1),
        now,
    )

    assert response.status_code == 201
    summary = json.loads(response.json()["content"])["summary"]
    assert summary["executions"] == 3
    assert summary["successes"] == 1
    assert summary["failures"] == 2
    assert summary["success_rate"] == 33.3
    assert summary["average_duration_ms"] == 200


async def test_generate_report_top_failed_jobs(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    noisy = await _create_job(db_session, name="Noisy Job")
    occasional = await _create_job(db_session, name="Occasional Job")
    db_session.add_all([
        Execution(job_id=noisy.id, trigger_type="manual", status="failure"),
        Execution(job_id=noisy.id, trigger_type="manual", status="failure"),
        Execution(job_id=occasional.id, trigger_type="manual", status="failure"),
    ])
    await db_session.commit()

    response = await _generate_report(
        async_client,
        now - timedelta(days=1),
        now + timedelta(days=1),
    )

    assert response.status_code == 201
    top_failed_jobs = json.loads(response.json()["content"])["top_failed_jobs"]
    assert top_failed_jobs[0]["job_name"] == "Noisy Job"
    assert top_failed_jobs[0]["failures"] == 2


async def test_generate_report_includes_alerts(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    db_session.add(
        Alert(
            title="Job failed",
            message="Timeout",
            severity="error",
            status="open",
            created_at=now - timedelta(hours=1),
        )
    )
    await db_session.commit()

    response = await _generate_report(
        async_client,
        now - timedelta(days=1),
        now,
    )

    assert response.status_code == 201
    content = json.loads(response.json()["content"])
    assert content["summary"]["alerts"] == 1
    assert content["alerts"][0]["title"] == "Job failed"


async def test_list_and_get_report(async_client: AsyncClient) -> None:
    now = datetime.now(UTC)
    created = await _generate_report(
        async_client,
        now - timedelta(days=1),
        now,
        name="List Me",
    )
    report_id = created.json()["id"]

    list_response = await async_client.get("/api/reports")
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == report_id
    assert "content" not in list_response.json()[0]

    get_response = await async_client.get(f"/api/reports/{report_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "List Me"
    assert get_response.json()["content"] is not None


async def test_download_report_formats(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    job = await _create_job(db_session, name="Exported Job")
    db_session.add(
        Execution(
            job_id=job.id,
            trigger_type="manual",
            status="success",
            started_at=now - timedelta(hours=1),
        )
    )
    await db_session.commit()
    created = await _generate_report(async_client, now - timedelta(days=1), now)
    report_id = created.json()["id"]

    json_response = await async_client.get(
        f"/api/reports/{report_id}/download?format=json"
    )
    assert json_response.status_code == 200
    assert json_response.headers["content-type"].startswith("application/json")
    assert json_response.json()["summary"]["executions"] == 1

    md_response = await async_client.get(
        f"/api/reports/{report_id}/download?format=markdown"
    )
    assert md_response.status_code == 200
    assert "# AutoFlowOps Operational Report" in md_response.text

    csv_response = await async_client.get(
        f"/api/reports/{report_id}/download?format=csv"
    )
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "Exported Job" in csv_response.text


async def test_download_report_pdf_format(async_client: AsyncClient) -> None:
    now = datetime.now(UTC)
    created = await _generate_report(async_client, now - timedelta(days=1), now)
    report_id = created.json()["id"]

    response = await async_client.get(f"/api/reports/{report_id}/download?format=pdf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content[:4] == b"%PDF"


async def test_download_report_invalid_format(async_client: AsyncClient) -> None:
    now = datetime.now(UTC)
    created = await _generate_report(async_client, now - timedelta(days=1), now)
    report_id = created.json()["id"]

    response = await async_client.get(f"/api/reports/{report_id}/download?format=xlsx")

    assert response.status_code == 422


async def test_report_not_found(async_client: AsyncClient) -> None:
    response = await async_client.get(
        "/api/reports/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


async def test_generate_report_invalid_period(async_client: AsyncClient) -> None:
    now = datetime.now(UTC)
    response = await _generate_report(
        async_client,
        now,
        now - timedelta(days=1),
    )

    assert response.status_code == 422
