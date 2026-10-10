"""对象级权限校验。"""
from __future__ import annotations

from fastapi import HTTPException, status

from app.models.enums import UserRole
from app.models.mutual_request import MutualRequest
from app.models.user import User


def ensure_admin(user: User) -> None:
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")


def can_view_request(user: User, req: MutualRequest) -> bool:
    """证据查看权限：申请者、发帖人、管理员。"""
    if user.role == UserRole.ADMIN.value:
        return True
    return user.id in (req.applicant_user_id, req.poster_user_id)


def can_view_evidence(user: User, req: MutualRequest) -> bool:
    return can_view_request(user, req)
