"""Executes HTTP jobs and persists execution records with masked sensitive data."""

import json
import time
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alert import Alert
from app.models.alert_rule import AlertRule
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


def _parse_non_negative_int(raw: str) -> int | None:
    try:
        value = int(raw)
    except ValueError:
        return None
    if value < 0:
        return None
    return value


async def create_queued_execution(
    job: Job,
    session: AsyncSession,
    trigger_type: str = "manual",
) -> Execution:
    headers = _load_headers(job)
    execution = Execution(
        id=uuid.uuid4(),
        job_id=job.id,
        workspace_id=job.workspace_id,
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


async def _count_consecutive_failures(
    job_id: uuid.UUID,
    session: AsyncSession,
    limit: int = 50,
) -> int:
    """Count consecutive failures among the most-recent completed executions."""
    result = await session.execute(
        select(Execution.status)
        .where(
            Execution.job_id == job_id,
            Execution.status.in_(["success", "failure", "timeout"]),
        )
        .order_by(Execution.started_at.desc())
        .limit(limit)
    )
    statuses = result.scalars().all()
    count = 0
    for s in statuses:
        if s in FAILED_EXECUTION_STATUSES:
            count += 1
        else:
            break
    return count


async def evaluate_alert_rules(
    job: Job,
    execution: Execution,
    session: AsyncSession,
) -> list[Alert]:
    """Evaluate enabled alert rules for *job* against the just-completed *execution*.

    Returns a list of Alert objects (not yet added to the session) for every
    rule whose condition is satisfied.
    """
    result = await session.execute(
        select(AlertRule).where(
            AlertRule.job_id == job.id,
            AlertRule.is_enabled.is_(True),
        )
    )
    rules = result.scalars().all()

    triggered: list[Alert] = []
    for rule in rules:
        detail: str | None = None

        if rule.condition_type == "http_status_gte":
            threshold = _parse_non_negative_int(rule.condition_value)
            if threshold is None:
                continue
            if (
                execution.response_status_code is not None
                and execution.response_status_code >= threshold
            ):
                detail = (
                    f"HTTP {execution.response_status_code} >= {threshold}"
                )

        elif rule.condition_type == "duration_ms_gte":
            threshold = _parse_non_negative_int(rule.condition_value)
            if threshold is None:
                continue
            if (
                execution.duration_ms is not None
                and execution.duration_ms >= threshold
            ):
                detail = f"Duration {execution.duration_ms} ms >= {threshold} ms"

        elif rule.condition_type == "response_body_contains":
            pattern = rule.condition_value
            if execution.response_body_preview and (
                pattern in execution.response_body_preview
            ):
                detail = f'Response body contains "{pattern}"'

        elif rule.condition_type == "consecutive_failures_gte":
            threshold = _parse_non_negative_int(rule.condition_value)
            if threshold is None:
                continue
            consecutive = await _count_consecutive_failures(job.id, session)
            if consecutive >= threshold:
                detail = (
                    f"{consecutive} consecutive failures (threshold: {threshold})"
                )

        if detail is not None:
            title = rule.message or f'Job "{job.name}": {detail}'
            triggered.append(
                Alert(
                    title=title[:255],
                    message=detail,
                    severity=rule.severity,
                    source_type="alert_rule",
                    source_id=rule.id,
                    workspace_id=job.workspace_id,
                )
            )

    return triggered


def create_failure_alert(job: Job, execution: Execution) -> Alert:
    detail = execution.error_message or f"HTTP {execution.response_status_code}"
    return Alert(
        title=f'Job "{job.name}" failed',
        message=detail,
        severity="error",
        source_type="job_execution",
        source_id=execution.id,
        workspace_id=job.workspace_id,
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
        execution = Execution(
            id=uuid.uuid4(),
            job_id=job.id,
            workspace_id=job.workspace_id,
        )

    execution.trigger_type = trigger_type
    execution.workspace_id = job.workspace_id
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

    rule_alerts: list[Alert] = []
    if create_alert:
        rule_alerts = await evaluate_alert_rules(job, execution, session)
        for ra in rule_alerts:
            session.add(ra)
            await session.flush()
            alerts_created_total.labels(severity=ra.severity).inc()

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

    for ra in rule_alerts:
        await dispatch_alert_notifications(session, ra)
        await publish_event_async(
            "alert.created",
            {
                "alert_id": str(ra.id),
                "title": ra.title,
                "severity": ra.severity,
                "status": ra.status,
                "source_type": ra.source_type,
            },
        )

    await session.refresh(execution)
    return execution
