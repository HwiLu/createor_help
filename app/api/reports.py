from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import ReportStatus
from app.models.report import Report
from app.models.user import User
from app.schemas import ReportCreate

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("")
def create_report(data: ReportCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = Report(
        reporter_user_id=user.id,
        target_type=data.target_type.value,
        target_id=data.target_id,
        reason=data.reason.strip(),
        description=data.description,
        status=ReportStatus.PENDING.value,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"id": report.id, "status": report.status}


@router.get("/my")
def my_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reports = (
        db.query(Report)
        .filter(Report.reporter_user_id == user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "reason": r.reason,
            "status": r.status,
            "resolution": r.resolution,
            "created_at": r.created_at,
        }
        for r in reports
    ]
