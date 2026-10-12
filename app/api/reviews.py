from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas import ReviewCreate
from app.services import review_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("")
def create_review(
    data: ReviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    review = review_service.create_review(
        db,
        user,
        data.reviewee_id,
        data.apply_comment_id,
        data.rating,
        data.content,
    )
    return {
        "id": review.id,
        "rating": review.rating,
        "content": review.content,
        "reviewee_id": review.reviewee_id,
        "created_at": review.created_at,
    }
