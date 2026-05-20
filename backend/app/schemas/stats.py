from pydantic import BaseModel


class DailyStats(BaseModel):
    date: str
    success: int
    failure: int


class StatsResponse(BaseModel):
    total_jobs: int
    active_jobs: int
    paused_jobs: int
    total_executions: int
    executions_24h: int
    failures_24h: int
    success_rate_24h: float
    daily_stats: list[DailyStats]
