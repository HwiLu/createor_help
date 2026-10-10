from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigInt
from app.models import utcnow
from app.models.enums import CreatorCategory, Platform


def follower_tier(follower_count: int) -> str:
    """把粉丝数转换为量级区间，用于展示（避免精确数字失真）。

    区间：亿级 / 千万级 / 百万级 / 十万级 / 万级 / 万以下。
    """
    if follower_count >= 100_000_000:
        return "亿级"
    if follower_count >= 10_000_000:
        return "千万级"
    if follower_count >= 1_000_000:
        return "百万级"
    if follower_count >= 100_000:
        return "十万级"
    if follower_count >= 10_000:
        return "万级"
    return "万以下"


class TopCreator(Base):
    """优秀博主（上榜展示）。

    is_featured 为业务预留字段：后续「付费上榜」流程中，用户完成付费后将其置为 True 才会展示；
    示例数据默认为 True，用于展示效果。
    """

    __tablename__ = "top_creators"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(32), default=Platform.XIAOHONGSHU.value, index=True)
    category: Mapped[str] = mapped_column(String(32), default=CreatorCategory.LIFESTYLE.value, index=True)
    username: Mapped[str] = mapped_column(String(128))
    nickname: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    profile_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    follower_display: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
