import os

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.enums import UserRole
from app.models.user import User

from tests.conftest import login


def make_admin(openid: str):
    db = SessionLocal()
    try:
        user = User(wechat_openid=openid, nickname="管理员", role=UserRole.ADMIN.value)
        db.add(user)
        db.commit()
    finally:
        db.close()


def test_admin_report_and_restrict(client):
    login(client, "alice", "Alice")
    # Alice 举报一个不存在的帖子（仅验证举报创建流程）
    r = client.post(
        "/api/v1/reports",
        json={"target_type": "POST", "target_id": 1, "reason": "违规内容", "description": "测试举报"},
    )
    assert r.status_code == 200

    make_admin("mock:admin")

    login(client, "admin", "管理员")
    r = client.get("/api/v1/admin/reports")
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    report_id = r.json()["items"][0]["id"]
    r = client.post(f"/api/v1/admin/reports/{report_id}/resolve", json={"resolution": "已处理", "status": "RESOLVED"})
    assert r.status_code == 200
    assert r.json()["status"] == "RESOLVED"


def test_non_admin_cannot_access_admin(client):
    login(client, "alice", "Alice")
    r = client.get("/api/v1/admin/reports")
    assert r.status_code == 403
