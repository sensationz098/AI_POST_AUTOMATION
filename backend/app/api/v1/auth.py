from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import UserCreate, UserLogin, Token, UserResponse, RefreshTokenRequest
from app.services.auth_service import auth_service
from app.api.v1.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account (Admin or Editor)."""
    return auth_service.register_user(db, user_in)

@router.post("/login", response_model=Token)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and obtain JWT access & refresh tokens."""
    return auth_service.authenticate_user(db, login_data)

@router.post("/refresh", response_model=Token)
def refresh(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Obtain a fresh JWT access token using a valid refresh token."""
    return auth_service.refresh_access_token(db, request.refresh_token)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve details for currently authenticated user."""
    return current_user
