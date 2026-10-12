"""后台反馈处理、邮件重试与系统设置接口。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.models.email_delivery_log import EmailDeliveryLog
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.schemas import FeedbackStatusUpdate, SystemSettingUpdate
from app.services import email_service, feedback_service

router = APIRouter(prefix="/admin", tags=["admin-feedback"])

# 允许在后台读写的非敏感配置项（SMTP 密码等敏感项永远不在其中）
SETTING_KEYS = {"feedback_recipient_email", "email_notifications_enabled", "email_subject_prefix"}


def _feedback_dict(f) -> dict:
    return {
        "id": f.id,
        "user_id": f.user_id,
        "user_nickname": f.user.nickname if f.user else "匿名用户",
        "category_id": f.category_id,
        "category_name": f.category.name if f.category else None,
        "category_code": f.category.code if f.category else None,
        "title": f.title,
        "content": f.content,
        "related_url": f.related_url,
        "contact_info": f.contact_info,
        "extra_data": f.extra_data,
        "status": f.status,
        "admin_note": f.admin_note,
        "handled_by": f.handled_by,
        "handled_at": f.handled_at,
        "created_at": f.created_at,
    }


@router.get("/feedback")
def list_feedback(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    items, total = feedback_service.list_feedbacks_admin(db, status_filter, page, page_size)
    return {"items": [_feedback_dict(f) for f in items], "total": total, "page": page, "page_size": page_size}


@router.post("/feedback/{feedback_id}/status")
def update_feedback_status(
    feedback_id: int,
    payload: FeedbackStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    feedback = feedback_service.update_feedback_status(db, admin, feedback_id, payload.status, payload.admin_note)
    return {"id": feedback.id, "status": feedback.status}


def _log_dict(l) -> dict:
    return {
        "id": l.id,
        "feedback_id": l.feedback_id,
        "recipient_email": l.recipient_email,
        "subject": l.subject,
        "status": l.status,
        "attempt_count": l.attempt_count,
        "last_error": l.last_error,
        "sent_at": l.sent_at,
        "created_at": l.created_at,
    }


@router.get("/email-logs")
def list_email_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    q = db.query(EmailDeliveryLog).order_by(EmailDeliveryLog.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_log_dict(l) for l in items], "total": total, "page": page, "page_size": page_size}


@router.post("/email-logs/{log_id}/retry")
def retry_email(
    log_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        log = email_service.retry_feedback_email(db, log_id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"id": log.id, "status": log.status, "attempt_count": log.attempt_count, "last_error": log.last_error}


@router.get("/settings")
def get_settings(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    rows = db.query(SystemSetting).filter(SystemSetting.key.in_(SETTING_KEYS)).all()
    return {"items": [{"key": s.key, "value": s.value, "description": s.description} for s in rows]}


@router.post("/settings")
def upsert_setting(
    payload: SystemSettingUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if payload.key not in SETTING_KEYS:
        raise HTTPException(status_code=400, detail="不允许修改该配置项")
    email_service.set_setting(db, payload.key, payload.value, payload.description)
    return {"key": payload.key, "value": payload.value}
