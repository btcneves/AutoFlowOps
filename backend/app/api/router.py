from fastapi import APIRouter, Depends

from app.api import (
    alerts,
    auth,
    escalation_policies,
    executions,
    health,
    jobs,
    notification_templates,
    notifications,
    reports,
    stats,
    webhook_receiver,
    webhooks,
)
from app.dependencies import get_current_user

router = APIRouter(prefix="/api")

# Public endpoints (no authentication required)
router.include_router(health.router, tags=["health"])
router.include_router(auth.router)
router.include_router(webhook_receiver.router)

# Protected endpoints — require a valid JWT Bearer token
_auth = [Depends(get_current_user)]
router.include_router(jobs.router, dependencies=_auth)
router.include_router(executions.router, dependencies=_auth)
router.include_router(stats.router, tags=["stats"], dependencies=_auth)
router.include_router(webhooks.router, dependencies=_auth)
router.include_router(alerts.router, dependencies=_auth)
router.include_router(notifications.router, dependencies=_auth)
router.include_router(notification_templates.router, dependencies=_auth)
router.include_router(escalation_policies.router, dependencies=_auth)
router.include_router(reports.router, dependencies=_auth)
