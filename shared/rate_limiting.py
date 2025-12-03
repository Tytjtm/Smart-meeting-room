"""
Rate Limiting Middleware

This module implements API rate limiting to prevent abuse and ensure fair usage.

Features:
- Per-IP rate limiting
- Per-user rate limiting (authenticated)
- Configurable limits per endpoint
- Redis-backed distributed rate limiting

Author: Tarek El Mourad
"""

from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis
from typing import Callable
import os

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)


def get_user_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    
    Uses username if authenticated, otherwise falls back to IP address.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Unique identifier for the user/IP
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            return f"user_{hash(token)}"
        except:
            pass
    
    return get_remote_address(request)

limiter = Limiter(
    key_func=get_user_identifier,
    storage_uri=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}"
)

RATE_LIMITS = {
    "auth": "10/minute",      # Login/register endpoints
    "read": "100/minute",     # GET endpoints
    "write": "30/minute",     # POST/PUT endpoints
    "delete": "10/minute",    # DELETE endpoints
    "default": "60/minute"    # Default limit
}


def get_rate_limit(endpoint_type: str = "default") -> str:
    """
    Get rate limit string for endpoint type.
    
    Args:
        endpoint_type: Type of endpoint (auth, read, write, delete)
        
    Returns:
        str: Rate limit string (e.g., "10/minute")
    """
    return RATE_LIMITS.get(endpoint_type, RATE_LIMITS["default"])


def rate_limit_decorator(limit_type: str = "default"):
    """
    Decorator factory for applying rate limits to endpoints.
    
    Args:
        limit_type: Type of rate limit to apply
        
    Returns:
        Decorator function
        
    Example:
        @app.post("/login")
        @rate_limit_decorator("auth")
        async def login():
            pass
    """
    def decorator(func: Callable):
        return limiter.limit(get_rate_limit(limit_type))(func)
    return decorator


class RateLimitMiddleware:
    """
    Middleware for applying rate limits globally.
    
    This middleware checks rate limits before processing requests
    and returns 429 Too Many Requests if limit is exceeded.
    """
    
    def __init__(self, app, limiter_instance):
        """
        Initialize rate limit middleware.
        
        Args:
            app: FastAPI application instance
            limiter_instance: Limiter instance to use
        """
        self.app = app
        self.limiter = limiter_instance
    
    async def __call__(self, request: Request, call_next):
        """
        Process request with rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response from next middleware or rate limit error
        """
        try:
            response = await call_next(request)
            return response
        except RateLimitExceeded:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": "60"}
            )


def setup_rate_limiting(app):
    """
    Set up rate limiting for FastAPI application.
    
    Args:
        app: FastAPI application instance
        
    Example:
        app = FastAPI()
        setup_rate_limiting(app)
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Rate limit statistics
def get_rate_limit_stats(identifier: str) -> dict:
    """
    Get rate limit statistics for a user/IP.
    
    Args:
        identifier: User or IP identifier
        
    Returns:
        dict: Statistics including requests count and remaining limit
    """
    try:
        key = f"slowapi:{identifier}"
        count = redis_client.get(key)
        ttl = redis_client.ttl(key)
        
        return {
            "identifier": identifier,
            "requests_count": int(count) if count else 0,
            "ttl_seconds": ttl if ttl > 0 else 0,
            "status": "active" if count else "inactive"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "unavailable"
        }


def reset_rate_limit(identifier: str) -> bool:
    """
    Reset rate limit for a specific user/IP (admin function).
    
    Args:
        identifier: User or IP identifier
        
    Returns:
        bool: True if reset successful
    """
    try:
        pattern = f"slowapi:{identifier}*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        return True
    except Exception as e:
        print(f"Error resetting rate limit: {e}")
        return False
