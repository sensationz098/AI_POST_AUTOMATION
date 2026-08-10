from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
import os

# Check if SQLite fallback is desired for local standalone running when Postgres is unavailable
db_url = settings.get_database_url()
if os.getenv("USE_SQLITE", "false").lower() == "true" or "sqlite" in db_url:
    engine = create_engine(
        "sqlite:///./social_ai.db", connect_args={"check_same_thread": False}
    )
else:
    try:
        test_engine = create_engine(db_url, pool_pre_ping=True)
        with test_engine.connect() as conn:
            pass
        engine = test_engine
    except Exception:
        # Fallback to local SQLite database if Postgres service is offline
        engine = create_engine(
            "sqlite:///./social_ai.db", connect_args={"check_same_thread": False}
        )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
