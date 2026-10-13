"""FastAPI 应用入口。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import settings
from app.core.logging import RequestContextMiddleware, setup_logging
from app.core.middleware import CSRFMiddleware
from app.db.base import Base
from app.db.session import engine
from app.web import web_router

logger = logging.getLogger("creatorhub")

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # 生产环境安全配置校验：弱密钥/弱密码/不安全 Cookie 直接拒绝启动
    settings.validate_security_settings()
    # 本地开发：自动建表（SQLite 快速启动）；生产请使用 `alembic upgrade head`
    if settings.APP_ENV != "production":
        import app.models  # noqa: F401  确保模型已注册

        Base.metadata.create_all(bind=engine)
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

    # 幂等初始化活动平台/类型/反馈分类字典（迁移与 create_all 两种建表路径均兜底）
    from app.db.session import SessionLocal
    from app.services import activity_service

    with SessionLocal() as db:
        activity_service.ensure_activity_dictionaries(db)

    logger.info("CreatorHub 启动，环境=%s", settings.APP_ENV)
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(CSRFMiddleware)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """统一安全响应头：防点击劫持、MIME 嗅探、侧信道泄露。"""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response


app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(api_router)
app.include_router(web_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("未处理异常: %s", exc)
    # 生产环境不向客户端泄露内部异常类型/堆栈信息
    if settings.is_production:
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误", "error": type(exc).__name__})


@app.get("/healthz")
def healthz():
    return {"status": "ok", "env": settings.APP_ENV}
