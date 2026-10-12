"""活动封面 / 二维码图片服务：公开可读、路径安全、格式校验。"""
from __future__ import annotations

import io
import re
import secrets
from pathlib import Path

from fastapi import HTTPException, status
from PIL import Image

from app.core.config import settings

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# 只允许形如 <hex>.jpg 的文件名，防止路径穿越
_KEY_RE = re.compile(r"^[a-f0-9]{32}\.(jpg|jpeg|png|webp)$")


def _upload_dir() -> Path:
    d = Path(settings.UPLOAD_DIR) / "activity_images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def validate_image(data: bytes) -> tuple[str, tuple[int, int]]:
    """校验图片真实格式与尺寸，返回 (format, (width, height))。"""
    if len(data) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="图片超过大小限制")
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        fmt = (img.format or "").upper()
        if fmt not in ALLOWED_FORMATS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的图片格式")
        img2 = Image.open(io.BytesIO(data))
        width, height = img2.size
        if width > 10000 or height > 10000:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片分辨率过大")
        return fmt, (width, height)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件不是有效的图片") from exc


def save_activity_image(data: bytes, filename: str | None) -> str:
    """保存活动图片，返回存储 key（公开读取用）。"""
    ext = ".jpg"
    if filename:
        name = filename.lower()
        for e in (".png", ".webp", ".jpeg", ".jpg"):
            if name.endswith(e):
                ext = e
                break
    fmt, _ = validate_image(data)
    ext_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
    ext = ext_map.get(fmt, ext)

    key = f"{secrets.token_hex(16)}{ext}"
    (_upload_dir() / key).write_bytes(data)
    return key


def read_activity_image(key: str) -> tuple[str, bytes]:
    """按 key 读取图片，返回 (media_type, data)。仅允许合法 key。"""
    if not _KEY_RE.match(key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片不存在")
    path = _upload_dir() / key
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片不存在")
    ext = Path(key).suffix.lower()
    media = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        ext.lstrip("."), "application/octet-stream"
    )
    return media, path.read_bytes()
