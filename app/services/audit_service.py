"""审计日志服务：所有管理员操作必须写入。"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit(
    db: Session,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    before: dict | None = None,
    after: dict | None = None,
    reason: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        before_data=json.dumps(before, ensure_ascii=False, default=str) if before else None,
        after_data=json.dumps(after, ensure_ascii=False, default=str) if after else None,
        reason=reason,
    )
    db.add(entry)
    return entry
