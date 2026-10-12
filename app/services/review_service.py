"""用户评价服务：互助业务完成后，双方互评。"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.enums import CommentType, NotificationType
from app.models.review import Review
from app.models.user import User
from app.services.notification_service import notify


def _is_completed(db: Session, apply: Comment) -> bool:
    """业务是否完成：申请是否已有回关回复。"""
    follow_back = (
        db.query(Comment)
        .filter(
            Comment.parent_id == apply.id,
            Comment.comment_type == CommentType.FOLLOW_BACK.value,
        )
        .first()
    )
    return follow_back is not None


def create_review(
    db: Session,
    reviewer: User,
    reviewee_id: int,
    apply_comment_id: int,
    rating: int,
    content: str,
) -> Review:
    apply = db.get(Comment, apply_comment_id)
    if apply is None or apply.comment_type != CommentType.APPLY.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="互关申请不存在")

    if not _is_completed(db, apply):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="业务尚未完成，暂不能评价")

    # 评价双方只能是该互关业务的双方（发帖人与申请者）
    from app.models.post import Post

    post = db.get(Post, apply.post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")
    poster_id = post.user_id
    applicant_id = apply.user_id

    if reviewer.id not in (poster_id, applicant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权评价该业务")
    if reviewee_id not in (poster_id, applicant_id) or reviewee_id == reviewer.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="评价对象无效")

    if rating < 1 or rating > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="评分需在 1~5 之间")

    existing = (
        db.query(Review)
        .filter(Review.reviewer_id == reviewer.id, Review.apply_comment_id == apply_comment_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="你已评价过该业务")

    review = Review(
        reviewer_id=reviewer.id,
        reviewee_id=reviewee_id,
        apply_comment_id=apply_comment_id,
        rating=rating,
        content=(content or "").strip(),
    )
    db.add(review)
    notify(
        db,
        reviewee_id,
        NotificationType.EVALUATION,
        "收到新的评价",
        f"{reviewer.nickname} 给了你 {rating} 星评价" + (f"：{review.content}" if review.content else ""),
        "REVIEW",
        review.id,
    )
    db.commit()
    db.refresh(review)
    return review
