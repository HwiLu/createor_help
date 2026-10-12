"""活动模块测试：公开查询、展示态计算、评论/举报、后台鉴权与 CRUD。"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.models.activity import ActivityPlatform, ActivityType
from app.models.enums import UserRole
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


def get_dict_ids():
    db = SessionLocal()
    try:
        platform_id = db.query(ActivityPlatform.id).filter(ActivityPlatform.code == "PDD").scalar()
        type_id = db.query(ActivityType.id).filter(ActivityType.code == "INVITE").scalar()
        return platform_id, type_id
    finally:
        db.close()


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def create_activity(client, platform_id, type_id, *, start=None, end=None, title="这是一个测试活动") -> int:
    now = datetime.utcnow()
    payload = {
        "title": title,
        "summary": "活动摘要",
        "content": "**活动详情**",
        "platform_id": platform_id,
        "activity_type_id": type_id,
        "start_at": _iso(start or (now - timedelta(days=1))),
        "end_at": _iso(end or (now + timedelta(days=1))),
    }
    r = client.post("/api/v1/admin/activities", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_non_admin_cannot_manage_activities(client):
    login(client, "alice", "Alice")
    r = client.get("/api/v1/admin/activities")
    assert r.status_code == 403


def test_activity_publish_visibility_and_status(client):
    make_admin("mock:admin")
    login(client, "admin", "管理员")
    pid, tid = get_dict_ids()
    assert pid and tid

    # 草稿不进入公开列表
    aid = create_activity(client, pid, tid, title="这是一个草稿活动")
    r = client.get("/api/v1/activities")
    assert r.status_code == 200
    assert all(item["id"] != aid for item in r.json()["items"])

    # 发布后进入公开列表，展示态为进行中
    r = client.post(f"/api/v1/admin/activities/{aid}/publish")
    assert r.status_code == 200
    r = client.get("/api/v1/activities")
    items = r.json()["items"]
    assert any(item["id"] == aid for item in items)
    published = next(item for item in items if item["id"] == aid)
    assert published["display_status"] == "ONGOING"

    # 即将开始：未来起止时间
    future = create_activity(client, pid, tid, title="这是一个未来活动", start=datetime.utcnow() + timedelta(days=5), end=datetime.utcnow() + timedelta(days=10))
    client.post(f"/api/v1/admin/activities/{future}/publish")
    r = client.get(f"/api/v1/activities/{future}")
    assert r.status_code == 200
    assert r.json()["display_status"] == "UPCOMING"

    # 已结束：过去的起止时间
    past = create_activity(client, pid, tid, title="这是一个过期活动", start=datetime.utcnow() - timedelta(days=10), end=datetime.utcnow() - timedelta(days=5))
    client.post(f"/api/v1/admin/activities/{past}/publish")
    r = client.get(f"/api/v1/activities/{past}")
    assert r.status_code == 200
    assert r.json()["display_status"] == "ENDED"


def test_activity_end_before_start_rejected(client):
    make_admin("mock:admin")
    login(client, "admin", "管理员")
    pid, tid = get_dict_ids()
    now = datetime.utcnow()
    r = client.post(
        "/api/v1/admin/activities",
        json={
            "title": "时间设置错误",
            "summary": "摘要",
            "content": "详情",
            "platform_id": pid,
            "activity_type_id": tid,
            "start_at": _iso(now),
            "end_at": _iso(now - timedelta(hours=1)),
        },
    )
    assert r.status_code == 400


def test_activity_comment_reply_report_and_moderate(client):
    make_admin("mock:admin")
    login(client, "admin", "管理员")
    pid, tid = get_dict_ids()
    aid = create_activity(client, pid, tid, title="这是评论测试活动")
    client.post(f"/api/v1/admin/activities/{aid}/publish")

    # 普通用户评论
    login(client, "bob", "Bob")
    r = client.post(f"/api/v1/activities/{aid}/comments", json={"content": "这个活动不错"})
    assert r.status_code == 200
    comment_id = r.json()["comment"]["id"]

    # 公开列表能查到评论
    r = client.get(f"/api/v1/activities/{aid}/comments")
    assert r.status_code == 200
    assert r.json()["count"] == 1

    # 另一用户回复
    login(client, "carol", "Carol")
    r = client.post(f"/api/v1/activities/{aid}/comments", json={"content": "我也觉得", "parent_id": comment_id})
    assert r.status_code == 200
    r = client.get(f"/api/v1/activities/{aid}/comments")
    assert r.json()["comments"][0]["replies"][0]["content"] == "我也觉得"

    # 举报评论
    r = client.post(f"/api/v1/activities/{aid}/comments/{comment_id}/reports", json={"reason": "广告"})
    assert r.status_code == 200

    # 管理员审核评论（隐藏）
    make_admin("mock:admin")
    login(client, "admin", "管理员")
    r = client.get("/api/v1/admin/activity-comments")
    assert r.status_code == 200
    r = client.post(f"/api/v1/admin/activity-comments/{comment_id}/moderate", json={"status": "HIDDEN"})
    assert r.status_code == 200

    # 隐藏后公开列表不再返回
    r = client.get(f"/api/v1/activities/{aid}/comments")
    assert r.json()["count"] == 0

    # 举报处理
    r = client.get("/api/v1/admin/activity-reports")
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    report_id = r.json()["items"][0]["id"]
    r = client.post(f"/api/v1/admin/activity-reports/{report_id}/resolve", json={"status": "RESOLVED", "resolution": "已隐藏该评论"})
    assert r.status_code == 200
    assert r.json()["status"] == "RESOLVED"
