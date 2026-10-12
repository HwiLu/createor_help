"""邮件发送服务：smtplib 标准库发送 + 投递日志 + 手动重试。

SMTP 密码仅从环境变量读取，不入源码、不入库、不返回前端。
邮件发送与反馈写入解耦：发送失败不回滚反馈记录。
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import utcnow
from app.models.email_delivery_log import EmailDeliveryLog
from app.models.enums import EmailDeliveryStatus
from app.models.feedback import Feedback
from app.models.system_setting import SystemSetting


def get_setting(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return row.value if row and row.value is not None else default


def set_setting(db: Session, key: str, value: Optional[str], description: Optional[str] = None) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if row is None:
        row = SystemSetting(key=key, value=value, description=description)
        db.add(row)
    else:
        row.value = value
        if description:
            row.description = description
    db.commit()


def email_enabled(db: Session) -> bool:
    """邮件开关：默认关闭，避免未配置 SMTP 时误报成功。"""
    value = get_setting(db, "email_notifications_enabled", "false")
    return str(value).lower() in ("true", "1", "yes", "on")


def get_recipient_email(db: Session) -> Optional[str]:
    recipient = get_setting(db, "feedback_recipient_email")
    return recipient or None


def _subject_prefix(db: Session) -> str:
    return get_setting(db, "email_subject_prefix", "") or ""


def _build_email(feedback: Feedback, recipient: str) -> tuple[str, str]:
    prefix = ""
    subject = f"[CreatorHub 反馈] {feedback.title}"
    body_lines = [
        f"收到一条新的用户反馈：",
        f"",
        f"分类：{feedback.category.name if feedback.category else '未分类'}",
        f"标题：{feedback.title}",
        f"内容：",
        feedback.content,
    ]
    if feedback.related_url:
        body_lines += ["", f"相关链接：{feedback.related_url}"]
    if feedback.contact_info:
        body_lines += ["", f"联系方式：{feedback.contact_info}"]
    if feedback.extra_data:
        body_lines += ["", "扩展信息（新活动提交）："]
        for k, v in feedback.extra_data.items():
            if v:
                body_lines.append(f"  {k}: {v}")
    body_lines += ["", "—— 本条为系统自动发送，请勿直接回复 ——"]
    if prefix:
        subject = f"{prefix}{subject}"
    return subject, "\n".join(body_lines)


def _send_raw(recipient: str, subject: str, body: str) -> tuple[EmailDeliveryStatus, Optional[str]]:
    if not settings.smtp_configured:
        return EmailDeliveryStatus.FAILED, "SMTP 未配置（缺少 SMTP_HOST / SMTP_USERNAME）"
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)
    server: Optional[smtplib.SMTP] = None
    try:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        server.ehlo()
        if settings.SMTP_USE_TLS:
            server.starttls()
            server.ehlo()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
        return EmailDeliveryStatus.SENT, None
    except Exception as exc:  # noqa: BLE001 - 如实记录发送失败原因
        return EmailDeliveryStatus.FAILED, str(exc)
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:  # noqa: BLE001
                pass


def _new_log(db: Session, feedback: Feedback, recipient: str, subject: str) -> EmailDeliveryLog:
    log = EmailDeliveryLog(
        feedback_id=feedback.id,
        recipient_email=recipient,
        subject=subject,
        status=EmailDeliveryStatus.PENDING.value,
        attempt_count=0,
    )
    db.add(log)
    db.flush()
    return log


def send_feedback_email(db: Session, feedback: Feedback) -> Optional[EmailDeliveryLog]:
    """发送反馈通知邮件，返回投递日志；失败不回滚反馈。"""
    if not email_enabled(db):
        return None
    recipient = get_recipient_email(db)
    if not recipient:
        return None
    subject, body = _build_email(feedback, recipient)
    log = _new_log(db, feedback, recipient, subject)
    status, error = _send_raw(recipient, subject, body)
    log.status = status.value
    log.attempt_count = log.attempt_count + 1
    log.last_error = error
    if status == EmailDeliveryStatus.SENT:
        log.sent_at = utcnow()
    db.commit()
    db.refresh(log)
    return log


def retry_feedback_email(db: Session, log_id: int) -> EmailDeliveryLog:
    """管理员手动重试发送邮件（重试次数受 settings.MAX_EMAIL_RETRY 上限约束）。"""
    from fastapi import HTTPException, status as http_status

    log = db.get(EmailDeliveryLog, log_id)
    if log is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="投递日志不存在")
    if log.status == EmailDeliveryStatus.SENT.value:
        return log
    if not email_enabled(db):
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="邮件通知开关已关闭")
    if not get_recipient_email(db):
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="未配置反馈接收邮箱")
    if log.attempt_count >= settings.MAX_EMAIL_RETRY:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"已达到最大重试次数（{settings.MAX_EMAIL_RETRY} 次）")

    feedback = db.get(Feedback, log.feedback_id)
    if feedback is not None:
        _, body = _build_email(feedback, log.recipient_email)
    else:
        body = "（反馈记录已删除，正文无法重建）"

    status, error = _send_raw(log.recipient_email, log.subject, body)
    log.status = status.value
    log.attempt_count = log.attempt_count + 1
    log.last_error = error
    if status == EmailDeliveryStatus.SENT:
        log.sent_at = utcnow()
    db.commit()
    db.refresh(log)
    return log
