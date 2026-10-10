"""帖子服务：创建、编辑、关闭、删除与列表筛选。"""
from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import utcnow
from app.models.creator_account import CreatorAccount
from app.models.enums import CreatorAccountStatus, MutualType, NotificationType, PostStatus
from app.models.mutual_request import MutualRequest
from app.models.post import Post
from app.models.user import User
from app.schemas import PostCreate, PostUpdate
from app.services.audit_service import write_audit
from app.services.notification_service import notify


def create_post(db: Session, user: User, data: PostCreate) -> Post:
    account = db.get(CreatorAccount, data.target_creator_account_id)
    if account is None or account.user_id != user.id or account.status == CreatorAccountStatus.DELETED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="目标自媒体账号无效或不属于当前用户")

    # 不要求回关的帖子不得宣传为互关
    if data.mutual_type == MutualType.FOLLOW_FOR_FOLLOW and not data.requires_follow_back:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="互关类型帖子必须要求回关")

    # 重复检测：同一用户 + 同一平台 + 标题或内容相同，拒绝重复发布
    duplicate = (
        db.query(Post)
        .filter(
            Post.user_id == user.id,
            Post.target_platform == data.target_platform.value,
            Post.status != PostStatus.DELETED.value,
            or_(Post.title == data.title.strip(), Post.content == data.content.strip()),
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="已存在标题或内容相同的互助帖子，请勿重复发布",
        )

    post = Post(
        user_id=user.id,
        title=data.title.strip(),
        content=data.content.strip(),
        mutual_type=data.mutual_type.value,
        target_platform=data.target_platform.value,
        target_creator_account_id=data.target_creator_account_id,
        requires_follow_back=data.requires_follow_back,
        max_applicants=data.max_applicants,
        expires_at=data.expires_at,
        category=data.category,
        status=PostStatus.PUBLISHED.value,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_post(db: Session, user: User, post_id: int, data: PostUpdate) -> Post:
    post = db.get(Post, post_id)
    if post is None or post.status == PostStatus.DELETED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")
    if post.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能编辑自己的帖子")

    changed = False
    for field in ("title", "content", "category", "max_applicants", "expires_at"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(post, field, val.strip() if isinstance(val, str) else val)
            changed = True
    if changed:
        post.updated_at = utcnow()
    db.commit()
    db.refresh(post)
    return post


def close_post(db: Session, user: User, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if post is None or post.status == PostStatus.DELETED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")
    if post.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能关闭自己的帖子")
    post.status = PostStatus.CLOSED.value
    post.updated_at = utcnow()
    db.commit()
    db.refresh(post)
    return post


def delete_post(db: Session, user: User, post_id: int) -> None:
    post = db.get(Post, post_id)
    if post is None or post.status == PostStatus.DELETED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")
    if post.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能删除自己的帖子")
    # 仅逻辑删除，保留既有互助记录
    post.status = PostStatus.DELETED.value
    post.updated_at = utcnow()
    db.commit()


def admin_delete_post(db: Session, admin: User, post_id: int, reason: str) -> Post:
    """管理员删除违规帖子：软删除 + 审计日志 + 通知作者。"""
    post = db.get(Post, post_id)
    if post is None or post.status == PostStatus.DELETED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在或已删除")
    post.status = PostStatus.DELETED.value
    post.updated_at = utcnow()
    write_audit(db, admin.id, "ADMIN_DELETE_POST", "POST", post.id, reason=reason)
    notify(
        db,
        post.user_id,
        NotificationType.ADMIN,
        "帖子已被删除",
        f"你的帖子「{post.title}」因违规被删除。原因：{reason}",
        "POST",
        post.id,
    )
    db.commit()
    db.refresh(post)
    return post


def list_posts(
    db: Session,
    platform: str | None,
    category: str | None,
    keyword: str | None,
    status_filter: str | None,
    page: int,
    page_size: int,
) -> tuple[list[Post], int]:
    query = db.query(Post).filter(Post.status != PostStatus.DELETED.value)
    if status_filter:
        query = query.filter(Post.status == status_filter)
    else:
        query = query.filter(Post.status.in_([PostStatus.PUBLISHED.value, PostStatus.CLOSED.value, PostStatus.EXPIRED.value]))
    if platform and platform.upper() != "ALL":
        query = query.filter(Post.target_platform == platform.upper())
    if category:
        query = query.filter(Post.category == category)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(Post.title.like(like), Post.content.like(like)))

    total = query.count()
    posts = (
        query.order_by(Post.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return posts, total


def get_post(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if post is None or post.status == PostStatus.DELETED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")
    # 自动标记过期
    if post.status == PostStatus.PUBLISHED.value and post.expires_at is not None and post.expires_at < utcnow():
        post.status = PostStatus.EXPIRED.value
        db.commit()
        db.refresh(post)
    return post


def applicant_count(db: Session, post_id: int) -> int:
    return (
        db.query(MutualRequest)
        .filter(MutualRequest.post_id == post_id, MutualRequest.status != "CANCELLED")
        .count()
    )
