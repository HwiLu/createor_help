"""Pydantic 请求/响应校验模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import EvidenceType, MutualType, Platform, ReportTargetType


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=30)
    avatar_url: Optional[str] = Field(default=None, max_length=512)
    bio: Optional[str] = Field(default=None, max_length=200)


class AccountCreate(BaseModel):
    platform: Platform
    account_name: str = Field(min_length=1, max_length=64)
    profile_url: Optional[str] = Field(default=None, max_length=512)
    bio: Optional[str] = Field(default=None, max_length=200)
    category: Optional[str] = Field(default=None, max_length=64)
    follower_range: Optional[str] = Field(default=None, max_length=64)


class AccountUpdate(BaseModel):
    platform: Optional[Platform] = None
    account_name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    profile_url: Optional[str] = Field(default=None, max_length=512)
    bio: Optional[str] = Field(default=None, max_length=200)
    category: Optional[str] = Field(default=None, max_length=64)
    follower_range: Optional[str] = Field(default=None, max_length=64)


class PostCreate(BaseModel):
    title: str = Field(min_length=5, max_length=50)
    content: str = Field(min_length=10, max_length=200)
    mutual_type: MutualType
    target_platform: Platform
    target_creator_account_id: int
    requires_follow_back: bool = True
    max_applicants: int = Field(default=10, ge=1, le=1000)
    expires_at: Optional[datetime] = None
    category: Optional[str] = Field(default=None, max_length=64)


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=5, max_length=50)
    content: Optional[str] = Field(default=None, min_length=10, max_length=200)
    category: Optional[str] = Field(default=None, max_length=64)
    max_applicants: Optional[int] = Field(default=None, ge=1, le=1000)
    expires_at: Optional[datetime] = None

    @field_validator("title", "content")
    @classmethod
    def strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class ApplicationCreate(BaseModel):
    applicant_creator_account_id: int
    application_message: Optional[str] = Field(default=None, max_length=500)
    evidence_type: EvidenceType = EvidenceType.SCREENSHOT


class EvidenceReview(BaseModel):
    accept: bool
    reason: Optional[str] = Field(default=None, max_length=500)


class ResubmitEvidence(BaseModel):
    evidence_type: EvidenceType = EvidenceType.SCREENSHOT


class DisputeCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ReportCreate(BaseModel):
    target_type: ReportTargetType
    target_id: int
    reason: str = Field(min_length=1, max_length=128)
    description: Optional[str] = Field(default=None, max_length=1000)


class ReportResolve(BaseModel):
    resolution: str = Field(min_length=1, max_length=1000)
    status: str = Field(default="RESOLVED")


class AdminRestrict(BaseModel):
    action: str = Field(default="RESTRICT")
    reason: str = Field(min_length=1, max_length=1000)
