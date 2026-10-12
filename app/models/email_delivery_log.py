"""邮件投递日志数据模型（只保存必要的元数据，不记录 SMTP 密码）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigInt
from app.models import utcnow
from app.models.enums import EmailDeliveryStatus


class EmailDeliveryLog(Base):
    __tablename__ = "email_delivery_logs"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    feedback_id: Mapped[int] = mapped_column(BigInt, ForeignKey("feedbacks.id"), index=True)
    recipient_email: Mapped[str] = mapped_column(String(256))
    subject: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(16), default=EmailDeliveryStatus.PENDING.value, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
