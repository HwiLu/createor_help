from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigInt
from app.models import utcnow
from app.models.enums import MutualType, Platform, PostStatus


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    mutual_type: Mapped[str] = mapped_column(String(32), default=MutualType.FOLLOW_FOR_FOLLOW.value)
    target_platform: Mapped[str] = mapped_column(String(32), default=Platform.OTHER.value)
    target_creator_account_id: Mapped[int] = mapped_column(BigInt, ForeignKey("creator_accounts.id"))
    requires_follow_back: Mapped[bool] = mapped_column(Boolean, default=True)
    max_applicants: Mapped[int] = mapped_column(Integer, default=10)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=PostStatus.PUBLISHED.value, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    qr_image_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    author = relationship("User", lazy="joined")
    target_account = relationship("CreatorAccount", lazy="joined")
