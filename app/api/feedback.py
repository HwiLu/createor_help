"""意见反馈公开接口：分类查询与反馈提交。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_optional
from app.db.session import get_db
from app.models.user import User
from app.schemas import FeedbackCreate
from app.services import email_service, feedback_service

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    categories = feedback_service.get_active_categories(db)
    return {"items": [{"id": c.id, "name": c.name, "code": c.code} for c in categories]}


@router.post("")
def submit_feedback(
    payload: FeedbackCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_optional),
):
    rate_key = f"user:{user.id}" if user else f"ip:{request.client.host if request.client else 'unknown'}"
    feedback_service.check_rate_limit(rate_key)

    feedback = feedback_service.create_feedback(
        db,
        user,
        payload.category_id,
        payload.title,
        payload.content,
        related_url=payload.related_url,
        contact_info=payload.contact_info,
        extra_data=payload.extra_data,
    )

    # 邮件通知与反馈写入解耦：发送失败不回滚反馈
    result: dict = {
        "id": feedback.id,
        "status": feedback.status,
        "email_status": None,
        "email_error": None,
    }
    if email_service.email_enabled(db) and email_service.get_recipient_email(db):
        log = email_service.send_feedback_email(db, feedback)
        if log is not None:
            result["email_status"] = log.status
            result["email_error"] = log.last_error
    else:
        result["email_status"] = "DISABLED"
    return result
