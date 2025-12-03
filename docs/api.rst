API Reference
=============

This section provides detailed API endpoint documentation for all services.

Users Service API
-----------------

Base URL: ``http://localhost:8001``

Authentication Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~

**POST /register**

Register a new user.

Request Body:

.. code-block:: json

    {
        "username": "string",
        "email": "user@example.com",
        "password": "string",
        "full_name": "string",
        "role": "REGULAR_USER"
    }

Response: ``201 Created``

**POST /login**

Authenticate user and get JWT token.

Request Body:

.. code-block:: json

    {
        "username": "string",
        "password": "string"
    }

Response: ``200 OK``

.. code-block:: json

    {
        "access_token": "string",
        "token_type": "bearer",
        "user": {...}
    }

User Management Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~

**GET /users** (Admin only)

Get all users.

**GET /users/{username}**

Get specific user details.

**PUT /users/{username}**

Update user profile.

**DELETE /users/{username}**

Delete user account.

**GET /users/{username}/bookings**

Get user's booking history.

Rooms Service API
-----------------

Base URL: ``http://localhost:8002``

Room Management Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~

**POST /rooms** (Admin/Facility Manager)

Create a new room.

**GET /rooms**

List all rooms with optional filters.

Query Parameters:
- ``min_capacity``: Minimum capacity
- ``location``: Filter by location
- ``equipment``: Filter by equipment
- ``available_only``: Show only available rooms

**GET /rooms/{room_id}**

Get specific room details.

**PUT /rooms/{room_id}** (Admin/Facility Manager)

Update room information.

**DELETE /rooms/{room_id}** (Admin/Facility Manager)

Delete a room.

**GET /rooms/available/search**

Search for available rooms in a time slot.

**PUT /rooms/{room_id}/status** (Admin/Facility Manager)

Toggle room availability status.

Bookings Service API
--------------------

Base URL: ``http://localhost:8003``

Booking Management Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**POST /bookings**

Create a new booking.

Request Body:

.. code-block:: json

    {
        "room_id": 1,
        "start_time": "2024-12-01T10:00:00",
        "end_time": "2024-12-01T12:00:00",
        "purpose": "string"
    }

**GET /bookings**

List all bookings (filtered by user role).

**GET /bookings/{booking_id}**

Get specific booking details.

**PUT /bookings/{booking_id}**

Update booking information.

**DELETE /bookings/{booking_id}**

Cancel a booking.

**POST /bookings/check-availability**

Check room availability for a time slot.

**GET /bookings/user/{user_id}**

Get bookings for specific user.

Reviews Service API
-------------------

Base URL: ``http://localhost:8004``

Review Management Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**POST /reviews**

Submit a review for a room.

Request Body:

.. code-block:: json

    {
        "room_id": 1,
        "rating": 4.5,
        "comment": "string"
    }

**GET /reviews**

Get all reviews.

Query Parameters:
- ``flagged_only``: Show only flagged reviews (Moderator/Admin)

**GET /reviews/{review_id}**

Get specific review details.

**GET /reviews/room/{room_id}**

Get all reviews for a specific room.

**PUT /reviews/{review_id}**

Update a review.

**DELETE /reviews/{review_id}**

Delete a review.

**PUT /reviews/{review_id}/flag**

Flag a review for moderation.

**PUT /reviews/{review_id}/moderate** (Moderator/Admin)

Moderate a flagged review.

Request Body:

.. code-block:: json

    {
        "is_moderated": true,
        "action": "approve|remove|restore"
    }

Authentication
--------------

All endpoints (except register and login) require JWT authentication.

Include the token in the Authorization header:

.. code-block:: text

    Authorization: Bearer <your_jwt_token>

Error Responses
---------------

All services return standard HTTP status codes:

- ``200 OK``: Success
- ``201 Created``: Resource created successfully
- ``204 No Content``: Success with no response body
- ``400 Bad Request``: Invalid request data
- ``401 Unauthorized``: Missing or invalid authentication
- ``403 Forbidden``: Insufficient privileges
- ``404 Not Found``: Resource not found
- ``422 Unprocessable Entity``: Validation error
