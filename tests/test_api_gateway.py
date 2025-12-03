"""
Tests for Part II Enhancement: API Gateway with Load Balancing
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.api_gateway import (
    ServiceEndpoint,
    LoadBalancer,
    APIGateway,
    ServiceStatus
)


def test_service_endpoint_initialization():
    """Test ServiceEndpoint initialization."""
    endpoint = ServiceEndpoint("http://localhost:8001")
    
    assert endpoint.url == "http://localhost:8001"
    assert endpoint.status == ServiceStatus.UNKNOWN
    assert endpoint.failure_count == 0
    assert endpoint.last_check is None
    assert endpoint.response_times == []


def test_service_endpoint_record_success():
    """Test recording successful request."""
    endpoint = ServiceEndpoint("http://localhost:8001")
    
    endpoint.record_success(0.15)
    
    assert endpoint.status == ServiceStatus.HEALTHY
    assert endpoint.failure_count == 0
    assert endpoint.last_check is not None
    assert len(endpoint.response_times) == 1
    assert endpoint.response_times[0] == 0.15


def test_service_endpoint_record_failure():
    """Test recording failed request."""
    endpoint = ServiceEndpoint("http://localhost:8001")
    
    # First failure
    endpoint.record_failure()
    assert endpoint.failure_count == 1
    assert endpoint.status == ServiceStatus.UNKNOWN
    
    # Second failure
    endpoint.record_failure()
    assert endpoint.failure_count == 2
    assert endpoint.status == ServiceStatus.UNKNOWN
    
    # Third failure - should mark as unhealthy
    endpoint.record_failure()
    assert endpoint.failure_count == 3
    assert endpoint.status == ServiceStatus.UNHEALTHY


def test_service_endpoint_avg_response_time():
    """Test average response time calculation."""
    endpoint = ServiceEndpoint("http://localhost:8001")
    
    # No data yet
    assert endpoint.get_avg_response_time() == 0.0
    
    # Add response times
    endpoint.record_success(0.10)
    endpoint.record_success(0.20)
    endpoint.record_success(0.30)
    
    avg = endpoint.get_avg_response_time()
    assert abs(avg - 0.20) < 0.01  # (0.10 + 0.20 + 0.30) / 3, allow floating point error


def test_service_endpoint_response_times_limit():
    """Test that response times list is limited to 100."""
    endpoint = ServiceEndpoint("http://localhost:8001")
    
    # Add 150 response times
    for i in range(150):
        endpoint.record_success(0.1)
    
    # Should only keep last 100
    assert len(endpoint.response_times) == 100


def test_load_balancer_initialization():
    """Test LoadBalancer initialization."""
    endpoints = ["http://localhost:8001", "http://localhost:8002"]
    lb = LoadBalancer("test_service", endpoints)
    
    assert lb.service_name == "test_service"
    assert len(lb.endpoints) == 2
    assert lb.current_index == 0


def test_load_balancer_round_robin():
    """Test round-robin endpoint selection."""
    endpoints = ["http://localhost:8001", "http://localhost:8002", "http://localhost:8003"]
    lb = LoadBalancer("test_service", endpoints)
    
    # Mark all as healthy
    for ep in lb.endpoints:
        ep.status = ServiceStatus.HEALTHY
    
    # Should cycle through endpoints
    ep1 = lb.get_next_endpoint()
    ep2 = lb.get_next_endpoint()
    ep3 = lb.get_next_endpoint()
    ep4 = lb.get_next_endpoint()  # Should wrap around
    
    assert ep1.url == endpoints[0]
    assert ep2.url == endpoints[1]
    assert ep3.url == endpoints[2]
    assert ep4.url == endpoints[0]  # Back to first


def test_load_balancer_skips_unhealthy():
    """Test that load balancer skips unhealthy endpoints."""
    endpoints = ["http://localhost:8001", "http://localhost:8002", "http://localhost:8003"]
    lb = LoadBalancer("test_service", endpoints)
    
    # Mark first as healthy, second as unhealthy, third as healthy
    lb.endpoints[0].status = ServiceStatus.HEALTHY
    lb.endpoints[1].status = ServiceStatus.UNHEALTHY
    lb.endpoints[2].status = ServiceStatus.HEALTHY
    
    # Should skip unhealthy endpoint
    ep1 = lb.get_next_endpoint()
    ep2 = lb.get_next_endpoint()
    ep3 = lb.get_next_endpoint()
    
    # Should never return the unhealthy endpoint
    assert ep1.url != endpoints[1]
    assert ep2.url != endpoints[1]
    assert ep3.url != endpoints[1]


def test_load_balancer_all_unhealthy():
    """Test load balancer behavior when all endpoints are unhealthy."""
    endpoints = ["http://localhost:8001"]
    lb = LoadBalancer("test_service", endpoints)
    
    # Mark as unhealthy
    lb.endpoints[0].status = ServiceStatus.UNHEALTHY
    
    # Should still return an endpoint (best effort)
    ep = lb.get_next_endpoint()
    assert ep is not None
    assert ep.url == endpoints[0]


def test_load_balancer_get_status():
    """Test getting load balancer status."""
    endpoints = ["http://localhost:8001"]
    lb = LoadBalancer("test_service", endpoints)
    
    lb.endpoints[0].record_success(0.15)
    
    status = lb.get_status()
    
    assert status["service"] == "test_service"
    assert "endpoints" in status
    assert len(status["endpoints"]) == 1
    assert status["endpoints"][0]["url"] == endpoints[0]
    assert status["endpoints"][0]["status"] == "healthy"


def test_api_gateway_initialization():
    """Test APIGateway initialization."""
    gateway = APIGateway()
    
    assert gateway.load_balancers is not None
    assert len(gateway.load_balancers) == 4  # users, rooms, bookings, reviews
    assert "users" in gateway.load_balancers
    assert "rooms" in gateway.load_balancers
    assert "bookings" in gateway.load_balancers
    assert "reviews" in gateway.load_balancers


def test_api_gateway_get_service_from_path():
    """Test extracting service name from path."""
    gateway = APIGateway()
    
    assert gateway.get_service_from_path("/users") == "users"
    assert gateway.get_service_from_path("/users/johndoe") == "users"
    assert gateway.get_service_from_path("/register") == "users"
    assert gateway.get_service_from_path("/login") == "users"
    assert gateway.get_service_from_path("/rooms") == "rooms"
    assert gateway.get_service_from_path("/rooms/1") == "rooms"
    assert gateway.get_service_from_path("/bookings") == "bookings"
    assert gateway.get_service_from_path("/reviews") == "reviews"
    assert gateway.get_service_from_path("/unknown") is None


@pytest.mark.asyncio
@patch('httpx.AsyncClient.request')
async def test_api_gateway_route_request_success(mock_request):
    """Test successful request routing."""
    gateway = APIGateway()
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}
    mock_response.headers = {"content-type": "application/json"}
    mock_request.return_value = mock_response
    
    # Mark endpoint as healthy
    gateway.load_balancers["users"].endpoints[0].status = ServiceStatus.HEALTHY
    
    response = await gateway.route_request(
        method="GET",
        path="/users",
        headers={},
        params=None,
        json_data=None
    )
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_gateway_route_request_invalid_service():
    """Test routing to invalid service."""
    gateway = APIGateway()
    
    with pytest.raises(Exception):  # Should raise HTTPException
        await gateway.route_request(
            method="GET",
            path="/invalid",
            headers={},
            params=None,
            json_data=None
        )


def test_api_gateway_get_gateway_status():
    """Test getting gateway status."""
    gateway = APIGateway()
    
    status = gateway.get_gateway_status()
    
    assert status["gateway"] == "operational"
    assert "timestamp" in status
    assert "services" in status
    assert len(status["services"]) == 4


@pytest.mark.asyncio
@patch('httpx.AsyncClient.get')
async def test_load_balancer_health_check(mock_get):
    """Test health check functionality."""
    endpoints = ["http://localhost:8001"]
    lb = LoadBalancer("test_service", endpoints)
    
    # Mock successful health check
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.elapsed.total_seconds.return_value = 0.05
    mock_get.return_value = mock_response
    
    await lb.health_check()
    
    assert lb.endpoints[0].status == ServiceStatus.HEALTHY


def test_service_endpoint_recovery_after_failure():
    """Test that endpoint can recover after failures."""
    endpoint = ServiceEndpoint("http://localhost:8001")
    
    # Cause failures
    endpoint.record_failure()
    endpoint.record_failure()
    endpoint.record_failure()
    assert endpoint.status == ServiceStatus.UNHEALTHY
    
    # Record success - should recover
    endpoint.record_success(0.1)
    assert endpoint.status == ServiceStatus.HEALTHY
    assert endpoint.failure_count == 0
