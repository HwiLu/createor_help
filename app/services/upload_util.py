"""上传文件读取工具：限制读取大小，避免一次性读入超大文件导致内存耗尽（DoS）。"""
from __future__ import annotations

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


def read_upload_limited(file: UploadFile, max_size: int | None = None) -> bytes:
    """受限读取上传文件内容，超过上限抛 413。

    仅多读 1 字节用于判断是否超限，避免大文件整块载入内存。
    """
    limit = max_size if max_size is not None else settings.MAX_UPLOAD_SIZE
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="文件超过大小限制",
        )
    return data
