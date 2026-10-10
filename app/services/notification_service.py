"""站内通知服务。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enums import NotificationType
from app.models.notification import Notification


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
