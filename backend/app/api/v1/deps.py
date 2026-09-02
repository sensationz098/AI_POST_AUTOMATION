from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import decode_token
from app.repositories.user_repository import user_repo
from app.models.user import User

security_bearer = HTTPBearer(
    bearerFormat="JWT",
    scheme_name="HTTPBearer",
    description="Enter your access token below.",
    auto_error=False
)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    auth_credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> User:
    """Strictly authenticate current user via Authorization: Bearer header only."""
    header_token = None
    if auth_credentials and auth_credentials.credentials:
        header_token = auth_credentials.credentials
    else:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            header_token = auth_header.split(" ", 1)[1].strip()

    if not header_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing. Please log in.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_token(header_token, expected_type="access")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = user_repo.get(db, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with token not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact an administrator."
        )

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verify authenticated user has Admin permissions loaded from database."""
    if current_user.role.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role privilege required for this action",
        )
    return current_user
