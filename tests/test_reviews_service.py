"""
Unit tests for Reviews Service.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.reviews_service import app
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
    assert response.json() == {"status": "healthy", "service": "reviews"}


def test_create_review(client, auth_headers_user, test_user, test_room):
    """Test creating a review."""
    review_data = {
        "room_id": test_room.id,
        "rating": 4.5,
        "comment": "Great room with excellent facilities!"
    }
    response = client.post("/reviews", json=review_data, headers=auth_headers_user)
    assert response.status_code == 201
    assert response.json()["rating"] == 4.5
    assert response.json()["room_id"] == test_room.id


def test_create_review_invalid_rating(client, auth_headers_user, test_room):
    """Test creating review with invalid rating (should fail)."""
    review_data = {
        "room_id": test_room.id,
        "rating": 6.0,
        "comment": "Invalid rating"
    }
    response = client.post("/reviews", json=review_data, headers=auth_headers_user)
    assert response.status_code == 422  # Pydantic validation error


def test_create_duplicate_review(client, auth_headers_user, test_room, db):
    """Test creating duplicate review for same room (should fail)."""
    from shared.models import Review
    
    # Create first review
    review_data = {
        "room_id": test_room.id,
        "rating": 4.0,
        "comment": "First review"
    }
    response1 = client.post("/reviews", json=review_data, headers=auth_headers_user)
    assert response1.status_code == 201
    
    # Try to create second review for same room
    review_data2 = {
        "room_id": test_room.id,
        "rating": 5.0,
        "comment": "Second review"
    }
    response2 = client.post("/reviews", json=review_data2, headers=auth_headers_user)
    assert response2.status_code == 400


def test_get_all_reviews(client, auth_headers_user):
    """Test getting all reviews."""
    response = client.get("/reviews", headers=auth_headers_user)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_room_reviews(client, auth_headers_user, test_room):
    """Test getting reviews for specific room."""
    response = client.get(f"/reviews/room/{test_room.id}", headers=auth_headers_user)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_update_review(client, auth_headers_user, test_user, test_room, db):
    """Test updating own review."""
    from shared.models import Review
    
    # Create review first
    review = Review(
        user_id=test_user.id,
        room_id=test_room.id,
        rating=3.0,
        comment="Original comment"
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    
    # Update review
    update_data = {
        "rating": 4.5,
        "comment": "Updated comment"
    }
    response = client.put(
        f"/reviews/{review.id}",
        json=update_data,
        headers=auth_headers_user
    )
    assert response.status_code == 200
    assert response.json()["rating"] == 4.5
    assert response.json()["comment"] == "Updated comment"


def test_delete_review(client, auth_headers_user, test_user, test_room, db):
    """Test deleting own review."""
    from shared.models import Review
    
    # Create review first
    review = Review(
        user_id=test_user.id,
        room_id=test_room.id,
        rating=3.0,
        comment="To be deleted"
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    
    # Delete review
    response = client.delete(f"/reviews/{review.id}", headers=auth_headers_user)
    assert response.status_code == 204


def test_flag_review(client, auth_headers_user, test_admin, test_room, db):
    """Test flagging a review."""
    from shared.models import Review
    
    # Create review by admin
    review = Review(
        user_id=test_admin.id,
        room_id=test_room.id,
        rating=1.0,
        comment="Inappropriate content"
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    
    # Flag review
    flag_data = {
        "reason": "Offensive language"
    }
    response = client.put(
        f"/reviews/{review.id}/flag",
        json=flag_data,
        headers=auth_headers_user
    )
    assert response.status_code == 200
    assert response.json()["is_flagged"] == True


def test_moderate_review_as_moderator(client, auth_headers_moderator, test_admin, test_room, db):
    """Test moderating a review as moderator."""
    from shared.models import Review
    
    # Create flagged review
    review = Review(
        user_id=test_admin.id,
        room_id=test_room.id,
        rating=2.0,
        comment="Flagged content",
        is_flagged=True
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    
    # Moderate review
    moderation_data = {
        "is_moderated": True,
        "action": "approve"
    }
    response = client.put(
        f"/reviews/{review.id}/moderate",
        json=moderation_data,
        headers=auth_headers_moderator
    )
    assert response.status_code == 200
    assert response.json()["is_moderated"] == True
    assert response.json()["is_flagged"] == False


def test_moderate_review_as_regular_user(client, auth_headers_user, test_admin, test_room, db):
    """Test moderating a review as regular user (should fail)."""
    from shared.models import Review
    
    # Create flagged review
    review = Review(
        user_id=test_admin.id,
        room_id=test_room.id,
        rating=2.0,
        comment="Flagged content",
        is_flagged=True
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    
    # Try to moderate
    moderation_data = {
        "is_moderated": True,
        "action": "approve"
    }
    response = client.put(
        f"/reviews/{review.id}/moderate",
        json=moderation_data,
        headers=auth_headers_user
    )
    assert response.status_code == 403


def test_unauthorized_access(client):
    """Test accessing protected endpoint without authentication."""
    response = client.get("/reviews")
    assert response.status_code == 401
