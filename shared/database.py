"""
Database configuration and session management.

This module provides database connection and session management
for all services in the Smart Meeting Room Management System.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@db:5432/smartmeetingroom"
)

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    Get database session.
    
    Yields:
        Session: Database session
        
    Example:
        >>> db = next(get_db())
        >>> # Use db session
        >>> db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    
    Creates all tables defined in the models.
    
    Example:
        >>> init_db()
    """
    Base.metadata.create_all(bind=engine)
