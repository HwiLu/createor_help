"""业务枚举定义。数据库以字符串存储，代码中以枚举保证类型安全。"""
from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class Platform(StrEnum):
    DOUYIN = "DOUYIN"
    XIAOHONGSHU = "XIAOHONGSHU"
    BILIBILI = "BILIBILI"
    WECHAT_OFFICIAL_ACCOUNT = "WECHAT_OFFICIAL_ACCOUNT"
    WECHAT_CHANNEL = "WECHAT_CHANNEL"
    OTHER = "OTHER"


PLATFORM_LABELS = {
    Platform.DOUYIN: "抖音",
    Platform.XIAOHONGSHU: "小红书",
    Platform.BILIBILI: "B站",
    Platform.WECHAT_OFFICIAL_ACCOUNT: "微信公众号",
    Platform.WECHAT_CHANNEL: "微信视频号",
    Platform.OTHER: "其他",
}


class UserRole(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RESTRICTED = "RESTRICTED"
    BANNED = "BANNED"
    DELETED = "DELETED"


class CreatorAccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"


class PostStatus(StrEnum):
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"
    DELETED = "DELETED"
    EXPIRED = "EXPIRED"


class MutualType(StrEnum):
    FOLLOW_FOR_FOLLOW = "FOLLOW_FOR_FOLLOW"
    LIKE_FOR_LIKE = "LIKE_FOR_LIKE"
    COMMENT_FOR_COMMENT = "COMMENT_FOR_COMMENT"
    OTHER = "OTHER"


MUTUAL_TYPE_LABELS = {
    MutualType.FOLLOW_FOR_FOLLOW: "互关",
    MutualType.LIKE_FOR_LIKE: "互赞",
    MutualType.COMMENT_FOR_COMMENT: "互评",
    MutualType.OTHER: "其他",
}


class MutualRequestStatus(StrEnum):
    PENDING_REVIEW = "PENDING_REVIEW"
    EVIDENCE_REJECTED = "EVIDENCE_REJECTED"
    WAITING_RETURN = "WAITING_RETURN"
    RETURNED_PENDING_CONFIRMATION = "RETURNED_PENDING_CONFIRMATION"
    COMPLETED = "COMPLETED"
    DISPUTED = "DISPUTED"
    CANCELLED = "CANCELLED"


REQUEST_STATUS_LABELS = {
    MutualRequestStatus.PENDING_REVIEW: "待核验",
    MutualRequestStatus.EVIDENCE_REJECTED: "证据被拒绝",
    MutualRequestStatus.WAITING_RETURN: "等待回关",
    MutualRequestStatus.RETURNED_PENDING_CONFIRMATION: "已声明回关，待确认",
    MutualRequestStatus.COMPLETED: "已完成",
    MutualRequestStatus.DISPUTED: "争议处理中",
    MutualRequestStatus.CANCELLED: "已取消",
}


# 状态机允许的后续状态
REQUEST_STATE_TRANSITIONS: dict[MutualRequestStatus, set[MutualRequestStatus]] = {
    MutualRequestStatus.PENDING_REVIEW: {
        MutualRequestStatus.WAITING_RETURN,
        MutualRequestStatus.EVIDENCE_REJECTED,
        MutualRequestStatus.CANCELLED,
    },
    MutualRequestStatus.EVIDENCE_REJECTED: {
        MutualRequestStatus.PENDING_REVIEW,
        MutualRequestStatus.CANCELLED,
    },
    MutualRequestStatus.WAITING_RETURN: {
        MutualRequestStatus.RETURNED_PENDING_CONFIRMATION,
        MutualRequestStatus.DISPUTED,
    },
    MutualRequestStatus.RETURNED_PENDING_CONFIRMATION: {
        MutualRequestStatus.COMPLETED,
        MutualRequestStatus.DISPUTED,
    },
    MutualRequestStatus.COMPLETED: set(),
    MutualRequestStatus.DISPUTED: {
        MutualRequestStatus.COMPLETED,
        MutualRequestStatus.CANCELLED,
    },
    MutualRequestStatus.CANCELLED: set(),
}


class EvidenceType(StrEnum):
    SCREENSHOT = "SCREENSHOT"
    OTHER = "OTHER"


class CommentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    HIDDEN = "HIDDEN"
    DELETED = "DELETED"


class ReportTargetType(StrEnum):
    POST = "POST"
    COMMENT = "COMMENT"
    MUTUAL_REQUEST = "MUTUAL_REQUEST"
    USER = "USER"


class ReportStatus(StrEnum):
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class NotificationType(StrEnum):
    NEW_APPLICATION = "NEW_APPLICATION"
    EVIDENCE_ACCEPTED = "EVIDENCE_ACCEPTED"
    EVIDENCE_REJECTED = "EVIDENCE_REJECTED"
    WAITING_RETURN_REMINDER = "WAITING_RETURN_REMINDER"
    RETURNED = "RETURNED"
    COMPLETED = "COMPLETED"
    DISPUTE_RESULT = "DISPUTE_RESULT"
    ADMIN = "ADMIN"
