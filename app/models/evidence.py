from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigInt
from app.models import utcnow
from app.models.enums import EvidenceType


class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    mutual_request_id: Mapped[int] = mapped_column(BigInt, ForeignKey("mutual_requests.id"), index=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(BigInt, ForeignKey("users.id"))
    storage_key: Mapped[str] = mapped_column(String(256))
    original_filename: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(64))
    file_size: Mapped[int] = mapped_column(Integer)
    evidence_type: Mapped[str] = mapped_column(String(32), default=EvidenceType.SCREENSHOT.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
