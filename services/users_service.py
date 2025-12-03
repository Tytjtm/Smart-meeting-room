"""
Users Service

This service manages user accounts, authentication, roles, and booking history.

Endpoints:
    - POST /register: Register a new user
    - POST /login: User login and authentication
    - GET /users: Get all users (admin only)
    - GET /users/{username}: Get specific user
    - PUT /users/{username}: Update user details
    - DELETE /users/{username}: Delete user account
    - GET /users/{username}/bookings: View user's booking history
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, init_db
from shared.models import User, UserRole, Booking, Room
from shared.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    sanitize_input,
    validate_email
)

app = FastAPI(title="Users Service", version="1.0.0")
security = HTTPBearer()


class UserRegister(BaseModel):
    """User registration request model."""
    name: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    email: EmailStr
    role: Optional[UserRole] = UserRole.REGULAR_USER


class UserLogin(BaseModel):
    """User login request model."""
    username: str
    password: str


class UserUpdate(BaseModel):
    """User update request model."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None


class UserResponse(BaseModel):
    """User response model."""
    id: int
    name: str
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class BookingHistoryResponse(BaseModel):
    """Booking history response model."""
    id: int
    room_name: str
    room_location: str
    start_time: datetime
    end_time: datetime
    purpose: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Dependency to get current user from token
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
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
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


# Dependency to check if user is admin
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Require admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current user if admin
        
    Raises:
        HTTPException: If user is not admin
    """
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


@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        UserResponse: Created user data
        
    Raises:
        HTTPException: If username or email already exists
    """
    name = sanitize_input(user_data.name)
    username = sanitize_input(user_data.username)
    
    if not validate_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        name=name,
        username=username,
        email=user_data.email,
        password_hash=hashed_password,
        role=user_data.role
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@app.post("/login", response_model=TokenResponse)
def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    User login and authentication.
    
    Args:
        login_data: Login credentials
        db: Database session
        
    Returns:
        TokenResponse: Access token and user data
        
    Raises:
        HTTPException: If credentials are invalid
    """
    username = sanitize_input(login_data.username)
    
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value}
    )
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.from_orm(user)
    )


@app.get("/users", response_model=List[UserResponse])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all users (admin only).
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        List[UserResponse]: List of users
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@app.get("/users/{username}", response_model=UserResponse)
def get_user(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific user by username.
    
    Args:
        username: Username to retrieve
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserResponse: User data
        
    Raises:
        HTTPException: If user not found or unauthorized
    """
    username = sanitize_input(username)
    
    if current_user.username != username and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@app.put("/users/{username}", response_model=UserResponse)
def update_user(
    username: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user details.
    
    Args:
        username: Username to update
        user_data: Updated user data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserResponse: Updated user data
        
    Raises:
        HTTPException: If user not found or unauthorized
    """
    username = sanitize_input(username)
    
    if current_user.username != username and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user_data.name is not None:
        user.name = sanitize_input(user_data.name)
    
    if user_data.email is not None:
        if not validate_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        # Check if email already exists for another user
        existing_user = db.query(User).filter(
            User.email == user_data.email,
            User.id != user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        user.email = user_data.email
    
    if user_data.role is not None:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can change user roles"
            )
        user.role = user_data.role
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user


@app.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user account.
    
    Args:
        username: Username to delete
        current_user: Current authenticated user
        db: Database session
        
    Raises:
        HTTPException: If user not found or unauthorized
    """
    username = sanitize_input(username)
    
    if current_user.username != username and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return None


@app.get("/users/{username}/bookings", response_model=List[BookingHistoryResponse])
def get_user_booking_history(
    username: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    View user's booking history.
    
    Args:
        username: Username to retrieve bookings for
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List[BookingHistoryResponse]: List of user's bookings
        
    Raises:
        HTTPException: If user not found or unauthorized
    """
    username = sanitize_input(username)
    
    if current_user.username != username and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's bookings"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    bookings = db.query(Booking).filter(Booking.user_id == user.id).join(Room).all()
    
    booking_history = []
    for booking in bookings:
        booking_history.append(BookingHistoryResponse(
            id=booking.id,
            room_name=booking.room.name,
            room_location=booking.room.location,
            start_time=booking.start_time,
            end_time=booking.end_time,
            purpose=booking.purpose,
            status=booking.status,
            created_at=booking.created_at
        ))
    
    return booking_history


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status
    """
    return {"status": "healthy", "service": "users"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
