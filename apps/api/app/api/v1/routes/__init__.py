from fastapi import APIRouter

from app.api.v1.routes.analysis_sessions import router as analysis_sessions_router
from app.api.v1.routes.analysis_sessions_files import router as analysis_sessions_files_router
from app.api.v1.routes.analysis_sessions_progress import router as analysis_sessions_progress_router
from app.api.v1.routes.admin import router as admin_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.comments import router as comments_router
from app.api.v1.routes.conversions import router as conversions_router
from app.api.v1.routes.converter import router as converter_router
from app.api.v1.routes.dashboards import router as dashboards_router
from app.api.v1.routes.datasets import router as datasets_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.image_tools import router as image_tools_router
from app.api.v1.routes.me import router as me_router
from app.api.v1.routes.workspace import router as workspace_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(admin_router)
api_router.include_router(auth_router)
api_router.include_router(comments_router)
api_router.include_router(conversions_router)
api_router.include_router(me_router)
api_router.include_router(analysis_sessions_router)
api_router.include_router(analysis_sessions_files_router)
api_router.include_router(analysis_sessions_progress_router)
api_router.include_router(converter_router)
api_router.include_router(image_tools_router)
api_router.include_router(datasets_router)
api_router.include_router(dashboards_router)
api_router.include_router(workspace_router)
