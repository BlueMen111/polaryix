from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from app.core.auth_store import get_current_user, public_user
from app.core.conversion_history import (
    delete_user_record,
    get_user_record,
    list_workspace_records,
    public_record,
    retention_hours,
    set_favorite,
    storage_limit_bytes,
    storage_used_bytes,
)


router = APIRouter(tags=["Workspace"])


def _storage_summary(user: dict) -> dict:
    used = storage_used_bytes(str(user["id"]))
    limit = storage_limit_bytes(user)
    return {
        "used": used,
        "limit": limit,
        "percent": round((used / max(limit, 1)) * 100, 1),
        "retention_hours": retention_hours(user),
    }


@router.get("/workspace")
async def workspace(
    request: Request,
    q: str | None = None,
    filter: str = Query("all", pattern="^(all|favorites|expired|completed|queued|processing|failed|deleted)$"),
    limit: int = 100,
) -> dict:
    user = get_current_user(request, required=True)
    favorite = True if filter == "favorites" else None
    status_filter = None if filter in {"all", "favorites"} else filter
    return {
        "files": list_workspace_records(str(user["id"]), limit=limit, favorite=favorite, search=q, status_filter=status_filter),
        "storage": _storage_summary(user),
    }


@router.get("/workspace/favorites")
async def workspace_favorites(request: Request, limit: int = 50) -> dict:
    user = get_current_user(request, required=True)
    return {"files": list_workspace_records(str(user["id"]), limit=limit, favorite=True), "storage": _storage_summary(user)}


@router.post("/workspace/{file_id}/favorite")
async def favorite_workspace_file(request: Request, file_id: str) -> dict:
    user = get_current_user(request, required=True)
    return {"file": set_favorite(str(user["id"]), file_id, True)}


@router.delete("/workspace/{file_id}/favorite")
async def unfavorite_workspace_file(request: Request, file_id: str) -> dict:
    user = get_current_user(request, required=True)
    return {"file": set_favorite(str(user["id"]), file_id, False)}


@router.delete("/workspace/{file_id}")
async def delete_workspace_file(request: Request, file_id: str) -> dict:
    user = get_current_user(request, required=True)
    return {"file": delete_user_record(str(user["id"]), file_id), "storage": _storage_summary(user)}


@router.get("/workspace/{file_id}/download")
async def download_workspace_file(request: Request, file_id: str) -> FileResponse:
    user = get_current_user(request, required=True)
    record = get_user_record(str(user["id"]), file_id)
    public = public_record(record)
    if public["status"] != "completed":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Arquivo expirado ou indisponivel.")

    file_path = Path(str(record.get("output_path") or "")).resolve()
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo final nao encontrado.")

    filename = Path(str(record.get("original_filename") or file_path.name)).stem
    extension = str(record.get("extension") or record.get("target_format") or file_path.suffix.lstrip(".")).lower()
    return FileResponse(file_path, media_type="application/octet-stream", filename=f"{filename}-polaryix.{extension}")


@router.get("/dashboard")
async def dashboard(request: Request) -> dict:
    user = get_current_user(request, required=True)
    files = list_workspace_records(str(user["id"]), limit=200)
    recent = files[:8]
    favorites = [item for item in files if item.get("is_favorite")][:6]
    active = [item for item in files if item.get("status") in {"queued", "processing"}]
    storage = _storage_summary(user)
    profile = public_user(user)
    return {
        "user": profile,
        "plan": profile["plan"],
        "credits": profile["credits_remaining"],
        "storage": storage,
        "workspace_count": len([item for item in files if item.get("status") != "deleted"]),
        "favorite_count": len(favorites),
        "active_jobs": active[:6],
        "recent_jobs": recent,
        "favorite_files": favorites,
    }
