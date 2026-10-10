from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import MutualRequestStatus
from app.models.mutual_request import MutualRequest, MutualRequestEvent
from app.models.user import User
from app.schemas import ApplicationCreate, DisputeCreate, EvidenceReview
from app.services.mutual_service import (
    cancel,
    confirm_completion,
    create_application,
    declare_returned,
    dispute,
)

router = APIRouter(tags=["mutual-requests"])


def _json(req: MutualRequest) -> dict:
    return {
        "id": req.id,
        "post_id": req.post_id,
        "applicant_user_id": req.applicant_user_id,
        "poster_user_id": req.poster_user_id,
        "applicant_creator_account_id": req.applicant_creator_account_id,
        "status": req.status,
        "application_message": req.application_message,
        "evidence_rejected_reason": req.evidence_rejected_reason,
        "resubmit_count": req.resubmit_count,
        "evidence_reviewed_at": req.evidence_reviewed_at,
        "returned_declared_at": req.returned_declared_at,
        "applicant_confirmed_at": req.applicant_confirmed_at,
        "completed_at": req.completed_at,
        "disputed_at": req.disputed_at,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
        "post": {"id": req.post.id, "title": req.post.title},
        "applicant": {"id": req.applicant.id, "nickname": req.applicant.nickname},
        "poster": {"id": req.poster.id, "nickname": req.poster.nickname},
        "applicant_account": {
            "id": req.applicant_account.id,
            "platform": req.applicant_account.platform,
            "account_name": req.applicant_account.account_name,
            "profile_url": req.applicant_account.profile_url,
        },
    }


@router.post("/posts/{post_id}/applications")
def create_application_api(
    post_id: int,
    data: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = create_application(db, user, post_id, data.applicant_creator_account_id, data.application_message)
    return _json(req)


@router.get("/mutual-requests")
def list_my_requests(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    role: str = Query(default="all"),  # all / received / sent
    status_filter: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
):
    query = db.query(MutualRequest)
    if role == "received":
        query = query.filter(MutualRequest.poster_user_id == user.id)
    elif role == "sent":
        query = query.filter(MutualRequest.applicant_user_id == user.id)
    else:
        query = query.filter(
            (MutualRequest.applicant_user_id == user.id) | (MutualRequest.poster_user_id == user.id)
        )
    if status_filter:
        query = query.filter(MutualRequest.status == status_filter.upper())

    total = query.count()
    items = query.order_by(MutualRequest.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_json(r) for r in items], "total": total, "page": page, "page_size": page_size}


@router.get("/mutual-requests/{request_id}")
def get_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    req = db.get(MutualRequest, request_id)
    if req is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申请不存在")
    from app.core.permissions import can_view_request

    if not can_view_request(user, req):
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限查看该申请")
    result = _json(req)
    events = (
        db.query(MutualRequestEvent)
        .filter(MutualRequestEvent.mutual_request_id == request_id)
        .order_by(MutualRequestEvent.created_at.asc())
        .all()
    )
    result["events"] = [
        {
            "from_status": e.from_status,
            "to_status": e.to_status,
            "note": e.note,
            "created_at": e.created_at,
            "actor": e.actor.nickname if e.actor else None,
        }
        for e in events
    ]
    return result


@router.post("/mutual-requests/{request_id}/cancel")
def cancel_api(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = cancel(db, user, request_id)
    return _json(req)


@router.post("/mutual-requests/{request_id}/review-evidence")
def review_evidence_api(
    request_id: int,
    body: EvidenceReview,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.mutual_service import review_evidence

    req = review_evidence(db, user, request_id, body.accept, body.reason)
    return _json(req)


@router.post("/mutual-requests/{request_id}/declare-returned")
def declare_returned_api(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = declare_returned(db, user, request_id)
    return _json(req)


@router.post("/mutual-requests/{request_id}/confirm-completion")
def confirm_completion_api(request_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = confirm_completion(db, user, request_id)
    return _json(req)


@router.post("/mutual-requests/{request_id}/dispute")
def dispute_api(request_id: int, data: DisputeCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = dispute(db, user, request_id, data.reason)
    return _json(req)
