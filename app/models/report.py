from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigInt
from app.models import utcnow
from app.models.enums import ReportStatus, ReportTargetType


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    reporter_user_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(32), default=ReportTargetType.POST.value)
    target_id: Mapped[int] = mapped_column(BigInt, index=True)
    reason: Mapped[str] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=ReportStatus.PENDING.value, index=True)
    handled_by_admin_id: Mapped[Optional[int]] = mapped_column(BigInt, ForeignKey("users.id"), nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
