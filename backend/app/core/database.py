from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
import os

db_url = settings.get_database_url()
sqlite_connect_args = {"check_same_thread": False, "timeout": 30}

if os.getenv("USE_SQLITE", "false").lower() == "true" or "sqlite" in db_url:
    engine = create_engine(
        "sqlite:///./social_ai.db", connect_args=sqlite_connect_args
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
            "sqlite:///./social_ai.db", connect_args=sqlite_connect_args
        )

# Enable SQLite Write-Ahead Logging (WAL) & 30-second busy timeout to prevent "database is locked" errors
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
