"""
Database initialization script.

This script creates initial data for the Smart Meeting Room Management System:
- Admin user
- Sample rooms
- Test data for development

Run with: python scripts/init_db.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import engine, SessionLocal, init_db
from shared.models import User, Room, UserRole
from shared.auth import get_password_hash


def create_admin_user(db):
    """Create default admin user."""
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@smartroom.com",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        print("Admin user created (username: admin, password: admin123)")
    else:
        print("Admin user already exists")


def create_sample_rooms(db):
    """Create sample meeting rooms."""
    rooms_data = [
        {
            "name": "Executive Board Room",
            "location": "Building A, Floor 10",
            "capacity": 15,
            "equipment": ["4K Display", "Video Conference", "Whiteboard", "Premium Audio"]
        },
        {
            "name": "Team Room 101",
            "location": "Building B, Floor 1",
            "capacity": 8,
            "equipment": ["TV Display", "Whiteboard", "HDMI"]
        },
        {
            "name": "Large Conference Hall",
            "location": "Building A, Floor 2",
            "capacity": 50,
            "equipment": ["Projector", "Sound System", "Microphones", "Stage"]
        },
        {
            "name": "Focus Room 201",
            "location": "Building B, Floor 2",
            "capacity": 4,
            "equipment": ["Monitor", "Whiteboard"]
        },
        {
            "name": "Innovation Lab",
            "location": "Building C, Floor 3",
            "capacity": 12,
            "equipment": ["Smartboard", "VR Equipment", "3D Printer", "Video Conference"]
        }
    ]
    
    created_count = 0
    for room_data in rooms_data:
        existing_room = db.query(Room).filter(Room.name == room_data["name"]).first()
        if not existing_room:
            room = Room(**room_data, is_available=True)
            db.add(room)
            created_count += 1
    
    db.commit()
    print(f"Created {created_count} sample rooms")


def create_test_users(db):
    """Create test users for different roles."""
    users_data = [
        {
            "username": "facility_manager",
            "email": "facility@smartroom.com",
            "password": "facility123",
            "full_name": "Facility Manager",
            "role": UserRole.FACILITY_MANAGER
        },
        {
            "username": "moderator",
            "email": "moderator@smartroom.com",
            "password": "moderator123",
            "full_name": "Content Moderator",
            "role": UserRole.MODERATOR
        },
        {
            "username": "john_doe",
            "email": "john@smartroom.com",
            "password": "john123",
            "full_name": "John Doe",
            "role": UserRole.REGULAR_USER
        },
        {
            "username": "jane_smith",
            "email": "jane@smartroom.com",
            "password": "jane123",
            "full_name": "Jane Smith",
            "role": UserRole.REGULAR_USER
        }
    ]
    
    created_count = 0
    for user_data in users_data:
        existing_user = db.query(User).filter(User.username == user_data["username"]).first()
        if not existing_user:
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=True
            )
            db.add(user)
            created_count += 1
    
    db.commit()
    print(f"Created {created_count} test users")


def main():
    """Initialize database with sample data."""
    print("Initializing database...")
    
    init_db()
    print("Database tables created")
    
    db = SessionLocal()
    
    try:
        create_admin_user(db)
        create_test_users(db)
        create_sample_rooms(db)
        
        print("\n" + "="*60)
        print("Database initialization complete!")
        print("="*60)
        print("\nTest Accounts:")
        print("-" * 60)
        print("Admin:             username: admin              password: admin123")
        print("Facility Manager:  username: facility_manager   password: facility123")
        print("Moderator:         username: moderator          password: moderator123")
        print("Regular User 1:    username: john_doe           password: john123")
        print("Regular User 2:    username: jane_smith         password: jane123")
        print("-" * 60)
        print("\nIMPORTANT: Change these passwords in production!")
        
    except Exception as e:
        print(f"\n Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
