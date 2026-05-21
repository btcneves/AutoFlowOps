"""Executes HTTP jobs and persists execution records with masked sensitive data."""

import json
import time
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alert import Alert
from app.models.execution import Execution
from app.models.job import Job
from app.observability import alerts_created_total, job_executions_total
from app.services.event_publisher import publish_event_async
from app.services.masking import mask_sensitive_body, mask_sensitive_headers
from app.services.notifications import dispatch_alert_notifications
from app.services.ssrf_guard import check_url

FAILED_EXECUTION_STATUSES = {"failure", "timeout"}


def _load_headers(job: Job) -> dict[str, str]:
    return json.loads(job.headers_encrypted) if job.headers_encrypted else {}


def _exception_message(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        return str(exc.detail)
    return str(exc)


async def create_queued_execution(
    job: Job,
    session: AsyncSession,
    trigger_type: str = "manual",
) -> Execution:
    headers = _load_headers(job)
    execution = Execution(
        id=uuid.uuid4(),
        job_id=job.id,
        trigger_type=trigger_type,
        status="queued",
        started_at=datetime.now(UTC),
        request_method=job.method or "GET",
        request_url=job.url,
        request_headers_masked=json.dumps(mask_sensitive_headers(headers)),
        request_body_masked=mask_sensitive_body(job.body_encrypted),
    )
    session.add(execution)
    await session.commit()
    await session.refresh(execution)
    return execution


def create_failure_alert(job: Job, execution: Execution) -> Alert:
    detail = execution.error_message or f"HTTP {execution.response_status_code}"
    return Alert(
        title=f'Job "{job.name}" failed',
        message=detail,
        severity="error",
        source_type="job_execution",
        source_id=execution.id,
    )


async def run_job_http(
    job: Job,
    session: AsyncSession,
    trigger_type: str = "manual",
    execution: Execution | None = None,
    create_alert: bool = True,
    retry_attempt: int = 0,
) -> Execution:
    headers = _load_headers(job)
    body: str | None = job.body_encrypted

    if execution is None:
        execution = Execution(id=uuid.uuid4(), job_id=job.id)

    execution.trigger_type = trigger_type
    execution.status = "running"
    execution.started_at = datetime.now(UTC)
    execution.finished_at = None
    execution.duration_ms = None
    execution.request_method = job.method or "GET"
    execution.request_url = job.url
    execution.request_headers_masked = json.dumps(mask_sensitive_headers(headers))
    execution.request_body_masked = mask_sensitive_body(body)
    execution.response_status_code = None
    execution.response_body_preview = None
    execution.error_message = None
    execution.retry_attempt = retry_attempt
    session.add(execution)
    await session.flush()

    await publish_event_async(
        "execution.started",
        {
            "execution_id": str(execution.id),
            "job_id": str(execution.job_id),
            "job_name": job.name,
            "trigger_type": trigger_type,
            "status": "running",
        },
    )

    start = time.monotonic()
    try:
        if (
            settings.enable_ssrf_protection
            and not settings.allow_private_network_targets
        ):
            check_url(job.url or "")

        async with httpx.AsyncClient(timeout=float(job.timeout_seconds)) as client:
            response = await client.request(
                method=job.method or "GET",
                url=job.url or "",
                headers=headers,
                content=body.encode() if body else None,
            )
        duration_ms = int((time.monotonic() - start) * 1000)
        execution.status = "success" if response.is_success else "failure"
        execution.response_status_code = response.status_code
        execution.response_body_preview = response.text[:500]
        execution.duration_ms = duration_ms
    except httpx.TimeoutException as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        execution.status = "timeout"
        execution.error_message = _exception_message(exc) or "Request timed out"
        execution.duration_ms = duration_ms
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((time.monotonic() - start) * 1000)
        execution.status = "failure"
        execution.error_message = _exception_message(exc)
        execution.duration_ms = duration_ms

    execution.finished_at = datetime.now(UTC)

    job.last_run_at = datetime.now(UTC)
    session.add(job)

    job_executions_total.labels(
        status=execution.status, trigger_type=trigger_type
    ).inc()

    should_alert = (
        create_alert
        and job.alert_on_failure
        and execution.status in FAILED_EXECUTION_STATUSES
    )
    alert: Alert | None = None
    if should_alert:
        alert = create_failure_alert(job, execution)
        session.add(alert)
        await session.flush()
        alerts_created_total.labels(severity=alert.severity).inc()

    await session.commit()

    await publish_event_async(
        "execution.completed",
        {
            "execution_id": str(execution.id),
            "job_id": str(execution.job_id),
            "job_name": job.name,
            "status": execution.status,
            "duration_ms": execution.duration_ms,
            "response_status_code": execution.response_status_code,
            "trigger_type": execution.trigger_type,
        },
    )

    if alert is not None:
        await dispatch_alert_notifications(session, alert)
        await publish_event_async(
            "alert.created",
            {
                "alert_id": str(alert.id),
                "title": alert.title,
                "severity": alert.severity,
                "status": alert.status,
                "source_type": alert.source_type,
            },
        )

    await session.refresh(execution)
    return execution
