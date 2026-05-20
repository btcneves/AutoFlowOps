"""Role-based access control enforcement tests."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job


async def _create_job(session: AsyncSession) -> Job:
    job = Job(
        name="Test job",
        type="http",
        method="GET",
        url="https://example.com",
        schedule_type="manual",
        timeout_seconds=30,
        retry_count=0,
        retry_delay_seconds=0,
        alert_on_failure=False,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


class TestViewerCanRead:
    @pytest.mark.asyncio
    async def test_viewer_can_list_jobs(
        self, viewer_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _create_job(db_session)
        response = await viewer_client.get("/api/jobs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_can_list_alerts(self, viewer_client: AsyncClient) -> None:
        response = await viewer_client.get("/api/alerts")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_can_list_webhooks(self, viewer_client: AsyncClient) -> None:
        response = await viewer_client.get("/api/webhooks")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_can_list_reports(self, viewer_client: AsyncClient) -> None:
        response = await viewer_client.get("/api/reports")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_viewer_can_list_channels(self, viewer_client: AsyncClient) -> None:
        response = await viewer_client.get("/api/notification-channels")
        assert response.status_code == 200


class TestViewerCannotWrite:
    @pytest.mark.asyncio
    async def test_viewer_cannot_create_job(self, viewer_client: AsyncClient) -> None:
        response = await viewer_client.post(
            "/api/jobs",
            json={
                "name": "x",
                "method": "GET",
                "url": "https://example.com",
                "schedule_type": "manual",
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_run_job(
        self, viewer_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        job = await _create_job(db_session)
        response = await viewer_client.post(f"/api/jobs/{job.id}/run")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_resolve_alert(
        self, viewer_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.models.alert import Alert

        alert = Alert(title="T", message="M", severity="error", status="open")
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)
        response = await viewer_client.patch(f"/api/alerts/{alert.id}/resolve")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_notification_channel(
        self, viewer_client: AsyncClient
    ) -> None:
        response = await viewer_client.post(
            "/api/notification-channels",
            json={
                "name": "x",
                "type": "discord_webhook",
                "config": {"webhook_url": "https://discord.com/api/webhooks/1/x"},
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_access_users(
        self, viewer_client: AsyncClient
    ) -> None:
        response = await viewer_client.get("/api/users")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_access_audit_logs(
        self, viewer_client: AsyncClient
    ) -> None:
        response = await viewer_client.get("/api/audit-logs")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_cannot_generate_report(
        self, viewer_client: AsyncClient
    ) -> None:
        response = await viewer_client.post(
            "/api/reports/generate",
            json={
                "period_start": "2026-01-01T00:00:00Z",
                "period_end": "2026-01-31T23:59:59Z",
            },
        )
        assert response.status_code == 403


class TestOperatorCanWrite:
    @pytest.mark.asyncio
    async def test_operator_can_create_job(
        self, operator_client: AsyncClient
    ) -> None:
        response = await operator_client.post(
            "/api/jobs",
            json={
                "name": "Operator job",
                "method": "GET",
                "url": "https://example.com",
                "schedule_type": "manual",
            },
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_operator_cannot_manage_users(
        self, operator_client: AsyncClient
    ) -> None:
        response = await operator_client.get("/api/users")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_operator_cannot_create_notification_channel(
        self, operator_client: AsyncClient
    ) -> None:
        response = await operator_client.post(
            "/api/notification-channels",
            json={
                "name": "x",
                "type": "discord_webhook",
                "config": {"webhook_url": "https://discord.com/api/webhooks/1/x"},
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_operator_cannot_create_template(
        self, operator_client: AsyncClient
    ) -> None:
        response = await operator_client.post(
            "/api/notification-templates",
            json={"name": "t", "title_template": "{title}", "body_template": "{body}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_operator_cannot_access_audit_logs(
        self, operator_client: AsyncClient
    ) -> None:
        response = await operator_client.get("/api/audit-logs")
        assert response.status_code == 403


class TestAdminCanDoAll:
    @pytest.mark.asyncio
    async def test_admin_can_list_users(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/users")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_access_audit_logs(
        self, async_client: AsyncClient
    ) -> None:
        response = await async_client.get("/api/audit-logs")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_can_create_job(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/jobs",
            json={
                "name": "Admin job",
                "method": "GET",
                "url": "https://example.com",
                "schedule_type": "manual",
            },
        )
        assert response.status_code == 201
