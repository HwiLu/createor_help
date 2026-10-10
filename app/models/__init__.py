"""模型聚合导出，便于 Alembic 自动发现与统一导入。"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """统一以 naive UTC 存储时间，前端按北京时间展示。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


from app.models.user import User  # noqa: E402,F401
from app.models.creator_account import CreatorAccount  # noqa: E402,F401
from app.models.post import Post  # noqa: E402,F401
from app.models.comment import Comment  # noqa: E402,F401
from app.models.mutual_request import MutualRequest, MutualRequestEvent  # noqa: E402,F401
from app.models.evidence import EvidenceFile  # noqa: E402,F401
from app.models.notification import Notification  # noqa: E402,F401
from app.models.report import Report  # noqa: E402,F401
from app.models.audit_log import AuditLog  # noqa: E402,F401
from app.models.top_creator import TopCreator, follower_tier  # noqa: E402,F401
