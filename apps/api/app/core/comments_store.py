from __future__ import annotations

import json
from datetime import datetime, timezone

UTC = timezone.utc
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config.settings import settings
from app.core.database import SessionLocal, is_database_enabled
from app.core.db_models import CommentModel


def comments_path() -> Path:
    return settings.storage_path / "comments" / "comments.json"


def read_comments() -> list[dict]:
    if is_database_enabled():
        with SessionLocal() as db:
            return [_db_comment_to_dict(comment) for comment in db.query(CommentModel).order_by(CommentModel.created_at.desc()).limit(200).all()]
    path = comments_path()
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Base de comentarios invalida.") from exc

    return data if isinstance(data, list) else []


def write_comments(comments: list[dict]) -> None:
    if is_database_enabled():
        with SessionLocal() as db:
            for comment in comments:
                db.merge(_dict_to_db_comment(comment))
            db.commit()
        return
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


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.now(UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _db_comment_to_dict(comment: CommentModel) -> dict:
    return {
        "id": comment.id,
        "user_id": comment.user_id,
        "user_name": comment.user_name,
        "avatar_url": comment.avatar_url,
        "message": comment.message,
        "status": comment.status,
        "created_at": comment.created_at.isoformat(),
        "updated_at": comment.updated_at.isoformat(),
    }


def _dict_to_db_comment(comment: dict) -> CommentModel:
    return CommentModel(
        id=str(comment["id"]),
        user_id=comment.get("user_id"),
        user_name=str(comment.get("user_name") or "Usuario Polaryix"),
        avatar_url=comment.get("avatar_url"),
        message=str(comment.get("message") or ""),
        status=str(comment.get("status") or "published"),
        created_at=_parse_datetime(comment.get("created_at")),
        updated_at=_parse_datetime(comment.get("updated_at") or comment.get("created_at")),
    )
