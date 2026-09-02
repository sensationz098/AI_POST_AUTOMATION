import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import create_access_token

def test_openapi_contains_http_bearer_security_scheme(client: TestClient):
    """
    Verify that OpenAPI schema defines HTTPBearer JWT security scheme,
    enabling Swagger UI to present a simple 'Bearer' token input box instead of OAuth2 password form.
    """
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    assert "components" in schema
    assert "securitySchemes" in schema["components"]
    security_schemes = schema["components"]["securitySchemes"]
    
    assert "HTTPBearer" in security_schemes
    bearer_scheme = security_schemes["HTTPBearer"]
    assert bearer_scheme["type"] == "http"
    assert bearer_scheme["scheme"] == "bearer"


def test_protected_endpoint_accepts_bearer_authorization_header(client: TestClient, db_session: Session):
    """
    Verify protected endpoints accept 'Authorization: Bearer <token>' header successfully.
    """
    user = User(
        email="swagger_test_user@example.com",
        full_name="Swagger Test User",
        hashed_password="hashed_password",
        is_active=True,
        role="Editor"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(subject=str(user.id), role=user.role)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "swagger_test_user@example.com"
    assert data["id"] == user.id


def test_protected_endpoint_rejects_missing_or_invalid_bearer_token(client: TestClient):
    """
    Verify protected endpoints reject requests without a valid Bearer token with 401 Unauthorized.
    """
    # 1. Missing token
    res_missing = client.get("/api/v1/auth/me")
    assert res_missing.status_code == 401
    assert res_missing.headers.get("WWW-Authenticate") == "Bearer"

    # 2. Invalid token
    res_invalid = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_garbage_token"}
    )
    assert res_invalid.status_code == 401


def test_login_endpoint_accepts_json_and_returns_access_token(client: TestClient, db_session: Session):
    """
    Verify that existing POST /api/v1/auth/login endpoint works with JSON body and returns access_token.
    """
    from app.core.security import get_password_hash
    email = "json_login_test@example.com"
    password = "Password123!"

    user = User(
        email=email,
        full_name="JSON Login User",
        hashed_password=get_password_hash(password),
        is_active=True,
        role="Editor"
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
