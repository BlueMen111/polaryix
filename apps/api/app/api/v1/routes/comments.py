from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.auth_store import get_current_user
from app.core.comments_store import create_comment, public_comment, read_comments


router = APIRouter(prefix="/comments", tags=["Comments"])


class CommentPayload(BaseModel):
    message: str = Field(..., min_length=3, max_length=500)


@router.get("")
async def list_comments(limit: int = 24) -> dict:
    safe_limit = min(max(limit, 1), 50)
    comments = [public_comment(comment) for comment in read_comments()[:safe_limit]]
    return {"comments": comments}


@router.post("", status_code=status.HTTP_201_CREATED)
async def post_comment(request: Request, payload: CommentPayload) -> dict:
    user = get_current_user(request, required=True)
    message = payload.message.strip()
    if len(message) < 3:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Escreva um comentario um pouco maior.")

    comment = create_comment(user, message)
    return {"comment": public_comment(comment)}
