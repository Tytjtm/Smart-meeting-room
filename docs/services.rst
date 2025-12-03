Services Documentation
======================

This section documents all microservices in the Smart Meeting Room Management System.

Overview
--------

The system is composed of four independent FastAPI microservices, each handling a specific domain:

* **Users Service** (Port 8001): Authentication and user management
* **Rooms Service** (Port 8002): Meeting room inventory
* **Bookings Service** (Port 8003): Room reservations and scheduling
* **Reviews Service** (Port 8004): User reviews and ratings

Users Service
-------------

Handles user registration, authentication, and profile management with role-based access control.

**Key Features:**

* JWT-based authentication
* Password hashing with bcrypt
* Role-based permissions (Admin, Regular User, Moderator, etc.)
* User CRUD operations

.. automodule:: services.users_service
   :members:
   :undoc-members:
   :show-inheritance:

Rooms Service
-------------

Manages meeting room inventory with capacity tracking and equipment information.

**Key Features:**

* Room CRUD operations
* Availability toggle
* Capacity and equipment tracking
* Advanced search functionality

.. automodule:: services.rooms_service
   :members:
   :undoc-members:
   :show-inheritance:

Bookings Service
----------------

Handles room reservations with conflict detection and availability checking.

**Key Features:**

* Booking creation with conflict validation
* Real-time availability checking
* User booking history
* Cancellation and updates

.. automodule:: services.bookings_service
   :members:
   :undoc-members:
   :show-inheritance:

Reviews Service
---------------

Manages user reviews with ratings, moderation, and flagging capabilities.

**Key Features:**

* Star-based rating system (1-5)
* Review moderation workflow
* Flagging for inappropriate content
* Statistics and analytics

.. automodule:: services.reviews_service
   :members:
   :undoc-members:
   :show-inheritance:

API Gateway
-----------

Provides unified API access to all services with load balancing and health monitoring.

**Key Features:**

* Round-robin load balancing
* Service health checks
* Request routing
* Gateway status monitoring

.. automodule:: services.api_gateway
   :members:
   :undoc-members:
   :show-inheritance:
