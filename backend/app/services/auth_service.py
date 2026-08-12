from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.repositories.user_repository import user_repo
from app.schemas.auth import UserCreate, UserLogin, Token
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, validate_password_strength, decode_token

class AuthService:
    def register_user(self, db: Session, user_in: UserCreate):
        validate_password_strength(user_in.password)
        existing = user_repo.get_by_email(db, user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email address already exists"
            )
        hashed_pwd = get_password_hash(user_in.password)
        user_data = user_in.model_dump()
        user_data["hashed_password"] = hashed_pwd
        del user_data["password"]
        
        user = user_repo.create(db, user_data)
        return user

    def authenticate_user(self, db: Session, login_data: UserLogin) -> Token:
        user = user_repo.get_by_email(db, login_data.email)
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive or deactivated user account"
            )
        
        access_token = create_access_token(subject=user.id, role=user.role)
        refresh_token = create_refresh_token(subject=user.id)
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            role=user.role,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email
        )

    def refresh_access_token(self, db: Session, refresh_token: str) -> Token:
        payload = decode_token(refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
        user = user_repo.get(db, int(user_id)) if user_id else None
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        new_access = create_access_token(subject=user.id, role=user.role)
        new_refresh = create_refresh_token(subject=user.id)
        return Token(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            role=user.role,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email
        )

auth_service = AuthService()
