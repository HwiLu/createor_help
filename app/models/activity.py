"""薅羊毛活动模块数据模型：活动、平台字典、类型字典、参与入口。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigInt
from app.models import utcnow
from app.models.enums import ActivityEntryType, ActivityStatus


class ActivityPlatform(Base):
    """活动所属平台（可配置字典，后台维护）。"""

    __tablename__ = "activity_platforms"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ActivityType(Base):
    """活动类型（可配置字典，后台维护）。"""

    __tablename__ = "activity_types"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Activity(Base):
    """薅羊毛活动主表。

    ``status`` 为管理状态（草稿/发布/下架），前端展示态（进行中/即将开始/已结束）
    由服务层结合 ``start_at`` / ``end_at`` 实时计算，避免人工填写导致状态失真。
    """

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100))
    cover_image_key: Mapped[str] = mapped_column(String(256))
    platform_id: Mapped[int] = mapped_column(BigInt, ForeignKey("activity_platforms.id"), index=True)
    activity_type_id: Mapped[int] = mapped_column(BigInt, ForeignKey("activity_types.id"), index=True)
    summary: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    start_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=ActivityStatus.DRAFT.value, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    featured_sort: Mapped[int] = mapped_column(Integer, default=0)
    display_sort: Mapped[int] = mapped_column(Integer, default=0, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    risk_notice: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    platform = relationship("ActivityPlatform", lazy="joined")
    activity_type = relationship("ActivityType", lazy="joined")
    creator = relationship("User", foreign_keys=[created_by], lazy="joined")


class ActivityEntry(Base):
    """活动参与入口：二维码或外部链接。"""

    __tablename__ = "activity_entries"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(BigInt, ForeignKey("activities.id"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    entry_type: Mapped[str] = mapped_column(String(16), default=ActivityEntryType.QR_IMAGE.value)
    qr_image_key: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    target_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
