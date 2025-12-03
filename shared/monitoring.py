"""
Prometheus Monitoring & Metrics

This module implements comprehensive monitoring and metrics collection.

Features:
- Request/response metrics
- Database query metrics
- Custom business metrics (bookings, reviews)
- Service health metrics
- Latency tracking

Author: Jad Eido
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from fastapi import FastAPI, Request
from typing import Callable
import time
import psutil
import os

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# Business metrics
bookings_total = Counter(
    'bookings_total',
    'Total bookings created',
    ['status']
)

bookings_active = Gauge(
    'bookings_active',
    'Number of active bookings'
)

rooms_available = Gauge(
    'rooms_available',
    'Number of available rooms'
)

users_total = Gauge(
    'users_total',
    'Total number of users',
    ['role']
)

reviews_total = Counter(
    'reviews_total',
    'Total reviews submitted',
    ['rating_range']
)

reviews_flagged = Counter(
    'reviews_flagged',
    'Total reviews flagged for moderation'
)

# Database metrics
db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type']
)

db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections'
)

# Authentication metrics
auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['result']
)

jwt_tokens_issued = Counter(
    'jwt_tokens_issued',
    'Total JWT tokens issued'
)

# System metrics
system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'CPU usage percentage'
)

system_memory_usage = Gauge(
    'system_memory_usage_bytes',
    'Memory usage in bytes'
)

system_info = Info(
    'system_info',
    'System information'
)


def setup_metrics(app: FastAPI):
    """
    Set up Prometheus metrics for FastAPI application.
    
    Args:
        app: FastAPI application instance
        
        Example:
        app = FastAPI()
        setup_metrics(app)
    """
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )
    
    # Add default metrics
    instrumentator.add(
        metrics.request_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )
    
    instrumentator.add(
        metrics.response_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )
    
    instrumentator.add(
        metrics.latency(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )
    
    instrumentator.add(
        metrics.requests(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )
    
    instrumentator.instrument(app)
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)
    
    system_info.info({
        'version': '1.0.0',
        'python_version': os.sys.version.split()[0],
        'environment': os.getenv('ENVIRONMENT', 'development')
    })
    
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        """Middleware to collect custom metrics."""
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response


def track_booking_created(status: str = "confirmed"):
    """
    Track booking creation metric.
    
    Args:
        status: Booking status (confirmed, pending, cancelled)
    """
    bookings_total.labels(status=status).inc()


def update_active_bookings(count: int):
    """
    Update active bookings gauge.
    
    Args:
        count: Number of active bookings
    """
    bookings_active.set(count)


def update_available_rooms(count: int):
    """
    Update available rooms gauge.
    
    Args:
        count: Number of available rooms
    """
    rooms_available.set(count)


def update_user_count(role: str, count: int):
    """
    Update user count by role.
    
    Args:
        role: User role
        count: Number of users with that role
    """
    users_total.labels(role=role).set(count)


def track_review_submitted(rating: float):
    """
    Track review submission.
    
    Args:
        rating: Review rating (1-5)
    """
    if rating <= 2.0:
        rating_range = "low"
    elif rating <= 3.5:
        rating_range = "medium"
    else:
        rating_range = "high"
    
    reviews_total.labels(rating_range=rating_range).inc()


def track_review_flagged():
    """Track flagged review."""
    reviews_flagged.inc()


def track_auth_attempt(success: bool):
    """
    Track authentication attempt.
    
    Args:
        success: Whether authentication was successful
    """
    result = "success" if success else "failure"
    auth_attempts_total.labels(result=result).inc()


def track_jwt_issued():
    """Track JWT token issuance."""
    jwt_tokens_issued.inc()


def track_db_query(query_type: str, duration: float):
    """
    Track database query.
    
    Args:
        query_type: Type of query (select, insert, update, delete)
        duration: Query duration in seconds
    """
    db_query_duration_seconds.labels(query_type=query_type).observe(duration)


def update_system_metrics():
    """Update system resource metrics."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        system_cpu_usage.set(cpu_percent)
        
        memory = psutil.virtual_memory()
        system_memory_usage.set(memory.used)
    except Exception as e:
        print(f"Error updating system metrics: {e}")


class MetricsCollector:
    """
    Context manager for collecting metrics with automatic timing.
    
    Example:
        with MetricsCollector("select") as collector:
            result = db.query(Room).all()
    """
    
    def __init__(self, query_type: str):
        """
        Initialize metrics collector.
        
        Args:
            query_type: Type of operation to track
        """
        self.query_type = query_type
        self.start_time = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Record duration."""
        if self.start_time:
            duration = time.time() - self.start_time
            track_db_query(self.query_type, duration)


def get_metrics_summary() -> dict:
    """
    Get summary of current metrics.
    
    Returns:
        dict: Summary of key metrics
    """
    try:
        total_requests = 0
        for metric in http_requests_total.collect():
            for sample in metric.samples:
                if sample.name == 'http_requests_total':
                    total_requests += sample.value
        
        return {
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            },
            "requests": {
                "total": total_requests,
            },
            "status": "healthy"
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}
