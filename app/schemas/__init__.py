"""Pydantic 请求/响应校验模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ActivityEntryType, ActivityStatus, EvidenceType, MutualType, Platform, ReportTargetType


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=30)
    avatar_url: Optional[str] = Field(default=None, max_length=512)
    bio: Optional[str] = Field(default=None, max_length=200)


class AccountCreate(BaseModel):
    platform: Platform
    account_name: str = Field(min_length=1, max_length=64)
    profile_url: Optional[str] = Field(default=None, max_length=512)
    bio: Optional[str] = Field(default=None, max_length=200)
    category: Optional[str] = Field(default=None, max_length=64)
    follower_range: Optional[str] = Field(default=None, max_length=64)


class AccountUpdate(BaseModel):
    platform: Optional[Platform] = None
    account_name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    profile_url: Optional[str] = Field(default=None, max_length=512)
    bio: Optional[str] = Field(default=None, max_length=200)
    category: Optional[str] = Field(default=None, max_length=64)
    follower_range: Optional[str] = Field(default=None, max_length=64)


class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=100)
    mutual_type: MutualType
    target_platform: Platform
    target_creator_account_id: Optional[int] = None
    target_account_name: Optional[str] = Field(default=None, max_length=64)
    target_account_url: Optional[str] = Field(default=None, max_length=512)
    qr_image_key: Optional[str] = Field(default=None, max_length=255)
    requires_follow_back: bool = True
    max_applicants: int = Field(default=10, ge=1, le=1000)
    expires_at: Optional[datetime] = None
    category: Optional[str] = Field(default=None, max_length=64)


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    content: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=64)
    expires_at: Optional[datetime] = None

    @field_validator("title", "content")
    @classmethod
    def strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class CommentCreate(BaseModel):
    content: str = Field(default="", max_length=500)
    image_key: Optional[str] = Field(default=None, max_length=255)
    comment_type: str = Field(default="COMMENT", max_length=24)
    parent_id: Optional[int] = None


class LikeCreate(BaseModel):
    target_type: str = Field(min_length=1, max_length=16)
    target_id: int


class ReviewCreate(BaseModel):
    apply_comment_id: int
    reviewee_id: int
    rating: int = Field(default=5, ge=1, le=5)
    content: str = Field(default="", max_length=500)

    @field_validator("content")
    @classmethod
    def _strip_content(cls, v):
        return v.strip() if isinstance(v, str) else v


class ApplicationCreate(BaseModel):
    applicant_creator_account_id: int
    application_message: Optional[str] = Field(default=None, max_length=500)
    evidence_type: EvidenceType = EvidenceType.SCREENSHOT


class EvidenceReview(BaseModel):
    accept: bool
    reason: Optional[str] = Field(default=None, max_length=500)


class ResubmitEvidence(BaseModel):
    evidence_type: EvidenceType = EvidenceType.SCREENSHOT


class DisputeCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ReportCreate(BaseModel):
    target_type: ReportTargetType
    target_id: int
    reason: str = Field(min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=1000)


class ReportResolve(BaseModel):
    resolution: str = Field(min_length=1, max_length=1000)
    status: str = Field(default="RESOLVED")


class AdminRestrict(BaseModel):
    action: str = Field(default="RESTRICT")
    reason: str = Field(min_length=1, max_length=1000)


# ---------------------------------------------------------------------------
# 薅羊毛活动
# ---------------------------------------------------------------------------


class ActivityCreate(BaseModel):
    title: str = Field(min_length=5, max_length=100)
    cover_image_key: str = Field(default="", max_length=256)
    platform_id: int
    activity_type_id: int
    summary: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1, max_length=20000)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    status: ActivityStatus = ActivityStatus.DRAFT
    is_featured: bool = False
    featured_sort: int = Field(default=0, ge=0, le=9999)
    display_sort: int = Field(default=0, ge=0, le=9999)
    source_url: Optional[str] = Field(default=None, max_length=512)
    risk_notice: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("title", "summary", "content", "source_url", "risk_notice")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class ActivityUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=5, max_length=100)
    cover_image_key: Optional[str] = Field(default=None, max_length=256)
    platform_id: Optional[int] = None
    activity_type_id: Optional[int] = None
    summary: Optional[str] = Field(default=None, min_length=1, max_length=300)
    content: Optional[str] = Field(default=None, min_length=1, max_length=20000)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    source_url: Optional[str] = Field(default=None, max_length=512)
    risk_notice: Optional[str] = Field(default=None, max_length=2000)
    featured_sort: Optional[int] = Field(default=None, ge=0, le=9999)
    display_sort: Optional[int] = Field(default=None, ge=0, le=9999)

    @field_validator("title", "summary", "content", "source_url", "risk_notice")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class ActivitySubmit(BaseModel):
    """用户端提交的新活动（进入待审批状态）。"""

    title: str = Field(min_length=5, max_length=100)
    platform_id: int
    activity_type_id: int
    summary: str = Field(min_length=1, max_length=300)
    content: str = Field(default="", max_length=20000)
    cover_image_key: Optional[str] = Field(default=None, max_length=256)
    source_url: Optional[str] = Field(default=None, max_length=512)
    end_at: Optional[datetime] = None

    @field_validator("title", "summary", "content", "source_url")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class ActivityEntryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    entry_type: ActivityEntryType = ActivityEntryType.QR_IMAGE
    qr_image_key: Optional[str] = Field(default=None, max_length=256)
    target_url: Optional[str] = Field(default=None, max_length=512)
    description: Optional[str] = Field(default=None, max_length=2000)
    sort_order: int = Field(default=0, ge=0, le=9999)
    is_enabled: bool = True
    expires_at: Optional[datetime] = None


class ActivityEntryUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=128)
    entry_type: Optional[ActivityEntryType] = None
    qr_image_key: Optional[str] = Field(default=None, max_length=256)
    target_url: Optional[str] = Field(default=None, max_length=512)
    description: Optional[str] = Field(default=None, max_length=2000)
    sort_order: Optional[int] = Field(default=None, ge=0, le=9999)
    is_enabled: Optional[bool] = None
    expires_at: Optional[datetime] = None


class ActivityPlatformCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=64)
    sort_order: int = Field(default=0, ge=0, le=9999)
    is_active: bool = True

    @field_validator("name", "code")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class ActivityTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=64)
    sort_order: int = Field(default=0, ge=0, le=9999)
    is_active: bool = True

    @field_validator("name", "code")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


# ---------------------------------------------------------------------------
# 活动评论与举报
# ---------------------------------------------------------------------------


class ActivityCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    parent_id: Optional[int] = None
    reply_to_user_id: Optional[int] = None

    @field_validator("content")
    @classmethod
    def _strip_content(cls, v):
        return v.strip() if isinstance(v, str) else v


class ActivityReportCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("reason")
    @classmethod
    def _strip_reason(cls, v):
        return v.strip() if isinstance(v, str) else v


class ActivityReportResolve(BaseModel):
    resolution: str = Field(min_length=1, max_length=1000)
    status: str = Field(default="RESOLVED", pattern="^(RESOLVED|DISMISSED)$")


class ActivityCommentModerate(BaseModel):
    status: str = Field(pattern="^(ACTIVE|HIDDEN|DELETED)$")


# ---------------------------------------------------------------------------
# 意见反馈
# ---------------------------------------------------------------------------


class FeedbackCreate(BaseModel):
    category_id: int
    title: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=5, max_length=5000)
    related_url: Optional[str] = Field(default=None, max_length=512)
    contact_info: Optional[str] = Field(default=None, max_length=256)
    extra_data: Optional[dict] = None

    @field_validator("title", "content", "related_url", "contact_info")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class FeedbackStatusUpdate(BaseModel):
    status: str = Field(pattern="^(PENDING|PROCESSING|RESOLVED|REJECTED)$")
    admin_note: Optional[str] = Field(default=None, max_length=2000)


class SystemSettingUpdate(BaseModel):
    key: str = Field(min_length=1, max_length=128)
    value: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=256)

    @field_validator("key")
    @classmethod
    def _strip_key(cls, v):
        return v.strip() if isinstance(v, str) else v
