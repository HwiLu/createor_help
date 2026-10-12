"""薅羊毛活动公开接口。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import ActivityDisplayStatus
from app.models.user import User
from app.schemas import ActivitySubmit
from app.services import activity_image_service, activity_service, audit_service

router = APIRouter(prefix="/activities", tags=["activities"])


def _iso(dt) -> Optional[str]:
    return dt.isoformat() if dt else None


def _activity_payload(db: Session, activity, with_entries: bool = False) -> dict:
    from app.services import activity_service as svc

    display = svc.compute_display_status(activity)
    payload = {
        "id": activity.id,
        "title": activity.title,
        "cover_image_key": activity.cover_image_key,
        "summary": activity.summary,
        "platform_id": activity.platform_id,
        "platform_name": activity.platform.name if activity.platform else "",
        "activity_type_id": activity.activity_type_id,
        "activity_type_name": activity.activity_type.name if activity.activity_type else "",
        "start_at": _iso(activity.start_at),
        "end_at": _iso(activity.end_at),
        "display_status": display.value if display else None,
        "source_url": activity.source_url,
        "comment_count": svc.comment_counts(db, [activity.id]).get(activity.id, 0),
    }
    if with_entries:
        payload["content"] = activity.content
        payload["risk_notice"] = activity.risk_notice
        payload["entries"] = [
            {
                "id": e.id,
                "title": e.title,
                "entry_type": e.entry_type,
                "qr_image_key": e.qr_image_key,
                "target_url": e.target_url,
                "description": e.description,
                "is_enabled": e.is_enabled,
                "available": svc.entry_is_available(e)[0],
                "unavailable_reason": svc.entry_is_available(e)[1],
            }
            for e in svc.get_entries(db, activity.id)
        ]
    return payload


@router.get("")
def list_activities(
    platform_id: Optional[int] = None,
    type_id: Optional[int] = None,
    display: Optional[str] = None,
    keyword: Optional[str] = None,
    sort: str = Query("latest", pattern="^(latest|deadline)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    items, total = activity_service.list_public_activities(
        db, platform_id=platform_id, type_id=type_id, display=display,
        keyword=keyword, sort=sort, page=page, page_size=page_size,
    )
    return {
        "items": [_activity_payload(db, a) for a in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/upload-image")
async def upload_activity_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """用户提交活动时上传封面图片，返回存储 key。"""
    data = await file.read()
    key = activity_image_service.save_activity_image(data, file.filename)
    return {"key": key, "url": f"/api/v1/activity-images/{key}"}


@router.post("")
def submit_activity(
    payload: ActivitySubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """用户提交新活动，进入待审批状态，由管理员审核发布。"""
    activity = activity_service.submit_activity(db, payload.model_dump(), user_id=user.id)
    audit_service.write_audit(db, user.id, "ACTIVITY_SUBMIT", "ACTIVITY", activity.id, after={"title": activity.title, "status": activity.status})
    db.commit()
    return {"id": activity.id, "status": activity.status, "message": "已提交，等待管理员审核"}


@router.get("/{activity_id}")
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = activity_service.get_public_activity(db, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在或未发布")
    return _activity_payload(db, activity, with_entries=True)
