from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.execution import Execution
from app.models.job import Job
from app.schemas.stats import DailyStats, StatsResponse

router = APIRouter()
FAILED_STATUSES = ("failure", "error")


@router.get("/stats", response_model=StatsResponse)
async def get_stats(session: AsyncSession = Depends(get_db)) -> StatsResponse:
    now = datetime.now(UTC)
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)

    total_jobs = (
        await session.execute(select(func.count()).select_from(Job))
    ).scalar_one()

    active_jobs = (
        await session.execute(
            select(func.count()).select_from(Job).where(Job.status == "active")
        )
    ).scalar_one()

    paused_jobs = (
        await session.execute(
            select(func.count()).select_from(Job).where(Job.status == "paused")
        )
    ).scalar_one()

    total_executions = (
        await session.execute(select(func.count()).select_from(Execution))
    ).scalar_one()

    executions_24h = (
        await session.execute(
            select(func.count())
            .select_from(Execution)
            .where(Execution.started_at >= since_24h)
        )
    ).scalar_one()

    failures_24h = (
        await session.execute(
            select(func.count())
            .select_from(Execution)
            .where(
                Execution.started_at >= since_24h,
                Execution.status.in_(FAILED_STATUSES),
            )
        )
    ).scalar_one()

    success_rate_24h = (
        round((executions_24h - failures_24h) / executions_24h * 100, 1)
        if executions_24h > 0
        else 0.0
    )

    rows = (
        await session.execute(
            select(Execution.started_at, Execution.status).where(
                Execution.started_at >= since_7d
            )
        )
    ).all()

    daily: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})
    for row in rows:
        started = row.started_at
        if started is not None:
            if started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            day_str = started.astimezone(UTC).strftime("%Y-%m-%d")
            if row.status in FAILED_STATUSES:
                daily[day_str]["failure"] += 1
            else:
                daily[day_str]["success"] += 1

    daily_stats = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        counts = daily.get(day, {})
        daily_stats.append(
            DailyStats(
                date=day,
                success=counts.get("success", 0),
                failure=counts.get("failure", 0),
            )
        )

    return StatsResponse(
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        paused_jobs=paused_jobs,
        total_executions=total_executions,
        executions_24h=executions_24h,
        failures_24h=failures_24h,
        success_rate_24h=success_rate_24h,
        daily_stats=daily_stats,
    )
