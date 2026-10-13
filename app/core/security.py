"""安全相关工具：会话签名、随机 token、CSRF token。"""
from __future__ import annotations

import hmac
import secrets
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings

# CSRF Cookie 名：前端从 Cookie 读取并回填到 X-CSRF-Token 请求头（double-submit 方案）
CSRF_COOKIE_NAME = "csrf_token"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.APP_SECRET_KEY, salt="creatorhub-session")


def sign_session(user_id: int) -> str:
    return _serializer().dumps({"uid": user_id})


def verify_session(token: str) -> Optional[int]:
    try:
        data = _serializer().loads(token, max_age=30 * 24 * 3600)
        return int(data.get("uid"))
    except (BadSignature, SignatureExpired, TypeError, ValueError):
        return None


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    """生成 CSRF 随机令牌（double-submit cookie，无需服务端存储）。"""
    return secrets.token_urlsafe(32)


def verify_csrf_token(cookie_value: Optional[str], header_value: Optional[str]) -> bool:
    """恒定时间比较 Cookie 与请求头中的 CSRF 令牌。"""
    if not cookie_value or not header_value:
        return False
    return hmac.compare_digest(cookie_value, header_value)
