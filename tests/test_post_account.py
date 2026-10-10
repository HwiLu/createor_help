from tests.conftest import create_account, create_post, login


def test_create_account_and_post(client):
    login(client, "alice", "Alice")
    account_id = create_account(client)
    post_id = create_post(client, account_id)

    r = client.get("/api/v1/posts")
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = client.get(f"/api/v1/posts/{post_id}")
    assert r.status_code == 200
    assert r.json()["title"] == "求互关一起涨粉"


def test_cannot_create_post_without_account(client):
    login(client, "alice", "Alice")
    r = client.post(
        "/api/v1/posts",
        json={
            "title": "测试帖子标题",
            "content": "这是一段足够长的正文内容。",
            "mutual_type": "FOLLOW_FOR_FOLLOW",
            "target_platform": "DOUYIN",
            "target_creator_account_id": 9999,
            "requires_follow_back": True,
            "max_applicants": 5,
        },
    )
    assert r.status_code == 400


def test_cannot_use_other_users_account(client):
    login(client, "alice", "Alice")
    account_id = create_account(client)

    login(client, "bob", "Bob")
    r = client.post(
        "/api/v1/posts",
        json={
            "title": "冒用账号测试帖",
            "content": "这是一段足够长的正文内容。",
            "mutual_type": "FOLLOW_FOR_FOLLOW",
            "target_platform": "DOUYIN",
            "target_creator_account_id": account_id,
            "requires_follow_back": True,
            "max_applicants": 5,
        },
    )
    assert r.status_code == 400
