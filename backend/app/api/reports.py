import csv
import json
import uuid
from collections import Counter
from datetime import datetime
from io import StringIO
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alert import Alert
from app.models.execution import Execution
from app.models.job import Job
from app.models.report import Report
from app.schemas.report import (
    ReportGenerateRequest,
    ReportRead,
    ReportSummaryRead,
)

router = APIRouter(prefix="/reports", tags=["reports"])

FAILED_STATUSES = {"failure", "error", "timeout"}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _load_content(report: Report) -> dict[str, Any]:
    try:
        content = json.loads(report.content or "{}")
    except json.JSONDecodeError:
        return {}
    return content if isinstance(content, dict) else {}


async def _get_or_404(session: AsyncSession, report_id: uuid.UUID) -> Report:
    result = await session.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


async def _build_report_content(
    session: AsyncSession,
    period_start: datetime,
    period_end: datetime,
) -> dict[str, Any]:
    jobs = (await session.execute(select(Job))).scalars().all()
    job_names = {str(job.id): job.name for job in jobs}

    executions = (
        (
            await session.execute(
                select(Execution)
                .where(
                    Execution.started_at >= period_start,
                    Execution.started_at <= period_end,
                )
                .order_by(Execution.started_at.desc())
            )
        )
        .scalars()
        .all()
    )

    alerts = (
        (
            await session.execute(
                select(Alert)
                .where(
                    Alert.created_at >= period_start,
                    Alert.created_at <= period_end,
                )
                .order_by(Alert.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    successes = sum(1 for item in executions if item.status == "success")
    failures = sum(1 for item in executions if item.status in FAILED_STATUSES)
    total_executions = len(executions)
    terminal_executions = successes + failures
    durations = [
        item.duration_ms for item in executions if item.duration_ms is not None
    ]
    average_duration_ms = (
        round(sum(durations) / len(durations)) if durations else None
    )
    success_rate = (
        round(successes / terminal_executions * 100, 1)
        if terminal_executions > 0
        else 0.0
    )

    failed_counter = Counter(
        str(item.job_id) for item in executions if item.status in FAILED_STATUSES
    )
    top_failed_jobs = [
        {
            "job_id": job_id,
            "job_name": job_names.get(job_id, "Unknown job"),
            "failures": count,
        }
        for job_id, count in failed_counter.most_common(5)
    ]

    execution_rows = [
        {
            "id": str(item.id),
            "job_id": str(item.job_id),
            "job_name": job_names.get(str(item.job_id), "Unknown job"),
            "trigger_type": item.trigger_type,
            "status": item.status,
            "started_at": _iso(item.started_at),
            "finished_at": _iso(item.finished_at),
            "duration_ms": item.duration_ms,
            "response_status_code": item.response_status_code,
            "error_message": item.error_message,
        }
        for item in executions
    ]

    alert_rows = [
        {
            "id": str(item.id),
            "title": item.title,
            "message": item.message,
            "severity": item.severity,
            "status": item.status,
            "source_type": item.source_type,
            "source_id": str(item.source_id) if item.source_id else None,
            "created_at": _iso(item.created_at),
        }
        for item in alerts
    ]

    recommendations = []
    if failures:
        recommendations.append("Review jobs with repeated failures.")
    else:
        recommendations.append("No failures recorded in the selected period.")
    if any(item.status != "resolved" for item in alerts):
        recommendations.append("Resolve or acknowledge open alerts.")

    return {
        "period": {
            "start": _iso(period_start),
            "end": _iso(period_end),
        },
        "summary": {
            "total_jobs": len(jobs),
            "executions": total_executions,
            "successes": successes,
            "failures": failures,
            "success_rate": success_rate,
            "average_duration_ms": average_duration_ms,
            "alerts": len(alerts),
        },
        "top_failed_jobs": top_failed_jobs,
        "alerts": alert_rows,
        "executions": execution_rows,
        "recommendations": recommendations,
    }


def _content_to_markdown(content: dict[str, Any]) -> str:
    period = content.get("period", {})
    summary = content.get("summary", {})
    top_failed_jobs = content.get("top_failed_jobs") or []
    alerts = content.get("alerts") or []
    recommendations = content.get("recommendations") or []

    lines = [
        "# AutoFlowOps Operational Report",
        "",
        f"- Period start: {period.get('start', '-')}",
        f"- Period end: {period.get('end', '-')}",
        "",
        "## Summary",
        "",
        f"- Total jobs: {summary.get('total_jobs', 0)}",
        f"- Executions: {summary.get('executions', 0)}",
        f"- Successes: {summary.get('successes', 0)}",
        f"- Failures: {summary.get('failures', 0)}",
        f"- Success rate: {summary.get('success_rate', 0.0)}%",
        f"- Average duration: {summary.get('average_duration_ms', '-')}",
        f"- Alerts: {summary.get('alerts', 0)}",
        "",
        "## Top Failed Jobs",
        "",
    ]

    if top_failed_jobs:
        for item in top_failed_jobs:
            if isinstance(item, dict):
                lines.append(
                    f"- {item.get('job_name', 'Unknown job')}: "
                    f"{item.get('failures', 0)} failures"
                )
    else:
        lines.append("- No failed jobs in this period.")

    lines.extend(["", "## Alerts", ""])
    if alerts:
        for item in alerts:
            if isinstance(item, dict):
                lines.append(
                    f"- [{item.get('severity', '-')}] "
                    f"{item.get('title', '-')} ({item.get('status', '-')})"
                )
    else:
        lines.append("- No alerts in this period.")

    lines.extend(["", "## Recommendations", ""])
    for item in recommendations:
        lines.append(f"- {item}")

    return "\n".join(lines) + "\n"


def _content_to_csv(content: dict[str, Any]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "job_id",
        "job_name",
        "trigger_type",
        "status",
        "started_at",
        "finished_at",
        "duration_ms",
        "response_status_code",
        "error_message",
    ])
    rows = content.get("executions") or []
    for row in rows:
        if not isinstance(row, dict):
            continue
        writer.writerow([
            row.get("id"),
            row.get("job_id"),
            row.get("job_name"),
            row.get("trigger_type"),
            row.get("status"),
            row.get("started_at"),
            row.get("finished_at"),
            row.get("duration_ms"),
            row.get("response_status_code"),
            row.get("error_message"),
        ])
    return output.getvalue()


@router.post("/generate", response_model=ReportRead, status_code=201)
async def generate_report(
    payload: ReportGenerateRequest,
    session: AsyncSession = Depends(get_db),
) -> ReportRead:
    content = await _build_report_content(
        session=session,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    name = payload.name or (
        f"Operational report {payload.period_start.date()} "
        f"to {payload.period_end.date()}"
    )
    report = Report(
        name=name,
        format="json",
        period_start=payload.period_start,
        period_end=payload.period_end,
        content=json.dumps(content, sort_keys=True),
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return ReportRead.model_validate(report)


@router.get("", response_model=list[ReportSummaryRead])
async def list_reports(
    session: AsyncSession = Depends(get_db),
) -> list[ReportSummaryRead]:
    result = await session.execute(select(Report).order_by(Report.created_at.desc()))
    return [ReportSummaryRead.model_validate(item) for item in result.scalars().all()]


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> ReportRead:
    report = await _get_or_404(session, report_id)
    return ReportRead.model_validate(report)


@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    format: Literal["json", "markdown", "csv"] = "json",
    session: AsyncSession = Depends(get_db),
) -> Response:
    report = await _get_or_404(session, report_id)
    content = _load_content(report)

    if format == "markdown":
        body = _content_to_markdown(content)
        media_type = "text/markdown"
        extension = "md"
    elif format == "csv":
        body = _content_to_csv(content)
        media_type = "text/csv"
        extension = "csv"
    else:
        body = json.dumps(content, indent=2, sort_keys=True)
        media_type = "application/json"
        extension = "json"

    return Response(
        content=body,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="autoflowops-report-{report.id}.{extension}"'
            )
        },
    )
