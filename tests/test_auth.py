"""Authentication & RBAC tests."""


def test_register_creates_user(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Alice Analyst",
            "email": "alice@test.com",
            "password": "secret123",
            "role": "security_analyst",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@test.com"
    assert data["role"] == "security_analyst"


def test_register_duplicate_email(client):
    payload = {
        "full_name": "Bob",
        "email": "bob@test.com",
        "password": "secret123",
        "role": "security_analyst",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


def test_login_returns_token(client):
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Carol", "email": "carol@test.com",
              "password": "secret123", "role": "security_analyst"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "carol@test.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    assert resp.json()["access_token"]


def test_login_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"full_name": "Dan", "email": "dan@test.com",
              "password": "correct", "role": "security_analyst"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "dan@test.com", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    resp = client.get("/api/v1/employees")
    assert resp.status_code == 401


def test_invalid_token_rejected(client):
    resp = client.get(
        "/api/v1/employees", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


def test_rbac_blocks_unauthorized_role(client, auth_headers):
    """Analysts cannot call admin/manager-only baseline computation."""
    headers = auth_headers(email="rbac@test.com", role="security_analyst")
    resp = client.post("/api/v1/anomaly/baselines/compute", headers=headers)
    assert resp.status_code == 403


def test_manager_can_compute_baselines(client, auth_headers):
    headers = auth_headers(email="mgr@test.com", role="security_manager")
    resp = client.post("/api/v1/anomaly/baselines/compute", headers=headers)
    assert resp.status_code == 200
    assert "baselines_computed" in resp.json()


def test_get_and_update_user_profile(client, auth_headers):
    headers = auth_headers(email="profile@test.com", full_name="Original Name")
    # GET /auth/me
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "profile@test.com"
    assert resp.json()["full_name"] == "Original Name"

    # PUT /auth/me
    upd = client.put(
        "/api/v1/auth/me",
        headers=headers,
        json={"full_name": "Updated Name", "password": "newpassword123"},
    )
    assert upd.status_code == 200
    assert upd.json()["full_name"] == "Updated Name"

    # Verify login with new password
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "profile@test.com", "password": "newpassword123"},
    )
    assert login_resp.status_code == 200

