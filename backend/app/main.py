from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.security import get_password_hash
import app.models  # Register all models with SQLAlchemy Base

# Import API routers
from app.api.v1.auth import router as auth_router
from app.api.v1.brands import router as brand_router
from app.api.v1.posts import router as post_router
from app.api.v1.ai import router as ai_router
from app.api.v1.meta import router as meta_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.audit import router as audit_router
from app.api.v1.health import router as health_router

from sqlalchemy import inspect, text

def run_db_migrations():
    """Ensure database schema is up-to-date with new model columns."""
    try:
        inspector = inspect(engine)
        if "meta_accounts" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("meta_accounts")]
            if "logo_url" not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE meta_accounts ADD COLUMN logo_url VARCHAR(500);"))
                    conn.commit()
    except Exception as e:
        print(f"Migration notice: {e}")

run_db_migrations()

# Create database tables automatically if not already existing
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="Production-Ready AI Social Media Automation Platform for Facebook & Instagram API."
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files route for uploaded post photos/graphics
import os
from fastapi.staticfiles import StaticFiles
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include v1 API routes
app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(brand_router, prefix=settings.API_V1_STR)
app.include_router(post_router, prefix=settings.API_V1_STR)
app.include_router(ai_router, prefix=settings.API_V1_STR)
app.include_router(meta_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def seed_default_data():
    """Seed a default Admin user and Brand Profile on first run so the app works immediately."""
    from app.models.user import User
    from app.models.brand import BrandProfile
    from app.models.meta_account import MetaAccount
    from datetime import datetime

    db = SessionLocal()
    try:
        # Create default admin user if not exists
        existing = db.query(User).filter(User.email == "admin@socialai.com").first()
        if not existing:
            user = User(
                email="admin@socialai.com",
                full_name="Admin User",
                hashed_password=get_password_hash("admin123"),
                role="Admin",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Create default brand profile
            brand = BrandProfile(
                name="Apex Innovations",
                logo_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=120&auto=format&fit=crop&q=80",
                brand_colors=["#6366F1", "#06B6D4"],
                tone_of_voice="Professional, Energetic & Visionary",
                target_audience="Tech-savvy entrepreneurs, developers & agency leads",
                cta_style="Urgency-driven & Value focused",
                industry="AI & Software",
                user_id=user.id,
            )
            db.add(brand)
            db.commit()
            db.refresh(brand)

            # Create default sandbox Meta account
            meta = MetaAccount(
                brand_id=brand.id,
                access_token="sandbox_token",
                facebook_page_id="sandbox",
                facebook_page_name="Apex Innovations (Sandbox)",
                instagram_account_id="sandbox",
                instagram_username="apex_innovations",
                is_connected=True,
                last_synced_at=datetime.utcnow(),
            )
            db.add(meta)
            db.commit()
    finally:
        db.close()

@app.get("/")
def root():
    return {
        "message": "Welcome to Social AI Automation Platform API",
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "default_login": {"email": "admin@socialai.com", "password": "admin123"}
    }
