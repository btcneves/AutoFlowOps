"""Executes HTTP jobs and persists execution records with masked sensitive data."""

import json
import time
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.execution import Execution
from app.models.job import Job
from app.services.masking import mask_sensitive_body, mask_sensitive_headers


async def run_job_http(
    job: Job,
    session: AsyncSession,
    trigger_type: str = "manual",
) -> Execution:
    headers: dict[str, str] = (
        json.loads(job.headers_encrypted) if job.headers_encrypted else {}
    )
    body: str | None = job.body_encrypted

    execution = Execution(
        id=uuid.uuid4(),
        job_id=job.id,
        trigger_type=trigger_type,
        status="running",
        started_at=datetime.now(UTC),
        request_method=job.method or "GET",
        request_url=job.url,
        request_headers_masked=json.dumps(mask_sensitive_headers(headers)),
        request_body_masked=mask_sensitive_body(body),
    )
    session.add(execution)
    await session.flush()

    start = time.monotonic()
    try:
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
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((time.monotonic() - start) * 1000)
        execution.status = "failure"
        execution.error_message = str(exc)
        execution.duration_ms = duration_ms

    execution.finished_at = datetime.now(UTC)

    job.last_run_at = datetime.now(UTC)
    session.add(job)

    if execution.status == "failure":
        detail = execution.error_message or (
            f"HTTP {execution.response_status_code}"
        )
        alert = Alert(
            title=f'Job "{job.name}" failed',
            message=detail,
            severity="error",
            source_type="job_execution",
            source_id=execution.id,
        )
        session.add(alert)

    await session.commit()
    await session.refresh(execution)
    return execution
