from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigInt
from app.models import utcnow
from app.models.enums import MutualRequestStatus


class MutualRequest(Base):
    __tablename__ = "mutual_requests"
    __table_args__ = (
        Index("ix_mr_post_applicant", "post_id", "applicant_user_id"),
    )

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInt, ForeignKey("posts.id"), index=True)
    applicant_user_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    poster_user_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    applicant_creator_account_id: Mapped[int] = mapped_column(BigInt, ForeignKey("creator_accounts.id"))
    status: Mapped[str] = mapped_column(String(32), default=MutualRequestStatus.PENDING_REVIEW.value, index=True)
    application_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_rejected_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resubmit_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    returned_declared_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    applicant_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    disputed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    post = relationship("Post", lazy="joined")
    applicant = relationship("User", foreign_keys=[applicant_user_id], lazy="joined")
    poster = relationship("User", foreign_keys=[poster_user_id], lazy="joined")
    applicant_account = relationship("CreatorAccount", lazy="joined")


class MutualRequestEvent(Base):
    """互助状态转换日志，服务端生成，普通用户不可修改。"""

    __tablename__ = "mutual_request_events"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    mutual_request_id: Mapped[int] = mapped_column(BigInt, ForeignKey("mutual_requests.id"), index=True)
    actor_user_id: Mapped[Optional[int]] = mapped_column(BigInt, ForeignKey("users.id"), nullable=True)
    from_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    actor = relationship("User", lazy="joined")
