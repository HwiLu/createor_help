"""意见反馈数据模型：反馈分类、反馈记录。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigInt
from app.models import utcnow
from app.models.enums import FeedbackStatus


class FeedbackCategory(Base):
    """反馈分类（可配置字典，后台维护）。"""

    __tablename__ = "feedback_categories"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Feedback(Base):
    """用户反馈记录。

    ``extra_data`` 用于保存「新活动提交」等分类的扩展字段（JSON），
    必须在服务层校验结构与内容后再落库。``admin_note`` 为管理员内部备注，
    永不公开给普通用户。
    """

    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(BigInt, ForeignKey("users.id"), nullable=True, index=True)
    category_id: Mapped[int] = mapped_column(BigInt, ForeignKey("feedback_categories.id"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    related_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    contact_info: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=FeedbackStatus.PENDING.value, index=True)
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    handled_by: Mapped[Optional[int]] = mapped_column(BigInt, ForeignKey("users.id"), nullable=True)
    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    category = relationship("FeedbackCategory", lazy="joined")
    user = relationship("User", foreign_keys=[user_id], lazy="joined")
