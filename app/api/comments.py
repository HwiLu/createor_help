from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.comment import Comment
from app.models.enums import CommentStatus
from app.models.post import Post
from app.models.user import User
from app.schemas import CommentCreate

router = APIRouter(prefix="/posts/{post_id}/comments", tags=["comments"])


def _json(c: Comment) -> dict:
    return {
        "id": c.id,
        "post_id": c.post_id,
        "user_id": c.user_id,
        "content": c.content,
        "created_at": c.created_at,
        "author": {"id": c.author.id, "nickname": c.author.nickname, "avatar_url": c.author.avatar_url},
    }


@router.get("")
def list_comments(
    post_id: int,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    _: Optional[User] = Depends(get_current_user_optional),
):
    query = db.query(Comment).filter(Comment.post_id == post_id, Comment.status == CommentStatus.ACTIVE.value)
    total = query.count()
    comments = query.order_by(Comment.created_at.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_json(c) for c in comments], "total": total, "page": page, "page_size": page_size}


@router.post("")
def create_comment(
    post_id: int,
    data: CommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.get(Post, post_id)
    if post is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")

    comment = Comment(post_id=post_id, user_id=user.id, content=data.content.strip(), status=CommentStatus.ACTIVE.value)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _json(comment)
