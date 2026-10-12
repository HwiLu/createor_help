"""点赞服务：帖子、评论、互关节点通用点赞/取消点赞。"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.like import Like, LIKE_TARGET_COMMENT, LIKE_TARGET_POST
from app.models.user import User

VALID_TARGETS = {LIKE_TARGET_POST, LIKE_TARGET_COMMENT}


def toggle_like(db: Session, user: User, target_type: str, target_id: int) -> dict:
    target_type = (target_type or "").upper()
    if target_type not in VALID_TARGETS:
        raise ValueError("无效的点赞目标类型")

    like = (
        db.query(Like)
        .filter(Like.user_id == user.id, Like.target_type == target_type, Like.target_id == target_id)
        .first()
    )
    if like is not None:
        db.delete(like)
        db.commit()
        liked = False
    else:
        db.add(Like(user_id=user.id, target_type=target_type, target_id=target_id))
        db.commit()
        liked = True

    count = db.query(Like).filter(Like.target_type == target_type, Like.target_id == target_id).count()
    return {"liked": liked, "count": count}


def like_counts(db: Session, target_type: str, target_ids: list[int]) -> dict[int, int]:
    """批量返回每个目标的点赞数。"""
    if not target_ids:
        return {}
    rows = (
        db.query(Like.target_id)
        .filter(Like.target_type == target_type, Like.target_id.in_(target_ids))
        .all()
    )
    result: dict[int, int] = defaultdict(int)
    for (tid,) in rows:
        result[tid] += 1
    return dict(result)


def liked_ids(db: Session, user_id: int | None, target_type: str, target_ids: list[int]) -> set[int]:
    """当前用户已点赞的目标 id 集合。"""
    if user_id is None or not target_ids:
        return set()
    rows = (
        db.query(Like.target_id)
        .filter(Like.user_id == user_id, Like.target_type == target_type, Like.target_id.in_(target_ids))
        .all()
    )
    return {tid for (tid,) in rows}
