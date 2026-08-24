import secrets
from fastapi import APIRouter, Depends, status, Request, Response, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limit import limiter
from app.schemas.auth import UserCreate, UserLogin, Token, UserResponse
from app.services.auth_service import auth_service
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


def set_refresh_cookie(response: Response, refresh_token_str: str) -> str:
    secure = settings.is_cookie_secure
    samesite = settings.refresh_cookie_samesite

    # 1. Set HttpOnly Refresh Token Cookie
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token_str,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path=settings.REFRESH_COOKIE_PATH,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
    )

    # 2. Set Readable CSRF Token Cookie for Double-Submit CSRF protection
    csrf_token_str = secrets.token_urlsafe(32)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token_str,
        httponly=False,
        secure=secure,
        samesite=samesite,
        path="/",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
    )
    return csrf_token_str


def clear_refresh_cookie(response: Response) -> None:
    secure = settings.is_cookie_secure
    samesite = settings.refresh_cookie_samesite

    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        httponly=True,
        secure=secure,
        samesite=samesite,
    )
    response.delete_cookie(
        key="csrf_token",
        path="/",
        httponly=False,
        secure=secure,
        samesite=samesite,
    )


def verify_csrf_protection(request: Request) -> None:
    """
    Anti-CSRF defense for cookie-authenticated POST endpoints (/auth/refresh, /auth/logout).
    Enforces anti-CSRF custom request header (X-Requested-With or X-CSRF-Token).
    Cross-site HTML forms cannot set custom headers. Cross-site XHR/fetch with custom headers triggers CORS preflight.
    """
    requested_with = request.headers.get("x-requested-with")
    csrf_header = request.headers.get("x-csrf-token")
    csrf_cookie = request.cookies.get("csrf_token")

    # Reject if no anti-CSRF custom header is provided
    if not requested_with and not csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF protection error: Missing required anti-CSRF header (X-Requested-With or X-CSRF-Token)."
        )

    # If double-submit CSRF header is provided alongside cookie, verify token match
    if csrf_header and csrf_cookie and csrf_header != csrf_cookie:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF protection error: Anti-CSRF token mismatch."
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def register(request: Request, user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account (Admin or Editor)."""
    return auth_service.register_user(db, user_in)


@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, response: Response, login_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user, set HttpOnly refresh cookie & CSRF cookie, and obtain short-lived JWT access token."""
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    token_resp, refresh_token_str = auth_service.authenticate_user(
        db=db,
        login_data=login_data,
        user_agent=user_agent,
        ip_address=ip_address
    )
    set_refresh_cookie(response, refresh_token_str)
    return token_resp


@router.post("/refresh", response_model=Token)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    """Obtain a fresh short-lived access token using a valid HttpOnly refresh cookie."""
    verify_csrf_protection(request)
    raw_refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    try:
        token_resp, new_refresh_token_str = auth_service.refresh_access_token(
            db=db,
            raw_refresh_token=raw_refresh_token,
            user_agent=user_agent,
            ip_address=ip_address
        )
        set_refresh_cookie(response, new_refresh_token_str)
        return token_resp
    except HTTPException as exc:
        clear_refresh_cookie(response)
        raise exc


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Revoke active refresh token session and clear HttpOnly cookie."""
    verify_csrf_protection(request)
    raw_refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    auth_service.logout_user(db, raw_refresh_token)
    clear_refresh_cookie(response)
    return {"detail": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve details for currently authenticated user."""
    return current_user
