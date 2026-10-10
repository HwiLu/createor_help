"""互助业务核心：申请创建与状态机转换（唯一合法入口）。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import utcnow
from app.models.creator_account import CreatorAccount
from app.models.enums import (
    CreatorAccountStatus,
    MutualRequestStatus,
    NotificationType,
    PostStatus,
    REQUEST_STATE_TRANSITIONS,
)
from app.models.mutual_request import MutualRequest, MutualRequestEvent
from app.models.post import Post
from app.models.user import User
from app.services.notification_service import notify

ACTIVE_STATUSES = {
    MutualRequestStatus.PENDING_REVIEW.value,
    MutualRequestStatus.EVIDENCE_REJECTED.value,
    MutualRequestStatus.WAITING_RETURN.value,
    MutualRequestStatus.RETURNED_PENDING_CONFIRMATION.value,
    MutualRequestStatus.COMPLETED.value,
    MutualRequestStatus.DISPUTED.value,
}


def _now() -> datetime:
    return utcnow()


def _get_request(db: Session, request_id: int) -> MutualRequest:
    req = db.get(MutualRequest, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申请不存在")
    return req


def _transition(
    db: Session,
    req: MutualRequest,
    actor_user_id: int,
    to_status: MutualRequestStatus,
    note: str | None = None,
) -> None:
    """状态机核心：仅允许合法转换，并记录事件日志。"""
    from_status = MutualRequestStatus(req.status)
    allowed = REQUEST_STATE_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"非法状态转换: {from_status.value} -> {to_status.value}",
        )

    req.status = to_status.value
    req.updated_at = _now()

    if to_status == MutualRequestStatus.WAITING_RETURN:
        req.evidence_reviewed_at = _now()
    elif to_status == MutualRequestStatus.EVIDENCE_REJECTED:
        req.evidence_reviewed_at = _now()
    elif to_status == MutualRequestStatus.RETURNED_PENDING_CONFIRMATION:
        req.returned_declared_at = _now()
    elif to_status == MutualRequestStatus.COMPLETED:
        req.applicant_confirmed_at = _now()
        req.completed_at = _now()
    elif to_status == MutualRequestStatus.DISPUTED:
        req.disputed_at = _now()

    event = MutualRequestEvent(
        mutual_request_id=req.id,
        actor_user_id=actor_user_id,
        from_status=from_status.value,
        to_status=to_status.value,
        note=note,
    )
    db.add(event)


def count_occupied_slots(db: Session, post_id: int) -> int:
    return (
        db.query(MutualRequest)
        .filter(MutualRequest.post_id == post_id, MutualRequest.status != MutualRequestStatus.CANCELLED.value)
        .count()
    )


def create_application(
    db: Session,
    user: User,
    post_id: int,
    applicant_creator_account_id: int,
    application_message: str | None,
) -> MutualRequest:
    post = db.get(Post, post_id)
    if post is None or post.status != PostStatus.PUBLISHED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在或不可申请")

    if post.expires_at is not None and post.expires_at < _now():
        post.status = PostStatus.EXPIRED.value
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="帖子已过期")

    if post.user_id == user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="不能申请自己的帖子")

    account = db.get(CreatorAccount, applicant_creator_account_id)
    if account is None or account.user_id != user.id or account.status == CreatorAccountStatus.DELETED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="自媒体账号无效或不属于当前用户")

    existing = (
        db.query(MutualRequest)
        .filter(
            MutualRequest.post_id == post_id,
            MutualRequest.applicant_user_id == user.id,
            MutualRequest.status != MutualRequestStatus.CANCELLED.value,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="你已存在有效申请，请勿重复申请")

    occupied = count_occupied_slots(db, post_id)
    if occupied >= post.max_applicants:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="申请名额已满")

    req = MutualRequest(
        post_id=post_id,
        applicant_user_id=user.id,
        poster_user_id=post.user_id,
        applicant_creator_account_id=applicant_creator_account_id,
        status=MutualRequestStatus.PENDING_REVIEW.value,
        application_message=application_message,
    )
    db.add(req)
    db.flush()

    # 创建申请属于初始事件，起点为空，不能走普通状态机转换。
    db.add(
        MutualRequestEvent(
            mutual_request_id=req.id,
            actor_user_id=user.id,
            from_status=None,
            to_status=MutualRequestStatus.PENDING_REVIEW.value,
            note="创建申请",
        )
    )

    notify(
        db,
        post.user_id,
        NotificationType.NEW_APPLICATION,
        "收到新的互助申请",
        f"用户 {user.nickname} 对你的帖子「{post.title}」发起了互助申请。",
        "MUTUAL_REQUEST",
        req.id,
    )
    db.commit()
    db.refresh(req)
    return req


def review_evidence(db: Session, poster: User, request_id: int, accept: bool, reason: str | None) -> MutualRequest:
    req = _get_request(db, request_id)
    if req.poster_user_id != poster.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有发帖人可以核验证据")
    if req.status != MutualRequestStatus.PENDING_REVIEW.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前状态不可核验")

    if accept:
        _transition(db, req, poster.id, MutualRequestStatus.WAITING_RETURN, note="证据有效")
        notify(
            db,
            req.applicant_user_id,
            NotificationType.EVIDENCE_ACCEPTED,
            "证据核验通过",
            "你的关注证据已被接受，请等待发帖人完成回关。",
            "MUTUAL_REQUEST",
            req.id,
        )
    else:
        if not reason or not reason.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="拒绝证据必须填写原因")
        req.evidence_rejected_reason = reason.strip()
        _transition(db, req, poster.id, MutualRequestStatus.EVIDENCE_REJECTED, note=reason.strip())
        notify(
            db,
            req.applicant_user_id,
            NotificationType.EVIDENCE_REJECTED,
            "证据被拒绝",
            f"你的关注证据被拒绝，原因：{reason.strip()}",
            "MUTUAL_REQUEST",
            req.id,
        )
    db.commit()
    db.refresh(req)
    return req


def resubmit_evidence(db: Session, applicant: User, request_id: int, max_resubmit: int) -> MutualRequest:
    req = _get_request(db, request_id)
    if req.applicant_user_id != applicant.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有申请者可以重新提交证据")
    if req.status != MutualRequestStatus.EVIDENCE_REJECTED.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前状态不可重新提交")

    post = db.get(Post, req.post_id)
    if post is None or post.status not in (PostStatus.PUBLISHED.value, PostStatus.CLOSED.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="帖子已关闭，无法重新提交")

    if req.resubmit_count >= max_resubmit:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已达重新提交次数上限")

    req.resubmit_count += 1
    req.evidence_rejected_reason = None
    _transition(db, req, applicant.id, MutualRequestStatus.PENDING_REVIEW, note="重新提交证据")
    db.commit()
    db.refresh(req)
    return req


def declare_returned(db: Session, poster: User, request_id: int) -> MutualRequest:
    req = _get_request(db, request_id)
    if req.poster_user_id != poster.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有发帖人可以声明回关")
    if req.status != MutualRequestStatus.WAITING_RETURN.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前状态不可声明回关")

    _transition(db, req, poster.id, MutualRequestStatus.RETURNED_PENDING_CONFIRMATION, note="发帖人声明已回关")
    notify(
        db,
        req.applicant_user_id,
        NotificationType.RETURNED,
        "对方已声明回关",
        "发帖人已声明完成回关，请核实后确认完成或发起争议。",
        "MUTUAL_REQUEST",
        req.id,
    )
    db.commit()
    db.refresh(req)
    return req


def confirm_completion(db: Session, applicant: User, request_id: int) -> MutualRequest:
    req = _get_request(db, request_id)
    if req.applicant_user_id != applicant.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有申请者可以确认完成")
    if req.status != MutualRequestStatus.RETURNED_PENDING_CONFIRMATION.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前状态不可确认完成")

    _transition(db, req, applicant.id, MutualRequestStatus.COMPLETED, note="申请者确认完成")
    notify(
        db,
        req.poster_user_id,
        NotificationType.COMPLETED,
        "互助已完成",
        "申请者已确认收到回关，本次互助已完成。",
        "MUTUAL_REQUEST",
        req.id,
    )
    db.commit()
    db.refresh(req)
    return req


def dispute(db: Session, applicant: User, request_id: int, reason: str) -> MutualRequest:
    req = _get_request(db, request_id)
    if req.applicant_user_id != applicant.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有申请者可以发起争议")
    if req.status not in (MutualRequestStatus.WAITING_RETURN.value, MutualRequestStatus.RETURNED_PENDING_CONFIRMATION.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前状态不可发起争议")

    _transition(db, req, applicant.id, MutualRequestStatus.DISPUTED, note=f"发起争议：{reason}")
    notify(
        db,
        req.poster_user_id,
        NotificationType.DISPUTE_RESULT,
        "收到争议",
        f"申请者对本次互助发起争议：{reason}",
        "MUTUAL_REQUEST",
        req.id,
    )
    db.commit()
    db.refresh(req)
    return req


def cancel(db: Session, user: User, request_id: int) -> MutualRequest:
    req = _get_request(db, request_id)
    if user.id not in (req.applicant_user_id, req.poster_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限取消该申请")
    if req.status not in (MutualRequestStatus.PENDING_REVIEW.value, MutualRequestStatus.EVIDENCE_REJECTED.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="当前状态不可取消")

    _transition(db, req, user.id, MutualRequestStatus.CANCELLED, note="取消申请")
    db.commit()
    db.refresh(req)
    return req


def admin_resolve(db: Session, admin: User, request_id: int, to_status: MutualRequestStatus, reason: str) -> MutualRequest:
    req = _get_request(db, request_id)
    if to_status not in (MutualRequestStatus.COMPLETED, MutualRequestStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="管理员仅可判定完成或撤销")

    _transition(db, req, admin.id, to_status, note=f"管理员处理：{reason}")
    db.commit()
    db.refresh(req)
    return req
