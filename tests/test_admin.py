import os

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.enums import UserRole
from app.models.user import User

from tests.conftest import create_account, create_post, login


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


def test_admin_list_and_delete_post(client):
    login(client, "alice", "Alice")
    account_id = create_account(client)
    post_id = create_post(client, account_id)

    # 普通用户无权删除（走管理员接口）
    r = client.delete(f"/api/v1/admin/posts/{post_id}?reason=违规")
    assert r.status_code == 403

    make_admin("mock:admin")
    login(client, "admin", "管理员")

    # 帖子列表返回重复标记字段
    r = client.get("/api/v1/admin/posts")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    item = r.json()["items"][0]
    assert item["id"] == post_id
    assert item["duplicate_count"] == 1

    # 管理员删除帖子（软删除）
    r = client.delete(f"/api/v1/admin/posts/{post_id}?reason=违规")
    assert r.status_code == 200
    assert r.json()["status"] == "DELETED"

    # 删除后列表为空
    r = client.get("/api/v1/admin/posts")
    assert r.json()["total"] == 0


def test_admin_detects_duplicate_posts(client):
    from app.db.session import SessionLocal
    from app.models.enums import MutualType, Platform, PostStatus
    from app.models.post import Post

    login(client, "alice", "Alice")
    account_id = create_account(client)
    post_id = create_post(client, account_id, title="重复标题啦")

    # 绕过创建接口的去重，直接入库一篇同用户同平台同标题的帖子
    db = SessionLocal()
    try:
        p0 = db.query(Post).filter(Post.id == post_id).first()
        db.add(
            Post(
                user_id=p0.user_id,
                title="重复标题啦",
                content="另一段完全不同的内容文字",
                mutual_type=MutualType.FOLLOW_FOR_FOLLOW.value,
                target_platform=Platform.DOUYIN.value,
                target_creator_account_id=account_id,
                status=PostStatus.PUBLISHED.value,
            )
        )
        db.commit()
    finally:
        db.close()

    make_admin("mock:admin")
    login(client, "admin", "管理员")
    r = client.get("/api/v1/admin/posts")
    assert r.status_code == 200
    counts = sorted(i["duplicate_count"] for i in r.json()["items"])
    assert counts == [2, 2]
