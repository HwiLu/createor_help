"""诚信统计：基于可追溯记录，普通用户不可修改。"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import MutualRequestStatus
from app.models.mutual_request import MutualRequest
from app.models.user import User


def compute_trust_stats(db: Session, user_id: int) -> dict:
    initiated = (
        db.query(func.count(MutualRequest.id))
        .filter(MutualRequest.applicant_user_id == user_id)
        .scalar()
        or 0
    )
    valid = (
        db.query(func.count(MutualRequest.id))
        .filter(
            MutualRequest.applicant_user_id == user_id,
            MutualRequest.status != MutualRequestStatus.CANCELLED.value,
        )
        .scalar()
        or 0
    )
    completed = (
        db.query(func.count(MutualRequest.id))
        .filter(
            MutualRequest.status == MutualRequestStatus.COMPLETED.value,
            (MutualRequest.applicant_user_id == user_id) | (MutualRequest.poster_user_id == user_id),
        )
        .scalar()
        or 0
    )
    disputed = (
        db.query(func.count(MutualRequest.id))
        .filter(
            MutualRequest.status == MutualRequestStatus.DISPUTED.value,
            (MutualRequest.applicant_user_id == user_id) | (MutualRequest.poster_user_id == user_id),
        )
        .scalar()
        or 0
    )

    completion_rate = round(completed / valid, 4) if valid else 0.0
    return {
        "initiated_applications": initiated,
        "valid_applications": valid,
        "completed_mutuals": completed,
        "completion_rate": completion_rate,
        "disputed_count": disputed,
    }


def compute_tags(stats: dict, joined_days: int) -> list[str]:
    tags: list[str] = []
    completed = stats["completed_mutuals"]
    if joined_days < 30 or completed < 3:
        tags.append("新加入")
    if completed >= 3:
        tags.append("互助积极")
    if completed >= 10 and stats["completion_rate"] >= 0.8 and stats["disputed_count"] == 0:
        tags.append("诚信创作者")
    if stats["disputed_count"] > 0:
        tags.append("争议处理中")
    return tags
