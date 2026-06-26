from fastapi import APIRouter

from app.api.v1.routes.analysis_sessions import router as analysis_sessions_router
from app.api.v1.routes.dashboards import router as dashboards_router
from app.api.v1.routes.datasets import router as datasets_router
from app.api.v1.routes.health import router as health_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(analysis_sessions_router)
api_router.include_router(datasets_router)
api_router.include_router(dashboards_router)