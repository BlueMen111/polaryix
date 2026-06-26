from fastapi import APIRouter, HTTPException

from app.domain.dashboards.schemas import CreateDashboardRequest
from app.infrastructure.storage.dashboard_storage import (
    create_dashboard,
    get_dashboard,
    get_public_dashboard,
    list_dashboards,
)

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.post("")
def create_dashboard_route(payload: CreateDashboardRequest):
    return create_dashboard(payload)


@router.get("")
def list_dashboards_route():
    return list_dashboards()


@router.get("/{dashboard_id}")
def get_dashboard_route(dashboard_id: str):
    dashboard = get_dashboard(dashboard_id)

    if dashboard is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    return dashboard


@router.get("/public/{slug}")
def get_public_dashboard_route(slug: str):
    dashboard = get_public_dashboard(slug)

    if dashboard is None:
        raise HTTPException(status_code=404, detail="Public dashboard not found")

    return dashboard