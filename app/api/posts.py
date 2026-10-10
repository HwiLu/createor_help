from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.post import Post
from app.models.user import User
from app.schemas import PostCreate, PostUpdate
from app.services.post_service import (
    applicant_count,
    close_post,
    create_post,
    delete_post,
    get_post,
    list_posts,
    update_post,
)

router = APIRouter(prefix="/posts", tags=["posts"])


def _json(post: Post, db: Session) -> dict:
    occupied = applicant_count(db, post.id)
    return {
        "id": post.id,
        "user_id": post.user_id,
        "title": post.title,
        "content": post.content,
        "mutual_type": post.mutual_type,
        "target_platform": post.target_platform,
        "target_creator_account_id": post.target_creator_account_id,
        "requires_follow_back": post.requires_follow_back,
        "max_applicants": post.max_applicants,
        "expires_at": post.expires_at,
        "status": post.status,
        "category": post.category,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "applicant_count": occupied,
        "remaining_slots": max(post.max_applicants - occupied, 0),
        "author": {
            "id": post.author.id,
            "nickname": post.author.nickname,
            "avatar_url": post.author.avatar_url,
        },
        "target_account": {
            "id": post.target_account.id,
            "platform": post.target_account.platform,
            "account_name": post.target_account.account_name,
            "profile_url": post.target_account.profile_url,
        },
    }


@router.get("")
def list_posts_api(
    db: Session = Depends(get_db),
    platform: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    _: Optional[User] = Depends(get_current_user_optional),
):
    posts, total = list_posts(db, platform, category, keyword, status_filter, page, page_size)
    return {"items": [_json(p, db) for p in posts], "total": total, "page": page, "page_size": page_size}


@router.post("")
def create_post_api(data: PostCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = create_post(db, user, data)
    return _json(post, db)


@router.get("/{post_id}")
def get_post_api(post_id: int, db: Session = Depends(get_db), _: Optional[User] = Depends(get_current_user_optional)):
    post = get_post(db, post_id)
    return _json(post, db)


@router.patch("/{post_id}")
def update_post_api(post_id: int, data: PostUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = update_post(db, user, post_id, data)
    return _json(post, db)


@router.post("/{post_id}/close")
def close_post_api(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = close_post(db, user, post_id)
    return _json(post, db)


@router.delete("/{post_id}")
def delete_post_api(post_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    delete_post(db, user, post_id)
    return {"ok": True}
