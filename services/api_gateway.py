"""
API Gateway with Load Balancing

This module implements a centralized API gateway with load balancing.

Features:
- Single entry point for all services
- Round-robin load balancing
- Health checks for backend services
- Request routing based on path
- Circuit breaker pattern
- Request/response logging

Author: Tarek El Mourad
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import httpx
from typing import Dict, List, Optional
import asyncio
from datetime import datetime, timedelta
import logging
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceEndpoint:
    """
    Represents a backend service endpoint.
    
    Attributes:
        url: Service URL
        status: Current health status
        last_check: Last health check timestamp
        failure_count: Number of consecutive failures
    """
    
    def __init__(self, url: str):
        """
        Initialize service endpoint.
        
        Args:
            url: Service URL
        """
        self.url = url
        self.status = ServiceStatus.UNKNOWN
        self.last_check = None
        self.failure_count = 0
        self.response_times = []
    
    def record_success(self, response_time: float):
        """
        Record successful request.
        
        Args:
            response_time: Response time in seconds
        """
        self.status = ServiceStatus.HEALTHY
        self.failure_count = 0
        self.last_check = datetime.utcnow()
        self.response_times.append(response_time)
        
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]
    
    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_check = datetime.utcnow()
        
        if self.failure_count >= 3:
            self.status = ServiceStatus.UNHEALTHY
    
    def get_avg_response_time(self) -> float:
        """
        Get average response time.
        
        Returns:
            float: Average response time in seconds
        """
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)


class LoadBalancer:
    """
    Round-robin load balancer for backend services.
    
    Distributes requests across multiple service instances.
    """
    
    def __init__(self, service_name: str, endpoints: List[str]):
        """
        Initialize load balancer.
        
        Args:
            service_name: Name of the service
            endpoints: List of service endpoint URLs
        """
        self.service_name = service_name
        self.endpoints = [ServiceEndpoint(url) for url in endpoints]
        self.current_index = 0
    
    def get_next_endpoint(self) -> Optional[ServiceEndpoint]:
        """
        Get next healthy endpoint using round-robin.
        
        Returns:
            ServiceEndpoint: Next healthy endpoint or None
        """
        for _ in range(len(self.endpoints)):
            endpoint = self.endpoints[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.endpoints)
            
            if endpoint.status != ServiceStatus.UNHEALTHY:
                return endpoint
        
        return self.endpoints[0] if self.endpoints else None
    
    async def health_check(self):
        """Perform health check on all endpoints."""
        async with httpx.AsyncClient() as client:
            for endpoint in self.endpoints:
                try:
                    response = await client.get(
                        f"{endpoint.url}/health",
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        endpoint.record_success(response.elapsed.total_seconds())
                    else:
                        endpoint.record_failure()
                        
                except Exception as e:
                    logger.error(f"Health check failed for {endpoint.url}: {e}")
                    endpoint.record_failure()
    
    def get_status(self) -> dict:
        """
        Get load balancer status.
        
        Returns:
            dict: Status information
        """
        return {
            "service": self.service_name,
            "endpoints": [
                {
                    "url": ep.url,
                    "status": ep.status.value,
                    "failure_count": ep.failure_count,
                    "avg_response_time": round(ep.get_avg_response_time(), 3),
                    "last_check": ep.last_check.isoformat() if ep.last_check else None
                }
                for ep in self.endpoints
            ]
        }


class APIGateway:
    """
    API Gateway for routing requests to backend services.
    
    Features:
    - Service discovery
    - Load balancing
    - Health monitoring
    - Request routing
    """
    
    def __init__(self):
        """Initialize API gateway."""
        self.load_balancers: Dict[str, LoadBalancer] = {}
        self.client = httpx.AsyncClient(timeout=30.0)
        self._setup_services()
    
    def _setup_services(self):
        """Set up service load balancers."""
        services = {
            "users": ["http://localhost:8001"],
            "rooms": ["http://localhost:8002"],
            "bookings": ["http://localhost:8003"],
            "reviews": ["http://localhost:8004"]
        }
        
        for service_name, endpoints in services.items():
            self.load_balancers[service_name] = LoadBalancer(
                service_name,
                endpoints
            )
    
    def get_service_from_path(self, path: str) -> Optional[str]:
        """
        Extract service name from request path.
        
        Args:
            path: Request path
            
        Returns:
            str: Service name or None
        """
        path_parts = path.strip('/').split('/')
        if not path_parts:
            return None
        
        service_map = {
            "users": "users",
            "register": "users",
            "login": "users",
            "rooms": "rooms",
            "bookings": "bookings",
            "reviews": "reviews"
        }
        
        return service_map.get(path_parts[0])
    
    async def route_request(
        self,
        method: str,
        path: str,
        headers: dict,
        params: dict = None,
        json_data: dict = None
    ) -> httpx.Response:
        """
        Route request to appropriate backend service.
        
        Args:
            method: HTTP method
            path: Request path
            headers: Request headers
            params: Query parameters
            json_data: JSON body data
            
        Returns:
            httpx.Response: Response from backend service
            
        Raises:
            HTTPException: If service not found or unavailable
        """
        service_name = self.get_service_from_path(path)
        
        if not service_name or service_name not in self.load_balancers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service not found"
            )
        
        lb = self.load_balancers[service_name]
        endpoint = lb.get_next_endpoint()
        
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service {service_name} is unavailable"
            )
        
        target_url = f"{endpoint.url}{path}"
        
        try:
        try:
            start_time = datetime.utcnow()
            
            response = await self.client.request(
                method=method,
                url=target_url,
                headers=headers,
                params=params,
                json=json_data
            )
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            endpoint.record_success(elapsed)
            
            return response
            
        except Exception as e:
            endpoint.record_failure()
            logger.error(f"Request to {target_url} failed: {e}")
            
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error communicating with {service_name} service"
            )
    
    async def health_check_all(self):
        """Perform health checks on all services."""
        tasks = [
            lb.health_check()
            for lb in self.load_balancers.values()
        ]
        await asyncio.gather(*tasks)
    
    def get_gateway_status(self) -> dict:
        """
        Get overall gateway status.
        
        Returns:
            dict: Gateway status with all services
        """
        return {
            "gateway": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                name: lb.get_status()
                for name, lb in self.load_balancers.items()
            }
        }


# Create FastAPI app for gateway
app = FastAPI(title="Smart Meeting Room API Gateway", version="1.0.0")
gateway = APIGateway()


@app.on_event("startup")
async def startup_event():
    """Perform initial health checks on startup."""
    await gateway.health_check_all()
    asyncio.create_task(periodic_health_checks())


async def periodic_health_checks():
    """Perform health checks every 30 seconds."""
    while True:
        await asyncio.sleep(30)
        try:
            await gateway.health_check_all()
        except Exception as e:
            logger.error(f"Health check error: {e}")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway_handler(request: Request, path: str):
    """
    Main gateway handler that routes all requests.
    
    Args:
        request: FastAPI request object
        path: Request path
        
    Returns:
        Response from backend service
    """
    headers = dict(request.headers)
    params = dict(request.query_params)
    
    json_data = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            json_data = await request.json()
        except:
            pass
    
    try:
        response = await gateway.route_request(
            method=request.method,
            path=f"/{path}",
            headers=headers,
            params=params,
            json_data=json_data
        )
        
        return JSONResponse(
            content=response.json() if response.headers.get("content-type") == "application/json" else response.text,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Gateway error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal gateway error"
        )


@app.get("/gateway/health")
async def gateway_health():
    """
    Gateway health check endpoint.
    
    Returns:
        dict: Gateway health status
    """
    return gateway.get_gateway_status()


@app.get("/gateway/status")
async def gateway_status():
    """
    Detailed gateway status endpoint.
    
    Returns:
        dict: Detailed status of all services
    """
    return gateway.get_gateway_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
