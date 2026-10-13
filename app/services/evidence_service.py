"""证据文件服务：格式校验、私有存储、对象级权限访问。"""
from __future__ import annotations

import io
import os
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import EvidenceType
from app.models.evidence import EvidenceFile
from app.models.mutual_request import MutualRequest
from app.models.user import User
from app.services.upload_util import read_upload_limited

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _validate_image(data: bytes) -> tuple[str, tuple[int, int]]:
    """通过文件签名/解码验证真实格式，返回 (format, size)。"""
    if len(data) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="文件超过大小限制")
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        fmt = (img.format or "").upper()
        if fmt not in ALLOWED_FORMATS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的图片格式")
        # verify 后需重新打开获取尺寸
        img2 = Image.open(io.BytesIO(data))
        width, height = img2.size
        if width > 10000 or height > 10000:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片分辨率过大")
        return fmt, (width, height)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件不是有效的图片") from exc


def _check_extension(filename: str | None) -> str:
    if not filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少文件名")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的扩展名")
    return ext


def save_evidence(
    db: Session,
    user: User,
    request_id: int,
    file: UploadFile,
    evidence_type: EvidenceType,
    max_files: int,
) -> EvidenceFile:
    req = db.get(MutualRequest, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申请不存在")
    if req.applicant_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有申请者可以上传证据")

    data = read_upload_limited(file)
    _check_extension(file.filename)
    fmt, _ = _validate_image(data)

    existing_count = (
        db.query(EvidenceFile).filter(EvidenceFile.mutual_request_id == request_id).count()
    )
    if existing_count >= max_files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="单次申请证据数量已达上限")

    upload_dir = Path(settings.UPLOAD_DIR) / "evidence"
    upload_dir.mkdir(parents=True, exist_ok=True)

    storage_key = f"evidence/{secrets.token_hex(16)}.{fmt.lower()}"
    target = Path(settings.UPLOAD_DIR) / storage_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)

    evidence = EvidenceFile(
        mutual_request_id=request_id,
        uploaded_by_user_id=user.id,
        storage_key=storage_key,
        original_filename=file.filename[:200] if file.filename else None,
        mime_type=f"image/{fmt.lower()}",
        file_size=len(data),
        evidence_type=evidence_type.value,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def list_evidence(db: Session, user: User, request_id: int) -> list[EvidenceFile]:
    req = db.get(MutualRequest, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申请不存在")
    from app.core.permissions import can_view_evidence

    if not can_view_evidence(user, req):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限查看证据")

    return (
        db.query(EvidenceFile)
        .filter(EvidenceFile.mutual_request_id == request_id)
        .order_by(EvidenceFile.created_at.asc())
        .all()
    )


def read_evidence_file(db: Session, user: User, evidence_id: int) -> tuple[EvidenceFile, bytes]:
    evidence = db.get(EvidenceFile, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="证据不存在")

    req = db.get(MutualRequest, evidence.mutual_request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="申请不存在")

    from app.core.permissions import can_view_evidence

    if not can_view_evidence(user, req):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限查看证据")

    path = Path(settings.UPLOAD_DIR) / evidence.storage_key
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="证据文件缺失")

    return evidence, path.read_bytes()
