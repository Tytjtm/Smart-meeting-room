# Smart Meeting Room Management System Backend

A microservices-based backend system for managing meeting rooms, bookings, user authentication, and reviews.

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Technologies](#technologies)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Security Features](#security-features)
- [Contributors](#contributors)

## Features

### Part I: Core Functionality

- **User Management**
  - User registration with email validation
  - JWT-based authentication
  - Role-Based Access Control (RBAC)
  - Profile management
  - Booking history retrieval

- **Room Management**
  - CRUD operations for meeting rooms
  - Capacity and equipment tracking
  - Availability status management
  - Location-based filtering
  - Advanced search with multiple filters

- **Booking System**
  - Room reservation with conflict detection
  - Time slot validation
  - Booking updates and cancellations
  - User-specific booking retrieval
  - Availability checking

- **Review System**
  - Submit and update reviews with ratings (1-5)
  - Room-specific review retrieval
  - Review flagging for moderation
  - Moderator review management
  - One review per user per room policy

### Security Features

- Password hashing with bcrypt
- JWT token authentication
- Input sanitization (XSS protection)
- Email validation with regex
- Rating validation (1.0-5.0 range)
- Role-based authorization
- SQL injection protection via SQLAlchemy ORM

### User Roles

- **ADMIN**: Full system access
- **REGULAR_USER**: Basic booking and review privileges
- **FACILITY_MANAGER**: Room management capabilities
- **MODERATOR**: Review moderation privileges
- **AUDITOR**: Read-only access for auditing
- **SERVICE_ACCOUNT**: Inter-service communication

## Architecture

The system follows a microservices architecture with 4 independent services:

```
┌─────────────────┐     ┌─────────────────┐
│  Users Service  │     │  Rooms Service  │
│    Port 8001    │     │    Port 8002    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │   ┌──────────────┐   │
         └───┤  PostgreSQL  ├───┘
             │   Database   │
         ┌───┤              ├───┐
         │   └──────────────┘   │
         │                      │
┌────────┴────────┐    ┌───────┴────────┐
│ Bookings Service│    │ Reviews Service│
│    Port 8003    │    │    Port 8004   │
└─────────────────┘    └────────────────┘
```

## Technologies

- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0+
- **Authentication**: python-jose (JWT)
- **Password Hashing**: passlib with bcrypt
- **Validation**: Pydantic v2
- **Testing**: pytest, pytest-cov
- **Documentation**: Sphinx with Read the Docs theme
- **Containerization**: Docker, Docker Compose
- **ASGI Server**: Uvicorn

## Installation

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

### Clone Repository

```bash
git clone <repository-url>
cd smartmeetingroom_project
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://smartroom_user:smartroom_password@localhost:5432/smartroom_db

# JWT Configuration
SECRET_KEY=your-super-secret-key-change-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database Credentials (for Docker)
POSTGRES_USER=smartroom_user
POSTGRES_PASSWORD=smartroom_password
POSTGRES_DB=smartroom_db
```

**IMPORTANT**: Change the `SECRET_KEY` in production!

## Running the Application

### Option 1: Docker Compose (Recommended)

Start all services with a single command:

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database on port 5432
- Users Service on port 8001
- Rooms Service on port 8002
- Bookings Service on port 8003
- Reviews Service on port 8004

View logs:
```bash
docker-compose logs -f
```

Stop services:
```bash
docker-compose down
```

### Option 2: Manual Startup

1. **Start PostgreSQL**:
```bash
docker run -d \
  --name smartroom_db \
  -e POSTGRES_USER=smartroom_user \
  -e POSTGRES_PASSWORD=smartroom_password \
  -e POSTGRES_DB=smartroom_db \
  -p 5432:5432 \
  postgres:15-alpine
```

2. **Start Each Service** (in separate terminals):

```bash
# Terminal 1 - Users Service
uvicorn services.users_service:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 - Rooms Service
uvicorn services.rooms_service:app --host 0.0.0.0 --port 8002 --reload

# Terminal 3 - Bookings Service
uvicorn services.bookings_service:app --host 0.0.0.0 --port 8003 --reload

# Terminal 4 - Reviews Service
uvicorn services.reviews_service:app --host 0.0.0.0 --port 8004 --reload
```

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_users_service.py -v
pytest tests/test_rooms_service.py -v
pytest tests/test_bookings_service.py -v
pytest tests/test_reviews_service.py -v
```

### Generate Coverage Report

```bash
pytest tests/ --cov=services --cov=shared --cov-report=html
```

View coverage report:
```bash
# Open htmlcov/index.html in browser
```

### Test Results

All services include comprehensive test coverage:
- Authentication and authorization tests
- CRUD operation tests
- Role-based access control tests
- Input validation tests
- Error handling tests

## 📚 API Documentation

### Interactive API Documentation (Swagger UI)

Once services are running, access interactive docs:

- **Users Service**: http://localhost:8001/docs
- **Rooms Service**: http://localhost:8002/docs
- **Bookings Service**: http://localhost:8003/docs
- **Reviews Service**: http://localhost:8004/docs

### Generate Sphinx Documentation

```bash
cd docs
sphinx-build -b html . _build
```

View documentation: Open `docs/_build/index.html` in browser

### Example API Usage

#### 1. Register a User

```bash
curl -X POST "http://localhost:8001/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password123",
    "full_name": "John Doe"
  }'
```

#### 2. Login

```bash
curl -X POST "http://localhost:8001/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "secure_password123"
  }'
```

Save the `access_token` from the response.

#### 3. Create a Room (Admin/Facility Manager)

```bash
curl -X POST "http://localhost:8002/rooms" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Conference Room A",
    "location": "Building 1, Floor 2",
    "capacity": 20,
    "equipment": ["Projector", "Whiteboard", "Video Conference"]
  }'
```

#### 4. Create a Booking

```bash
curl -X POST "http://localhost:8003/bookings" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": 1,
    "start_time": "2024-12-01T10:00:00",
    "end_time": "2024-12-01T12:00:00",
    "purpose": "Team Sprint Planning"
  }'
```

#### 5. Submit a Review

```bash
curl -X POST "http://localhost:8004/reviews" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": 1,
    "rating": 4.5,
    "comment": "Great room with excellent equipment!"
  }'
```

## Project Structure

```
smartmeetingroom_project/
├── services/
│   ├── users_service.py         # User authentication & management
│   ├── rooms_service.py         # Room management
│   ├── bookings_service.py      # Booking system
│   └── reviews_service.py       # Review system
├── shared/
│   ├── database.py              # Database configuration
│   ├── models.py                # SQLAlchemy models
│   └── auth.py                  # Authentication utilities
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_users_service.py
│   ├── test_rooms_service.py
│   ├── test_bookings_service.py
│   └── test_reviews_service.py
├── docs/
│   ├── conf.py                  # Sphinx configuration
│   ├── index.rst                # Main documentation page
│   ├── services.rst             # Services documentation
│   ├── shared.rst               # Shared modules docs
│   └── api.rst                  # API reference
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Container definition
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
├── .dockerignore               # Docker ignore rules
└── README.md                    # This file
```

## 🔒 Security Features

### Implemented Security Measures

1. **Authentication & Authorization**
   - JWT tokens with expiration (30 minutes default)
   - Password hashing with bcrypt (cost factor 12)
   - Role-Based Access Control (RBAC)

2. **Input Validation**
   - Email validation with regex
   - Rating validation (1.0-5.0)
   - Input sanitization (HTML escaping)
   - Pydantic validation for all request bodies

3. **Database Security**
   - SQLAlchemy ORM prevents SQL injection
   - Parameterized queries throughout
   - Connection pooling and timeout management

4. **API Security**
   - Bearer token authentication
   - CORS configuration (if needed)
   - Rate limiting (recommended for production)


## 👥 Contributors

- **Jad Eido**
- **Tarek El Mourad**

**Course**: EECE435L   
**Institution**: American University of Beirut (AUB)

## 📝 License

This project is part of an academic assignment for EECE435L.



## Testing Checklist

- [x] User registration and login
- [x] JWT token generation and validation
- [x] Role-based access control
- [x] Room CRUD operations
- [x] Booking conflict detection
- [x] Review submission and moderation
- [x] Input validation and sanitization
- [x] Database relationships and cascades
- [x] Error handling and status codes
- [x] Docker containerization

## Deployment

### Production Deployment Steps

1. Update `.env` with production credentials
2. Build Docker images: `docker-compose build`
3. Start services: `docker-compose up -d`
5. Verify health checks: 
   - http://localhost:8001/health
   - http://localhost:8002/health
   - http://localhost:8003/health
   - http://localhost:8004/health

---


