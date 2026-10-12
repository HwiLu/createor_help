"""站内通知服务。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.enums import NotificationType
from app.models.notification import Notification
from app.models.review import Review


def notify(
    db: Session,
    user_id: int,
    type_: NotificationType,
    title: str,
    content: str,
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
) -> Notification:
    n = Notification(
        user_id=user_id,
        type=type_.value,
        title=title,
        content=content,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(n)
    return n


def build_link(db: Session, n: Notification) -> str | None:
    """根据通知关联实体生成站内跳转链接（用于通知中心点击跳转）。"""
    et = n.related_entity_type
    eid = n.related_entity_id
    if not et or eid is None:
        return None

    if et == "POST":
        return f"/posts/{eid}"

    if et == "COMMENT":
        comment = db.get(Comment, eid)
        if comment is None:
            return None
        return f"/posts/{comment.post_id}#comment-{eid}"

    if et == "REVIEW":
        review = db.get(Review, eid)
        if review is None:
            return None
        apply_comment = db.get(Comment, review.apply_comment_id)
        if apply_comment is None:
            return None
        return f"/posts/{apply_comment.post_id}#comment-{apply_comment.id}"

    return None
