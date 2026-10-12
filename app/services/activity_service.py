"""薅羊毛活动核心业务：公开查询、展示态计算、可配置字典管理。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import utcnow
from app.models.activity import Activity, ActivityEntry, ActivityPlatform, ActivityType
from app.models.activity_comment import ActivityComment
from app.models.enums import (
    ActivityCommentStatus,
    ActivityDisplayStatus,
    ActivityEntryType,
    ActivityStatus,
)
from app.models.feedback import FeedbackCategory

# 平台/类型/反馈分类的默认字典（幂等初始化用，与迁移种子保持一致）
DEFAULT_PLATFORMS = [
    ("拼多多", "PDD"),
    ("支付宝", "ALIPAY"),
    ("招商银行", "CMB"),
    ("京东", "JD"),
    ("淘宝/天猫", "TAOBAO"),
    ("抖音", "DOUYIN"),
    ("微信", "WECHAT"),
    ("其他平台", "OTHER"),
]
DEFAULT_TYPES = [
    ("砍价助力", "BARGAIN"),
    ("邀请好友", "INVITE"),
    ("集卡活动", "CARD_COLLECTION"),
    ("组队活动", "TEAM"),
    ("抽奖活动", "LOTTERY"),
    ("限时福利", "LIMITED_OFFER"),
    ("其他活动", "OTHER"),
]
DEFAULT_FEEDBACK_CATEGORIES = [
    ("功能意见", "FEATURE"),
    ("页面体验问题", "UX"),
    ("Bug / 错误反馈", "BUG"),
    ("内容纠错或失效活动", "CORRECTION"),
    ("其他建议", "OTHER"),
]


def compute_display_status(activity: Activity, now: Optional[datetime] = None) -> Optional[ActivityDisplayStatus]:
    """根据真实配置与时间规则计算活动展示态。

    草稿/下架/已软删除不进入公开展示，返回 None。
    """
    if activity.status != ActivityStatus.PUBLISHED.value or activity.deleted_at is not None:
        return None
    now = now or utcnow()
    start = activity.start_at
    end = activity.end_at
    if start is not None and now < start:
        return ActivityDisplayStatus.UPCOMING
    if end is not None and now > end:
        return ActivityDisplayStatus.ENDED
    return ActivityDisplayStatus.ONGOING


def ensure_activity_dictionaries(db: Session) -> None:
    """幂等初始化平台/类型/反馈分类字典（用于非迁移建表场景兜底）。"""
    for idx, (name, code) in enumerate(DEFAULT_PLATFORMS, start=1):
        if not db.query(ActivityPlatform.id).filter(ActivityPlatform.code == code).first():
            db.add(ActivityPlatform(name=name, code=code, sort_order=idx, is_active=True))
    for idx, (name, code) in enumerate(DEFAULT_TYPES, start=1):
        if not db.query(ActivityType.id).filter(ActivityType.code == code).first():
            db.add(ActivityType(name=name, code=code, sort_order=idx, is_active=True))
    for idx, (name, code) in enumerate(DEFAULT_FEEDBACK_CATEGORIES, start=1):
        if not db.query(FeedbackCategory.id).filter(FeedbackCategory.code == code).first():
            db.add(FeedbackCategory(name=name, code=code, sort_order=idx, is_active=True))
    db.commit()


def get_active_platforms(db: Session) -> list[ActivityPlatform]:
    return db.query(ActivityPlatform).filter(ActivityPlatform.is_active.is_(True)).order_by(ActivityPlatform.sort_order).all()


def get_active_types(db: Session) -> list[ActivityType]:
    return db.query(ActivityType).filter(ActivityType.is_active.is_(True)).order_by(ActivityType.sort_order).all()


def get_all_platforms(db: Session) -> list[ActivityPlatform]:
    return db.query(ActivityPlatform).order_by(ActivityPlatform.sort_order).all()


def get_all_types(db: Session) -> list[ActivityType]:
    return db.query(ActivityType).order_by(ActivityType.sort_order).all()


def list_public_activities(
    db: Session,
    platform_id: Optional[int] = None,
    type_id: Optional[int] = None,
    display: Optional[str] = None,
    keyword: Optional[str] = None,
    sort: str = "latest",
    page: int = 1,
    page_size: int = 12,
) -> tuple[list[Activity], int]:
    """公开活动列表：只返回已发布且未软删除的活动。"""
    q = db.query(Activity).filter(
        Activity.status == ActivityStatus.PUBLISHED.value,
        Activity.deleted_at.is_(None),
    )
    if platform_id:
        q = q.filter(Activity.platform_id == platform_id)
    if type_id:
        q = q.filter(Activity.activity_type_id == type_id)

    if display:
        now = utcnow()
        if display == ActivityDisplayStatus.ONGOING.value:
            q = q.filter(
                or_(Activity.start_at.is_(None), Activity.start_at <= now),
                or_(Activity.end_at.is_(None), Activity.end_at >= now),
            )
        elif display == ActivityDisplayStatus.UPCOMING.value:
            q = q.filter(Activity.start_at.isnot(None), Activity.start_at > now)
        elif display == ActivityDisplayStatus.ENDED.value:
            q = q.filter(Activity.end_at.isnot(None), Activity.end_at < now)

    if keyword:
        like = f"%{keyword.strip()}%"
        q = q.filter(or_(Activity.title.ilike(like), Activity.summary.ilike(like)))

    if sort == "deadline":
        # 最近截止优先：有截止时间的排前面
        q = q.order_by(Activity.end_at.is_(None), Activity.end_at.asc(), Activity.display_sort.asc(), Activity.created_at.desc())
    else:  # latest
        q = q.order_by(Activity.display_sort.asc(), Activity.created_at.desc())

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_public_activity(db: Session, activity_id: int) -> Optional[Activity]:
    return (
        db.query(Activity)
        .filter(
            Activity.id == activity_id,
            Activity.status == ActivityStatus.PUBLISHED.value,
            Activity.deleted_at.is_(None),
        )
        .first()
    )


def get_activity_by_id(db: Session, activity_id: int, include_deleted: bool = False) -> Optional[Activity]:
    q = db.query(Activity).filter(Activity.id == activity_id)
    if not include_deleted:
        q = q.filter(Activity.deleted_at.is_(None))
    return q.first()


def get_featured_activities(db: Session, limit: Optional[int] = None) -> list[Activity]:
    """首页精选：仅已发布且精选的活动，按 featured_sort 升序。"""
    limit = limit or settings.HOME_FEATURED_ACTIVITIES
    return (
        db.query(Activity)
        .filter(
            Activity.status == ActivityStatus.PUBLISHED.value,
            Activity.deleted_at.is_(None),
            Activity.is_featured.is_(True),
        )
        .order_by(Activity.featured_sort.asc(), Activity.display_sort.asc(), Activity.created_at.desc())
        .limit(limit)
        .all()
    )


def get_entries(db: Session, activity_id: int) -> list[ActivityEntry]:
    return (
        db.query(ActivityEntry)
        .filter(ActivityEntry.activity_id == activity_id)
        .order_by(ActivityEntry.sort_order.asc(), ActivityEntry.id.asc())
        .all()
    )


def comment_counts(db: Session, activity_ids: list[int]) -> dict[int, int]:
    """按活动批量统计真实评论数（仅计入已通过审核、未删除的评论）。"""
    if not activity_ids:
        return {}
    rows = (
        db.query(ActivityComment.activity_id, func.count(ActivityComment.id))
        .filter(
            ActivityComment.activity_id.in_(activity_ids),
            ActivityComment.status == ActivityCommentStatus.ACTIVE.value,
            ActivityComment.deleted_at.is_(None),
        )
        .group_by(ActivityComment.activity_id)
        .all()
    )
    return {activity_id: count for activity_id, count in rows}


def entry_is_available(entry: ActivityEntry, now: Optional[datetime] = None) -> tuple[bool, str]:
    """判断参与入口当前是否可用，返回 (是否可用, 不可用原因)。

    不可用原因如实返回，供前端展示真实状态，不做误导。
    """
    now = now or utcnow()
    if not entry.is_enabled:
        return False, "入口已停用"
    if entry.expires_at is not None and now > entry.expires_at:
        return False, "入口已过期"
    if entry.entry_type == "QR_IMAGE" and not entry.qr_image_key:
        return False, "二维码未配置"
    if entry.entry_type == "LINK" and not entry.target_url:
        return False, "链接未配置"
    return True, ""


def _get_or_404(db: Session, activity_id: int) -> Activity:
    activity = get_activity_by_id(db, activity_id)
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="活动不存在或已删除")
    return activity


# ---------------------------------------------------------------------------
# 后台管理写操作
# ---------------------------------------------------------------------------


def _validate_times(start_at: Optional[datetime], end_at: Optional[datetime]) -> None:
    if start_at is not None and end_at is not None and end_at < start_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="结束时间不能早于开始时间")


def _require_platform(db: Session, platform_id: int) -> ActivityPlatform:
    platform = db.get(ActivityPlatform, platform_id)
    if platform is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="所选平台不存在")
    return platform


def _require_type(db: Session, type_id: int) -> ActivityType:
    atype = db.get(ActivityType, type_id)
    if atype is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="所选活动类型不存在")
    return atype


def create_activity(db: Session, data: dict, created_by: int) -> Activity:
    _validate_times(data.get("start_at"), data.get("end_at"))
    _require_platform(db, data["platform_id"])
    _require_type(db, data["activity_type_id"])
    status_value = (data.get("status") or ActivityStatus.DRAFT).value
    is_featured = bool(data.get("is_featured", False))
    if status_value != ActivityStatus.PUBLISHED.value:
        is_featured = False
    activity = Activity(
        title=data["title"],
        cover_image_key=data.get("cover_image_key") or "",
        platform_id=data["platform_id"],
        activity_type_id=data["activity_type_id"],
        summary=data["summary"],
        content=data["content"],
        start_at=data.get("start_at"),
        end_at=data.get("end_at"),
        status=status_value,
        is_featured=is_featured,
        featured_sort=data.get("featured_sort", 0),
        display_sort=data.get("display_sort", 0),
        source_url=data.get("source_url"),
        risk_notice=data.get("risk_notice"),
        created_by=created_by,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def submit_activity(db: Session, data: dict, user_id: int) -> Activity:
    """用户提交新活动：进入待审批状态，由管理员审核发布。"""
    _validate_times(None, data.get("end_at"))
    _require_platform(db, data["platform_id"])
    _require_type(db, data["activity_type_id"])
    activity = Activity(
        title=data["title"],
        cover_image_key=data.get("cover_image_key") or "",
        platform_id=data["platform_id"],
        activity_type_id=data["activity_type_id"],
        summary=data["summary"],
        content=data.get("content") or "",
        start_at=None,
        end_at=data.get("end_at"),
        status=ActivityStatus.PENDING.value,
        is_featured=False,
        featured_sort=0,
        display_sort=0,
        source_url=data.get("source_url"),
        risk_notice=None,
        created_by=user_id,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def update_activity(db: Session, activity: Activity, data: dict) -> Activity:
    if "title" in data:
        activity.title = data["title"]
    if "cover_image_key" in data:
        activity.cover_image_key = data["cover_image_key"] or ""
    if "platform_id" in data:
        _require_platform(db, data["platform_id"])
        activity.platform_id = data["platform_id"]
    if "activity_type_id" in data:
        _require_type(db, data["activity_type_id"])
        activity.activity_type_id = data["activity_type_id"]
    if "summary" in data:
        activity.summary = data["summary"]
    if "content" in data:
        activity.content = data["content"]
    if "start_at" in data:
        activity.start_at = data["start_at"]
    if "end_at" in data:
        activity.end_at = data["end_at"]
    if "source_url" in data:
        activity.source_url = data["source_url"]
    if "risk_notice" in data:
        activity.risk_notice = data["risk_notice"]
    if "featured_sort" in data:
        activity.featured_sort = data["featured_sort"]
    if "display_sort" in data:
        activity.display_sort = data["display_sort"]

    _validate_times(activity.start_at, activity.end_at)
    # 精选仅对已发布活动生效
    if activity.status != ActivityStatus.PUBLISHED.value:
        activity.is_featured = False
    db.commit()
    db.refresh(activity)
    return activity


def set_activity_status(db: Session, activity: Activity, new_status: ActivityStatus) -> Activity:
    activity.status = new_status.value
    # 下架/草稿时自动取消精选，避免精选列表出现非发布状态
    if new_status != ActivityStatus.PUBLISHED:
        activity.is_featured = False
    db.commit()
    db.refresh(activity)
    return activity


def set_featured(db: Session, activity: Activity, is_featured: bool, featured_sort: int = 0) -> Activity:
    if is_featured and activity.status != ActivityStatus.PUBLISHED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅已发布活动可设为精选")
    activity.is_featured = is_featured
    if is_featured:
        activity.featured_sort = featured_sort
    db.commit()
    db.refresh(activity)
    return activity


def soft_delete_activity(db: Session, activity: Activity) -> None:
    activity.deleted_at = utcnow()
    activity.is_featured = False
    db.commit()


def create_platform(db: Session, data: dict) -> ActivityPlatform:
    if db.query(ActivityPlatform.id).filter(ActivityPlatform.code == data["code"]).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="平台编码已存在")
    platform = ActivityPlatform(
        name=data["name"], code=data["code"], sort_order=data.get("sort_order", 0), is_active=data.get("is_active", True)
    )
    db.add(platform)
    db.commit()
    db.refresh(platform)
    return platform


def update_platform(db: Session, platform: ActivityPlatform, data: dict) -> ActivityPlatform:
    if "code" in data and data["code"] != platform.code:
        if db.query(ActivityPlatform.id).filter(ActivityPlatform.code == data["code"]).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="平台编码已存在")
        platform.code = data["code"]
    if "name" in data:
        platform.name = data["name"]
    if "sort_order" in data:
        platform.sort_order = data["sort_order"]
    if "is_active" in data:
        platform.is_active = data["is_active"]
    db.commit()
    db.refresh(platform)
    return platform


def delete_platform(db: Session, platform: ActivityPlatform) -> None:
    used = db.query(Activity.id).filter(Activity.platform_id == platform.id, Activity.deleted_at.is_(None)).first()
    if used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该平台下存在活动，无法删除")
    db.delete(platform)
    db.commit()


def create_type(db: Session, data: dict) -> ActivityType:
    if db.query(ActivityType.id).filter(ActivityType.code == data["code"]).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="类型编码已存在")
    atype = ActivityType(
        name=data["name"], code=data["code"], sort_order=data.get("sort_order", 0), is_active=data.get("is_active", True)
    )
    db.add(atype)
    db.commit()
    db.refresh(atype)
    return atype


def update_type(db: Session, atype: ActivityType, data: dict) -> ActivityType:
    if "code" in data and data["code"] != atype.code:
        if db.query(ActivityType.id).filter(ActivityType.code == data["code"]).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="类型编码已存在")
        atype.code = data["code"]
    if "name" in data:
        atype.name = data["name"]
    if "sort_order" in data:
        atype.sort_order = data["sort_order"]
    if "is_active" in data:
        atype.is_active = data["is_active"]
    db.commit()
    db.refresh(atype)
    return atype


def delete_type(db: Session, atype: ActivityType) -> None:
    used = db.query(Activity.id).filter(Activity.activity_type_id == atype.id, Activity.deleted_at.is_(None)).first()
    if used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该类型下存在活动，无法删除")
    db.delete(atype)
    db.commit()


def add_entry(db: Session, activity_id: int, data: dict) -> ActivityEntry:
    entry = ActivityEntry(
        activity_id=activity_id,
        title=data["title"],
        entry_type=(data.get("entry_type") or ActivityEntryType.QR_IMAGE).value,
        qr_image_key=data.get("qr_image_key"),
        target_url=data.get("target_url"),
        description=data.get("description"),
        sort_order=data.get("sort_order", 0),
        is_enabled=data.get("is_enabled", True),
        expires_at=data.get("expires_at"),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def update_entry(db: Session, entry: ActivityEntry, data: dict) -> ActivityEntry:
    if "title" in data:
        entry.title = data["title"]
    if "entry_type" in data:
        entry.entry_type = data["entry_type"].value
    if "qr_image_key" in data:
        entry.qr_image_key = data["qr_image_key"]
    if "target_url" in data:
        entry.target_url = data["target_url"]
    if "description" in data:
        entry.description = data["description"]
    if "sort_order" in data:
        entry.sort_order = data["sort_order"]
    if "is_enabled" in data:
        entry.is_enabled = data["is_enabled"]
    if "expires_at" in data:
        entry.expires_at = data["expires_at"]
    db.commit()
    db.refresh(entry)
    return entry


def delete_entry(db: Session, entry: ActivityEntry) -> None:
    db.delete(entry)
    db.commit()
