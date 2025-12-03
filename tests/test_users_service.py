"""
Unit tests for Users Service.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.users_service import app
from shared.database import get_db


@pytest.fixture(scope="function")
def client(override_get_db):
    """Create a test client."""
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "users"}


def test_register_user(client):
    """Test user registration."""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "newpassword123",
        "name": "New User"
    }
    response = client.post("/register", json=user_data)
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"
    assert response.json()["email"] == "newuser@example.com"
    assert "id" in response.json()


def test_register_duplicate_username(client, test_user):
    """Test registration with duplicate username."""
    user_data = {
        "username": "testuser",
        "email": "different@example.com",
        "password": "password123",
        "name": "Different User"
    }
    response = client.post("/register", json=user_data)
    assert response.status_code == 400


def test_register_duplicate_email(client, test_user):
    """Test registration with duplicate email."""
    user_data = {
        "username": "differentuser",
        "email": "test@example.com",
        "password": "password123",
        "name": "Different User"
    }
    response = client.post("/register", json=user_data)
    assert response.status_code == 400


def test_login_success(client, test_user):
    """Test successful login."""
    login_data = {
        "username": "testuser",
        "password": "testpassword"
    }
    response = client.post("/login", json=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
    assert "user" in response.json()


def test_login_wrong_password(client, test_user):
    """Test login with wrong password."""
    login_data = {
        "username": "testuser",
        "password": "wrongpassword"
    }
    response = client.post("/login", json=login_data)
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """Test login with nonexistent user."""
    login_data = {
        "username": "nonexistent",
        "password": "password123"
    }
    response = client.post("/login", json=login_data)
    assert response.status_code == 401


def test_get_all_users_as_admin(client, auth_headers_admin, test_user):
    """Test getting all users as admin."""
    response = client.get("/users", headers=auth_headers_admin)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_all_users_as_regular_user(client, auth_headers_user):
    """Test getting all users as regular user (should fail)."""
    response = client.get("/users", headers=auth_headers_user)
    assert response.status_code == 403


def test_get_user_self(client, auth_headers_user, test_user):
    """Test getting own user information."""
    response = client.get(f"/users/{test_user.username}", headers=auth_headers_user)
    assert response.status_code == 200
    assert response.json()["username"] == test_user.username


def test_update_user_self(client, auth_headers_user, test_user):
    """Test updating own user information."""
    update_data = {
        "name": "Updated Name"
    }
    response = client.put(
        f"/users/{test_user.username}",
        json=update_data,
        headers=auth_headers_user
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_update_user_role_as_regular_user(client, auth_headers_user, test_user):
    """Test updating user role as regular user (should fail)."""
    update_data = {
        "role": "admin"
    }
    response = client.put(
        f"/users/{test_user.username}",
        json=update_data,
        headers=auth_headers_user
    )
    assert response.status_code == 403


def test_delete_user_self(client, auth_headers_user, test_user):
    """Test deleting own account."""
    response = client.delete(f"/users/{test_user.username}", headers=auth_headers_user)
    assert response.status_code == 204


def test_unauthorized_access(client):
    """Test accessing protected endpoint without authentication."""
    response = client.get("/users")
    assert response.status_code == 401
