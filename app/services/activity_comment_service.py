"""活动评论/回复/举报业务：公开查询与后台审核处理。"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import utcnow
from app.models.activity import Activity
from app.models.activity_comment import ActivityComment, ActivityReport
from app.models.enums import ActivityCommentStatus, ActivityReportStatus, ActivityStatus
from app.models.user import User
from app.services.audit_service import write_audit


def _get_public_activity_or_404(db: Session, activity_id: int) -> Activity:
    activity = db.get(Activity, activity_id)
    if activity is None or activity.status != ActivityStatus.PUBLISHED.value or activity.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在或未发布")
    return activity


def _serialize_comment(c: ActivityComment) -> dict:
    return {
        "id": c.id,
        "activity_id": c.activity_id,
        "parent_id": c.parent_id,
        "reply_to_user_id": c.reply_to_user_id,
        "content": c.content,
        "created_at": c.created_at,
        "author": {
            "id": c.author.id if c.author else c.user_id,
            "nickname": c.author.nickname if c.author else "用户已注销",
            "avatar_url": c.author.avatar_url if c.author else None,
        },
        "reply_to_nickname": c.reply_to_user.nickname if c.reply_to_user else None,
    }


def list_public_comments(db: Session, activity_id: int) -> tuple[list[ActivityComment], dict[int, list[ActivityComment]]]:
    """返回已审核（ACTIVE 且未删除）的一级评论与其一层回复。

    回复的 ``parent_id`` 指向一级评论；仅一层，不递归。
    """
    top_level = (
        db.query(ActivityComment)
        .filter(
            ActivityComment.activity_id == activity_id,
            ActivityComment.parent_id.is_(None),
            ActivityComment.status == ActivityCommentStatus.ACTIVE.value,
            ActivityComment.deleted_at.is_(None),
        )
        .order_by(ActivityComment.created_at.asc())
        .all()
    )
    top_ids = {c.id for c in top_level}
    replies_map: dict[int, list[ActivityComment]] = {}
    if top_ids:
        replies = (
            db.query(ActivityComment)
            .filter(
                ActivityComment.activity_id == activity_id,
                ActivityComment.parent_id.in_(top_ids),
                ActivityComment.status == ActivityCommentStatus.ACTIVE.value,
                ActivityComment.deleted_at.is_(None),
            )
            .order_by(ActivityComment.created_at.asc())
            .all()
        )
        for r in replies:
            replies_map.setdefault(r.parent_id, []).append(r)
    return top_level, replies_map


def create_comment(
    db: Session,
    activity_id: int,
    user: User,
    content: str,
    parent_id: Optional[int] = None,
    reply_to_user_id: Optional[int] = None,
) -> ActivityComment:
    _get_public_activity_or_404(db, activity_id)

    if parent_id is not None:
        parent = db.get(ActivityComment, parent_id)
        if parent is None or parent.activity_id != activity_id or parent.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="被回复的评论不存在")
        if parent.parent_id is not None:
            # 仅允许一层回复：不允许对回复再回复
            parent_id = parent.parent_id
        if reply_to_user_id is None:
            reply_to_user_id = parent.user_id

    comment = ActivityComment(
        activity_id=activity_id,
        user_id=user.id,
        parent_id=parent_id,
        reply_to_user_id=reply_to_user_id,
        content=content.strip(),
        status=ActivityCommentStatus.ACTIVE.value,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def create_report(
    db: Session,
    reporter: User,
    target_type: str,
    target_id: int,
    reason: str,
    description: Optional[str] = None,
) -> ActivityReport:
    activity_id: Optional[int] = None
    comment_id: Optional[int] = None
    if target_type == "ACTIVITY":
        activity = _get_public_activity_or_404(db, target_id)
        activity_id = activity.id
    else:  # COMMENT
        comment = db.get(ActivityComment, target_id)
        if comment is None or comment.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="被举报的评论不存在")
        activity_id = comment.activity_id
        comment_id = comment.id

    # 同一用户对同一目标去重（避免重复刷举报）
    existing = (
        db.query(ActivityReport)
        .filter(
            ActivityReport.reporter_user_id == reporter.id,
            ActivityReport.activity_id == activity_id,
            ActivityReport.comment_id == comment_id,
            ActivityReport.status == ActivityReportStatus.PENDING.value,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="你已举报过该内容，请等待处理")

    report = ActivityReport(
        activity_id=activity_id,
        comment_id=comment_id,
        reporter_user_id=reporter.id,
        reason=reason.strip(),
        description=description,
        status=ActivityReportStatus.PENDING.value,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# ---------------------------------------------------------------------------
# 后台审核
# ---------------------------------------------------------------------------


def list_comments_admin(
    db: Session,
    activity_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[ActivityComment], int]:
    q = db.query(ActivityComment).filter(ActivityComment.deleted_at.is_(None))
    if activity_id:
        q = q.filter(ActivityComment.activity_id == activity_id)
    if status_filter:
        q = q.filter(ActivityComment.status == status_filter.upper())
    total = q.count()
    items = q.order_by(ActivityComment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def moderate_comment(db: Session, admin: User, comment_id: int, new_status: str) -> ActivityComment:
    comment = db.get(ActivityComment, comment_id)
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
    try:
        enum_status = ActivityCommentStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的评论状态")
    old_status = comment.status
    comment.status = enum_status.value
    if enum_status == ActivityCommentStatus.DELETED:
        comment.deleted_at = utcnow()
    write_audit(
        db, admin.id, "moderate", "activity_comment", comment.id,
        before={"status": old_status}, after={"status": enum_status.value},
    )
    db.commit()
    db.refresh(comment)
    return comment


def list_reports_admin(
    db: Session,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[ActivityReport], int]:
    q = db.query(ActivityReport)
    if status_filter:
        q = q.filter(ActivityReport.status == status_filter.upper())
    total = q.count()
    items = q.order_by(ActivityReport.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def resolve_report(db: Session, admin: User, report_id: int, new_status: str, resolution: str) -> ActivityReport:
    report = db.get(ActivityReport, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="举报不存在")
    try:
        enum_status = ActivityReportStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的举报处理状态")
    old_status = report.status
    report.status = enum_status.value
    report.resolution = resolution
    report.handled_by = admin.id
    write_audit(
        db, admin.id, "resolve", "activity_report", report.id,
        before={"status": old_status}, after={"status": enum_status.value},
    )
    db.commit()
    db.refresh(report)
    return report
