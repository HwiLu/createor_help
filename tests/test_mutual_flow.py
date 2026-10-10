from tests.conftest import create_account, create_post, login, make_png


def _apply(client, post_id, account_id):
    r = client.post(
        f"/api/v1/posts/{post_id}/applications",
        json={"applicant_creator_account_id": account_id, "application_message": "已关注"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _upload_evidence(client, request_id, png):
    r = client.post(f"/api/v1/mutual-requests/{request_id}/evidence", files={"file": ("proof.png", png, "image/png")})
    assert r.status_code == 200, r.text


def test_full_closed_loop(client):
    # 发帖人 Alice
    login(client, "alice", "Alice")
    alice_account = create_account(client, name="Alice 抖音号")
    post_id = create_post(client, alice_account)

    # 申请者 Bob
    login(client, "bob", "Bob")
    bob_account = create_account(client, name="Bob 抖音号")

    request_id = _apply(client, post_id, bob_account)
    _upload_evidence(client, request_id, make_png((0, 255, 0)))

    # Bob 无法确认完成（非法状态）
    r = client.post(f"/api/v1/mutual-requests/{request_id}/confirm-completion")
    assert r.status_code == 409

    # Alice 核验证据：接受 -> WAITING_RETURN
    login(client, "alice", "Alice")
    r = client.post(f"/api/v1/mutual-requests/{request_id}/review-evidence", json={"accept": True})
    assert r.status_code == 200
    assert r.json()["status"] == "WAITING_RETURN"

    # Alice 声明回关 -> RETURNED_PENDING_CONFIRMATION
    r = client.post(f"/api/v1/mutual-requests/{request_id}/declare-returned")
    assert r.status_code == 200
    assert r.json()["status"] == "RETURNED_PENDING_CONFIRMATION"

    # Bob 确认完成 -> COMPLETED
    login(client, "bob", "Bob")
    r = client.post(f"/api/v1/mutual-requests/{request_id}/confirm-completion")
    assert r.status_code == 200
    assert r.json()["status"] == "COMPLETED"


def test_cannot_apply_own_post(client):
    login(client, "alice", "Alice")
    account_id = create_account(client)
    post_id = create_post(client, account_id)

    r = client.post(f"/api/v1/posts/{post_id}/applications", json={"applicant_creator_account_id": account_id})
    assert r.status_code == 409


def test_duplicate_application_rejected(client):
    login(client, "alice", "Alice")
    alice_account = create_account(client)
    post_id = create_post(client, alice_account)

    login(client, "bob", "Bob")
    bob_account = create_account(client)
    _apply(client, post_id, bob_account)

    r = client.post(f"/api/v1/posts/{post_id}/applications", json={"applicant_creator_account_id": bob_account})
    assert r.status_code == 409


def test_evidence_reject_and_resubmit(client):
    login(client, "alice", "Alice")
    alice_account = create_account(client)
    post_id = create_post(client, alice_account)

    login(client, "bob", "Bob")
    bob_account = create_account(client)
    request_id = _apply(client, post_id, bob_account)
    _upload_evidence(client, request_id, make_png())

    login(client, "alice", "Alice")
    r = client.post(f"/api/v1/mutual-requests/{request_id}/review-evidence", json={"accept": False, "reason": "截图不清晰"})
    assert r.status_code == 200
    assert r.json()["status"] == "EVIDENCE_REJECTED"

    # Bob 重新提交
    login(client, "bob", "Bob")
    r = client.post(f"/api/v1/mutual-requests/{request_id}/resubmit", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "PENDING_REVIEW"


def test_evidence_access_control(client):
    login(client, "alice", "Alice")
    alice_account = create_account(client)
    post_id = create_post(client, alice_account)

    login(client, "bob", "Bob")
    bob_account = create_account(client)
    request_id = _apply(client, post_id, bob_account)
    _upload_evidence(client, request_id, make_png())

    # 无关用户 Carol 无法查看证据
    login(client, "carol", "Carol")
    r = client.get(f"/api/v1/mutual-requests/{request_id}/evidence")
    assert r.status_code == 403


def test_dispute_flow(client):
    login(client, "alice", "Alice")
    alice_account = create_account(client)
    post_id = create_post(client, alice_account)

    login(client, "bob", "Bob")
    bob_account = create_account(client)
    request_id = _apply(client, post_id, bob_account)
    _upload_evidence(client, request_id, make_png())

    login(client, "alice", "Alice")
    client.post(f"/api/v1/mutual-requests/{request_id}/review-evidence", json={"accept": True})
    client.post(f"/api/v1/mutual-requests/{request_id}/declare-returned")

    login(client, "bob", "Bob")
    r = client.post(f"/api/v1/mutual-requests/{request_id}/dispute", json={"reason": "没有看到对方关注"})
    assert r.status_code == 200
    assert r.json()["status"] == "DISPUTED"
