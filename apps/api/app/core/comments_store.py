from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config.settings import settings


def comments_path() -> Path:
    return settings.storage_path / "comments" / "comments.json"


def read_comments() -> list[dict]:
    path = comments_path()
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Base de comentarios invalida.") from exc

    return data if isinstance(data, list) else []


def write_comments(comments: list[dict]) -> None:
    path = comments_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(comments, ensure_ascii=False, indent=2), encoding="utf-8")


def public_comment(comment: dict) -> dict:
    return {
        "id": comment["id"],
        "message": comment["message"],
        "user_name": comment["user_name"],
        "avatar_url": comment.get("avatar_url"),
        "created_at": comment["created_at"],
    }


def create_comment(user: dict, message: str) -> dict:
    now = datetime.now(UTC).isoformat()
    comment = {
        "id": str(uuid4()),
        "user_id": user["id"],
        "user_name": user.get("name") or "Usuario Polaryix",
        "avatar_url": user.get("avatar_url"),
        "message": message.strip(),
        "created_at": now,
        "updated_at": now,
    }

    comments = read_comments()
    comments.insert(0, comment)
    write_comments(comments[:200])
    return comment
