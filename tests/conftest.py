"""测试环境配置：使用独立 SQLite 数据库，开启 Mock 登录。"""
from __future__ import annotations

import io
import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_creatorhub.db"
os.environ["MOCK_LOGIN_ENABLED"] = "true"
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-tests"

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.db.base import Base
from app.db.session import engine
from app.main import app as fastapi_app
import app.models  # noqa: F401


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(fastapi_app) as c:
        yield c


def login(client: TestClient, openid: str, nickname: str) -> TestClient:
    r = client.post(f"/api/v1/auth/mock-login?openid={openid}&nickname={nickname}", follow_redirects=False)
    assert r.status_code == 302
    return client


def make_png(color: tuple = (255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (20, 20), color).save(buf, format="PNG")
    return buf.getvalue()


def create_account(client: TestClient, platform: str = "DOUYIN", name: str = "我的账号") -> int:
    r = client.post("/api/v1/accounts", json={"platform": platform, "account_name": name, "profile_url": None})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def create_post(client: TestClient, account_id: int, title: str = "求互关一起涨粉", mutual_type: str = "FOLLOW_FOR_FOLLOW") -> int:
    r = client.post(
        "/api/v1/posts",
        json={
            "title": title,
            "content": "这是我的互助帖子，欢迎申请互关互助。",
            "mutual_type": mutual_type,
            "target_platform": "DOUYIN",
            "target_creator_account_id": account_id,
            "requires_follow_back": True,
            "max_applicants": 5,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]
