"""安全相关工具：会话签名、随机 token。"""
from __future__ import annotations

import secrets
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import settings


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
