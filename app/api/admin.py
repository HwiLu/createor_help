from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.enums import MutualRequestStatus, PostStatus, ReportStatus
from app.models.mutual_request import MutualRequest
from app.models.post import Post
from app.models.report import Report
from app.models.user import User
from app.schemas import AdminRestrict, ReportResolve
from app.services.audit_service import write_audit
from app.services.moderation_service import resolve_report, restrict_user
from app.services.post_service import admin_delete_post

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
def dashboard(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return {
        "users": db.query(func.count(User.id)).scalar() or 0,
        "posts": db.query(func.count(Post.id)).scalar() or 0,
        "active_requests": db.query(func.count(MutualRequest.id)).scalar() or 0,
        "pending_reports": db.query(func.count(Report.id)).filter(Report.status == ReportStatus.PENDING.value).scalar() or 0,
        "completed": db.query(func.count(MutualRequest.id)).filter(MutualRequest.status == MutualRequestStatus.COMPLETED.value).scalar() or 0,
        "disputed": db.query(func.count(MutualRequest.id)).filter(MutualRequest.status == MutualRequestStatus.DISPUTED.value).scalar() or 0,
    }


@router.get("/reports")
def list_reports(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
):
    query = db.query(Report)
    if status_filter:
        query = query.filter(Report.status == status_filter.upper())
    total = query.count()
    items = query.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [
            {
                "id": r.id,
                "reporter_user_id": r.reporter_user_id,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "reason": r.reason,
                "description": r.description,
                "status": r.status,
                "resolution": r.resolution,
                "created_at": r.created_at,
            }
            for r in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/reports/{report_id}/resolve")
def resolve_report_api(
    report_id: int,
    data: ReportResolve,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    report = resolve_report(db, admin, report_id, data.resolution, data.status)
    return {"id": report.id, "status": report.status, "resolution": report.resolution}


@router.post("/users/{user_id}/restrict")
def restrict_api(
    user_id: int,
    data: AdminRestrict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = restrict_user(db, admin, user_id, data.action, data.reason)
    return {"id": user.id, "status": user.status}


@router.post("/users/{user_id}/ban")
def ban_api(
    user_id: int,
    data: AdminRestrict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = restrict_user(db, admin, user_id, "BAN", data.reason)
    return {"id": user.id, "status": user.status}


@router.get("/users")
def list_users(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
):
    query = db.query(User)
    total = query.count()
    items = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [
            {
                "id": u.id,
                "nickname": u.nickname,
                "role": u.role,
                "status": u.status,
                "created_at": u.created_at,
                "last_login_at": u.last_login_at,
            }
            for u in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/audit-logs")
def audit_logs(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
):
    query = db.query(AuditLog)
    total = query.count()
    items = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [
            {
                "id": a.id,
                "actor_user_id": a.actor_user_id,
                "action": a.action,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "reason": a.reason,
                "created_at": a.created_at,
            }
            for a in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/mutual-requests/{request_id}/resolve")
def admin_resolve_request(
    request_id: int,
    body: dict,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from app.models.enums import MutualRequestStatus as S
    from app.services.mutual_service import admin_resolve

    to_status = S(body["to_status"])
    reason = body.get("reason", "管理员处理")
    req = admin_resolve(db, admin, request_id, to_status, reason)
    write_audit(db, admin.id, "ADMIN_RESOLVE_REQUEST", "MUTUAL_REQUEST", request_id, after={"to_status": to_status.value}, reason=reason)
    db.commit()
    from app.api.mutual_requests import _json

    return _json(req)


def _post_duplicate_groups(db: Session) -> tuple[dict[int, int], dict[int, int]]:
    """计算帖子重复分组。

    判定口径：同一用户 + 同一平台 + (标题相同 或 内容相同) 视为重复。
    返回 (post_id -> group_id, group_id -> 成员数量)，成员数 > 1 即存在重复。
    """
    posts = (
        db.query(Post)
        .filter(Post.status != PostStatus.DELETED.value)
        .order_by(Post.created_at.asc())
        .all()
    )
    parent = {p.id: p.id for p in posts}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    title_seen: dict[tuple, int] = {}
    content_seen: dict[tuple, int] = {}
    for p in posts:
        tkey = (p.user_id, p.target_platform, p.title.strip().lower())
        if tkey in title_seen:
            union(p.id, title_seen[tkey])
        else:
            title_seen[tkey] = p.id

        ckey = (p.user_id, p.target_platform, p.content.strip().lower())
        if ckey in content_seen:
            union(p.id, content_seen[ckey])
        else:
            content_seen[ckey] = p.id

    group_ids: dict[int, int] = {}
    for p in posts:
        root = find(p.id)
        group_ids.setdefault(root, len(group_ids) + 1)

    post_group = {p.id: group_ids[find(p.id)] for p in posts}
    group_count: dict[int, int] = {}
    for gid in post_group.values():
        group_count[gid] = group_count.get(gid, 0) + 1
    return post_group, group_count


@router.get("/posts")
def list_posts_admin(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    query = db.query(Post).filter(Post.status != PostStatus.DELETED.value)
    total = query.count()
    items = query.order_by(Post.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    post_group, group_count = _post_duplicate_groups(db)
    return {
        "items": [
            {
                "id": p.id,
                "title": p.title,
                "content": p.content,
                "target_platform": p.target_platform,
                "status": p.status,
                "category": p.category,
                "author_nickname": p.author.nickname if p.author else None,
                "created_at": p.created_at,
                "duplicate_group": post_group.get(p.id),
                "duplicate_count": group_count.get(post_group.get(p.id), 1),
            }
            for p in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.delete("/posts/{post_id}")
def admin_delete_post_api(
    post_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    reason: str = Query(default="违规内容", min_length=1, max_length=1000),
):
    post = admin_delete_post(db, admin, post_id, reason)
    return {"ok": True, "id": post.id, "status": post.status}
