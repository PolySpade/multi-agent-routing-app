"""
Database connection configuration for PostgreSQL.

Handles SQLAlchemy engine creation and session management.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from typing import Generator
import os
from dotenv import load_dotenv
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:admin1234@localhost:5432/masfro"
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL query logging
)

# Create SessionLocal class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create Base class for declarative models
Base = declarative_base()


def get_db() -> Generator:
    """
    Dependency function to get database session.

    Yields:
        Database session

    Example:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(OperationalError),
    before_sleep=before_sleep_log(logger, logging.INFO)
)
def init_db():
    """
    Initialize database by creating all tables with automatic retry.

    Retries up to 5 times with exponential backoff on connection failures.
    Should be called on application startup.

    Raises:
        OperationalError: If database is unreachable after all retry attempts
        Exception: For other database errors (e.g., permission issues)
    """
    from app.database.models import Base

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("[OK] Database tables created successfully")
    except OperationalError as e:
        logger.error(f"[ERROR] Error creating database tables (retrying): {e}")
        raise  # Tenacity will retry
    except Exception as e:
        logger.error(f"[ERROR] Error creating database tables (non-retryable): {e}")
        raise


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(OperationalError),
    before_sleep=before_sleep_log(logger, logging.INFO)
)
def check_connection() -> bool:
    """
    Check if database connection is working with automatic retry.

    Retries up to 5 times with exponential backoff (2s, 4s, 8s, 16s, 30s)
    on OperationalError (database unavailable, connection refused, etc.).

    Returns:
        True if connection successful, False otherwise

    Raises:
        OperationalError: If database is unreachable after all retry attempts
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("[OK] Database connection successful")
        return True
    except OperationalError as e:
        logger.error(f"[ERROR] Database connection failed: {e}")
        raise  # Tenacity will retry
    except Exception as e:
        # Non-retryable errors (e.g., authentication, invalid database name)
        logger.error(f"[ERROR] Database connection failed (non-retryable): {e}")
        return False
