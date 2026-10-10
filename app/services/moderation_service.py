"""审核与管理员服务：举报处理、封禁限制、审计日志。"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import ReportStatus, UserStatus
from app.models.report import Report
from app.models.user import User
from app.services.audit_service import write_audit
from app.services.notification_service import notify


def resolve_report(db: Session, admin: User, report_id: int, resolution: str, new_status: str) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="举报不存在")
    report.status = new_status
    report.handled_by_admin_id = admin.id
    report.resolution = resolution
    write_audit(
        db,
        admin.id,
        "RESOLVE_REPORT",
        "REPORT",
        report.id,
        before={"status": ReportStatus.PENDING.value},
        after={"status": new_status, "resolution": resolution},
    )
    db.commit()
    db.refresh(report)
    return report


def restrict_user(db: Session, admin: User, target_id: int, action: str, reason: str) -> User:
    target = db.get(User, target_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if target.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能操作自己")

    before_status = target.status
    if action == "RESTRICT":
        target.status = UserStatus.RESTRICTED.value
    elif action == "BAN":
        target.status = UserStatus.BANNED.value
    elif action == "UNBAN":
        target.status = UserStatus.ACTIVE.value
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效操作")

    write_audit(
        db,
        admin.id,
        f"USER_{action}",
        "USER",
        target.id,
        before={"status": before_status},
        after={"status": target.status},
        reason=reason,
    )
    notify(db, target.id, "ADMIN", "账号状态变更", f"你的账号状态已变更为 {target.status}。原因：{reason}", "USER", target.id)
    db.commit()
    db.refresh(target)
    return target


def mark_non_compliance(db: Session, admin: User, target_id: int, reason: str) -> None:
    write_audit(
        db,
        admin.id,
        "MARK_NON_COMPLIANCE",
        "USER",
        target_id,
        before=None,
        after={"non_compliance": True},
        reason=reason,
    )
    db.commit()
