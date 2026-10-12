"""意见反馈与邮件测试：反馈写入、extra_data 校验、限流、邮件失败不回滚、后台流转。"""
from __future__ import annotations

from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.feedback import FeedbackCategory
from app.models.user import User

from tests.conftest import login


def make_admin(openid: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.wechat_openid == openid).first()
        if user is None:
            user = User(wechat_openid=openid, nickname="管理员", role=UserRole.ADMIN.value)
            db.add(user)
        else:
            user.role = UserRole.ADMIN.value
        db.commit()
    finally:
        db.close()


def _cat_id(code: str) -> int:
    db = SessionLocal()
    try:
        return db.query(FeedbackCategory.id).filter(FeedbackCategory.code == code).scalar()
    finally:
        db.close()


def test_feedback_submit_basic_email_disabled(client):
    login(client, "fb_basic_1", "反馈用户A")
    cid = _cat_id("FEATURE")
    r = client.post("/api/v1/feedback", json={"category_id": cid, "title": "希望增加夜间模式", "content": "希望增加夜间模式，保护眼睛。"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "PENDING"
    # 邮件默认关闭：如实返回 DISABLED，不伪造发送成功
    assert data["email_status"] == "DISABLED"


def test_feedback_new_activity_validation(client):
    cid = _cat_id("NEW_ACTIVITY")
    # 缺少必填字段 -> 400（使用独立用户，避免命中限流）
    login(client, "fb_new_invalid", "反馈用户B1")
    r = client.post("/api/v1/feedback", json={
        "category_id": cid, "title": "新活动", "content": "发现一个新活动",
        "extra_data": {"platform": "拼多多"},
    })
    assert r.status_code == 400

    # 字段完整 -> 200
    login(client, "fb_new_valid", "反馈用户B2")
    r = client.post("/api/v1/feedback", json={
        "category_id": cid, "title": "新活动提交", "content": "发现一个不错的邀请活动",
        "extra_data": {
            "activity_name": "拼多多助力",
            "platform": "拼多多",
            "activity_desc": "邀请好友助力得红包",
            "official_url": "https://example.com",
            "group_entry": "微信群",
            "deadline": "2026-12-31",
            "recommend_reason": "门槛低",
        },
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "PENDING"


def test_feedback_rate_limit(client):
    login(client, "fb_rate_1", "反馈用户C")
    cid = _cat_id("FEATURE")
    body = {"category_id": cid, "title": "限流测试A", "content": "第一次提交的内容"}
    r = client.post("/api/v1/feedback", json=body)
    assert r.status_code == 200
    r = client.post("/api/v1/feedback", json={"category_id": cid, "title": "限流测试B", "content": "第二次提交的内容"})
    assert r.status_code == 429


def test_feedback_admin_status_transition(client):
    login(client, "fb_admin_1", "反馈用户D")
    cid = _cat_id("FEATURE")
    r = client.post("/api/v1/feedback", json={"category_id": cid, "title": "需要处理", "content": "这是一个需要处理的反馈"})
    assert r.status_code == 200
    fid = r.json()["id"]

    make_admin("mock:admin")
    login(client, "admin", "管理员")
    r = client.get("/api/v1/admin/feedback")
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    # 待处理 -> 已处理（合法流转）
    r = client.post(f"/api/v1/admin/feedback/{fid}/status", json={"status": "RESOLVED", "admin_note": "已处理"})
    assert r.status_code == 200
    assert r.json()["status"] == "RESOLVED"

    # 已处理为终态，不能再流转
    r = client.post(f"/api/v1/admin/feedback/{fid}/status", json={"status": "PROCESSING"})
    assert r.status_code == 400


def _enable_email(client):
    """管理员开启邮件通知并配置接收邮箱。"""
    make_admin("mock:admin")
    login(client, "admin", "管理员")
    r = client.post("/api/v1/admin/settings", json={"key": "email_notifications_enabled", "value": "true"})
    assert r.status_code == 200, r.text
    r = client.post("/api/v1/admin/settings", json={"key": "feedback_recipient_email", "value": "admin@example.com"})
    assert r.status_code == 200, r.text


def test_feedback_admin_settings_whitelist(client):
    make_admin("mock:admin")
    login(client, "admin", "管理员")

    # 初始可正常读取（未配置时为空列表）
    r = client.get("/api/v1/admin/settings")
    assert r.status_code == 200
    assert isinstance(r.json()["items"], list)

    # 写入合法配置后能读回
    r = client.post("/api/v1/admin/settings", json={"key": "feedback_recipient_email", "value": "ops@example.com"})
    assert r.status_code == 200
    r = client.get("/api/v1/admin/settings")
    keys = {item["key"]: item["value"] for item in r.json()["items"]}
    assert keys.get("feedback_recipient_email") == "ops@example.com"

    # 越权配置项被拒绝（敏感项 SMTP_PASSWORD 永不可通过后台写入）
    r = client.post("/api/v1/admin/settings", json={"key": "SMTP_PASSWORD", "value": "secret"})
    assert r.status_code == 400


def test_email_send_success_and_delivery_log(client, monkeypatch):
    _enable_email(client)

    from app.services import email_service
    from app.models.enums import EmailDeliveryStatus

    monkeypatch.setattr(email_service, "_send_raw", lambda *a, **k: (EmailDeliveryStatus.SENT, None))

    login(client, "fb_email_ok", "反馈用户E")
    cid = _cat_id("FEATURE")
    r = client.post("/api/v1/feedback", json={"category_id": cid, "title": "邮件发送测试", "content": "这条反馈应当成功发送邮件"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "PENDING"
    assert r.json()["email_status"] == "SENT"

    # 投递日志落库
    login(client, "admin", "管理员")
    r = client.get("/api/v1/admin/email-logs")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    log = r.json()["items"][0]
    assert log["status"] == "SENT"
    assert log["recipient_email"] == "admin@example.com"


def test_email_send_failure_does_not_rollback_feedback(client, monkeypatch):
    _enable_email(client)

    from app.services import email_service
    from app.models.enums import EmailDeliveryStatus

    monkeypatch.setattr(email_service, "_send_raw", lambda *a, **k: (EmailDeliveryStatus.FAILED, "smtp connect timeout"))

    login(client, "fb_email_fail", "反馈用户F")
    cid = _cat_id("FEATURE")
    r = client.post("/api/v1/feedback", json={"category_id": cid, "title": "邮件失败测试", "content": "邮件发送失败但反馈应已保存"})
    assert r.status_code == 200, r.text
    # 反馈写入成功，邮件如实返回失败
    assert r.json()["status"] == "PENDING"
    assert r.json()["email_status"] == "FAILED"

    # 反馈记录确实存在（未被邮件失败回滚）
    login(client, "admin", "管理员")
    r = client.get("/api/v1/admin/feedback")
    assert r.status_code == 200
    assert any(item["title"] == "邮件失败测试" for item in r.json()["items"])

    # 投递日志记录失败原因
    r = client.get("/api/v1/admin/email-logs")
    assert r.json()["items"][0]["status"] == "FAILED"
    assert "smtp connect timeout" in r.json()["items"][0]["last_error"]


def test_email_retry_when_disabled(client, monkeypatch):
    _enable_email(client)

    from app.services import email_service
    from app.models.enums import EmailDeliveryStatus

    # 首次发送失败，产生 FAILED 日志
    monkeypatch.setattr(email_service, "_send_raw", lambda *a, **k: (EmailDeliveryStatus.FAILED, "boom"))
    login(client, "fb_retry", "反馈用户G")
    cid = _cat_id("FEATURE")
    client.post("/api/v1/feedback", json={"category_id": cid, "title": "重试测试", "content": "用于邮件重试的反馈"})

    login(client, "admin", "管理员")
    log_id = client.get("/api/v1/admin/email-logs").json()["items"][0]["id"]

    # 关闭邮件开关后重试 -> 400
    client.post("/api/v1/admin/settings", json={"key": "email_notifications_enabled", "value": "false"})
    r = client.post(f"/api/v1/admin/email-logs/{log_id}/retry")
    assert r.status_code == 400

    # 重新开启开关并恢复真实发送 -> 重试成功
    client.post("/api/v1/admin/settings", json={"key": "email_notifications_enabled", "value": "true"})
    monkeypatch.setattr(email_service, "_send_raw", lambda *a, **k: (EmailDeliveryStatus.SENT, None))
    r = client.post(f"/api/v1/admin/email-logs/{log_id}/retry")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "SENT"
    assert r.json()["attempt_count"] == 2
