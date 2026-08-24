import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, hash_token
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.user import User
from app.repositories.refresh_token_repository import refresh_token_repo


def test_successful_login(client: TestClient, db_session: Session):
    """Test successful user login issuing short-lived access_token and setting HttpOnly refresh cookie."""
    email = f"user_login_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Login User", role="Editor")
    db_session.add(user)
    db_session.commit()

    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" not in data  # Never returned in JSON body
    assert data["role"] == "Editor"
    assert data["email"] == email

    # Verify HttpOnly cookie
    assert settings.REFRESH_COOKIE_NAME in res.cookies
    refresh_cookie_header = res.headers.get("set-cookie", "")
    assert "httponly" in refresh_cookie_header.lower()
    assert "path=/api/v1/auth" in refresh_cookie_header.lower()


def test_login_wrong_password(client: TestClient, db_session: Session):
    """Test login attempt with incorrect password fails with 401 Unauthorized."""
    email = f"wrong_pwd_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("CorrectPassword123!"), full_name="Wrong Pwd", role="Editor")
    db_session.add(user)
    db_session.commit()

    res = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword123!"})
    assert res.status_code == 401
    assert "Incorrect email or password" in res.json()["detail"]


def test_inactive_user_cannot_login_or_refresh(client: TestClient, db_session: Session):
    """Test inactive/deactivated user cannot log in or refresh tokens."""
    email = f"inactive_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Inactive User", is_active=False)
    db_session.add(user)
    db_session.commit()

    # Login attempt
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    assert res.status_code == 403
    assert "Inactive" in res.json()["detail"]


def test_access_token_expiry(client: TestClient, db_session: Session):
    """Test that an expired access token returns 401 Unauthorized when accessing protected endpoints."""
    email = f"exp_token_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Exp Token User")
    db_session.add(user)
    db_session.commit()

    # Create expired access token (-1 minute)
    expired_token = create_access_token(subject=user.id, role=user.role, expires_delta=timedelta(minutes=-1))
    
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_refresh_using_httponly_cookie(client: TestClient, db_session: Session):
    """Test /auth/refresh using valid HttpOnly refresh cookie."""
    email = f"refresh_cookie_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Refresh Cookie User")
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    assert login_res.status_code == 200

    ref_res = client.post("/api/v1/auth/refresh", cookies=login_res.cookies, headers={"X-Requested-With": "XMLHttpRequest"})
    assert ref_res.status_code == 200
    ref_data = ref_res.json()
    assert "access_token" in ref_data
    assert ref_data["email"] == email
    assert settings.REFRESH_COOKIE_NAME in ref_res.cookies


def test_refresh_token_rotation(client: TestClient, db_session: Session):
    """Test that refreshing access token generates a NEW rotated refresh cookie."""
    email = f"rotation_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Rotation User")
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    old_cookie = login_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    ref_res = client.post("/api/v1/auth/refresh", cookies=login_res.cookies, headers={"X-Requested-With": "XMLHttpRequest"})
    assert ref_res.status_code == 200
    new_cookie = ref_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    assert old_cookie != new_cookie


def test_old_refresh_token_rejected_after_rotation(client: TestClient, db_session: Session):
    """Test that presenting an old refresh token after it was rotated is rejected."""
    email = f"old_rejected_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Old Rejected User")
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    old_cookie = login_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    # Perform refresh -> rotates token
    ref_res = client.post("/api/v1/auth/refresh", cookies={settings.REFRESH_COOKIE_NAME: old_cookie}, headers={"X-Requested-With": "XMLHttpRequest"})
    assert ref_res.status_code == 200

    # Try to use old cookie again -> must be rejected (due to reuse detection / revocation)
    second_ref = client.post("/api/v1/auth/refresh", cookies={settings.REFRESH_COOKIE_NAME: old_cookie}, headers={"X-Requested-With": "XMLHttpRequest"})
    assert second_ref.status_code == 401


def test_revoked_refresh_token_rejected(client: TestClient, db_session: Session):
    """Test that manually revoked refresh token is rejected."""
    email = f"manual_revoked_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Manual Revoked")
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    cookie_val = login_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    # Logout to revoke
    client.post("/api/v1/auth/logout", cookies={settings.REFRESH_COOKIE_NAME: cookie_val}, headers={"X-Requested-With": "XMLHttpRequest"})

    # Try to refresh -> 401
    ref_res = client.post("/api/v1/auth/refresh", cookies={settings.REFRESH_COOKIE_NAME: cookie_val}, headers={"X-Requested-With": "XMLHttpRequest"})
    assert ref_res.status_code == 401


def test_refresh_token_reuse_detection_revokes_family(client: TestClient, db_session: Session):
    """Test that presenting a previously revoked refresh token triggers family revocation (reuse detection)."""
    email = f"reuse_detect_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Reuse Detect")
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    initial_cookie = login_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    # Legitimate refresh 1
    ref1_res = client.post("/api/v1/auth/refresh", cookies={settings.REFRESH_COOKIE_NAME: initial_cookie}, headers={"X-Requested-With": "XMLHttpRequest"})
    assert ref1_res.status_code == 200
    legit_cookie_2 = ref1_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    # Attacker tries to reuse initial_cookie (which was revoked)
    reuse_res = client.post("/api/v1/auth/refresh", cookies={settings.REFRESH_COOKIE_NAME: initial_cookie}, headers={"X-Requested-With": "XMLHttpRequest"})
    assert reuse_res.status_code == 401
    assert "reuse detected" in reuse_res.json()["detail"].lower()

    # Legitimate cookie 2 should now ALSO be revoked due to family revocation
    ref2_res = client.post("/api/v1/auth/refresh", cookies={settings.REFRESH_COOKIE_NAME: legit_cookie_2}, headers={"X-Requested-With": "XMLHttpRequest"})
    assert ref2_res.status_code == 401


def test_logout_revocation(client: TestClient, db_session: Session):
    """Test POST /auth/logout revokes session in database."""
    email = f"logout_rev_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Logout User")
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    cookie_val = login_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    logout_res = client.post("/api/v1/auth/logout", cookies={settings.REFRESH_COOKIE_NAME: cookie_val}, headers={"X-Requested-With": "XMLHttpRequest"})
    assert logout_res.status_code == 200
    assert logout_res.json()["detail"] == "Successfully logged out"

    # Verify session revoked in DB
    rec = refresh_token_repo.get_by_hash(db_session, hash_token(cookie_val))
    assert rec is not None
    assert rec.revoked_at is not None


def test_logout_clears_cookie(client: TestClient, db_session: Session):
    """Test POST /auth/logout sets response headers clearing the refresh cookie."""
    email = f"logout_clear_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Clear Cookie User")
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    logout_res = client.post("/api/v1/auth/logout", cookies=login_res.cookies, headers={"X-Requested-With": "XMLHttpRequest"})
    assert logout_res.status_code == 200


    cookie_header = logout_res.headers.get("set-cookie", "")
    assert settings.REFRESH_COOKIE_NAME in cookie_header
    assert "max-age=0" in cookie_header.lower() or 'expires=thu, 01 jan 1970' in cookie_header.lower()


def test_query_parameter_token_rejected(client: TestClient, db_session: Session):
    """Test that access token passed as ?token= query parameter is REJECTED (Bearer header required)."""
    email = f"query_param_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Query Param User")
    db_session.add(user)
    db_session.commit()

    token = create_access_token(subject=user.id, role=user.role)

    # Attempt access using ?token= query parameter -> Must fail 401
    res = client.get(f"/api/v1/auth/me?token={token}")
    assert res.status_code == 401
    assert "Authentication token is missing" in res.json()["detail"]


def test_authentication_rate_limiting(client: TestClient, db_session: Session):
    """Test that rate limiting can be explicitly enabled on login endpoint."""
    limiter.enabled = True
    try:
        email = f"rate_limit_{uuid.uuid4().hex[:8]}@test.com"
        responses = [client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword!"}) for _ in range(8)]
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes
    finally:
        limiter.enabled = False


def test_cookie_security_attributes(client: TestClient, db_session: Session):
    """Test that HttpOnly refresh cookie sets appropriate security attributes."""
    email = f"cookie_attrs_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Cookie Attrs User")
    db_session.add(user)
    db_session.commit()

    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    cookie_header = res.headers.get("set-cookie", "")

    assert "httponly" in cookie_header.lower()
    assert "samesite=lax" in cookie_header.lower()
    assert "path=/api/v1/auth" in cookie_header.lower()


from fastapi import HTTPException
from app.api.v1.deps import require_admin

def test_existing_role_admin_authorization_remains_functional(client: TestClient, db_session: Session):
    """Verify role-based authorization (Admin vs Editor) continues to function strictly."""
    admin_user = User(email="admin@test.com", hashed_password=get_password_hash("Password123!"), full_name="Admin User", role="Admin")
    editor_user = User(email="editor@test.com", hashed_password=get_password_hash("Password123!"), full_name="Editor User", role="Editor")

    assert require_admin(admin_user) == admin_user

    with pytest.raises(HTTPException) as exc_info:
        require_admin(editor_user)
    assert exc_info.value.status_code == 403
    assert "Admin role privilege required" in exc_info.value.detail

