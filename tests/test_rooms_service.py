"""
Unit tests for Rooms Service.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.rooms_service import app
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
    assert response.json() == {"status": "healthy", "service": "rooms"}


def test_create_room_as_admin(client, auth_headers_admin):
    """Test creating a room as admin."""
    room_data = {
        "name": "Conference Room A",
        "location": "Building B, Floor 2",
        "capacity": 20,
        "equipment": "Projector, Video Conference"
    }
    response = client.post("/rooms", json=room_data, headers=auth_headers_admin)
    assert response.status_code == 201
    assert response.json()["name"] == "Conference Room A"
    assert response.json()["capacity"] == 20


def test_create_room_as_regular_user(client, auth_headers_user):
    """Test creating a room as regular user (should fail)."""
    room_data = {
        "name": "Conference Room B",
        "location": "Building C, Floor 1",
        "capacity": 15,
        "equipment": "Whiteboard"
    }
    response = client.post("/rooms", json=room_data, headers=auth_headers_user)
    assert response.status_code == 403


def test_get_all_rooms(client, auth_headers_user, test_room):
    """Test getting all rooms."""
    response = client.get("/rooms", headers=auth_headers_user)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0


def test_get_rooms_with_filters(client, auth_headers_user, test_room):
    """Test getting rooms with capacity filter."""
    response = client.get("/rooms?min_capacity=5", headers=auth_headers_user)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_room_by_id(client, auth_headers_user, test_room):
    """Test getting specific room."""
    response = client.get(f"/rooms/{test_room.id}", headers=auth_headers_user)
    assert response.status_code == 200
    assert response.json()["id"] == test_room.id
    assert response.json()["name"] == test_room.name


def test_get_nonexistent_room(client, auth_headers_user):
    """Test getting nonexistent room."""
    response = client.get("/rooms/99999", headers=auth_headers_user)
    assert response.status_code == 404


def test_update_room_as_admin(client, auth_headers_admin, test_room):
    """Test updating room as admin."""
    update_data = {
        "name": "Updated Room Name",
        "capacity": 15
    }
    response = client.put(
        f"/rooms/{test_room.id}",
        json=update_data,
        headers=auth_headers_admin
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Room Name"
    assert response.json()["capacity"] == 15


def test_update_room_as_regular_user(client, auth_headers_user, test_room):
    """Test updating room as regular user (should fail)."""
    update_data = {
        "name": "Unauthorized Update"
    }
    response = client.put(
        f"/rooms/{test_room.id}",
        json=update_data,
        headers=auth_headers_user
    )
    assert response.status_code == 403


def test_toggle_room_status(client, auth_headers_admin, test_room):
    """Test toggling room availability status."""
    original_status = test_room.is_available
    response = client.put(
        f"/rooms/{test_room.id}/status",
        json={"is_available": not original_status},
        headers=auth_headers_admin
    )
    assert response.status_code == 200
    assert response.json()["is_available"] != original_status


def test_delete_room_as_admin(client, auth_headers_admin, test_room):
    """Test deleting room as admin."""
    response = client.delete(f"/rooms/{test_room.id}", headers=auth_headers_admin)
    assert response.status_code == 204


def test_search_available_rooms(client, auth_headers_user, test_room):
    """Test searching for available rooms."""
    future_start = datetime.utcnow() + timedelta(days=1)
    future_end = future_start + timedelta(hours=2)
    search_params = {
        "start_time": future_start.isoformat(),
        "end_time": future_end.isoformat()
    }
    response = client.get(
        "/rooms/available/search",
        params=search_params,
        headers=auth_headers_user
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
