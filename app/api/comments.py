from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_user_optional
from app.core.rate_limit import comment_limiter
from app.db.session import get_db
from app.models.comment import Comment
from app.models.enums import CommentStatus, CommentType, NotificationType
from app.models.post import Post
from app.models.user import User
from app.schemas import CommentCreate
from app.services import comment_image_service, credit_service, upload_util
from app.services.notification_service import notify

router = APIRouter(prefix="/posts/{post_id}/comments", tags=["comments"])


def _json(c: Comment) -> dict:
    return {
        "id": c.id,
        "post_id": c.post_id,
        "user_id": c.user_id,
        "content": c.content,
        "parent_id": c.parent_id,
        "image_key": c.image_key,
        "image_url": f"/api/v1/posts/{c.post_id}/comments/image/{c.image_key}" if c.image_key else None,
        "comment_type": c.comment_type,
        "created_at": c.created_at,
        "author": {"id": c.author.id, "nickname": c.author.nickname, "avatar_url": c.author.avatar_url},
    }


@router.get("")
def list_comments(
    post_id: int,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    _: Optional[User] = Depends(get_current_user_optional),
):
    query = db.query(Comment).filter(Comment.post_id == post_id, Comment.status == CommentStatus.ACTIVE.value)
    total = query.count()
    comments = query.order_by(Comment.created_at.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_json(c) for c in comments], "total": total, "page": page, "page_size": page_size}


@router.post("/image")
def upload_comment_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    data = upload_util.read_upload_limited(file)
    key = comment_image_service.save_comment_image(data, file.filename)
    return {"key": key}


@router.get("/image/{key}")
def get_comment_image(key: str):
    media_type, data = comment_image_service.read_comment_image(key)
    return Response(
        content=data,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )


@router.post("")
def create_comment(
    post_id: int,
    data: CommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not comment_limiter.allow(f"comment:{user.id}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="操作过于频繁，请稍后再试",
        )
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")

    content = data.content.strip() if data.content else ""
    image_key = data.image_key
    comment_type = (data.comment_type or CommentType.COMMENT.value).upper()
    parent_id = data.parent_id
    applicant_id = None

    if not content and not image_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="评论内容或图片至少填写一项")

    if comment_type == CommentType.APPLY.value:
        if post.user_id == user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能在自己的帖子下申请互关")
        if not image_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="申请互关需上传关注证据截图")
        parent_id = None
        existing = (
            db.query(Comment)
            .filter(
                Comment.post_id == post_id,
                Comment.user_id == user.id,
                Comment.comment_type == CommentType.APPLY.value,
                Comment.status == CommentStatus.ACTIVE.value,
            )
            .first()
        )
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="你已提交过互关申请，请等待发帖人处理")
    elif comment_type == CommentType.FOLLOW_BACK.value:
        if post.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有发帖人可以回复回关")
        if not parent_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少要回复的申请")
        if not image_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="回关需上传回关证据截图")
        parent = db.get(Comment, parent_id)
        if parent is None or parent.comment_type != CommentType.APPLY.value or parent.post_id != post_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的申请评论")
        applicant_id = parent.user_id
        existing = (
            db.query(Comment)
            .filter(
                Comment.post_id == post_id,
                Comment.user_id == user.id,
                Comment.comment_type == CommentType.FOLLOW_BACK.value,
                Comment.parent_id == parent_id,
            )
            .first()
        )
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="你已回复过该申请")
    else:
        comment_type = CommentType.COMMENT.value
        parent_id = None

    comment = Comment(
        post_id=post_id,
        user_id=user.id,
        content=content,
        image_key=image_key,
        comment_type=comment_type,
        parent_id=parent_id,
        status=CommentStatus.ACTIVE.value,
    )
    db.add(comment)
    db.flush()

    credit_gained = None
    if comment_type == CommentType.APPLY.value:
        notify(
            db,
            post.user_id,
            NotificationType.NEW_APPLICATION,
            "新的互关申请",
            f"{user.nickname} 向你发起了互关申请",
            "COMMENT",
            comment.id,
        )
        # 申请者提交关注证据后立即 +10（无需等待对方回关）
        credit_gained = credit_service.apply_evidence_credit(db, user.id, comment.id)
    elif comment_type == CommentType.FOLLOW_BACK.value and applicant_id is not None:
        notify(
            db,
            applicant_id,
            NotificationType.COMPLETED,
            "对方已回关",
            f"{user.nickname} 已回关，互关业务已完成",
            "COMMENT",
            comment.id,
        )
        credit_gained = credit_service.complete_mutual(db, post, parent_id)
    else:
        if post.user_id != user.id:
            notify(
                db,
                post.user_id,
                NotificationType.COMMENT,
                "收到新评论",
                f"{user.nickname} 评论了你的帖子",
                "COMMENT",
                comment.id,
            )

    db.commit()
    db.refresh(comment)
    result = _json(comment)
    result["credit_gained"] = credit_gained
    return result
