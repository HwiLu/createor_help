"""活动评论/回复/举报公开接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import ActivityCommentCreate, ActivityReportCreate
from app.services import activity_comment_service
from app.services.activity_service import get_public_activity

router = APIRouter(prefix="/activities", tags=["activity-comments"])


@router.get("/{activity_id}/comments")
def list_comments(activity_id: int, db: Session = Depends(get_db)):
    if get_public_activity(db, activity_id) is None:
        raise HTTPException(status_code=404, detail="活动不存在或未发布")
    top_level, replies_map = activity_comment_service.list_public_comments(db, activity_id)
    return {
        "count": len(top_level) + sum(len(v) for v in replies_map.values()),
        "comments": [
            {
                **activity_comment_service._serialize_comment(c),
                "replies": [activity_comment_service._serialize_comment(r) for r in replies_map.get(c.id, [])],
            }
            for c in top_level
        ],
    }


@router.post("/{activity_id}/comments")
def create_comment(
    activity_id: int,
    payload: ActivityCommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    comment = activity_comment_service.create_comment(
        db,
        activity_id,
        user,
        payload.content,
        parent_id=payload.parent_id,
        reply_to_user_id=payload.reply_to_user_id,
    )
    return {"comment": activity_comment_service._serialize_comment(comment)}


@router.post("/{activity_id}/reports")
def report_activity(
    activity_id: int,
    payload: ActivityReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = activity_comment_service.create_report(
        db, user, "ACTIVITY", activity_id, payload.reason, payload.description
    )
    return {"id": report.id, "status": report.status}


@router.post("/{activity_id}/comments/{comment_id}/reports")
def report_comment(
    activity_id: int,
    comment_id: int,
    payload: ActivityReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    report = activity_comment_service.create_report(
        db, user, "COMMENT", comment_id, payload.reason, payload.description
    )
    return {"id": report.id, "status": report.status}
