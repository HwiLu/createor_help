"""认证服务：微信 OAuth 登录（含开发 Mock）。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_state, sign_session
from app.models.enums import UserRole, UserStatus
from app.models.user import User

logger = logging.getLogger("creatorhub")

WECHAT_AUTHORIZE_URL = "https://open.weixin.qq.com/connect/qrconnect"
WECHAT_ACCESS_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WECHAT_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"


def _state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.APP_SECRET_KEY, salt="wechat-oauth-state")


def create_oauth_state() -> str:
    raw = generate_state()
    return _state_serializer().dumps({"state": raw})


def verify_oauth_state(token: str) -> bool:
    try:
        _state_serializer().loads(token, max_age=600)
        return True
    except (BadSignature, SignatureExpired):
        return False


def build_wechat_login_url() -> str:
    params = {
        "appid": settings.WECHAT_APP_ID,
        "redirect_uri": settings.WECHAT_REDIRECT_URI,
        "response_type": "code",
        "scope": "snsapi_login",
        "state": create_oauth_state(),
    }
    return f"{WECHAT_AUTHORIZE_URL}?{urlencode(params)}#wechat_redirect"


def wechat_oauth_callback(code: str, db: Session) -> User:
    """用授权码换取 openid，并登录或创建用户。"""
    params = {
        "appid": settings.WECHAT_APP_ID,
        "secret": settings.WECHAT_APP_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    }
    resp = httpx.get(WECHAT_ACCESS_TOKEN_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if "errcode" in data and data.get("errcode") != 0:
        raise RuntimeError(f"微信登录失败: {data.get('errmsg')}")

    openid = data.get("openid")
    unionid = data.get("unionid")
    if not openid:
        raise RuntimeError("微信返回缺少 openid")

    user = db.query(User).filter(User.wechat_openid == openid).first()
    if user is None:
        user = User(wechat_openid=openid, wechat_unionid=unionid, role=UserRole.USER.value)
        db.add(user)
        db.commit()
        db.refresh(user)

    # 可选拉取昵称头像（scope 为 snsapi_login 时可用）
    access_token = data.get("access_token")
    if access_token:
        try:
            info = httpx.get(
                WECHAT_USERINFO_URL,
                params={"access_token": access_token, "openid": openid},
                timeout=10,
            ).json()
            if "errcode" not in info:
                if not user.nickname or user.nickname == "创作者":
                    user.nickname = info.get("nickname", "创作者")[:30]
                user.avatar_url = info.get("headimgurl")
        except Exception as exc:  # noqa: BLE001
            logger.warning("拉取微信用户信息失败: %s", exc)

    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return user


def mock_login(openid: str, nickname: str, db: Session) -> User:
    """开发环境 Mock 登录。生产环境禁止。"""
    if not settings.mock_login_available:
        raise RuntimeError("Mock 登录未启用")
    if not openid:
        openid = "mock_default"
    user = db.query(User).filter(User.wechat_openid == f"mock:{openid}").first()
    if user is None:
        user = User(
            wechat_openid=f"mock:{openid}",
            nickname=nickname or "Mock 用户",
            role=UserRole.USER.value,
            status=UserStatus.ACTIVE.value,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif nickname and user.nickname == "创作者":
        user.nickname = nickname
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return user


def make_session_cookie(user_id: int) -> str:
    return sign_session(user_id)
