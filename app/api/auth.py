from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_json(user: User) -> dict:
    return {
        "id": user.id,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "role": user.role,
        "status": user.status,
    }


@router.get("/wechat/start")
def wechat_start():
    if not settings.wechat_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="微信登录尚未配置，请完成微信开放平台配置后重试",
        )
    url = auth_service.build_wechat_login_url()
    return JSONResponse({"authorize_url": url})


@router.get("/wechat/callback")
def wechat_callback(code: str, state: str, db: Session = Depends(get_db)):
    if not settings.wechat_configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="微信登录尚未配置")
    if not auth_service.verify_oauth_state(state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="state 校验失败")

    try:
        user = auth_service.wechat_oauth_callback(code, db)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    token = auth_service.make_session_cookie(user.id)
    resp = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    resp.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=30 * 24 * 3600,
        path="/",
    )
    return resp


@router.post("/mock-login")
def mock_login(
    request: Request,
    openid: str = Form(None),
    nickname: str = Form(None),
    db: Session = Depends(get_db),
):
    if not settings.mock_login_available:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mock 登录未启用")
    # 兼容表单提交（页面）与查询参数（测试/脚本）。
    openid = openid or request.query_params.get("openid") or "mock_default"
    nickname = nickname or request.query_params.get("nickname") or "Mock 用户"
    user = auth_service.mock_login(openid, nickname, db)
    token = auth_service.make_session_cookie(user.id)
    resp = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    resp.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=30 * 24 * 3600,
        path="/",
    )
    return resp


@router.post("/login")
def login(
    username: str = Form(""),
    password: str = Form(""),
    next_url: str = Form("/admin"),
    db: Session = Depends(get_db),
):
    """管理员账号密码登录（表单提交）。成功后写入会话 Cookie 并跳转。"""
    if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/admin"
    try:
        user = auth_service.login_with_password(username, password, db)
    except RuntimeError:
        return RedirectResponse(
            url=f"/login?next={quote(next_url)}&error=1",
            status_code=status.HTTP_302_FOUND,
        )

    token = auth_service.make_session_cookie(user.id)
    resp = RedirectResponse(url=next_url, status_code=status.HTTP_302_FOUND)
    resp.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        max_age=30 * 24 * 3600,
        path="/",
    )
    return resp


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _user_json(user)


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
    return resp
