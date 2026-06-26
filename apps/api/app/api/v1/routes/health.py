from fastapi import APIRouter

from app.core.config.settings import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check() -> dict:
    """Verifica se a API está online."""

    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }