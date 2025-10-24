"""
Database connection and session management
Day 1, Step 1: Database connection pooling
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create engine with connection pooling
# QueuePool maintains a pool of connections for reuse
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,          # Number of connections to maintain in pool
    max_overflow=10,      # Maximum overflow connections allowed
    pool_timeout=30,      # Timeout for getting connection from pool
    pool_recycle=1800,    # Recycle connections after 30 minutes
    echo=False            # Set to True for SQL query logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Get database session
    Used as a dependency in FastAPI endpoints
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Test database connection
def test_connection():
    """
    Test database connectivity
    Used in health checks
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False