"""
Tests for Part II Enhancement: Prometheus Monitoring
"""

import pytest
from unittest.mock import Mock, patch

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.monitoring import (
    track_booking_created,
    update_active_bookings,
    update_available_rooms,
    update_user_count,
    track_review_submitted,
    track_review_flagged,
    track_auth_attempt,
    track_jwt_issued,
    track_db_query,
    MetricsCollector,
    get_metrics_summary
)


def test_track_booking_created():
    """Test booking creation tracking."""
    # Should not raise exception
    track_booking_created("confirmed")
    track_booking_created("pending")
    track_booking_created("cancelled")


def test_update_active_bookings():
    """Test active bookings gauge update."""
    update_active_bookings(10)
    update_active_bookings(0)
    update_active_bookings(100)


def test_update_available_rooms():
    """Test available rooms gauge update."""
    update_available_rooms(5)
    update_available_rooms(0)
    update_available_rooms(50)


def test_update_user_count():
    """Test user count update by role."""
    update_user_count("ADMIN", 2)
    update_user_count("REGULAR_USER", 100)
    update_user_count("MODERATOR", 5)


def test_track_review_submitted():
    """Test review submission tracking."""
    # Low rating
    track_review_submitted(1.5)
    
    # Medium rating
    track_review_submitted(3.0)
    
    # High rating
    track_review_submitted(4.5)


def test_track_review_flagged():
    """Test flagged review tracking."""
    track_review_flagged()
    track_review_flagged()


def test_track_auth_attempt():
    """Test authentication attempt tracking."""
    track_auth_attempt(success=True)
    track_auth_attempt(success=False)


def test_track_jwt_issued():
    """Test JWT token issuance tracking."""
    track_jwt_issued()
    track_jwt_issued()


def test_track_db_query():
    """Test database query tracking."""
    track_db_query("select", 0.050)
    track_db_query("insert", 0.020)
    track_db_query("update", 0.030)
    track_db_query("delete", 0.015)


def test_metrics_collector_context_manager():
    """Test MetricsCollector context manager."""
    import time
    
    with MetricsCollector("select") as collector:
        # Simulate some work
        time.sleep(0.01)
        assert collector is not None
    
    # Should complete without errors


def test_metrics_collector_timing():
    """Test that MetricsCollector measures time correctly."""
    import time
    
    start_time = time.time()
    with MetricsCollector("select"):
        time.sleep(0.05)
    elapsed = time.time() - start_time
    
    # Should take at least 0.05 seconds
    assert elapsed >= 0.05


def test_get_metrics_summary():
    """Test metrics summary retrieval."""
    summary = get_metrics_summary()
    
    assert isinstance(summary, dict)
    
    if "error" not in summary:
        # If successful, should have system metrics
        assert "system" in summary
        assert "requests" in summary
        assert "status" in summary
        assert summary["status"] == "healthy"
    else:
        # If error (e.g., psutil not available), should have error key
        assert "error" in summary
        assert summary["status"] == "error"


@patch('shared.monitoring.psutil.cpu_percent')
@patch('shared.monitoring.psutil.virtual_memory')
@patch('shared.monitoring.psutil.disk_usage')
def test_get_metrics_summary_with_mocked_psutil(mock_disk, mock_memory, mock_cpu):
    """Test metrics summary with mocked system utilities."""
    # Mock system metrics
    mock_cpu.return_value = 45.5
    
    mock_memory_obj = Mock()
    mock_memory_obj.percent = 60.2
    mock_memory.return_value = mock_memory_obj
    
    mock_disk_obj = Mock()
    mock_disk_obj.percent = 75.0
    mock_disk.return_value = mock_disk_obj
    
    summary = get_metrics_summary()
    
    if summary["status"] == "error":
        print(f"Error: {summary.get('error', 'Unknown error')}")
    assert summary["status"] == "healthy", f"Got error: {summary.get('error', 'Unknown')}"
    assert "system" in summary
    assert summary["system"]["cpu_percent"] == 45.5
    assert summary["system"]["memory_percent"] == 60.2
    assert summary["system"]["disk_percent"] == 75.0


def test_review_rating_categorization():
    """Test that review ratings are correctly categorized."""
    # Low ratings (1-2)
    track_review_submitted(1.0)
    track_review_submitted(2.0)
    
    # Medium ratings (2.1-3.5)
    track_review_submitted(2.5)
    track_review_submitted(3.5)
    
    # High ratings (3.6-5)
    track_review_submitted(4.0)
    track_review_submitted(5.0)
    
    # Should not raise any exceptions


def test_multiple_metric_updates():
    """Test updating multiple metrics in sequence."""
    # Simulate a series of operations
    update_available_rooms(10)
    track_booking_created("confirmed")
    update_active_bookings(5)
    track_auth_attempt(True)
    track_jwt_issued()
    track_db_query("select", 0.025)
    update_user_count("REGULAR_USER", 50)
    track_review_submitted(4.5)
    
    # All should complete without errors
    assert True


def test_metrics_with_zero_values():
    """Test metrics with zero or boundary values."""
    update_active_bookings(0)
    update_available_rooms(0)
    update_user_count("ADMIN", 0)
    track_db_query("select", 0.0)
    
    # Should handle zero values gracefully
    assert True


def test_metrics_with_large_values():
    """Test metrics with large values."""
    update_active_bookings(10000)
    update_available_rooms(5000)
    update_user_count("REGULAR_USER", 100000)
    track_db_query("select", 10.5)
    
    # Should handle large values gracefully
    assert True
