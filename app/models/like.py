"""通用点赞模型：帖子、评论、互关节点均可点赞。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigInt
from app.models import utcnow

# 点赞目标类型
LIKE_TARGET_POST = "POST"
LIKE_TARGET_COMMENT = "COMMENT"


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "target_type", "target_id", name="uq_likes_user_target"),)

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(16), index=True)
    target_id: Mapped[int] = mapped_column(BigInt, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
