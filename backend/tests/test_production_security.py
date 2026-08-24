import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_password_hash, create_access_token
from app.core.security_encryption import encrypt_token, decrypt_token, mask_token
from app.core.redis import set_oauth_state, pop_oauth_state
from app.models.user import User
from app.models.brand import BrandProfile
from app.models.post import Post

client = TestClient(app)

def test_unauthenticated_request_fails(db_session):
    """Unauthenticated request without JWT header must return 401 Unauthorized."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "token is missing" in response.json()["detail"].lower()

def test_password_strength_validation(db_session):
    """Registration with weak password must fail with 400 Bad Request or 422 validation error."""
    res = client.post("/api/v1/auth/register", json={
        "email": "weakpass@test.com",
        "password": "short",
        "full_name": "Weak Pass"
    })
    assert res.status_code in [400, 422]

import uuid

def test_registration_and_login_flow(client):
    """Successful registration, login, and refresh token flow."""
    email = f"secure_{uuid.uuid4().hex[:8]}@test.com"
    reg_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "Secure User"
    })
    assert reg_res.status_code == 201

    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "SecurePassword123!"
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert "refresh_token" not in data  # No longer exposed in JSON response body
    assert "refresh_token" in login_res.cookies  # Delivered via HttpOnly cookie

    # Test me endpoint with access token
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # Test refresh token using cookie
    ref_res = client.post("/api/v1/auth/refresh", cookies=login_res.cookies)
    assert ref_res.status_code == 200
    assert "access_token" in ref_res.json()


def test_idor_user_isolation(client, db_session):
    """User A must NOT be able to access User B's brand profile or post."""
    # Register User A
    email_a = f"userA_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={"email": email_a, "password": "Password123!", "full_name": "User A"})
    token_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": "Password123!"}).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register User B
    email_b = f"userB_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v1/auth/register", json={"email": email_b, "password": "Password123!", "full_name": "User B"})
    token_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": "Password123!"}).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B creates a Brand
    res_b_brand = client.post("/api/v1/brands/", json={"name": "User B Brand", "tone_of_voice": "Bold"}, headers=headers_b)
    assert res_b_brand.status_code == 201
    brand2_id = res_b_brand.json()["id"]

    # User B creates a Post
    res_b_post = client.post("/api/v1/posts/", json={
        "brand_id": brand2_id,
        "title": "User B Post",
        "caption": "Private Post Caption"
    }, headers=headers_b)
    assert res_b_post.status_code == 201
    post2_id = res_b_post.json()["id"]

    # User A tries to access User B's brand -> 404 Not Found
    res_brand = client.get(f"/api/v1/brands/{brand2_id}", headers=headers_a)
    assert res_brand.status_code in [403, 404]

    # User A tries to access User B's post -> 404 Not Found
    res_post = client.get(f"/api/v1/posts/{post2_id}", headers=headers_a)
    assert res_post.status_code in [403, 404]

def test_token_encryption_at_rest():
    """Verify Fernet symmetric encryption and decryption of access tokens."""
    plain = "EAANNCrODiz0BSBxCzacKzydhz8ldveVLEwIUZBRlxf8YMgXqZA5PWjJ1my9RUqQ"
    encrypted = encrypt_token(plain)
    assert encrypted.startswith("enc_gAAAAA")
    assert encrypted != plain

    decrypted = decrypt_token(encrypted)
    assert decrypted == plain

    masked = mask_token(encrypted)
    assert masked.startswith("EAANNCr...")
    assert "..." in masked

def test_oauth_state_management():
    """Verify one-time OAuth state storage and consumption."""
    state_token = "test_csrf_token_12345"
    set_oauth_state(state_token, user_id=99, ttl_seconds=60)
    
    # First pop should return user_id
    user_id = pop_oauth_state(state_token)
    assert user_id == 99

    # Second pop should return None (one-time use)
    user_id_2 = pop_oauth_state(state_token)
    assert user_id_2 is None

def test_health_and_readiness():
    """Test /health and /ready endpoints."""
    res_h = client.get("/api/v1/health")
    assert res_h.status_code == 200
    assert res_h.json()["status"] == "healthy"

    res_r = client.get("/api/v1/ready")
    assert res_r.status_code in [200, 530]
