"""
Health check script for all services.

Tests connectivity and basic functionality of all microservices.

Usage: python scripts/health_check.py
"""

import requests
import sys
from typing import Dict, List


SERVICES = {
    "Users Service": "http://localhost:8001/health",
    "Rooms Service": "http://localhost:8002/health",
    "Bookings Service": "http://localhost:8003/health",
    "Reviews Service": "http://localhost:8004/health",
}


def check_service(name: str, url: str) -> Dict:
    """Check if a service is healthy."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "name": name,
                "status": "HEALTHY",
                "response": data,
                "error": None
            }
        else:
            return {
                "name": name,
                "status": "UNHEALTHY",
                "response": None,
                "error": f"Status code: {response.status_code}"
            }
    except requests.exceptions.ConnectionError:
        return {
            "name": name,
            "status": "OFFLINE",
            "response": None,
            "error": "Connection refused - service may not be running"
        }
    except requests.exceptions.Timeout:
        return {
            "name": name,
            "status": "TIMEOUT",
            "response": None,
            "error": "Request timed out"
        }
    except Exception as e:
        return {
            "name": name,
            "status": "ERROR",
            "response": None,
            "error": str(e)
        }


def main():
    """Run health checks on all services."""
    print("="*70)
    print(" Smart Meeting Room Management System - Health Check")
    print("="*70)
    print()
    
    results = []
    for service_name, service_url in SERVICES.items():
        print(f"Checking {service_name}...", end=" ")
        result = check_service(service_name, service_url)
        results.append(result)
        print(result["status"])
        
        if result["error"]:
            print(f"  Error: {result['error']}")
        elif result["response"]:
            print(f"  Response: {result['response']}")
        print()
    
    # Summary
    print("="*70)
    print(" Summary")
    print("="*70)
    
    healthy_count = sum(1 for r in results if "HEALTHY" in r["status"])
    total_count = len(results)
    
    print(f"Total Services: {total_count}")
    print(f"Healthy: {healthy_count}")
    print(f"Unhealthy: {total_count - healthy_count}")
    
    if healthy_count == total_count:
        print("\nAll services are operational!")
        sys.exit(0)
    else:
        print("\nSome services are not operational!")
        print("\nTroubleshooting:")
        print("1. Check if Docker containers are running: docker-compose ps")
        print("2. Check Docker logs: docker-compose logs -f")
        print("3. Restart services: docker-compose restart")
        sys.exit(1)


if __name__ == "__main__":
    main()
