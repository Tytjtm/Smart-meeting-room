Smart Meeting Room Management System Documentation
===================================================

Welcome to the Smart Meeting Room Management System Backend documentation.

This system provides a comprehensive microservices-based backend for managing meeting rooms,
user authentication, bookings, and reviews.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   services
   shared
   enhancements
   api

Core Features (Part I)
----------------------

* **User Management**: Registration, authentication, role-based access control (RBAC)
* **Room Management**: CRUD operations for meeting rooms with capacity and equipment tracking
* **Booking System**: Room reservations with conflict detection and availability checking
* **Review System**: User reviews with ratings, moderation, and flagging capabilities
* **Security**: JWT authentication, password hashing, input sanitization
* **Containerization**: Docker and Docker Compose for easy deployment

Advanced Features (Part II)
---------------------------

* **Rate Limiting**: API protection with configurable per-IP and per-user rate limits using Redis
* **Caching Layer**: High-performance Redis caching for frequently accessed data (50-80% faster responses)
* **Prometheus Monitoring**: Comprehensive metrics collection with Grafana dashboards for real-time insights
* **API Gateway**: Centralized entry point with load balancing, health checks, and circuit breaker pattern

Architecture
------------

The system consists of 4 independent microservices:

1. **Users Service** (Port 8001): Handles user authentication and profile management
2. **Rooms Service** (Port 8002): Manages meeting room inventory and availability
3. **Bookings Service** (Port 8003): Handles room reservations and scheduling
4. **Reviews Service** (Port 8004): Manages user reviews and ratings

All services share a common PostgreSQL database and use FastAPI for REST API endpoints.

User Roles
----------

* **ADMIN**: Full system access, can manage users and modify all resources
* **REGULAR_USER**: Can book rooms, submit reviews, manage own profile
* **FACILITY_MANAGER**: Can manage rooms and view bookings
* **MODERATOR**: Can moderate reviews and flag inappropriate content
* **AUDITOR**: Read-only access for auditing purposes
* **SERVICE_ACCOUNT**: For inter-service communication

Quick Start
-----------

1. Install dependencies::

    pip install -r requirements.txt

2. Start services with Docker Compose::

    docker-compose up -d

3. Access services:
   
   * Users Service: http://localhost:8001/docs
   * Rooms Service: http://localhost:8002/docs
   * Bookings Service: http://localhost:8003/docs
   * Reviews Service: http://localhost:8004/docs

Running Tests
-------------

Run all tests with pytest::

    pytest tests/ -v

Run specific test file::

    pytest tests/test_users_service.py -v

Generate coverage report::

    pytest tests/ --cov=services --cov-report=html

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
