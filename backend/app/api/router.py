from fastapi import APIRouter

from app.api import alerts, health, jobs, reports, stats, webhooks

router = APIRouter(prefix="/api")
router.include_router(health.router, tags=["health"])
router.include_router(jobs.router)
router.include_router(stats.router, tags=["stats"])
router.include_router(webhooks.router)
router.include_router(alerts.router)
router.include_router(reports.router)
