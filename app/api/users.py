from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.user import User
from app.schemas import UserUpdate
from app.services.trust_service import compute_tags, compute_trust_stats

router = APIRouter(prefix="/users", tags=["users"])


def _public_user(user: User, db: Session) -> dict:
    stats = compute_trust_stats(db, user.id)
    from datetime import datetime, timezone

    joined_days = (datetime.now(timezone.utc) - user.created_at.replace(tzinfo=timezone.utc)).days
    tags = compute_tags(stats, joined_days)
    return {
        "id": user.id,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "role": user.role,
        "created_at": user.created_at,
        "stats": stats,
        "tags": tags,
    }


@router.get("/me")
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _public_user(user, db)


@router.patch("/me")
def update_me(data: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.nickname is not None:
        user.nickname = data.nickname.strip()
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    if data.bio is not None:
        user.bio = data.bio
    db.commit()
    db.refresh(user)
    return _public_user(user, db)


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db), _: Optional[User] = Depends(get_current_user_optional)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return _public_user(user, db)
