"""FastAPI 依赖：当前用户、管理员鉴权。"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_session
from app.db.session import get_db
from app.models.enums import UserRole, UserStatus
from app.models.user import User


def _read_session_token(request: Request) -> Optional[str]:
    """从请求 Cookie 读取会话令牌，兼容 Depends 注入与直接函数调用。"""
    return request.cookies.get(settings.SESSION_COOKIE_NAME)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    user = None
    session_token = _read_session_token(request)
    if session_token:
        uid = verify_session(session_token)
        if uid is not None:
            user = db.get(User, uid)

    if user is None or user.status == UserStatus.DELETED.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")

    if user.status == UserStatus.BANNED.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被封禁")

    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    session_token = _read_session_token(request)
    if not session_token:
        return None
    uid = verify_session(session_token)
    if uid is None:
        return None
    user = db.get(User, uid)
    if user is None or user.status in (UserStatus.DELETED.value, UserStatus.BANNED.value):
        return None
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user
