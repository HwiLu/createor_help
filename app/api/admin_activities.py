"""后台活动管理接口（平台/类型字典、活动、参与入口）。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.models.activity import ActivityEntry, ActivityPlatform, ActivityType
from app.models.user import User
from app.schemas import (
    ActivityCreate,
    ActivityEntryCreate,
    ActivityEntryUpdate,
    ActivityPlatformCreate,
    ActivityTypeCreate,
    ActivityUpdate,
)
from app.services import activity_service
from app.services.activity_image_service import save_activity_image
from app.services.audit_service import write_audit

router = APIRouter(prefix="/admin", tags=["admin-activities"])


def _a(activity) -> dict:
    ds = activity_service.compute_display_status(activity)
    return {
        "id": activity.id,
        "title": activity.title,
        "cover_image_key": activity.cover_image_key,
        "platform_id": activity.platform_id,
        "platform_name": activity.platform.name if activity.platform else None,
        "activity_type_id": activity.activity_type_id,
        "activity_type_name": activity.activity_type.name if activity.activity_type else None,
        "summary": activity.summary,
        "content": activity.content,
        "start_at": activity.start_at,
        "end_at": activity.end_at,
        "status": activity.status,
        "display_status": ds.value if ds else None,
        "is_featured": activity.is_featured,
        "featured_sort": activity.featured_sort,
        "display_sort": activity.display_sort,
        "source_url": activity.source_url,
        "risk_notice": activity.risk_notice,
        "created_by": activity.created_by,
        "creator_nickname": activity.creator.nickname if activity.creator else None,
        "created_at": activity.created_at,
        "deleted_at": activity.deleted_at,
    }


def _e(entry) -> dict:
    return {
        "id": entry.id,
        "activity_id": entry.activity_id,
        "title": entry.title,
        "entry_type": entry.entry_type,
        "qr_image_key": entry.qr_image_key,
        "target_url": entry.target_url,
        "description": entry.description,
        "sort_order": entry.sort_order,
        "is_enabled": entry.is_enabled,
        "expires_at": entry.expires_at,
    }


@router.post("/upload-image")
async def upload_activity_image(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_admin),
):
    data = await file.read()
    key = save_activity_image(data, file.filename)
    return {"key": key, "url": f"/api/v1/activity-images/{key}"}


# ---------------------------------------------------------------------------
# 平台字典
# ---------------------------------------------------------------------------


@router.get("/platforms")
def list_platforms(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return {
        "items": [
            {"id": p.id, "name": p.name, "code": p.code, "sort_order": p.sort_order, "is_active": p.is_active}
            for p in activity_service.get_all_platforms(db)
        ]
    }


@router.post("/platforms")
def create_platform(
    data: ActivityPlatformCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    platform = activity_service.create_platform(db, data.model_dump())
    write_audit(db, admin.id, "ACTIVITY_PLATFORM_CREATE", "ACTIVITY_PLATFORM", platform.id, after=data.model_dump())
    db.commit()
    return {"id": platform.id, "name": platform.name, "code": platform.code}


@router.put("/platforms/{platform_id}")
def update_platform(
    platform_id: int,
    data: ActivityPlatformCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    platform = db.get(ActivityPlatform, platform_id)
    if not platform:
        return {"error": "平台不存在"}
    before = {"name": platform.name, "code": platform.code}
    platform = activity_service.update_platform(db, platform, data.model_dump(exclude_unset=True))
    write_audit(db, admin.id, "ACTIVITY_PLATFORM_UPDATE", "ACTIVITY_PLATFORM", platform.id, before=before, after=data.model_dump(exclude_unset=True))
    db.commit()
    return {"id": platform.id, "name": platform.name, "code": platform.code}


@router.delete("/platforms/{platform_id}")
def delete_platform(
    platform_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    platform = db.get(ActivityPlatform, platform_id)
    if not platform:
        return {"error": "平台不存在"}
    try:
        activity_service.delete_platform(db, platform)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    write_audit(db, admin.id, "ACTIVITY_PLATFORM_DELETE", "ACTIVITY_PLATFORM", platform_id)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 类型字典
# ---------------------------------------------------------------------------


@router.get("/types")
def list_types(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return {
        "items": [
            {"id": t.id, "name": t.name, "code": t.code, "sort_order": t.sort_order, "is_active": t.is_active}
            for t in activity_service.get_all_types(db)
        ]
    }


@router.post("/types")
def create_type(
    data: ActivityTypeCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    atype = activity_service.create_type(db, data.model_dump())
    write_audit(db, admin.id, "ACTIVITY_TYPE_CREATE", "ACTIVITY_TYPE", atype.id, after=data.model_dump())
    db.commit()
    return {"id": atype.id, "name": atype.name, "code": atype.code}


@router.put("/types/{type_id}")
def update_type(
    type_id: int,
    data: ActivityTypeCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    atype = db.get(ActivityType, type_id)
    if not atype:
        return {"error": "类型不存在"}
    before = {"name": atype.name, "code": atype.code}
    atype = activity_service.update_type(db, atype, data.model_dump(exclude_unset=True))
    write_audit(db, admin.id, "ACTIVITY_TYPE_UPDATE", "ACTIVITY_TYPE", atype.id, before=before, after=data.model_dump(exclude_unset=True))
    db.commit()
    return {"id": atype.id, "name": atype.name, "code": atype.code}


@router.delete("/types/{type_id}")
def delete_type(
    type_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    atype = db.get(ActivityType, type_id)
    if not atype:
        return {"error": "类型不存在"}
    try:
        activity_service.delete_type(db, atype)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    write_audit(db, admin.id, "ACTIVITY_TYPE_DELETE", "ACTIVITY_TYPE", type_id)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 活动 CRUD
# ---------------------------------------------------------------------------


@router.get("/activities")
def list_activities_admin(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(default=None),
    include_deleted: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    q = db.query(activity_service.Activity)
    if not include_deleted:
        q = q.filter(activity_service.Activity.deleted_at.is_(None))
    if status_filter:
        q = q.filter(activity_service.Activity.status == status_filter.upper())
    total = q.count()
    items = q.order_by(activity_service.Activity.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_a(a) for a in items], "total": total, "page": page, "page_size": page_size}


@router.get("/activities/{activity_id}")
def get_activity_admin(
    activity_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    activity = db.get(activity_service.Activity, activity_id)
    if not activity:
        return {"error": "活动不存在"}
    return {"activity": _a(activity), "entries": [_e(e) for e in activity_service.get_entries(db, activity_id)]}


@router.post("/activities")
def create_activity_api(
    data: ActivityCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    activity = activity_service.create_activity(db, data.model_dump(), created_by=admin.id)
    write_audit(db, admin.id, "ACTIVITY_CREATE", "ACTIVITY", activity.id, after=_a(activity))
    db.commit()
    return _a(activity)


@router.put("/activities/{activity_id}")
def update_activity_api(
    activity_id: int,
    data: ActivityUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    activity = activity_service._get_or_404(db, activity_id)
    before = _a(activity)
    activity = activity_service.update_activity(db, activity, data.model_dump(exclude_unset=True))
    write_audit(db, admin.id, "ACTIVITY_UPDATE", "ACTIVITY", activity.id, before=before, after=_a(activity))
    db.commit()
    return _a(activity)


@router.post("/activities/{activity_id}/publish")
def publish_activity(
    activity_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    activity = activity_service._get_or_404(db, activity_id)
    from app.models.enums import ActivityStatus

    activity = activity_service.set_activity_status(db, activity, ActivityStatus.PUBLISHED)
    write_audit(db, admin.id, "ACTIVITY_PUBLISH", "ACTIVITY", activity.id, after={"status": activity.status})
    db.commit()
    return _a(activity)


@router.post("/activities/{activity_id}/offline")
def offline_activity(
    activity_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    activity = activity_service._get_or_404(db, activity_id)
    from app.models.enums import ActivityStatus

    activity = activity_service.set_activity_status(db, activity, ActivityStatus.OFFLINE)
    write_audit(db, admin.id, "ACTIVITY_OFFLINE", "ACTIVITY", activity.id, after={"status": activity.status})
    db.commit()
    return _a(activity)


@router.post("/activities/{activity_id}/reject")
def reject_activity(
    activity_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    activity = activity_service._get_or_404(db, activity_id)
    from app.models.enums import ActivityStatus

    activity = activity_service.set_activity_status(db, activity, ActivityStatus.REJECTED)
    write_audit(db, admin.id, "ACTIVITY_REJECT", "ACTIVITY", activity.id, after={"status": activity.status})
    db.commit()
    return _a(activity)


@router.post("/activities/{activity_id}/featured")
def feature_activity(
    activity_id: int,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    activity = activity_service._get_or_404(db, activity_id)
    is_featured = bool(body.get("is_featured", True))
    featured_sort = int(body.get("featured_sort", 0))
    try:
        activity = activity_service.set_featured(db, activity, is_featured, featured_sort)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    write_audit(db, admin.id, "ACTIVITY_FEATURE", "ACTIVITY", activity.id, after={"is_featured": activity.is_featured, "featured_sort": activity.featured_sort})
    db.commit()
    return _a(activity)


@router.delete("/activities/{activity_id}")
def delete_activity(
    activity_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    activity = activity_service._get_or_404(db, activity_id)
    activity_service.soft_delete_activity(db, activity)
    write_audit(db, admin.id, "ACTIVITY_DELETE", "ACTIVITY", activity.id)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 参与入口
# ---------------------------------------------------------------------------


@router.post("/activities/{activity_id}/entries")
def add_entry_api(
    activity_id: int,
    data: ActivityEntryCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    activity_service._get_or_404(db, activity_id)
    entry = activity_service.add_entry(db, activity_id, data.model_dump())
    write_audit(db, admin.id, "ACTIVITY_ENTRY_CREATE", "ACTIVITY_ENTRY", entry.id, after=_e(entry))
    db.commit()
    return _e(entry)


@router.put("/entries/{entry_id}")
def update_entry_api(
    entry_id: int,
    data: ActivityEntryUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    entry = db.get(ActivityEntry, entry_id)
    if not entry:
        return {"error": "入口不存在"}
    before = _e(entry)
    entry = activity_service.update_entry(db, entry, data.model_dump(exclude_unset=True))
    write_audit(db, admin.id, "ACTIVITY_ENTRY_UPDATE", "ACTIVITY_ENTRY", entry.id, before=before, after=_e(entry))
    db.commit()
    return _e(entry)


@router.delete("/entries/{entry_id}")
def delete_entry_api(
    entry_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    entry = db.get(ActivityEntry, entry_id)
    if not entry:
        return {"error": "入口不存在"}
    activity_service.delete_entry(db, entry)
    write_audit(db, admin.id, "ACTIVITY_ENTRY_DELETE", "ACTIVITY_ENTRY", entry_id)
    db.commit()
    return {"ok": True}
