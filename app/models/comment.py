from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigInt
from app.models import utcnow
from app.models.enums import CommentStatus, CommentType


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInt, ForeignKey("posts.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    parent_id: Mapped[Optional[int]] = mapped_column(BigInt, ForeignKey("comments.id"), nullable=True, index=True)
    image_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    comment_type: Mapped[str] = mapped_column(String(24), default=CommentType.COMMENT.value, server_default=CommentType.COMMENT.value, index=True)
    status: Mapped[str] = mapped_column(String(16), default=CommentStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    author = relationship("User", lazy="joined")
