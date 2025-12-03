"""
Shared database models for all services.

This module contains SQLAlchemy models used across all services
in the Smart Meeting Room Management System.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from shared.database import Base


class UserRole(enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"
    REGULAR_USER = "regular_user"
    FACILITY_MANAGER = "facility_manager"
    MODERATOR = "moderator"
    AUDITOR = "auditor"
    SERVICE_ACCOUNT = "service_account"


class User(Base):
    """
    User model representing system users.
    
    Attributes:
        id (int): Primary key
        name (str): Full name of the user
        username (str): Unique username
        email (str): Email address
        password_hash (str): Hashed password
        role (UserRole): User role (admin, regular_user, etc.)
        created_at (datetime): Account creation timestamp
        updated_at (datetime): Last update timestamp
        is_active (bool): Account active status
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.REGULAR_USER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")


class Room(Base):
    """
    Room model representing meeting rooms.
    
    Attributes:
        id (int): Primary key
        name (str): Room name
        capacity (int): Maximum capacity
        location (str): Room location
        equipment (str): Available equipment (comma-separated)
        is_available (bool): Availability status
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
    """
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    capacity = Column(Integer, nullable=False)
    location = Column(String(255), nullable=False)
    equipment = Column(Text, nullable=True)  # Comma-separated equipment list
    is_available = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    bookings = relationship("Booking", back_populates="room", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="room", cascade="all, delete-orphan")


class Booking(Base):
    """
    Booking model representing room reservations.
    
    Attributes:
        id (int): Primary key
        user_id (int): Foreign key to User
        room_id (int): Foreign key to Room
        start_time (datetime): Booking start time
        end_time (datetime): Booking end time
        purpose (str): Meeting purpose
        status (str): Booking status (confirmed, cancelled, completed)
        created_at (datetime): Booking creation timestamp
        updated_at (datetime): Last update timestamp
    """
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    purpose = Column(Text, nullable=True)
    status = Column(String(50), default="confirmed", nullable=False)  # confirmed, cancelled, completed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    room = relationship("Room", back_populates="bookings")


class Review(Base):
    """
    Review model representing room reviews.
    
    Attributes:
        id (int): Primary key
        user_id (int): Foreign key to User
        room_id (int): Foreign key to Room
        rating (float): Rating (1-5)
        comment (str): Review comment
        is_flagged (bool): Flagged for moderation
        is_moderated (bool): Moderation status
        created_at (datetime): Review creation timestamp
        updated_at (datetime): Last update timestamp
    """
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Float, nullable=False)  # 1-5 rating
    comment = Column(Text, nullable=True)
    is_flagged = Column(Boolean, default=False, nullable=False)
    is_moderated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="reviews")
    room = relationship("Room", back_populates="reviews")
