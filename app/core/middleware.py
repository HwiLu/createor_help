"""CSRF 防护中间件（Double-Submit Cookie 方案）。

原理：
- 首次响应时下发一个非 HttpOnly 的 ``csrf_token`` Cookie（前端可读）。
- 前端 fetch 对写请求自动回填 ``X-CSRF-Token`` 请求头。
- 中间件对受保护路径的写请求恒定时间比对两者，不一致则拒绝。

已豁免登录类接口（无会话状态，另有暴力破解限流防护）。
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.security import CSRF_COOKIE_NAME, generate_csrf_token, verify_csrf_token

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
# 无需 CSRF 保护的写接口（登录类，尚未建立会话）
_EXEMPT_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/mock-login",
    "/api/v1/auth/wechat/",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME, "")

        if request.method not in _SAFE_METHODS and self._requires_csrf(path):
            header_token = request.headers.get("X-CSRF-Token", "")
            if not verify_csrf_token(cookie_token, header_token):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF 校验失败，请刷新页面后重试"},
                )

        response = await call_next(request)

        # 首次访问（无 token）时下发；静态资源不设置
        if not path.startswith("/static") and not cookie_token:
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=generate_csrf_token(),
                httponly=False,
                secure=settings.SESSION_COOKIE_SECURE,
                samesite=settings.SESSION_COOKIE_SAMESITE,
                path="/",
                max_age=30 * 24 * 3600,
            )
        return response

    @staticmethod
    def _requires_csrf(path: str) -> bool:
        if not path.startswith("/api/"):
            return False
        return not any(path.startswith(p) for p in _EXEMPT_PREFIXES)
