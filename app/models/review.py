"""用户评价模型：互助业务完成后，双方互评。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigInt
from app.models import utcnow


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("reviewer_id", "apply_comment_id", name="uq_reviews_reviewer_apply"),)

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    reviewer_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    reviewee_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    apply_comment_id: Mapped[int] = mapped_column(BigInt, ForeignKey("comments.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer, default=5)
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    reviewer = relationship("User", foreign_keys=[reviewer_id], lazy="joined")
    reviewee = relationship("User", foreign_keys=[reviewee_id], lazy="joined")
