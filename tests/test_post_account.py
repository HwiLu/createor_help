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


def test_duplicate_title_rejected(client):
    login(client, "alice", "Alice")
    account_id = create_account(client)
    create_post(client, account_id, title="求互关一起涨粉")

    # 同一用户 + 同一平台 + 相同标题，应被拒绝
    r = client.post(
        "/api/v1/posts",
        json={
            "title": "求互关一起涨粉",
            "content": "这是我的互助帖子，欢迎申请互关互助。",
            "mutual_type": "FOLLOW_FOR_FOLLOW",
            "target_platform": "DOUYIN",
            "target_creator_account_id": account_id,
            "requires_follow_back": True,
            "max_applicants": 5,
        },
    )
    assert r.status_code == 409


def test_duplicate_content_rejected(client):
    login(client, "alice", "Alice")
    account_id = create_account(client)
    create_post(client, account_id, title="求互关一起涨粉")

    # 标题不同但内容相同，应被拒绝
    r = client.post(
        "/api/v1/posts",
        json={
            "title": "一个全新的不同标题",
            "content": "这是我的互助帖子，欢迎申请互关互助。",
            "mutual_type": "FOLLOW_FOR_FOLLOW",
            "target_platform": "DOUYIN",
            "target_creator_account_id": account_id,
            "requires_follow_back": True,
            "max_applicants": 5,
        },
    )
    assert r.status_code == 409


def test_different_user_same_title_allowed(client):
    login(client, "alice", "Alice")
    account_a = create_account(client, name="A账号")
    create_post(client, account_a, title="求互关一起涨粉")

    # 不同用户使用相同标题不应被误伤
    login(client, "bob", "Bob")
    account_b = create_account(client, name="B账号")
    r = client.post(
        "/api/v1/posts",
        json={
            "title": "求互关一起涨粉",
            "content": "这是我的互助帖子，欢迎申请互关互助。",
            "mutual_type": "FOLLOW_FOR_FOLLOW",
            "target_platform": "DOUYIN",
            "target_creator_account_id": account_b,
            "requires_follow_back": True,
            "max_applicants": 5,
        },
    )
    assert r.status_code == 200
