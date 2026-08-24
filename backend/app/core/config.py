from typing import List, Optional, Union
import os
import sys
import logging
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Social AI Automation Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment mode: development | staging | production
    APP_ENV: str = Field(default="development", env="APP_ENV")
    
    # Security & JWT
    SECRET_KEY: str = Field(default="super-secret-jwt-key-for-social-ai-automation-2026", env="SECRET_KEY")
    TOKEN_ENCRYPTION_KEY: Optional[str] = Field(default=None, env="TOKEN_ENCRYPTION_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes (short-lived access token)
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    REFRESH_COOKIE_NAME: str = "refresh_token"
    REFRESH_COOKIE_PATH: str = "/api/v1/auth"
    REFRESH_COOKIE_SECURE: Optional[bool] = Field(default=None, env="REFRESH_COOKIE_SECURE")
    
    # Rate Limiting
    RATE_LIMIT_LOGIN: str = "5 per minute"
    RATE_LIMIT_REGISTER: str = "5 per hour"
    RATE_LIMIT_PUBLISH: str = "30 per minute"
    RATE_LIMIT_AI: str = "20 per minute"

    @property
    def is_cookie_secure(self) -> bool:
        if self.REFRESH_COOKIE_SECURE is not None:
            return self.REFRESH_COOKIE_SECURE
        return self.APP_ENV.lower() == "production"

    @property
    def refresh_cookie_samesite(self) -> str:
        # Cross-site cookies (e.g. Vercel frontend <-> Render backend) REQUIRE SameSite=None and Secure=True.
        # For local HTTP development without TLS, SameSite must be "lax".
        return "none" if self.is_cookie_secure else "lax"
    
    # Database & Connection Pooling

    POSTGRES_SERVER: str = Field(default="localhost", env="POSTGRES_SERVER")
    POSTGRES_USER: str = Field(default="postgres", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="postgres", env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(default="social_ai_db", env="POSTGRES_DB")
    POSTGRES_PORT: str = Field(default="5432", env="POSTGRES_PORT")
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")
    DB_POOL_SIZE: int = Field(default=10, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=20, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=1800, env="DB_POOL_RECYCLE")
    
    # Cache / Celery Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # OpenAI / OpenRouter API
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    OPENAI_BASE_URL: Optional[str] = Field(default=None, env="OPENAI_BASE_URL")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    OPENAI_IMAGE_MODEL: str = Field(default="dall-e-3", env="OPENAI_IMAGE_MODEL")
    
    # Cloudinary Media CDN & Upload Size Limits
    CLOUDINARY_CLOUD_NAME: Optional[str] = Field(default=None, env="CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: Optional[str] = Field(default=None, env="CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: Optional[str] = Field(default=None, env="CLOUDINARY_API_SECRET")
    MAX_VIDEO_UPLOAD_BYTES: int = Field(default=500 * 1024 * 1024, env="MAX_VIDEO_UPLOAD_BYTES")  # 500 MB max for videos
    MAX_IMAGE_UPLOAD_BYTES: int = Field(default=30 * 1024 * 1024, env="MAX_IMAGE_UPLOAD_BYTES")   # 30 MB max for images
    
    # Meta Graph API (Facebook & Instagram OAuth)
    META_APP_ID: Optional[str] = Field(default=None, env="META_APP_ID")
    META_APP_SECRET: Optional[str] = Field(default=None, env="META_APP_SECRET")
    META_GRAPH_API_VERSION: str = "v19.0"
    META_OAUTH_REDIRECT_URI: str = Field(default="http://localhost:8000/api/v1/meta/oauth/callback", env="META_OAUTH_REDIRECT_URI")
    META_MOCK_MODE: bool = Field(default=False, env="META_MOCK_MODE")
    FRONTEND_URL: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    META_CONFIG_ID: Optional[str] = Field(default=None, env="META_CONFIG_ID")
    
    # Meta Long Video Processing & Polling Configurations
    META_VIDEO_PROCESSING_MAX_SECONDS: int = Field(default=300, env="META_VIDEO_PROCESSING_MAX_SECONDS")
    META_VIDEO_POLL_INITIAL_SECONDS: int = Field(default=3, env="META_VIDEO_POLL_INITIAL_SECONDS")
    META_VIDEO_POLL_MAX_SECONDS: int = Field(default=15, env="META_VIDEO_POLL_MAX_SECONDS")
    META_VIDEO_UPLOAD_TIMEOUT_SECONDS: int = Field(default=120, env="META_VIDEO_UPLOAD_TIMEOUT_SECONDS")
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://ai-post-automation.vercel.app",
        ],
        env="BACKEND_CORS_ORIGINS"
    )


    @property
    def cors_origins(self) -> List[str]:
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            import json
            try:
                return json.loads(self.BACKEND_CORS_ORIGINS)
            except Exception:
                return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]
        return self.BACKEND_CORS_ORIGINS

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    def validate_production_secrets(self) -> None:
        """Validate production configuration and fail fast if secrets are missing or insecure."""
        if self.APP_ENV.lower() != "production":
            return

        missing_fields = []
        db_url = self.get_database_url()
        if "sqlite" in db_url.lower():
            missing_fields.append("DATABASE_URL (SQLite is strictly forbidden in production. Use PostgreSQL: postgresql+psycopg://...)")
        if not self.SECRET_KEY or "super-secret" in self.SECRET_KEY or len(self.SECRET_KEY) < 32:
            missing_fields.append("SECRET_KEY (must be a strong, unique secret of at least 32 characters)")
        if not self.TOKEN_ENCRYPTION_KEY or len(self.TOKEN_ENCRYPTION_KEY) < 32:
            missing_fields.append("TOKEN_ENCRYPTION_KEY (must be a Fernet key or 32+ char key for token encryption at rest)")
        if not self.DATABASE_URL and self.POSTGRES_PASSWORD == "postgres":
            missing_fields.append("DATABASE_URL or non-default POSTGRES_PASSWORD")
        if not self.REDIS_URL:
            missing_fields.append("REDIS_URL")
        if not self.META_APP_ID or self.META_APP_ID.startswith("your-"):
            missing_fields.append("META_APP_ID")
        if not self.META_APP_SECRET or self.META_APP_SECRET.startswith("your-"):
            missing_fields.append("META_APP_SECRET")
        if not self.CLOUDINARY_CLOUD_NAME or not self.CLOUDINARY_API_KEY or not self.CLOUDINARY_API_SECRET:
            missing_fields.append("CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET")
        if not self.OPENAI_API_KEY:
            missing_fields.append("OPENAI_API_KEY")

        if missing_fields:
            error_msg = f"CRITICAL PRODUCTION CONFIGURATION ERROR:\nApplication in APP_ENV=production cannot start due to missing or insecure configuration settings:\n - " + "\n - ".join(missing_fields)
            logger.critical(error_msg)
            raise ValueError(error_msg)

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"

settings = Settings()
settings.validate_production_secrets()
