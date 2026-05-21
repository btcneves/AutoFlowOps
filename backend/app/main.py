import asyncio
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

import app.models  # noqa: F401 — ensure all models register with Base.metadata
from app import __version__
from app.api.router import router
from app.api.ws import redis_subscriber
from app.api.ws import router as ws_router
from app.config import settings
from app.database import async_session_factory, engine
from app.models.base import Base
from app.observability import configure_logging
from app.services.auth import bootstrap_admin
from app.services.scheduler import (
    get_scheduler,
    load_scheduled_jobs,
    register_escalation_checker,
)
from app.services.workspace import get_or_create_default_workspace

configure_logging(log_level=settings.log_level, env=settings.app_env)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "AutoFlowOps started (env=%s, version=%s)", settings.app_env, __version__
    )
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection OK")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database not available at startup: %s", exc)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema up to date")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not apply schema: %s", exc)

    try:
        async with async_session_factory() as session:
            await bootstrap_admin(session)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not bootstrap admin user: %s", exc)

    try:
        async with async_session_factory() as session:
            await get_or_create_default_workspace(session)
        logger.info("Default workspace ready")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not bootstrap default workspace: %s", exc)

    scheduler = get_scheduler()
    try:
        async with async_session_factory() as session:
            await load_scheduled_jobs(session)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load scheduled jobs at startup: %s", exc)
    register_escalation_checker()
    scheduler.start()
    logger.info("Scheduler started")

    subscriber_task = asyncio.create_task(redis_subscriber())

    yield

    subscriber_task.cancel()
    await asyncio.gather(subscriber_task, return_exceptions=True)
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "Open-source automation platform for scheduled jobs, "
        "API integrations and webhooks."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next: object) -> Response:
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=str(uuid.uuid4()))
    response: Response = await call_next(request)  # type: ignore[operator]
    return response


Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)

app.include_router(router)
app.include_router(ws_router)
