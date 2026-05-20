from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert


async def _seed_alert(
    session: AsyncSession,
    title: str = "Test Alert",
    message: str = "Something failed",
    severity: str = "error",
) -> dict:
    alert = Alert(title=title, message=message, severity=severity)
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return {"id": str(alert.id), "title": alert.title, "status": alert.status}


# ── List ──────────────────────────────────────────────────────────────────────


async def test_list_alerts_empty(async_client: AsyncClient) -> None:
    r = await async_client.get("/api/alerts")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_alerts(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_alert(db_session, title="Alert A")
    await _seed_alert(db_session, title="Alert B")
    r = await async_client.get("/api/alerts")
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_list_alerts_filter_open(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_alert(db_session, title="Open One")
    r = await async_client.get("/api/alerts?status=open")
    assert r.status_code == 200
    assert all(a["status"] == "open" for a in r.json())


async def test_list_alerts_filter_resolved(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    created = await _seed_alert(db_session, title="Will Resolve")
    await async_client.patch(f"/api/alerts/{created['id']}/resolve")
    r = await async_client.get("/api/alerts?status=resolved")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["status"] == "resolved"


async def test_alert_fields(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    created = await _seed_alert(
        db_session,
        title="Field Check",
        message="details here",
        severity="warning",
    )
    r = await async_client.get("/api/alerts")
    assert r.status_code == 200
    item = next(a for a in r.json() if a["id"] == created["id"])
    assert item["title"] == "Field Check"
    assert item["message"] == "details here"
    assert item["severity"] == "warning"
    assert item["source_type"] is None
    assert item["source_id"] is None
    assert item["acknowledged_at"] is None
    assert item["resolved_at"] is None


# ── Resolve ───────────────────────────────────────────────────────────────────


async def test_resolve_alert(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    created = await _seed_alert(db_session)
    r = await async_client.patch(f"/api/alerts/{created['id']}/resolve")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "resolved"
    assert data["resolved_at"] is not None


async def test_resolve_alert_already_resolved(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    created = await _seed_alert(db_session)
    await async_client.patch(f"/api/alerts/{created['id']}/resolve")
    r = await async_client.patch(f"/api/alerts/{created['id']}/resolve")
    assert r.status_code == 409


async def test_resolve_alert_not_found(async_client: AsyncClient) -> None:
    r = await async_client.patch(
        "/api/alerts/00000000-0000-0000-0000-000000000000/resolve"
    )
    assert r.status_code == 404


# ── Acknowledge ───────────────────────────────────────────────────────────────


async def test_acknowledge_alert(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    created = await _seed_alert(db_session)
    r = await async_client.patch(f"/api/alerts/{created['id']}/acknowledge")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "acknowledged"
    assert data["acknowledged_at"] is not None


async def test_acknowledge_alert_not_found(async_client: AsyncClient) -> None:
    r = await async_client.patch(
        "/api/alerts/00000000-0000-0000-0000-000000000000/acknowledge"
    )
    assert r.status_code == 404


# ── Auto-alert on job failure ─────────────────────────────────────────────────


async def test_auto_alert_on_job_failure(
    async_client: AsyncClient,
) -> None:
    r = await async_client.post(
        "/api/jobs",
        json={
            "name": "FailJob",
            "url": "http://this-host-does-not-exist.invalid/path",
            "method": "GET",
        },
    )
    assert r.status_code == 201
    job_id = r.json()["id"]

    exec_r = await async_client.post(f"/api/jobs/{job_id}/run")
    assert exec_r.status_code == 202
    assert exec_r.json()["status"] == "failure"

    alerts_r = await async_client.get("/api/alerts")
    assert alerts_r.status_code == 200
    alerts = alerts_r.json()
    assert len(alerts) >= 1
    auto = next(
        (a for a in alerts if "FailJob" in a["title"]),
        None,
    )
    assert auto is not None
    assert auto["severity"] == "error"
    assert auto["source_type"] == "job_execution"
    assert auto["source_id"] is not None
    assert auto["status"] == "open"
