import io

from tests.conftest import create_account, create_post, login, make_png


def _apply(client, post_id, account_id):
    r = client.post(f"/api/v1/posts/{post_id}/applications", json={"applicant_creator_account_id": account_id})
    return r.json()["id"]


def test_upload_rejects_non_image(client):
    login(client, "alice", "Alice")
    alice_account = create_account(client)
    post_id = create_post(client, alice_account)

    login(client, "bob", "Bob")
    bob_account = create_account(client)
    request_id = _apply(client, post_id, bob_account)

    r = client.post(
        f"/api/v1/mutual-requests/{request_id}/evidence",
        files={"file": ("evil.png", b"not an image at all", "image/png")},
    )
    assert r.status_code == 400


def test_upload_rejects_wrong_extension(client):
    login(client, "alice", "Alice")
    alice_account = create_account(client)
    post_id = create_post(client, alice_account)

    login(client, "bob", "Bob")
    bob_account = create_account(client)
    request_id = _apply(client, post_id, bob_account)

    r = client.post(
        f"/api/v1/mutual-requests/{request_id}/evidence",
        files={"file": ("proof.exe", make_png(), "image/png")},
    )
    assert r.status_code == 400


def test_upload_valid_png(client):
    login(client, "alice", "Alice")
    alice_account = create_account(client)
    post_id = create_post(client, alice_account)

    login(client, "bob", "Bob")
    bob_account = create_account(client)
    request_id = _apply(client, post_id, bob_account)

    r = client.post(
        f"/api/v1/mutual-requests/{request_id}/evidence",
        files={"file": ("proof.png", make_png(), "image/png")},
    )
    assert r.status_code == 200
