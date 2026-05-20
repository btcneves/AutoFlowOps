"""Seed demo records for screenshots and local exploration."""

import asyncio
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import async_session_factory, engine
from app.models import Alert, Execution, Job, Report, Webhook, WebhookEvent


async def main() -> None:
    async with async_session_factory() as session:
        existing = await session.execute(
            select(Job).where(Job.name == "Demo Health Check")
        )
        if existing.scalar_one_or_none() is not None:
            print("Demo data already exists.")
            return

        now = datetime.now(UTC)
        health_job = Job(
            name="Demo Health Check",
            description="Checks the public API health endpoint every 5 minutes.",
            type="http",
            status="active",
            schedule_type="interval",
            schedule_expression="300",
            method="GET",
            url="https://httpbin.org/status/200",
            timeout_seconds=15,
            alert_on_failure=True,
            last_run_at=now - timedelta(minutes=8),
            next_run_at=now + timedelta(minutes=2),
        )
        billing_job = Job(
            name="Billing Sync",
            description="Example POST integration that recently failed.",
            type="http",
            status="active",
            schedule_type="cron",
            schedule_expression="*/30 * * * *",
            method="POST",
            url="https://api.example.com/billing/sync",
            headers_encrypted=json.dumps({"Authorization": "Bearer demo-token"}),
            body_encrypted=json.dumps({"account_id": "demo"}),
            timeout_seconds=30,
            alert_on_failure=True,
            last_run_at=now - timedelta(minutes=31),
            next_run_at=now + timedelta(minutes=29),
        )
        session.add_all([health_job, billing_job])
        await session.flush()

        executions = [
            Execution(
                job_id=health_job.id,
                trigger_type="scheduled",
                status="success",
                started_at=now - timedelta(minutes=8),
                finished_at=now - timedelta(minutes=7, seconds=59),
                duration_ms=340,
                request_method="GET",
                request_url=health_job.url,
                response_status_code=200,
                response_body_preview="OK",
            ),
            Execution(
                job_id=billing_job.id,
                trigger_type="scheduled",
                status="failure",
                started_at=now - timedelta(minutes=31),
                finished_at=now - timedelta(minutes=30, seconds=52),
                duration_ms=8200,
                request_method="POST",
                request_url=billing_job.url,
                request_headers_masked=json.dumps({"Authorization": "***MASKED***"}),
                response_status_code=503,
                response_body_preview="Service unavailable",
                error_message="HTTP 503",
            ),
        ]
        session.add_all(executions)
        await session.flush()

        webhook = Webhook(
            name="Order Events",
            slug="order-events",
            status="active",
            last_received_at=now - timedelta(minutes=12),
        )
        session.add(webhook)
        await session.flush()
        session.add(
            WebhookEvent(
                webhook_id=webhook.id,
                headers_masked=json.dumps({"content-type": "application/json"}),
                payload=json.dumps({"event": "order.created", "order_id": "demo-1001"}),
                source_ip="127.0.0.1",
                status="received",
            )
        )

        session.add(
            Alert(
                title='Job "Billing Sync" failed',
                message="HTTP 503",
                severity="error",
                source_type="job_execution",
                source_id=executions[1].id,
                status="open",
                created_at=now - timedelta(minutes=30),
            )
        )

        report_content = {
            "period": {
                "start": (now - timedelta(days=7)).isoformat(),
                "end": now.isoformat(),
            },
            "summary": {
                "total_jobs": 2,
                "executions": 2,
                "successes": 1,
                "failures": 1,
                "success_rate": 50.0,
                "average_duration_ms": 4270,
                "alerts": 1,
            },
            "top_failed_jobs": [
                {
                    "job_id": str(billing_job.id),
                    "job_name": billing_job.name,
                    "failures": 1,
                }
            ],
            "alerts": [
                {
                    "title": 'Job "Billing Sync" failed',
                    "severity": "error",
                    "status": "open",
                }
            ],
            "executions": [
                {
                    "id": str(execution.id),
                    "job_id": str(execution.job_id),
                    "job_name": (
                        health_job.name
                        if execution.job_id == health_job.id
                        else billing_job.name
                    ),
                    "trigger_type": execution.trigger_type,
                    "status": execution.status,
                    "started_at": execution.started_at.isoformat(),
                    "finished_at": (
                        execution.finished_at.isoformat()
                        if execution.finished_at
                        else None
                    ),
                    "duration_ms": execution.duration_ms,
                    "response_status_code": execution.response_status_code,
                    "error_message": execution.error_message,
                }
                for execution in executions
            ],
            "recommendations": ["Review jobs with repeated failures."],
        }
        session.add(
            Report(
                name="Demo Operational Report",
                format="json",
                period_start=now - timedelta(days=7),
                period_end=now,
                content=json.dumps(report_content, sort_keys=True),
            )
        )

        await session.commit()
        print("Demo data created.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
