"""API 路由聚合。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api import accounts, admin, auth, comments, evidence, mutual_requests, notifications, posts, reports, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(accounts.router)
api_router.include_router(posts.router)
api_router.include_router(comments.router)
api_router.include_router(mutual_requests.router)
api_router.include_router(evidence.router)
api_router.include_router(notifications.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)
