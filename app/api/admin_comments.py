"""后台评论审核与举报处理接口。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas import ActivityCommentModerate, ActivityReportResolve
from app.services import activity_comment_service

router = APIRouter(prefix="/admin", tags=["admin-activity-moderation"])


def _comment_admin_dict(c) -> dict:
    return {
        "id": c.id,
        "activity_id": c.activity_id,
        "content": c.content,
        "parent_id": c.parent_id,
        "status": c.status,
        "created_at": c.created_at,
        "author_id": c.user_id,
        "author_nickname": c.author.nickname if c.author else "用户已注销",
    }


@router.get("/activity-comments")
def list_comments(
    activity_id: Optional[int] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    items, total = activity_comment_service.list_comments_admin(db, activity_id, status_filter, page, page_size)
    return {"items": [_comment_admin_dict(c) for c in items], "total": total, "page": page, "page_size": page_size}


@router.post("/activity-comments/{comment_id}/moderate")
def moderate_comment(
    comment_id: int,
    payload: ActivityCommentModerate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    comment = activity_comment_service.moderate_comment(db, admin, comment_id, payload.status)
    return {"id": comment.id, "status": comment.status}


def _report_admin_dict(r) -> dict:
    target = None
    if r.comment is not None:
        target = {"type": "COMMENT", "id": r.comment.id, "content": r.comment.content}
    else:
        target = {"type": "ACTIVITY", "id": r.activity_id, "title": r.activity.title if r.activity else None}
    return {
        "id": r.id,
        "target": target,
        "reason": r.reason,
        "description": r.description,
        "status": r.status,
        "reporter_nickname": r.reporter.nickname if r.reporter else "用户已注销",
        "handled_by": r.handled_by,
        "resolution": r.resolution,
        "created_at": r.created_at,
    }


@router.get("/activity-reports")
def list_reports(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    items, total = activity_comment_service.list_reports_admin(db, status_filter, page, page_size)
    return {"items": [_report_admin_dict(r) for r in items], "total": total, "page": page, "page_size": page_size}


@router.post("/activity-reports/{report_id}/resolve")
def resolve_report(
    report_id: int,
    payload: ActivityReportResolve,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    report = activity_comment_service.resolve_report(db, admin, report_id, payload.status, payload.resolution)
    return {"id": report.id, "status": report.status}
