from fastapi import APIRouter
from sqlalchemy import text

from app import __version__
from app.config import settings
from app.database import engine

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    db_status = "ok"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_status = "error"
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "database": db_status,
    }


@router.get("/version")
def get_version() -> dict:
    return {
        "version": __version__,
        "app": settings.app_name,
    }
