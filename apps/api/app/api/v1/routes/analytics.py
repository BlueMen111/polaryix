from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.analytics import get_analytics_summary, record_analytics_event
from app.core.auth_store import get_current_user
from app.core.config.settings import settings


router = APIRouter(prefix="/analytics", tags=["Analytics"])


class AnalyticsEventPayload(BaseModel):
    event_type: str = Field("page_view", max_length=80)
    path: str | None = Field(None, max_length=512)
    referrer: str | None = Field(None, max_length=512)
    metadata: dict | None = None


@router.post("/events", status_code=status.HTTP_201_CREATED)
async def create_analytics_event(request: Request, payload: AnalyticsEventPayload) -> dict:
    user = get_current_user(request, required=False)
    event = record_analytics_event(
        event_type=payload.event_type,
        path=payload.path,
        referrer=payload.referrer,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
        user_id=str(user["id"]) if user else None,
        metadata=payload.metadata,
    )
    return {"ok": True, "id": event["id"]}


@router.get("/summary")
async def analytics_summary(x_admin_token: str | None = Header(default=None)) -> dict:
    if settings.admin_cleanup_token and x_admin_token != settings.admin_cleanup_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token administrativo invalido.")
    if not settings.admin_cleanup_token and not settings.debug:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Configure ADMIN_CLEANUP_TOKEN para usar este endpoint.")
    return get_analytics_summary()


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else None
