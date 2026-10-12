"""API 路由聚合。"""
from __future__ import annotations

from fastapi import APIRouter

from app.api import accounts, activities, activity_comments, activity_images, admin, admin_activities, admin_comments, admin_feedback, auth, comments, evidence, feedback, likes, mutual_requests, notifications, posts, reports, reviews, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(accounts.router)
api_router.include_router(posts.router)
api_router.include_router(comments.router)
api_router.include_router(likes.router)
api_router.include_router(reviews.router)
api_router.include_router(mutual_requests.router)
api_router.include_router(evidence.router)
api_router.include_router(notifications.router)
api_router.include_router(reports.router)
api_router.include_router(activities.router)
api_router.include_router(activity_comments.router)
api_router.include_router(activity_images.router)
api_router.include_router(admin_activities.router)
api_router.include_router(admin_comments.router)
api_router.include_router(admin_feedback.router)
api_router.include_router(feedback.router)
api_router.include_router(admin.router)
