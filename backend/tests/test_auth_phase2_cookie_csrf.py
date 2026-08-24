import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User


def test_production_cookie_attributes(client: TestClient, db_session: Session):
    """Verify that in production mode, refresh cookies enforce HttpOnly=True, Secure=True, SameSite=None, and Path=/api/v1/auth."""
    old_env = settings.APP_ENV
    old_secure = settings.REFRESH_COOKIE_SECURE
    try:
        settings.APP_ENV = "production"
        settings.REFRESH_COOKIE_SECURE = True

        email = f"prod_cookie_{uuid.uuid4().hex[:8]}@test.com"
        user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Prod Cookie User")
        db_session.add(user)
        db_session.commit()

        res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        assert res.status_code == 200

        cookie_header = res.headers.get("set-cookie", "").lower()
        assert "httponly" in cookie_header
        assert "secure" in cookie_header
        assert "samesite=none" in cookie_header
        assert "path=/api/v1/auth" in cookie_header
    finally:
        settings.APP_ENV = old_env
        settings.REFRESH_COOKIE_SECURE = old_secure


def test_development_cookie_attributes(client: TestClient, db_session: Session):
    """Verify that in local development HTTP mode, cookies use SameSite=Lax without Secure to keep localhost usable."""
    old_env = settings.APP_ENV
    old_secure = settings.REFRESH_COOKIE_SECURE
    try:
        settings.APP_ENV = "development"
        settings.REFRESH_COOKIE_SECURE = False

        email = f"dev_cookie_{uuid.uuid4().hex[:8]}@test.com"
        user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="Dev Cookie User")
        db_session.add(user)
        db_session.commit()

        res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        assert res.status_code == 200

        cookie_header = res.headers.get("set-cookie", "").lower()
        assert "httponly" in cookie_header
        assert "samesite=lax" in cookie_header
        assert "path=/api/v1/auth" in cookie_header
    finally:
        settings.APP_ENV = old_env
        settings.REFRESH_COOKIE_SECURE = old_secure


def test_cors_allows_exact_vercel_origin(client: TestClient):
    """Verify CORS explicitly allows the production Vercel frontend origin with allow_credentials=True."""
    vercel_origin = "https://ai-post-automation.vercel.app"
    res = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": vercel_origin,
            "Access-Control-Request-Method": "POST",
        }
    )
    assert res.headers.get("access-control-allow-origin") == vercel_origin
    assert res.headers.get("access-control-allow-credentials") == "true"


def test_cors_allows_localhost_origin(client: TestClient):
    """Verify CORS preserves local development origins."""
    local_origin = "http://localhost:3000"
    res = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": local_origin,
            "Access-Control-Request-Method": "POST",
        }
    )
    assert res.headers.get("access-control-allow-origin") == local_origin
    assert res.headers.get("access-control-allow-credentials") == "true"


def test_cors_rejects_unauthorized_origin(client: TestClient):
    """Verify CORS rejects unauthorized cross-site origins."""
    malicious_origin = "https://malicious-attacker.com"
    res = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": malicious_origin,
            "Access-Control-Request-Method": "POST",
        }
    )
    assert res.headers.get("access-control-allow-origin") != malicious_origin
    assert res.headers.get("access-control-allow-origin") != "*"


def test_cors_no_wildcard_with_credentials(client: TestClient):
    """Verify CORS configuration never uses wildcard ('*') when allow_credentials=True."""
    assert "*" not in settings.cors_origins


def test_csrf_protection_rejects_missing_header(client: TestClient, db_session: Session):
    """Verify that state-changing cookie endpoints (/auth/refresh, /auth/logout) reject requests missing anti-CSRF headers."""
    email = f"csrf_missing_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="CSRF Missing User")
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    cookie_val = login_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    # Call /auth/refresh WITHOUT X-Requested-With or X-CSRF-Token headers
    res = client.post("/api/v1/auth/refresh", cookies={settings.REFRESH_COOKIE_NAME: cookie_val})
    assert res.status_code == 403
    assert "CSRF protection error" in res.json()["detail"]

    # Call /auth/logout WITHOUT X-Requested-With or X-CSRF-Token headers
    logout_res = client.post("/api/v1/auth/logout", cookies={settings.REFRESH_COOKIE_NAME: cookie_val})
    assert logout_res.status_code == 403
    assert "CSRF protection error" in logout_res.json()["detail"]


def test_csrf_protection_accepts_valid_custom_header(client: TestClient, db_session: Session):
    """Verify that requests carrying the standard anti-CSRF header (X-Requested-With) pass protection checks."""
    email = f"csrf_valid_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="CSRF Valid User")
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    cookie_val = login_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    res = client.post(
        "/api/v1/auth/refresh",
        cookies={settings.REFRESH_COOKIE_NAME: cookie_val},
        headers={"X-Requested-With": "XMLHttpRequest"}
    )
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_csrf_protection_double_submit_token_mismatch_rejected(client: TestClient, db_session: Session):
    """Verify double-submit CSRF token mismatch is rejected with 403 Forbidden."""
    email = f"csrf_mismatch_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, hashed_password=get_password_hash("Password123!"), full_name="CSRF Mismatch User")
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    refresh_cookie = login_res.cookies.get(settings.REFRESH_COOKIE_NAME)

    res = client.post(
        "/api/v1/auth/refresh",
        cookies={
            settings.REFRESH_COOKIE_NAME: refresh_cookie,
            "csrf_token": "valid_cookie_csrf_value"
        },
        headers={
            "X-CSRF-Token": "invalid_header_csrf_value",
            "X-Requested-With": "XMLHttpRequest"
        }
    )
    assert res.status_code == 403
    assert "mismatch" in res.json()["detail"].lower()
