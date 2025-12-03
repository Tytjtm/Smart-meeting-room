"""
Reviews Service

This service handles room and service reviews from users.

Endpoints:
    - POST /reviews: Submit a review for a meeting room
    - GET /reviews: Get all reviews
    - GET /reviews/{review_id}: Get specific review
    - GET /reviews/room/{room_id}: Get reviews for a specific room
    - PUT /reviews/{review_id}: Update a review
    - DELETE /reviews/{review_id}: Delete a review
    - PUT /reviews/{review_id}/flag: Flag a review for moderation
    - PUT /reviews/{review_id}/moderate: Moderate a flagged review
"""

from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, init_db
from shared.models import Review, User, Room, UserRole
from shared.auth import decode_access_token, sanitize_input, validate_rating

app = FastAPI(title="Reviews Service", version="1.0.0")
security = HTTPBearer()


class ReviewCreate(BaseModel):
    """Review creation request model."""
    room_id: int
    rating: float = Field(..., ge=1.0, le=5.0)
    comment: Optional[str] = Field(None, max_length=1000)


class ReviewUpdate(BaseModel):
    """Review update request model."""
    rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    comment: Optional[str] = Field(None, max_length=1000)


class ReviewResponse(BaseModel):
    """Review response model."""
    id: int
    user_id: int
    username: str
    room_id: int
    room_name: str
    rating: float
    comment: Optional[str]
    is_flagged: bool
    is_moderated: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewFlag(BaseModel):
    """Review flag model."""
    reason: Optional[str] = Field(None, max_length=500)


class ReviewModeration(BaseModel):
    """Review moderation model."""
    is_moderated: bool
    action: str = Field(..., pattern="^(approve|remove|restore)$")


# Dependency to get current user
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user


# Dependency for moderator or admin role
def require_moderator(current_user: User = Depends(get_current_user)) -> User:
    """Require moderator or admin role."""
    if current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator or Admin privileges required"
        )
    return current_user


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.post("/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a review for a meeting room.
    
    Args:
        review_data: Review creation data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ReviewResponse: Created review data
        
    Raises:
        HTTPException: If room not found or validation fails
    """
    if not validate_rating(review_data.rating):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1.0 and 5.0"
        )
    
    room = db.query(Room).filter(Room.id == review_data.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    existing_review = db.query(Review).filter(
        Review.user_id == current_user.id,
        Review.room_id == review_data.room_id
    ).first()
    
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this room. Use update instead."
        )
    
    comment = sanitize_input(review_data.comment) if review_data.comment else None
    
    new_review = Review(
        user_id=current_user.id,
        room_id=review_data.room_id,
        rating=review_data.rating,
        comment=comment,
        is_flagged=False,
        is_moderated=False
    )
    
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    
    return ReviewResponse(
        id=new_review.id,
        user_id=new_review.user_id,
        username=current_user.username,
        room_id=new_review.room_id,
        room_name=room.name,
        rating=new_review.rating,
        comment=new_review.comment,
        is_flagged=new_review.is_flagged,
        is_moderated=new_review.is_moderated,
        created_at=new_review.created_at,
        updated_at=new_review.updated_at
    )


@app.get("/reviews", response_model=List[ReviewResponse])
def get_all_reviews(
    skip: int = 0,
    limit: int = 100,
    flagged_only: bool = Query(False, description="Show only flagged reviews"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all reviews.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        flagged_only: Filter for flagged reviews only
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[ReviewResponse]: List of reviews
    """
    query = db.query(Review)
    
    if flagged_only:
        if current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges to view flagged reviews"
            )
        query = query.filter(Review.is_flagged == True)
    
    reviews = query.offset(skip).limit(limit).all()
    
    result = []
    for review in reviews:
        result.append(ReviewResponse(
            id=review.id,
            user_id=review.user_id,
            username=review.user.username,
            room_id=review.room_id,
            room_name=review.room.name,
            rating=review.rating,
            comment=review.comment,
            is_flagged=review.is_flagged,
            is_moderated=review.is_moderated,
            created_at=review.created_at,
            updated_at=review.updated_at
        ))
    
    return result


@app.get("/reviews/{review_id}", response_model=ReviewResponse)
def get_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific review details.
    
    Args:
        review_id: Review ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ReviewResponse: Review data
        
    Raises:
        HTTPException: If review not found
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        username=review.user.username,
        room_id=review.room_id,
        room_name=review.room.name,
        rating=review.rating,
        comment=review.comment,
        is_flagged=review.is_flagged,
        is_moderated=review.is_moderated,
        created_at=review.created_at,
        updated_at=review.updated_at
    )


@app.get("/reviews/room/{room_id}", response_model=List[ReviewResponse])
def get_room_reviews(
    room_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all reviews for a specific room.
    
    Args:
        room_id: Room ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[ReviewResponse]: List of reviews for the room
        
    Raises:
        HTTPException: If room not found
    """
    # Check if room exists
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    reviews = db.query(Review).filter(
        Review.room_id == room_id
    ).offset(skip).limit(limit).all()
    
    result = []
    for review in reviews:
        result.append(ReviewResponse(
            id=review.id,
            user_id=review.user_id,
            username=review.user.username,
            room_id=review.room_id,
            room_name=review.room.name,
            rating=review.rating,
            comment=review.comment,
            is_flagged=review.is_flagged,
            is_moderated=review.is_moderated,
            created_at=review.created_at,
            updated_at=review.updated_at
        ))
    
    return result


@app.put("/reviews/{review_id}", response_model=ReviewResponse)
def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a review.
    
    Args:
        review_id: Review ID
        review_data: Updated review data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ReviewResponse: Updated review data
        
    Raises:
        HTTPException: If review not found or unauthorized
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    if review.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this review"
        )
    
    if review_data.rating is not None:
        if not validate_rating(review_data.rating):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1.0 and 5.0"
            )
        review.rating = review_data.rating
    
    if review_data.comment is not None:
        review.comment = sanitize_input(review_data.comment)
    
    review.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(review)
    
    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        username=review.user.username,
        room_id=review.room_id,
        room_name=review.room.name,
        rating=review.rating,
        comment=review.comment,
        is_flagged=review.is_flagged,
        is_moderated=review.is_moderated,
        created_at=review.created_at,
        updated_at=review.updated_at
    )


@app.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a review.
    
    Args:
        review_id: Review ID
        current_user: Current authenticated user
        db: Database session
        
    Raises:
        HTTPException: If review not found or unauthorized
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    if (review.user_id != current_user.id and 
        current_user.role not in [UserRole.ADMIN, UserRole.MODERATOR]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this review"
        )
    
    db.delete(review)
    db.commit()
    
    return None


@app.put("/reviews/{review_id}/flag", response_model=ReviewResponse)
def flag_review(
    review_id: int,
    flag_data: ReviewFlag,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Flag a review for moderation.
    
    Args:
        review_id: Review ID
        flag_data: Flagging reason
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ReviewResponse: Flagged review data
        
    Raises:
        HTTPException: If review not found
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    review.is_flagged = True
    review.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(review)
    
    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        username=review.user.username,
        room_id=review.room_id,
        room_name=review.room.name,
        rating=review.rating,
        comment=review.comment,
        is_flagged=review.is_flagged,
        is_moderated=review.is_moderated,
        created_at=review.created_at,
        updated_at=review.updated_at
    )


@app.put("/reviews/{review_id}/moderate", response_model=ReviewResponse)
def moderate_review(
    review_id: int,
    moderation_data: ReviewModeration,
    current_user: User = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """
    Moderate a flagged review (moderator/admin only).
    
    Args:
        review_id: Review ID
        moderation_data: Moderation action
        current_user: Current authenticated moderator/admin
        db: Database session
        
    Returns:
        ReviewResponse: Moderated review data
        
    Raises:
        HTTPException: If review not found
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    if moderation_data.action == "approve":
        review.is_flagged = False
        review.is_moderated = True
    elif moderation_data.action == "remove":
        # Delete the review
        db.delete(review)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail="Review removed successfully"
        )
    elif moderation_data.action == "restore":
        review.is_flagged = False
        review.is_moderated = False
    
    review.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(review)
    
    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        username=review.user.username,
        room_id=review.room_id,
        room_name=review.room.name,
        rating=review.rating,
        comment=review.comment,
        is_flagged=review.is_flagged,
        is_moderated=review.is_moderated,
        created_at=review.created_at,
        updated_at=review.updated_at
    )


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status
    """
    return {"status": "healthy", "service": "reviews"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
