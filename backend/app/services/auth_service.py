import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories.user_repository import user_repo
from app.repositories.refresh_token_repository import refresh_token_repo
from app.schemas.auth import UserCreate, UserLogin, Token
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    validate_password_strength,
    decode_token,
    hash_token,
)


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

    def authenticate_user(
        self,
        db: Session,
        login_data: UserLogin,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[Token, str]:
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

        family_id = str(uuid.uuid4())
        access_token = create_access_token(subject=user.id, role=user.role)
        raw_refresh_token = create_refresh_token(subject=user.id, family_id=family_id)

        token_h = hash_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

        refresh_token_repo.create(
            db=db,
            user_id=user.id,
            token_hash=token_h,
            family_id=family_id,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )

        token_response = Token(
            access_token=access_token,
            token_type="bearer",
            role=user.role,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email
        )
        return token_response, raw_refresh_token

    def refresh_access_token(
        self,
        db: Session,
        raw_refresh_token: Optional[str],
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[Token, str]:
        if not raw_refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token cookie missing. Please log in.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = decode_token(raw_refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
        family_id = payload.get("family_id")
        
        token_h = hash_token(raw_refresh_token)
        refresh_record = refresh_token_repo.get_by_hash(db, token_h)

        # REUSE DETECTION: If token record exists but was already revoked
        if refresh_record and refresh_record.revoked_at is not None:
            # Revoke entire token family due to suspected reuse attack
            if refresh_record.family_id:
                refresh_token_repo.revoke_family(db, refresh_record.family_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token reuse detected. All sessions revoked for security.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not refresh_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token session",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check expiration against database record and UTC time
        now = datetime.now(timezone.utc)
        record_exp = refresh_record.expires_at
        if record_exp.tzinfo is None:
            record_exp = record_exp.replace(tzinfo=timezone.utc)
            
        if record_exp < now:
            refresh_token_repo.revoke(db, refresh_record)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Expired refresh token session",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = user_repo.get(db, int(user_id)) if user_id else None
        if not user or not user.is_active:
            refresh_token_repo.revoke(db, refresh_record)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive or no longer exists",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # REFRESH TOKEN ROTATION:
        active_family_id = refresh_record.family_id or family_id or str(uuid.uuid4())
        new_raw_refresh_token = create_refresh_token(subject=user.id, family_id=active_family_id)
        new_token_h = hash_token(new_raw_refresh_token)
        new_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

        # Revoke old refresh token & mark replacement
        refresh_token_repo.revoke(db, refresh_record, replaced_by=new_token_h)

        # Store rotated refresh token session
        refresh_token_repo.create(
            db=db,
            user_id=user.id,
            token_hash=new_token_h,
            family_id=active_family_id,
            expires_at=new_expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )

        new_access_token = create_access_token(subject=user.id, role=user.role)

        token_response = Token(
            access_token=new_access_token,
            token_type="bearer",
            role=user.role,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email
        )
        return token_response, new_raw_refresh_token

    def logout_user(self, db: Session, raw_refresh_token: Optional[str]) -> bool:
        if raw_refresh_token:
            try:
                token_h = hash_token(raw_refresh_token)
                record = refresh_token_repo.get_by_hash(db, token_h)
                if record and record.revoked_at is None:
                    refresh_token_repo.revoke(db, record)
            except Exception:
                pass
        return True


auth_service = AuthService()
