def test_healthcheck(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_user_registration_and_login(client):
    # Register
    reg_payload = {
        "email": "test@socialai.com",
        "password": "Password123!",
        "full_name": "Test Architect",
        "role": "Admin"
    }
    res = client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == reg_payload["email"]
    assert data["role"] == "Admin"

    # Login
    login_payload = {
        "email": "test@socialai.com",
        "password": "Password123!"
    }
    res_login = client.post("/api/v1/auth/login", json=login_payload)
    assert res_login.status_code == 200
    token_data = res_login.json()
    assert "access_token" in token_data
    assert token_data["role"] == "Admin"

    # Get Me
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "test@socialai.com"
