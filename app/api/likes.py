from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas import LikeCreate
from app.services import like_service

router = APIRouter(prefix="/likes", tags=["likes"])


@router.post("/toggle")
def toggle(
    data: LikeCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return like_service.toggle_like(db, user, data.target_type, data.target_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
