"""
Pytest configuration and fixtures for testing all services.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import Base, get_db
from shared.models import User, Room, Booking, Review, UserRole
from shared.auth import get_password_hash


# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def override_get_db(db):
    """Override the get_db dependency."""
    def _override_get_db():
        try:
            yield db
        finally:
            pass
    return _override_get_db


@pytest.fixture(scope="function")
def test_user(db):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=get_password_hash("testpassword"),
        name="Test User",
        role=UserRole.REGULAR_USER,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin(db):
    """Create a test admin user."""
    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=get_password_hash("adminpassword"),
        name="Admin User",
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def test_moderator(db):
    """Create a test moderator user."""
    moderator = User(
        username="moderator",
        email="moderator@example.com",
        password_hash=get_password_hash("modpassword"),
        name="Moderator User",
        role=UserRole.MODERATOR,
        is_active=True
    )
    db.add(moderator)
    db.commit()
    db.refresh(moderator)
    return moderator


@pytest.fixture(scope="function")
def test_room(db):
    """Create a test room."""
    room = Room(
        name="Test Room",
        location="Building A, Floor 1",
        capacity=10,
        equipment="Projector, Whiteboard",
        is_available=True
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@pytest.fixture(scope="function")
def auth_headers_user(test_user):
    """Get authentication headers for test user."""
    from shared.auth import create_access_token
    token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def auth_headers_admin(test_admin):
    """Get authentication headers for admin user."""
    from shared.auth import create_access_token
    token = create_access_token(data={"sub": test_admin.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def auth_headers_moderator(test_moderator):
    """Get authentication headers for moderator user."""
    from shared.auth import create_access_token
    token = create_access_token(data={"sub": test_moderator.username})
    return {"Authorization": f"Bearer {token}"}
