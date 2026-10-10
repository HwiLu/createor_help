from tests.conftest import login


def test_mock_login_and_me(client):
    login(client, "alice", "Alice")
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert data["nickname"] == "Alice"


def test_unauthenticated_me_returns_401(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_logout(client):
    login(client, "alice", "Alice")
    assert client.get("/api/v1/auth/me").status_code == 200
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/me").status_code == 401
