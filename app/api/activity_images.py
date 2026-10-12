"""活动图片公开读取接口（封面/二维码）。"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from app.services.activity_image_service import read_activity_image

router = APIRouter(tags=["activity-images"])


@router.get("/activity-images/{key}")
def get_activity_image(key: str):
    media_type, data = read_activity_image(key)
    return Response(
        content=data,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )
