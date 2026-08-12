from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.security import decode_token
from app.repositories.user_repository import user_repo
from app.models.user import User
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

def get_current_user(
    db: Session = Depends(get_db),
    header_token: Optional[str] = Depends(oauth2_scheme),
    token_param: Optional[str] = Query(None, alias="token")
) -> User:
    """Strictly authenticate current user via JWT bearer token (header or query parameter)."""
    token = header_token or token_param
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing. Please log in.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_token(token, expected_type="access")
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
