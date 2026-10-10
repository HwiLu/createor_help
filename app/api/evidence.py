from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import EvidenceType
from app.models.user import User
from app.schemas import ResubmitEvidence
from app.services.evidence_service import list_evidence, read_evidence_file, save_evidence
from app.services.mutual_service import resubmit_evidence

router = APIRouter(tags=["evidence"])


@router.post("/mutual-requests/{request_id}/evidence")
def upload_evidence(
    request_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 同步处理（FastAPI 会在线程池中运行），兼容 Python 3.8。
    evidence = save_evidence(
        db, user, request_id, file, EvidenceType.SCREENSHOT, settings.MAX_EVIDENCE_FILES
    )
    return {
        "id": evidence.id,
        "mutual_request_id": evidence.mutual_request_id,
        "mime_type": evidence.mime_type,
        "file_size": evidence.file_size,
        "evidence_type": evidence.evidence_type,
        "created_at": evidence.created_at,
    }


@router.get("/mutual-requests/{request_id}/evidence")
def get_evidence_list(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    files = list_evidence(db, user, request_id)
    return {
        "items": [
            {
                "id": f.id,
                "mutual_request_id": f.mutual_request_id,
                "mime_type": f.mime_type,
                "file_size": f.file_size,
                "evidence_type": f.evidence_type,
                "created_at": f.created_at,
                "file_url": f"/api/v1/evidence/{f.id}/file",
            }
            for f in files
        ]
    }


@router.get("/evidence/{evidence_id}/file")
def get_evidence_file(evidence_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    evidence, data = read_evidence_file(db, user, evidence_id)
    return Response(
        content=data,
        media_type=evidence.mime_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/mutual-requests/{request_id}/resubmit")
def resubmit_evidence_api(
    request_id: int,
    data: ResubmitEvidence,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = resubmit_evidence(db, user, request_id, settings.MAX_EVIDENCE_RESUBMIT)
    from app.api.mutual_requests import _json

    return _json(req)
