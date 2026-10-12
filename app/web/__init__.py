"""页面路由：Jinja2 服务端渲染 + 轻量 JS 调用 API。"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

import jinja2
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_admin, get_current_user, get_current_user_optional
from app.db.session import get_db
from app.models.activity import Activity
from app.models.comment import Comment
from app.models.creator_account import CreatorAccount
from app.models.enums import (
    ACTIVITY_DISPLAY_STATUS_LABELS,
    ACTIVITY_ENTRY_TYPE_LABELS,
    ACTIVITY_STATUS_LABELS,
    COMMENT_TYPE_LABELS,
    CREATOR_CATEGORY_LABELS,
    MUTUAL_TYPE_LABELS,
    PLATFORM_LABELS,
    ActivityDisplayStatus,
    ActivityStatus,
    CommentStatus,
    CommentType,
    CreatorAccountStatus,
    CreatorCategory,
    MutualType,
    Platform,
    PostStatus,
    ReportStatus,
    UserRole,
)
from app.models.like import LIKE_TARGET_COMMENT, LIKE_TARGET_POST
from app.models.notification import Notification
from app.models.post import Post
from app.models.report import Report
from app.models.review import Review
from app.models.top_creator import TopCreator, follower_tier
from app.models.user import User
from app.services import activity_comment_service, activity_service, credit_service, feedback_service, like_service
from app.services.markdown_service import render_markdown
from app.services.post_service import get_post, list_posts
from app.services.trust_service import compute_tags, compute_trust_stats

BASE_DIR = Path(__file__).resolve().parent.parent.parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

templates.env.globals.update(
    {
        "settings": settings,
        "PLATFORM_LABELS": {k.value: v for k, v in PLATFORM_LABELS.items()},
        "MUTUAL_TYPE_LABELS": {k.value: v for k, v in MUTUAL_TYPE_LABELS.items()},
        "COMMENT_TYPE_LABELS": {k.value: v for k, v in COMMENT_TYPE_LABELS.items()},
        "CREATOR_CATEGORY_LABELS": {k.value: v for k, v in CREATOR_CATEGORY_LABELS.items()},
        "ACTIVITY_STATUS_LABELS": {k.value: v for k, v in ACTIVITY_STATUS_LABELS.items()},
        "ACTIVITY_DISPLAY_STATUS_LABELS": {k.value: v for k, v in ACTIVITY_DISPLAY_STATUS_LABELS.items()},
        "ACTIVITY_ENTRY_TYPE_LABELS": {k.value: v for k, v in ACTIVITY_ENTRY_TYPE_LABELS.items()},
        "Platform": Platform,
        "MutualType": MutualType,
        "PostStatus": PostStatus,
        "UserRole": UserRole,
        "CreatorCategory": CreatorCategory,
        "ActivityDisplayStatus": ActivityDisplayStatus,
        "activity_display_status": activity_service.compute_display_status,
        "follower_tier": follower_tier,
    }
)


@jinja2.pass_context
def activity_filter_url(ctx: dict, **overrides) -> str:
    """生成活动列表筛选链接：保留当前查询参数并覆盖指定项。

    标签/分页链接均通过此函数生成，点击标签自动回到第一页（去除 page）。
    """
    request = ctx.get("request")
    params: dict[str, str] = {}
    if request is not None:
        for key, value in request.query_params.items():
            if key == "page" or value == "":
                continue
            params[key] = value
    for key, value in overrides.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    qs = urlencode(params)
    return "/activities" + (f"?{qs}" if qs else "")


templates.env.globals["activity_filter_url"] = activity_filter_url


def _fmt_dt(dt):
    """naive UTC -> 北京时间字符串（中国无夏令时，固定 +8 小时）。"""
    if not dt:
        return ""
    return (dt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")


templates.env.filters["fmt_dt"] = _fmt_dt

web_router = APIRouter(include_in_schema=False)


def _ctx(request: Request, db: Session, **extra) -> dict:
    user = get_current_user_optional(request, db)
    unread_count = 0
    if user is not None:
        unread_count = (
            db.query(Notification)
            .filter(Notification.user_id == user.id, Notification.is_read.is_(False))
            .count()
        )
        # 失信惰性检查：作为发帖人，超一周未回关的申请自动扣分
        try:
            if credit_service.check_defaulters(db, user.id) > 0:
                db.commit()
        except Exception:
            db.rollback()
    ctx = {"request": request, "current_user": user, "unread_count": unread_count}
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
    featured_activities = activity_service.get_featured_activities(db)
    featured_counts = activity_service.comment_counts(db, [a.id for a in featured_activities])
    return templates.TemplateResponse(
        request,
        "home.html",
        _ctx(
            request,
            db,
            posts=posts,
            total=total,
            featured_activities=featured_activities,
            featured_counts=featured_counts,
            platform_filter=platform,
            keyword=keyword or "",
            my_accounts=accounts,
        ),
    )


@web_router.get("/activities")
def activities_page(
    request: Request,
    db: Session = Depends(get_db),
    platform_id: Optional[int] = None,
    type_id: Optional[int] = None,
    display: Optional[str] = None,
    keyword: Optional[str] = None,
    sort: str = "latest",
    page: int = 1,
):
    page = max(1, page)
    page_size = 12
    items, total = activity_service.list_public_activities(
        db,
        platform_id=platform_id,
        type_id=type_id,
        display=display,
        keyword=keyword,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    platforms = activity_service.get_active_platforms(db)
    types = activity_service.get_active_types(db)
    counts = activity_service.comment_counts(db, [a.id for a in items])
    total_pages = (total + page_size - 1) // page_size if total else 0
    return templates.TemplateResponse(
        request,
        "activities.html",
        _ctx(
            request,
            db,
            activities=items,
            total=total,
            counts=counts,
            platforms=platforms,
            types=types,
            platform_id=platform_id,
            type_id=type_id,
            display=display,
            keyword=keyword or "",
            sort=sort,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        ),
    )


@web_router.get("/activities/{activity_id}")
def activity_detail(request: Request, activity_id: int, db: Session = Depends(get_db)):
    activity = activity_service.get_public_activity(db, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="活动不存在或未发布")
    activity.view_count += 1
    db.commit()
    entries = activity_service.get_entries(db, activity_id)
    entry_states = {e.id: activity_service.entry_is_available(e) for e in entries}
    display_status = activity_service.compute_display_status(activity)
    comment_count = activity_service.comment_counts(db, [activity_id]).get(activity_id, 0)
    content_html = render_markdown(activity.content)
    risk_html = render_markdown(activity.risk_notice)
    top_comments, reply_map = activity_comment_service.list_public_comments(db, activity_id)
    return templates.TemplateResponse(
        request,
        "activity_detail.html",
        _ctx(
            request,
            db,
            activity=activity,
            entries=entries,
            entry_states=entry_states,
            display_status=display_status,
            comment_count=comment_count,
            content_html=content_html,
            risk_html=risk_html,
            comments=top_comments,
            reply_map=reply_map,
        ),
    )


@web_router.get("/feedback")
def feedback_page(request: Request, db: Session = Depends(get_db)):
    categories = feedback_service.get_active_categories(db)
    return templates.TemplateResponse(request, "feedback.html", _ctx(request, db, categories=categories))


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
def login_page(
    request: Request,
    db: Session = Depends(get_db),
    next_url: str = Query(None, alias="next"),
    error: str = Query(""),
):
    user = get_current_user_optional(request, db)
    # 管理员已登录：直接进后台
    if user and user.role == UserRole.ADMIN.value:
        return RedirectResponse(url="/admin", status_code=302)
    # 已登录的非管理员：若目标不是进入后台则回首页；否则停留在登录页，方便切换管理员账号
    if user and next_url != "/admin":
        return RedirectResponse(url="/", status_code=302)
    if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/admin"
    return templates.TemplateResponse(request, "login.html", _ctx(request, db, next_url=next_url, error=error))


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
    post.view_count += 1
    db.commit()

    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post_id, Comment.status == CommentStatus.ACTIVE.value)
        .order_by(Comment.created_at.asc())
        .all()
    )
    # 分组：普通评论与互关业务线程（申请 + 回关回复）
    normal_comments: list[Comment] = []
    mutual_threads: list[dict[str, Any]] = []
    apply_map: dict[int, dict[str, Any]] = {}
    for c in comments:
        if c.comment_type == CommentType.APPLY.value:
            thread = {"apply": c, "replies": []}
            mutual_threads.append(thread)
            apply_map[c.id] = thread
        elif c.comment_type == CommentType.FOLLOW_BACK.value and c.parent_id in apply_map:
            apply_map[c.parent_id]["replies"].append(c)
        else:
            normal_comments.append(c)

    current_user = get_current_user_optional(request, db)
    uid = current_user.id if current_user else None

    # 点赞数据：帖子 + 所有评论/互关节点
    comment_ids = [c.id for c in comments]
    post_like_count = like_service.like_counts(db, LIKE_TARGET_POST, [post.id]).get(post.id, 0)
    comment_like_counts = like_service.like_counts(db, LIKE_TARGET_COMMENT, comment_ids)
    post_liked = uid is not None and post.id in like_service.liked_ids(db, uid, LIKE_TARGET_POST, [post.id])
    comment_liked_ids = like_service.liked_ids(db, uid, LIKE_TARGET_COMMENT, comment_ids)

    # 评价数据：每个已完成的互关线程附带双方评价与可评价状态
    reviews_by_apply: dict[int, list[Review]] = {}
    apply_ids = [t["apply"].id for t in mutual_threads]
    if apply_ids:
        for r in db.query(Review).filter(Review.apply_comment_id.in_(apply_ids)).all():
            reviews_by_apply.setdefault(r.apply_comment_id, []).append(r)

    for thread in mutual_threads:
        apply = thread["apply"]
        thread["completed"] = len(thread["replies"]) > 0
        thread["reviews"] = reviews_by_apply.get(apply.id, [])
        my_review = next((r for r in thread["reviews"] if r.reviewer_id == uid), None) if uid else None
        reviewee_id = None
        can_review = False
        if uid is not None and thread["completed"] and my_review is None:
            if uid == post.user_id and uid != apply.user_id:
                can_review = True
                reviewee_id = apply.user_id
            elif uid == apply.user_id and uid != post.user_id:
                can_review = True
                reviewee_id = post.user_id
        thread["can_review"] = can_review
        thread["reviewee_id"] = reviewee_id
        thread["my_review"] = my_review

    return templates.TemplateResponse(
        request,
        "post_detail.html",
        _ctx(
            request,
            db,
            post=post,
            comments=normal_comments,
            mutual_threads=mutual_threads,
            total_comments=len(comments),
            post_like_count=post_like_count,
            post_liked=post_liked,
            comment_like_counts=comment_like_counts,
            comment_liked_ids=comment_liked_ids,
        ),
    )


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
        "pending_reports": db.query(func.count(Report.id)).filter(Report.status == ReportStatus.PENDING.value).scalar() or 0,
    }
    reports = db.query(Report).order_by(Report.created_at.desc()).limit(50).all()
    users = db.query(User).order_by(User.created_at.desc()).limit(100).all()
    pending_activities = (
        db.query(Activity)
        .filter(Activity.status == ActivityStatus.PENDING.value, Activity.deleted_at.is_(None))
        .order_by(Activity.created_at.asc())
        .limit(100)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "admin.html",
        _ctx(request, db, dashboard=dashboard, reports=reports, users=users, pending_activities=pending_activities),
    )


@web_router.get("/agreement")
def agreement(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "legal.html", _ctx(request, db, title="用户协议", body="用户协议初始模板内容……"))


@web_router.get("/privacy")
def privacy(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "legal.html", _ctx(request, db, title="隐私政策", body="隐私政策初始模板内容……"))
