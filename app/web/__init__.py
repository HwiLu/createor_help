"""页面路由：Jinja2 服务端渲染 + 轻量 JS 调用 API。"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_admin, get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.comment import Comment
from app.models.creator_account import CreatorAccount
from app.models.enums import (
    CREATOR_CATEGORY_LABELS,
    MUTUAL_TYPE_LABELS,
    PLATFORM_LABELS,
    REQUEST_STATUS_LABELS,
    CommentStatus,
    CreatorAccountStatus,
    CreatorCategory,
    MutualRequestStatus,
    MutualType,
    Platform,
    PostStatus,
    ReportStatus,
    UserRole,
)
from app.models.mutual_request import MutualRequest
from app.models.post import Post
from app.models.report import Report
from app.models.top_creator import TopCreator, follower_tier
from app.models.user import User
from app.services.post_service import applicant_count, get_post, list_posts
from app.services.trust_service import compute_tags, compute_trust_stats

BASE_DIR = Path(__file__).resolve().parent.parent.parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

templates.env.globals.update(
    {
        "settings": settings,
        "PLATFORM_LABELS": {k.value: v for k, v in PLATFORM_LABELS.items()},
        "MUTUAL_TYPE_LABELS": {k.value: v for k, v in MUTUAL_TYPE_LABELS.items()},
        "REQUEST_STATUS_LABELS": {k.value: v for k, v in REQUEST_STATUS_LABELS.items()},
        "CREATOR_CATEGORY_LABELS": {k.value: v for k, v in CREATOR_CATEGORY_LABELS.items()},
        "Platform": Platform,
        "MutualType": MutualType,
        "PostStatus": PostStatus,
        "MutualRequestStatus": MutualRequestStatus,
        "UserRole": UserRole,
        "CreatorCategory": CreatorCategory,
        "follower_tier": follower_tier,
    }
)

web_router = APIRouter(include_in_schema=False)


def _ctx(request: Request, db: Session, **extra) -> dict:
    user = get_current_user_optional(request, db)
    ctx = {"request": request, "current_user": user}
    ctx.update(extra)
    return ctx


def _stats(db: Session, user_id: int) -> dict:
    stats = compute_trust_stats(db, user_id)
    return stats


@web_router.get("/")
def home(request: Request, db: Session = Depends(get_db), platform: Optional[str] = None, keyword: Optional[str] = None):
    posts, total = list_posts(db, platform, None, keyword, None, 1, 20)
    user = get_current_user_optional(request, db)
    accounts = []
    if user:
        accounts = (
            db.query(CreatorAccount)
            .filter(CreatorAccount.user_id == user.id, CreatorAccount.status == CreatorAccountStatus.ACTIVE.value)
            .all()
        )
    applicant_counts = {p.id: applicant_count(db, p.id) for p in posts}
    return templates.TemplateResponse(
        request,
        "home.html",
        _ctx(
            request,
            db,
            posts=posts,
            total=total,
            applicant_counts=applicant_counts,
            platform_filter=platform,
            keyword=keyword or "",
            my_accounts=accounts,
        ),
    )


@web_router.get("/creators")
def creators_page(
    request: Request,
    db: Session = Depends(get_db),
    platform: Optional[str] = None,
    category: Optional[str] = None,
):
    """优秀博主展示墙：顶部按平台筛选，左侧按主题筛选。"""
    query = db.query(TopCreator).filter(
        TopCreator.status == "ACTIVE",
        TopCreator.is_featured == True,  # noqa: E712
    )
    if platform:
        query = query.filter(TopCreator.platform == platform)
    if category:
        query = query.filter(TopCreator.category == category)
    creators = query.order_by(TopCreator.rank.asc(), TopCreator.id.asc()).all()

    grouped: dict[str, list[TopCreator]] = {}
    for c in creators:
        grouped.setdefault(c.category, []).append(c)

    return templates.TemplateResponse(
        request,
        "creators.html",
        _ctx(
            request,
            db,
            creators=creators,
            grouped=grouped,
            platform_filter=platform,
            category_filter=category,
        ),
    )


@web_router.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request, "login.html", _ctx(request, db))


@web_router.get("/posts/new")
def new_post_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/posts/new", status_code=302)
    accounts = (
        db.query(CreatorAccount)
        .filter(CreatorAccount.user_id == user.id, CreatorAccount.status == CreatorAccountStatus.ACTIVE.value)
        .all()
    )
    if not accounts:
        return RedirectResponse(url="/me?need_account=1", status_code=302)
    return templates.TemplateResponse(request, "post_new.html", _ctx(request, db, accounts=accounts))


@web_router.get("/posts/{post_id}")
def post_detail(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = get_post(db, post_id)
    user = get_current_user_optional(request, db)
    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post_id, Comment.status == CommentStatus.ACTIVE.value)
        .order_by(Comment.created_at.asc())
        .all()
    )
    my_application = None
    my_accounts = []
    if user:
        my_application = (
            db.query(MutualRequest)
            .filter(
                MutualRequest.post_id == post_id,
                MutualRequest.applicant_user_id == user.id,
                MutualRequest.status != MutualRequestStatus.CANCELLED.value,
            )
            .first()
        )
        my_accounts = (
            db.query(CreatorAccount)
            .filter(CreatorAccount.user_id == user.id, CreatorAccount.status == CreatorAccountStatus.ACTIVE.value)
            .all()
        )
    return templates.TemplateResponse(
        request,
        "post_detail.html",
        _ctx(request, db, post=post, comments=comments, my_application=my_application, my_accounts=my_accounts, applicants=applicant_count(db, post_id)),
    )


@web_router.get("/posts/{post_id}/apply")
def apply_page(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = get_post(db, post_id)
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url=f"/login?next=/posts/{post_id}/apply", status_code=302)
    if user.id == post.user_id:
        return RedirectResponse(url=f"/posts/{post_id}", status_code=302)
    accounts = (
        db.query(CreatorAccount)
        .filter(CreatorAccount.user_id == user.id, CreatorAccount.status == CreatorAccountStatus.ACTIVE.value)
        .all()
    )
    if not accounts:
        return RedirectResponse(url="/me?need_account=1", status_code=302)
    return templates.TemplateResponse(request, "apply.html", _ctx(request, db, post=post, accounts=accounts))


@web_router.get("/mutual")
def mutual_center(request: Request, db: Session = Depends(get_db), role: str = "all"):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/mutual", status_code=302)
    query = db.query(MutualRequest)
    if role == "received":
        query = query.filter(MutualRequest.poster_user_id == user.id)
    elif role == "sent":
        query = query.filter(MutualRequest.applicant_user_id == user.id)
    else:
        query = query.filter((MutualRequest.applicant_user_id == user.id) | (MutualRequest.poster_user_id == user.id))
    requests = query.order_by(MutualRequest.created_at.desc()).limit(100).all()
    return templates.TemplateResponse(request, "mutual.html", _ctx(request, db, requests=requests, role=role))


@web_router.get("/me")
def profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/me", status_code=302)
    accounts = (
        db.query(CreatorAccount)
        .filter(CreatorAccount.user_id == user.id, CreatorAccount.status == CreatorAccountStatus.ACTIVE.value)
        .all()
    )
    my_posts = db.query(Post).filter(Post.user_id == user.id, Post.status != PostStatus.DELETED.value).order_by(Post.created_at.desc()).limit(20).all()
    stats = _stats(db, user.id)
    joined_days = 0
    from datetime import datetime, timezone

    if user.created_at:
        joined_days = (datetime.now(timezone.utc) - user.created_at.replace(tzinfo=timezone.utc)).days
    tags = compute_tags(stats, joined_days)
    return templates.TemplateResponse(request, "profile.html", _ctx(request, db, accounts=accounts, my_posts=my_posts, stats=stats, tags=tags))


@web_router.get("/notifications")
def notifications_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user:
        return RedirectResponse(url="/login?next=/notifications", status_code=302)
    return templates.TemplateResponse(request, "notifications.html", _ctx(request, db))


@web_router.get("/admin")
def admin_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_optional(request, db)
    if not user or user.role != UserRole.ADMIN.value:
        return RedirectResponse(url="/login?next=/admin", status_code=302)
    dashboard = {
        "users": db.query(func.count(User.id)).scalar() or 0,
        "posts": db.query(func.count(Post.id)).scalar() or 0,
        "active_requests": db.query(func.count(MutualRequest.id)).scalar() or 0,
        "pending_reports": db.query(func.count(Report.id)).filter(Report.status == ReportStatus.PENDING.value).scalar() or 0,
    }
    reports = db.query(Report).order_by(Report.created_at.desc()).limit(50).all()
    users = db.query(User).order_by(User.created_at.desc()).limit(100).all()
    return templates.TemplateResponse(request, "admin.html", _ctx(request, db, dashboard=dashboard, reports=reports, users=users))


@web_router.get("/agreement")
def agreement(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "legal.html", _ctx(request, db, title="用户协议", body="用户协议初始模板内容……"))


@web_router.get("/privacy")
def privacy(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "legal.html", _ctx(request, db, title="隐私政策", body="隐私政策初始模板内容……"))
