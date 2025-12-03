"""
Unit tests for Bookings Service.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.bookings_service import app
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
    assert response.json() == {"status": "healthy", "service": "bookings"}


def test_create_booking(client, auth_headers_user, test_user, test_room):
    """Test creating a booking."""
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=2)
    
    booking_data = {
        "room_id": test_room.id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "purpose": "Team Meeting"
    }
    response = client.post("/bookings", json=booking_data, headers=auth_headers_user)
    assert response.status_code == 201
    assert response.json()["room_id"] == test_room.id
    assert response.json()["purpose"] == "Team Meeting"


def test_create_booking_past_time(client, auth_headers_user, test_room):
    """Test creating booking with past time (should fail)."""
    start_time = datetime.utcnow() - timedelta(days=1)
    end_time = start_time + timedelta(hours=2)
    
    booking_data = {
        "room_id": test_room.id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "purpose": "Past Meeting"
    }
    response = client.post("/bookings", json=booking_data, headers=auth_headers_user)
    assert response.status_code == 400


def test_create_booking_invalid_time_range(client, auth_headers_user, test_room):
    """Test creating booking with end time before start time (should fail)."""
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time - timedelta(hours=1)
    
    booking_data = {
        "room_id": test_room.id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "purpose": "Invalid Meeting"
    }
    response = client.post("/bookings", json=booking_data, headers=auth_headers_user)
    assert response.status_code == 400


def test_get_all_bookings_as_user(client, auth_headers_user, test_user):
    """Test getting all bookings as regular user (sees own only)."""
    response = client.get("/bookings", headers=auth_headers_user)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_all_bookings_as_admin(client, auth_headers_admin):
    """Test getting all bookings as admin (sees all)."""
    response = client.get("/bookings", headers=auth_headers_admin)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_check_availability(client, auth_headers_user, test_room):
    """Test checking room availability."""
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=2)
    
    availability_data = {
        "room_id": test_room.id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat()
    }
    response = client.post(
        "/bookings/check-availability",
        json=availability_data,
        headers=auth_headers_user
    )
    assert response.status_code == 200
    assert "available" in response.json()
    assert "conflicting_bookings" in response.json()


def test_get_user_bookings(client, auth_headers_user, test_user):
    """Test getting bookings for specific user."""
    response = client.get(f"/bookings/user/{test_user.id}", headers=auth_headers_user)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_unauthorized_access(client):
    """Test accessing protected endpoint without authentication."""
    response = client.get("/bookings")
    assert response.status_code == 401
