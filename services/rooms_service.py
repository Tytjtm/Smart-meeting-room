"""
Rooms Service

This service manages meeting room availability and room details.

Endpoints:
    - POST /rooms: Add a new meeting room
    - GET /rooms: Get all rooms or search by criteria
    - GET /rooms/{room_id}: Get specific room details
    - PUT /rooms/{room_id}: Update room details
    - DELETE /rooms/{room_id}: Delete a room
    - GET /rooms/available: Get available rooms
    - PUT /rooms/{room_id}/status: Update room status
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
from shared.models import Room, User, UserRole, Booking
from shared.auth import decode_access_token, sanitize_input

app = FastAPI(title="Rooms Service", version="1.0.0")
security = HTTPBearer()


class RoomCreate(BaseModel):
    """Room creation request model."""
    name: str = Field(..., min_length=1, max_length=255)
    capacity: int = Field(..., gt=0)
    location: str = Field(..., min_length=1, max_length=255)
    equipment: Optional[str] = None


class RoomUpdate(BaseModel):
    """Room update request model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    capacity: Optional[int] = Field(None, gt=0)
    location: Optional[str] = Field(None, min_length=1, max_length=255)
    equipment: Optional[str] = None
    is_available: Optional[bool] = None


class RoomResponse(BaseModel):
    """Room response model."""
    id: int
    name: str
    capacity: int
    location: str
    equipment: Optional[str]
    is_available: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoomStatusUpdate(BaseModel):
    """Room status update model."""
    is_available: bool


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


# Dependency to check if user can manage rooms (admin or facility manager)
def require_room_manager(current_user: User = Depends(get_current_user)) -> User:
    """Require admin or facility manager role."""
    if current_user.role not in [UserRole.ADMIN, UserRole.FACILITY_MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Facility Manager privileges required"
        )
    return current_user


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.post("/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    room_data: RoomCreate,
    current_user: User = Depends(require_room_manager),
    db: Session = Depends(get_db)
):
    """
    Add a new meeting room.
    
    Args:
        room_data: Room creation data
        current_user: Current authenticated user (admin/facility manager)
        db: Database session
        
    Returns:
        RoomResponse: Created room data
        
    Raises:
        HTTPException: If room name already exists
    """
    name = sanitize_input(room_data.name)
    location = sanitize_input(room_data.location)
    equipment = sanitize_input(room_data.equipment) if room_data.equipment else None
    
    if db.query(Room).filter(Room.name == name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room name already exists"
        )
    
    new_room = Room(
        name=name,
        capacity=room_data.capacity,
        location=location,
        equipment=equipment,
        is_available=True
    )
    
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    
    return new_room


@app.get("/rooms", response_model=List[RoomResponse])
def get_rooms(
    skip: int = 0,
    limit: int = 100,
    capacity: Optional[int] = Query(None, description="Minimum capacity"),
    location: Optional[str] = Query(None, description="Location filter"),
    equipment: Optional[str] = Query(None, description="Equipment filter"),
    available_only: bool = Query(False, description="Show only available rooms"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all rooms with optional filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        capacity: Minimum room capacity filter
        location: Location filter
        equipment: Equipment filter
        available_only: Filter for available rooms only
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[RoomResponse]: List of rooms matching criteria
    """
    query = db.query(Room)
    
    if capacity is not None:
        query = query.filter(Room.capacity >= capacity)
    
    if location:
        location = sanitize_input(location)
        query = query.filter(Room.location.ilike(f"%{location}%"))
    
    if equipment:
        equipment = sanitize_input(equipment)
        query = query.filter(Room.equipment.ilike(f"%{equipment}%"))
    
    if available_only:
        query = query.filter(Room.is_available == True)
    
    rooms = query.offset(skip).limit(limit).all()
    return rooms


@app.get("/rooms/{room_id}", response_model=RoomResponse)
def get_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific room details.
    
    Args:
        room_id: Room ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        RoomResponse: Room data
        
    Raises:
        HTTPException: If room not found
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    return room


@app.put("/rooms/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    room_data: RoomUpdate,
    current_user: User = Depends(require_room_manager),
    db: Session = Depends(get_db)
):
    """
    Update room details.
    
    Args:
        room_id: Room ID
        room_data: Updated room data
        current_user: Current authenticated user (admin/facility manager)
        db: Database session
        
    Returns:
        RoomResponse: Updated room data
        
    Raises:
        HTTPException: If room not found or name already exists
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    if room_data.name is not None:
        name = sanitize_input(room_data.name)
        existing_room = db.query(Room).filter(
            Room.name == name,
            Room.id != room_id
        ).first()
        if existing_room:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Room name already exists"
            )
        room.name = name
    
    if room_data.capacity is not None:
        room.capacity = room_data.capacity
    
    if room_data.location is not None:
        room.location = sanitize_input(room_data.location)
    
    if room_data.equipment is not None:
        room.equipment = sanitize_input(room_data.equipment)
    
    if room_data.is_available is not None:
        room.is_available = room_data.is_available
    
    room.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(room)
    
    return room


@app.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    current_user: User = Depends(require_room_manager),
    db: Session = Depends(get_db)
):
    """
    Delete a room.
    
    Args:
        room_id: Room ID
        current_user: Current authenticated user (admin/facility manager)
        db: Database session
        
    Raises:
        HTTPException: If room not found or has active bookings
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    active_bookings = db.query(Booking).filter(
        Booking.room_id == room_id,
        Booking.status == "confirmed",
        Booking.end_time > datetime.utcnow()
    ).first()
    
    if active_bookings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete room with active bookings"
        )
    
    db.delete(room)
    db.commit()
    
    return None


@app.get("/rooms/available/search", response_model=List[RoomResponse])
def get_available_rooms(
    start_time: datetime = Query(..., description="Booking start time"),
    end_time: datetime = Query(..., description="Booking end time"),
    capacity: Optional[int] = Query(None, description="Minimum capacity"),
    location: Optional[str] = Query(None, description="Location filter"),
    equipment: Optional[str] = Query(None, description="Equipment filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get available rooms for a specific time slot.
    
    Args:
        start_time: Desired start time
        end_time: Desired end time
        capacity: Minimum capacity filter
        location: Location filter
        equipment: Equipment filter
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[RoomResponse]: List of available rooms
        
    Raises:
        HTTPException: If time range is invalid
    """
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    if start_time < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be in the future"
        )
    
    query = db.query(Room).filter(Room.is_available == True)
    
    if capacity is not None:
        query = query.filter(Room.capacity >= capacity)
    
    if location:
        location = sanitize_input(location)
        query = query.filter(Room.location.ilike(f"%{location}%"))
    
    if equipment:
        equipment = sanitize_input(equipment)
        query = query.filter(Room.equipment.ilike(f"%{equipment}%"))
    
    all_rooms = query.all()
    
    available_rooms = []
    for room in all_rooms:
        conflict = db.query(Booking).filter(
            Booking.room_id == room.id,
            Booking.status == "confirmed",
            Booking.start_time < end_time,
            Booking.end_time > start_time
        ).first()
        
        if not conflict:
            available_rooms.append(room)
    
    return available_rooms


@app.put("/rooms/{room_id}/status", response_model=RoomResponse)
def update_room_status(
    room_id: int,
    status_data: RoomStatusUpdate,
    current_user: User = Depends(require_room_manager),
    db: Session = Depends(get_db)
):
    """
    Update room availability status.
    
    Args:
        room_id: Room ID
        status_data: Status update data
        current_user: Current authenticated user (admin/facility manager)
        db: Database session
        
    Returns:
        RoomResponse: Updated room data
        
    Raises:
        HTTPException: If room not found
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    room.is_available = status_data.is_available
    room.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(room)
    
    return room


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status
    """
    return {"status": "healthy", "service": "rooms"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
