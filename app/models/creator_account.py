from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigInt
from app.models import utcnow
from app.models.enums import CreatorAccountStatus, Platform


class CreatorAccount(Base):
    __tablename__ = "creator_accounts"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    platform: Mapped[str] = mapped_column(String(32), default=Platform.OTHER.value)
    account_name: Mapped[str] = mapped_column(String(128))
    profile_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    follower_range: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=CreatorAccountStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    owner = relationship("User", lazy="joined")
