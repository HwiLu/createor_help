from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigInt
from app.models import utcnow
from app.models.enums import CommentStatus


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInt, ForeignKey("posts.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default=CommentStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    author = relationship("User", lazy="joined")
