from fastapi import APIRouter

from app import __version__
from app.config import settings

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@router.get("/version")
def get_version() -> dict:
    return {
        "version": __version__,
        "app": settings.app_name,
    }
