"""意见反馈业务：反馈写入、extra_data 校验、状态流转、轻量限流。"""
from __future__ import annotations

import time
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import utcnow
from app.models.enums import FEEDBACK_STATE_TRANSITIONS, FeedbackStatus
from app.models.feedback import Feedback, FeedbackCategory
from app.models.user import User
from app.services.audit_service import write_audit

# 「新活动提交」分类编码及其扩展字段（方式 A）
NEW_ACTIVITY_CODE = "NEW_ACTIVITY"
NEW_ACTIVITY_FIELDS = {
    "activity_name": "活动名称",
    "platform": "活动平台",
    "activity_desc": "活动介绍",
    "official_url": "官方链接",
    "group_entry": "群入口线索",
    "deadline": "截止时间",
    "recommend_reason": "推荐理由",
}
# 必填字段（其余可选）
NEW_ACTIVITY_REQUIRED = {"activity_name", "activity_desc", "official_url"}

# 轻量限流：进程内存记录（key -> 最近提交时间戳）
_rate_tracker: dict[str, float] = {}


def check_rate_limit(key: str, limit_seconds: Optional[int] = None) -> None:
    limit_seconds = limit_seconds or settings.FEEDBACK_RATE_LIMIT_SECONDS
    if limit_seconds <= 0:
        return
    now = time.time()
    last = _rate_tracker.get(key)
    if last and (now - last) < limit_seconds:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="提交过于频繁，请稍后再试")
    _rate_tracker[key] = now


def get_active_categories(db: Session) -> list[FeedbackCategory]:
    # 「新活动提交」已迁移到薅羊毛活动页右上角，此处不再作为反馈分类展示
    return (
        db.query(FeedbackCategory)
        .filter(FeedbackCategory.is_active.is_(True), FeedbackCategory.code != NEW_ACTIVITY_CODE)
        .order_by(FeedbackCategory.sort_order)
        .all()
    )


def _validate_extra_data(category: FeedbackCategory, extra_data: Optional[dict]) -> Optional[dict]:
    if category.code != NEW_ACTIVITY_CODE:
        return None
    if not isinstance(extra_data, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新活动提交需要填写活动信息")
    normalized: dict[str, str] = {}
    for key in NEW_ACTIVITY_FIELDS:
        raw = extra_data.get(key)
        if raw is None:
            continue
        if not isinstance(raw, str):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"字段「{NEW_ACTIVITY_FIELDS[key]}」格式错误")
        value = raw.strip()
        if value:
            normalized[key] = value[:500]
    for key in NEW_ACTIVITY_REQUIRED:
        if not normalized.get(key):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"请填写「{NEW_ACTIVITY_FIELDS[key]}」")
    return normalized


def create_feedback(
    db: Session,
    user: Optional[User],
    category_id: int,
    title: str,
    content: str,
    related_url: Optional[str] = None,
    contact_info: Optional[str] = None,
    extra_data: Optional[dict] = None,
) -> Feedback:
    category = db.get(FeedbackCategory, category_id)
    if category is None or not category.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="反馈分类不存在或已停用")

    normalized_extra = _validate_extra_data(category, extra_data)

    feedback = Feedback(
        user_id=user.id if user else None,
        category_id=category.id,
        title=title.strip(),
        content=content.strip(),
        related_url=related_url or None,
        contact_info=contact_info or None,
        extra_data=normalized_extra,
        status=FeedbackStatus.PENDING.value,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def list_feedbacks_admin(
    db: Session,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Feedback], int]:
    q = db.query(Feedback)
    if status_filter:
        q = q.filter(Feedback.status == status_filter.upper())
    total = q.count()
    items = q.order_by(Feedback.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def update_feedback_status(
    db: Session,
    admin: User,
    feedback_id: int,
    new_status: str,
    admin_note: Optional[str] = None,
) -> Feedback:
    feedback = db.get(Feedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="反馈不存在")
    try:
        target = FeedbackStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的反馈状态")
    try:
        current = FeedbackStatus(feedback.status)
    except ValueError:
        current = FeedbackStatus.PENDING

    allowed = FEEDBACK_STATE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的反馈状态流转")

    old_status = feedback.status
    feedback.status = target.value
    if admin_note is not None:
        feedback.admin_note = admin_note
    feedback.handled_by = admin.id
    feedback.handled_at = utcnow()
    write_audit(
        db, admin.id, "update_status", "feedback", feedback.id,
        before={"status": old_status}, after={"status": target.value},
    )
    db.commit()
    db.refresh(feedback)
    return feedback


def get_feedback(db: Session, feedback_id: int) -> Optional[Feedback]:
    return db.get(Feedback, feedback_id)
