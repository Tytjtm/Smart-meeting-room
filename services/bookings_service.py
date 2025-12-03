"""
Bookings Service

This service manages meeting room bookings and reservations.

Endpoints:
    - GET /bookings: View all bookings
    - POST /bookings: Make a new booking
    - GET /bookings/{booking_id}: Get specific booking
    - PUT /bookings/{booking_id}: Update booking
    - DELETE /bookings/{booking_id}: Cancel booking
    - GET /bookings/check-availability: Check room availability
    - GET /bookings/user/{user_id}: Get user's bookings
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
from shared.models import Booking, User, Room, UserRole
from shared.auth import decode_access_token, sanitize_input

app = FastAPI(title="Bookings Service", version="1.0.0")
security = HTTPBearer()


class BookingCreate(BaseModel):
    """Booking creation request model."""
    room_id: int
    start_time: datetime
    end_time: datetime
    purpose: Optional[str] = None


class BookingUpdate(BaseModel):
    """Booking update request model."""
    room_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    purpose: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(confirmed|cancelled|completed)$")


class BookingResponse(BaseModel):
    """Booking response model."""
    id: int
    user_id: int
    username: str
    room_id: int
    room_name: str
    room_location: str
    start_time: datetime
    end_time: datetime
    purpose: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AvailabilityCheck(BaseModel):
    """Availability check model."""
    room_id: int
    start_time: datetime
    end_time: datetime


class AvailabilityResponse(BaseModel):
    """Availability response model."""
    available: bool
    conflicting_bookings: List[dict] = []


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


# Dependency for admin role
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_data: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Make a new booking.
    
    Args:
        booking_data: Booking creation data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        BookingResponse: Created booking data
        
    Raises:
        HTTPException: If room not found, not available, or time slot conflicts
    """
    if booking_data.start_time >= booking_data.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    if booking_data.start_time < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be in the future"
        )
    
    room = db.query(Room).filter(Room.id == booking_data.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    if not room.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room is not available"
        )
    
    conflict = db.query(Booking).filter(
        Booking.room_id == booking_data.room_id,
        Booking.status == "confirmed",
        Booking.start_time < booking_data.end_time,
        Booking.end_time > booking_data.start_time
    ).first()
    
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room is already booked for this time slot"
        )
    
    purpose = sanitize_input(booking_data.purpose) if booking_data.purpose else None
    
    new_booking = Booking(
        user_id=current_user.id,
        room_id=booking_data.room_id,
        start_time=booking_data.start_time,
        end_time=booking_data.end_time,
        purpose=purpose,
        status="confirmed"
    )
    
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    
    return BookingResponse(
        id=new_booking.id,
        user_id=new_booking.user_id,
        username=current_user.username,
        room_id=new_booking.room_id,
        room_name=room.name,
        room_location=room.location,
        start_time=new_booking.start_time,
        end_time=new_booking.end_time,
        purpose=new_booking.purpose,
        status=new_booking.status,
        created_at=new_booking.created_at,
        updated_at=new_booking.updated_at
    )


@app.get("/bookings", response_model=List[BookingResponse])
def get_all_bookings(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    View all bookings.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status_filter: Filter by booking status
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[BookingResponse]: List of bookings
    """
    query = db.query(Booking)
    
    if current_user.role not in [UserRole.ADMIN, UserRole.FACILITY_MANAGER]:
        query = query.filter(Booking.user_id == current_user.id)
    
    if status_filter:
        query = query.filter(Booking.status == status_filter)
    
    bookings = query.offset(skip).limit(limit).all()
    
    result = []
    for booking in bookings:
        result.append(BookingResponse(
            id=booking.id,
            user_id=booking.user_id,
            username=booking.user.username,
            room_id=booking.room_id,
            room_name=booking.room.name,
            room_location=booking.room.location,
            start_time=booking.start_time,
            end_time=booking.end_time,
            purpose=booking.purpose,
            status=booking.status,
            created_at=booking.created_at,
            updated_at=booking.updated_at
        ))
    
    return result


@app.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific booking details.
    
    Args:
        booking_id: Booking ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        BookingResponse: Booking data
        
    Raises:
        HTTPException: If booking not found or unauthorized
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    if (booking.user_id != current_user.id and 
        current_user.role not in [UserRole.ADMIN, UserRole.FACILITY_MANAGER]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this booking"
        )
    
    return BookingResponse(
        id=booking.id,
        user_id=booking.user_id,
        username=booking.user.username,
        room_id=booking.room_id,
        room_name=booking.room.name,
        room_location=booking.room.location,
        start_time=booking.start_time,
        end_time=booking.end_time,
        purpose=booking.purpose,
        status=booking.status,
        created_at=booking.created_at,
        updated_at=booking.updated_at
    )


@app.put("/bookings/{booking_id}", response_model=BookingResponse)
def update_booking(
    booking_id: int,
    booking_data: BookingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update or modify a booking.
    
    Args:
        booking_id: Booking ID
        booking_data: Updated booking data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        BookingResponse: Updated booking data
        
    Raises:
        HTTPException: If booking not found, unauthorized, or conflicts exist
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    if (booking.user_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this booking"
        )
    
    if booking_data.room_id is not None:
        room = db.query(Room).filter(Room.id == booking_data.room_id).first()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room not found"
            )
        if not room.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Room is not available"
            )
        booking.room_id = booking_data.room_id
    
    start_time = booking_data.start_time if booking_data.start_time else booking.start_time
    end_time = booking_data.end_time if booking_data.end_time else booking.end_time
    
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    conflict = db.query(Booking).filter(
        Booking.room_id == booking.room_id,
        Booking.id != booking_id,
        Booking.status == "confirmed",
        Booking.start_time < end_time,
        Booking.end_time > start_time
    ).first()
    
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room is already booked for this time slot"
        )
    
    if booking_data.start_time:
        booking.start_time = booking_data.start_time
    if booking_data.end_time:
        booking.end_time = booking_data.end_time
    
    if booking_data.purpose is not None:
        booking.purpose = sanitize_input(booking_data.purpose)
    
    if booking_data.status is not None:
        booking.status = booking_data.status
    
    booking.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(booking)
    
    return BookingResponse(
        id=booking.id,
        user_id=booking.user_id,
        username=booking.user.username,
        room_id=booking.room_id,
        room_name=booking.room.name,
        room_location=booking.room.location,
        start_time=booking.start_time,
        end_time=booking.end_time,
        purpose=booking.purpose,
        status=booking.status,
        created_at=booking.created_at,
        updated_at=booking.updated_at
    )


@app.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a booking.
    
    Args:
        booking_id: Booking ID
        current_user: Current authenticated user
        db: Database session
        
    Raises:
        HTTPException: If booking not found or unauthorized
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    if (booking.user_id != current_user.id and current_user.role != UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this booking"
        )
    
    booking.status = "cancelled"
    booking.updated_at = datetime.utcnow()
    db.commit()
    
    return None


@app.post("/bookings/check-availability", response_model=AvailabilityResponse)
def check_availability(
    availability_data: AvailabilityCheck,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check room availability for a specific time slot.
    
    Args:
        availability_data: Availability check data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        AvailabilityResponse: Availability status and conflicts
        
    Raises:
        HTTPException: If room not found or invalid time range
    """
    if availability_data.start_time >= availability_data.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    room = db.query(Room).filter(Room.id == availability_data.room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    conflicts = db.query(Booking).filter(
        Booking.room_id == availability_data.room_id,
        Booking.status == "confirmed",
        Booking.start_time < availability_data.end_time,
        Booking.end_time > availability_data.start_time
    ).all()
    
    conflicting_bookings = []
    for conflict in conflicts:
        conflicting_bookings.append({
            "booking_id": conflict.id,
            "start_time": conflict.start_time.isoformat(),
            "end_time": conflict.end_time.isoformat(),
            "user": conflict.user.username
        })
    
    return AvailabilityResponse(
        available=len(conflicts) == 0 and room.is_available,
        conflicting_bookings=conflicting_bookings
    )


@app.get("/bookings/user/{user_id}", response_model=List[BookingResponse])
def get_user_bookings(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all bookings for a specific user.
    
    Args:
        user_id: User ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[BookingResponse]: List of user's bookings
        
    Raises:
        HTTPException: If unauthorized
    """
    if (user_id != current_user.id and 
        current_user.role not in [UserRole.ADMIN, UserRole.FACILITY_MANAGER]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's bookings"
        )
    
    bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
    
    result = []
    for booking in bookings:
        result.append(BookingResponse(
            id=booking.id,
            user_id=booking.user_id,
            username=booking.user.username,
            room_id=booking.room_id,
            room_name=booking.room.name,
            room_location=booking.room.location,
            start_time=booking.start_time,
            end_time=booking.end_time,
            purpose=booking.purpose,
            status=booking.status,
            created_at=booking.created_at,
            updated_at=booking.updated_at
        ))
    
    return result


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status
    """
    return {"status": "healthy", "service": "bookings"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
