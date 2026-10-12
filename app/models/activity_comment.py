"""薅羊毛活动评论与举报数据模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigInt
from app.models import utcnow
from app.models.enums import ActivityCommentStatus, ActivityReportStatus


class ActivityComment(Base):
    """活动评论。

    ``parent_id`` 为空表示一级评论；非空表示回复某条一级评论（仅一层回复）。
    ``reply_to_user_id`` 记录被回复用户，用于展示「A 回复 B」。
    """

    __tablename__ = "activity_comments"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(BigInt, ForeignKey("activities.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(BigInt, nullable=True, index=True)
    reply_to_user_id: Mapped[Optional[int]] = mapped_column(BigInt, ForeignKey("users.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default=ActivityCommentStatus.ACTIVE.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    author = relationship("User", foreign_keys=[user_id], lazy="joined")
    reply_to_user = relationship("User", foreign_keys=[reply_to_user_id], lazy="joined")


class ActivityReport(Base):
    """活动/活动评论违规举报。"""

    __tablename__ = "activity_reports"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    activity_id: Mapped[Optional[int]] = mapped_column(BigInt, ForeignKey("activities.id"), nullable=True, index=True)
    comment_id: Mapped[Optional[int]] = mapped_column(BigInt, ForeignKey("activity_comments.id"), nullable=True, index=True)
    reporter_user_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=ActivityReportStatus.PENDING.value, index=True)
    handled_by: Mapped[Optional[int]] = mapped_column(BigInt, ForeignKey("users.id"), nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    reporter = relationship("User", foreign_keys=[reporter_user_id], lazy="joined")
    comment = relationship("ActivityComment", lazy="joined")
    activity = relationship("Activity", lazy="joined")
