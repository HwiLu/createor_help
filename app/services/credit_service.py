"""信用分服务：完成互关加分、失信扣分（惰性检查）、补做回补。"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import utcnow
from app.models.comment import Comment
from app.models.credit_log import CreditLog, CREDIT_APPLY_EVIDENCE, CREDIT_DEFAULT, CREDIT_MUTUAL_COMPLETE
from app.models.enums import CommentStatus, CommentType, NotificationType
from app.models.post import Post
from app.models.user import User
from app.services.notification_service import notify

DEFAULT_DEADLINE_DAYS = 7


def apply_credit(
    db: Session,
    user_id: int,
    change: int,
    reason: str,
    entity_type: str,
    entity_id: int,
    title: str,
    content: str,
) -> int | None:
    """幂等加减分：同 (user, entity, reason) 只执行一次。返回实际变更值，未变更返回 None。"""
    existing = (
        db.query(CreditLog)
        .filter(
            CreditLog.user_id == user_id,
            CreditLog.reason == reason,
            CreditLog.entity_type == entity_type,
            CreditLog.entity_id == entity_id,
        )
        .first()
    )
    if existing is not None:
        return None

    user = db.get(User, user_id)
    if user is None:
        return None
    user.credit_score += change
    db.add(
        CreditLog(
            user_id=user_id,
            change=change,
            reason=reason,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    )
    notify(db, user_id, NotificationType.CREDIT, title, content, entity_type, entity_id)
    return change


def apply_evidence_credit(db: Session, applicant_id: int, apply_comment_id: int) -> int:
    """申请者提交关注证据后立即 +10（无需等待对方回关）。"""
    return apply_credit(
        db,
        applicant_id,
        10,
        CREDIT_APPLY_EVIDENCE,
        "COMMENT",
        apply_comment_id,
        "信用分已更新",
        "提交关注证据，信用分 +10",
    )


def complete_mutual(db: Session, post: Post, apply_comment_id: int) -> int:
    """业务完成（发帖人回关）：发帖人 +10；发帖人若曾失信则额外 +10（合计 +20）。返回发帖人本次加分。"""
    poster_id = post.user_id

    defaulted = (
        db.query(CreditLog)
        .filter(
            CreditLog.user_id == poster_id,
            CreditLog.reason == CREDIT_DEFAULT,
            CreditLog.entity_type == "COMMENT",
            CreditLog.entity_id == apply_comment_id,
        )
        .first()
    )
    poster_gain = 20 if defaulted is not None else 10

    apply_credit(
        db,
        poster_id,
        poster_gain,
        CREDIT_MUTUAL_COMPLETE,
        "COMMENT",
        apply_comment_id,
        "信用分已更新",
        f"完成互关业务，信用分 +{poster_gain}",
    )
    return poster_gain


def check_defaulters(db: Session, poster_id: int) -> int:
    """惰性检查：扫描发帖人超期未回关的申请并扣分。返回本次扣分次数。"""
    cutoff = utcnow() - timedelta(days=DEFAULT_DEADLINE_DAYS)
    post_ids = [pid for (pid,) in db.query(Post.id).filter(Post.user_id == poster_id).all()]
    if not post_ids:
        return 0

    applies = (
        db.query(Comment)
        .filter(
            Comment.post_id.in_(post_ids),
            Comment.comment_type == CommentType.APPLY.value,
            Comment.status == CommentStatus.ACTIVE.value,
            Comment.created_at < cutoff,
        )
        .all()
    )

    penalized = 0
    for apply in applies:
        has_follow_back = (
            db.query(Comment)
            .filter(
                Comment.parent_id == apply.id,
                Comment.comment_type == CommentType.FOLLOW_BACK.value,
            )
            .first()
        )
        if has_follow_back is not None:
            continue
        changed = apply_credit(
            db,
            poster_id,
            -10,
            CREDIT_DEFAULT,
            "COMMENT",
            apply.id,
            "信用分扣减",
            "互关申请超一周未回关，信用分 -10",
        )
        if changed is not None:
            penalized += 1
    return penalized
