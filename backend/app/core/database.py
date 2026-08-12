from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
import os

db_url = settings.get_database_url()
sqlite_connect_args = {"check_same_thread": False, "timeout": 30}

if "sqlite" in db_url.lower():
    if settings.APP_ENV.lower() == "production":
        raise ValueError("CRITICAL DATABASE CONFIGURATION ERROR: SQLite database is forbidden in APP_ENV=production. Use PostgreSQL.")
    engine = create_engine(db_url, connect_args=sqlite_connect_args)
else:
    # PostgreSQL production-safe engine with configurable connection pooling & pre-ping
    engine = create_engine(
        db_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True
    )

# Enable SQLite Write-Ahead Logging (WAL) & 30-second busy timeout for local dev
if "sqlite" in str(engine.url):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.close()
        except Exception:
            pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
