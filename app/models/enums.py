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


class CommentType(StrEnum):
    """评论区业务类型：普通评论 / 互关申请 / 回关回复。"""

    COMMENT = "COMMENT"
    APPLY = "APPLY"
    FOLLOW_BACK = "FOLLOW_BACK"


COMMENT_TYPE_LABELS = {
    CommentType.COMMENT: "评论",
    CommentType.APPLY: "互关申请",
    CommentType.FOLLOW_BACK: "已回关",
}


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
    COMMENT = "COMMENT"
    EVALUATION = "EVALUATION"
    CREDIT = "CREDIT"


class CreatorCategory(StrEnum):
    """优秀博主展示的主题板块（固定顺序）。"""

    BEAUTY = "BEAUTY"
    FITNESS = "FITNESS"
    LIFESTYLE = "LIFESTYLE"
    FOOTBALL = "FOOTBALL"
    WORK = "WORK"
    TRAVEL = "TRAVEL"
    GAMING = "GAMING"


CREATOR_CATEGORY_LABELS = {
    CreatorCategory.BEAUTY: "美妆",
    CreatorCategory.FITNESS: "健身",
    CreatorCategory.LIFESTYLE: "生活",
    CreatorCategory.FOOTBALL: "足球",
    CreatorCategory.WORK: "工作",
    CreatorCategory.TRAVEL: "旅游",
    CreatorCategory.GAMING: "游戏",
}


# ---------------------------------------------------------------------------
# 薅羊毛活动模块
# ---------------------------------------------------------------------------


class ActivityStatus(StrEnum):
    """活动管理状态（后台控制，与展示态分离）。"""

    PENDING = "PENDING"
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    OFFLINE = "OFFLINE"
    REJECTED = "REJECTED"


ACTIVITY_STATUS_LABELS = {
    ActivityStatus.PENDING: "待审批",
    ActivityStatus.DRAFT: "草稿",
    ActivityStatus.PUBLISHED: "已发布",
    ActivityStatus.OFFLINE: "已下架",
    ActivityStatus.REJECTED: "已拒绝",
}


class ActivityDisplayStatus(StrEnum):
    """活动展示态（由 status + 起止时间实时计算，避免人工填写的状态失真）。"""

    ONGOING = "ONGOING"
    UPCOMING = "UPCOMING"
    ENDED = "ENDED"


ACTIVITY_DISPLAY_STATUS_LABELS = {
    ActivityDisplayStatus.ONGOING: "进行中",
    ActivityDisplayStatus.UPCOMING: "即将开始",
    ActivityDisplayStatus.ENDED: "已结束",
}


class ActivityEntryType(StrEnum):
    QR_IMAGE = "QR_IMAGE"
    LINK = "LINK"


ACTIVITY_ENTRY_TYPE_LABELS = {
    ActivityEntryType.QR_IMAGE: "二维码",
    ActivityEntryType.LINK: "链接",
}


class ActivityCommentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    HIDDEN = "HIDDEN"
    DELETED = "DELETED"


class ActivityReportStatus(StrEnum):
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


# ---------------------------------------------------------------------------
# 意见反馈模块
# ---------------------------------------------------------------------------


class FeedbackStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


FEEDBACK_STATUS_LABELS = {
    FeedbackStatus.PENDING: "待处理",
    FeedbackStatus.PROCESSING: "处理中",
    FeedbackStatus.RESOLVED: "已处理",
    FeedbackStatus.REJECTED: "不予处理",
}


# 反馈状态机允许的流转（管理员操作）
FEEDBACK_STATE_TRANSITIONS: dict[FeedbackStatus, set[FeedbackStatus]] = {
    FeedbackStatus.PENDING: {
        FeedbackStatus.PROCESSING,
        FeedbackStatus.RESOLVED,
        FeedbackStatus.REJECTED,
    },
    FeedbackStatus.PROCESSING: {
        FeedbackStatus.RESOLVED,
        FeedbackStatus.REJECTED,
        FeedbackStatus.PENDING,
    },
    FeedbackStatus.RESOLVED: set(),
    FeedbackStatus.REJECTED: set(),
}


class EmailDeliveryStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


EMAIL_DELIVERY_STATUS_LABELS = {
    EmailDeliveryStatus.PENDING: "待发送",
    EmailDeliveryStatus.SENT: "已发送",
    EmailDeliveryStatus.FAILED: "发送失败",
    EmailDeliveryStatus.UNKNOWN: "状态待确认",
}
