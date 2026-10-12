"""帖子评论图片服务：公开可读、路径安全、格式校验。"""
from __future__ import annotations

import re
import secrets
from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings
from app.services.activity_image_service import validate_image

# 只允许形如 <hex>.jpg 的文件名，防止路径穿越
_KEY_RE = re.compile(r"^[a-f0-9]{32}\.(jpg|jpeg|png|webp)$")


def _upload_dir() -> Path:
    d = Path(settings.UPLOAD_DIR) / "comment_images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_comment_image(data: bytes, filename: str | None = None) -> str:
    """保存评论图片，返回公开读取用的 storage key。"""
    fmt, _ = validate_image(data)
    ext_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
    ext = ext_map.get(fmt, ".jpg")
    key = f"{secrets.token_hex(16)}{ext}"
    (_upload_dir() / key).write_bytes(data)
    return key


def read_comment_image(key: str) -> tuple[str, bytes]:
    """按 key 读取图片，返回 (media_type, data)。仅允许合法 key。"""
    if not _KEY_RE.match(key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片不存在")
    path = _upload_dir() / key
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片不存在")
    ext = Path(key).suffix.lower().lstrip(".")
    media = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        ext, "application/octet-stream"
    )
    return media, path.read_bytes()
