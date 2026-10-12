"""信用分流水：记录每次加减分，用于幂等与审计。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigInt
from app.models import utcnow

# 信用分变动原因
CREDIT_APPLY_EVIDENCE = "APPLY_EVIDENCE"  # 提交关注证据 +10（申请者）
CREDIT_MUTUAL_COMPLETE = "MUTUAL_COMPLETE"  # 回关完成 +10（发帖人）
CREDIT_DEFAULT = "DEFAULT"  # 失信未回关 -10（发帖人）


class CreditLog(Base):
    __tablename__ = "credit_logs"
    __table_args__ = (UniqueConstraint("user_id", "entity_type", "entity_id", "reason", name="uq_credit_log_idempotent"),)

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"), index=True)
    change: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(32))
    entity_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(BigInt, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
