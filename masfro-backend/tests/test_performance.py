# filename: tests/test_performance.py
"""
Test suite for performance monitoring utilities.

Tests cover Issue #21: Performance monitoring and profiling.

Author: MAS-FRO Development Team
Date: January 2026
"""

import pytest
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.performance import (
    PerformanceMonitor,
    OperationStats,
    CacheStats,
    get_monitor,
    timed_operation,
    record_cache_hit,
    record_cache_miss,
    get_performance_stats,
    log_performance_summary
)


class TestOperationStats:
    """Tests for OperationStats dataclass."""

    def test_initial_state(self):
        """Stats should start at zero."""
        stats = OperationStats(name="test")
        assert stats.call_count == 0
        assert stats.total_time_ms == 0.0
        assert stats.min_time_ms == float('inf')
        assert stats.max_time_ms == 0.0
        assert stats.slow_count == 0

    def test_avg_time_no_calls(self):
        """Average time should be 0 when no calls."""
        stats = OperationStats(name="test")
        assert stats.avg_time_ms == 0.0

    def test_avg_time_calculation(self):
        """Average time should be calculated correctly."""
        stats = OperationStats(name="test")
        stats.call_count = 10
        stats.total_time_ms = 100.0
        assert stats.avg_time_ms == 10.0

    def test_slow_percentage(self):
        """Slow percentage should be calculated correctly."""
        stats = OperationStats(name="test")
        stats.call_count = 100
        stats.slow_count = 20
        assert stats.slow_percentage == 20.0

    def test_to_dict(self):
        """Stats should serialize to dict correctly."""
        stats = OperationStats(name="test")
        stats.call_count = 5
        stats.total_time_ms = 50.0
        stats.min_time_ms = 5.0
        stats.max_time_ms = 15.0
        stats.slow_count = 1

        d = stats.to_dict()
        assert d['name'] == "test"
        assert d['call_count'] == 5
        assert d['avg_time_ms'] == 10.0
        assert d['slow_count'] == 1


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_initial_state(self):
        """Cache stats should start at zero."""
        stats = CacheStats(name="test_cache")
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0

    def test_total_requests(self):
        """Total requests should sum hits and misses."""
        stats = CacheStats(name="test_cache")
        stats.hits = 80
        stats.misses = 20
        assert stats.total_requests == 100

    def test_hit_rate_calculation(self):
        """Hit rate should be calculated correctly."""
        stats = CacheStats(name="test_cache")
        stats.hits = 80
        stats.misses = 20
        assert stats.hit_rate == 80.0

    def test_hit_rate_no_requests(self):
        """Hit rate should be 0 when no requests."""
        stats = CacheStats(name="test_cache")
        assert stats.hit_rate == 0.0

    def test_to_dict(self):
        """Cache stats should serialize correctly."""
        stats = CacheStats(name="test_cache")
        stats.hits = 80
        stats.misses = 20
        stats.evictions = 5

        d = stats.to_dict()
        assert d['name'] == "test_cache"
        assert d['hits'] == 80
        assert d['hit_rate_percent'] == 80.0
        assert d['evictions'] == 5


class TestPerformanceMonitor:
    """Tests for PerformanceMonitor class."""

    @pytest.fixture
    def monitor(self):
        """Create fresh monitor for each test."""
        m = PerformanceMonitor()
        m.reset()  # Clear any previous state
        return m

    def test_singleton_pattern(self):
        """Monitor should be a singleton."""
        m1 = PerformanceMonitor()
        m2 = PerformanceMonitor()
        assert m1 is m2

    def test_record_operation(self, monitor):
        """Operations should be recorded correctly."""
        monitor.record_operation("test_op", 50.0)
        monitor.record_operation("test_op", 100.0)

        stats = monitor.get_operation_stats("test_op")
        assert stats['call_count'] == 2
        assert stats['total_time_ms'] == 150.0
        assert stats['min_time_ms'] == 50.0
        assert stats['max_time_ms'] == 100.0

    def test_slow_operation_detection(self, monitor):
        """Slow operations should be detected."""
        monitor.SLOW_OPERATION_THRESHOLD_MS = 50

        monitor.record_operation("fast_op", 30.0)
        monitor.record_operation("slow_op", 100.0)

        fast_stats = monitor.get_operation_stats("fast_op")
        slow_stats = monitor.get_operation_stats("slow_op")

        assert fast_stats['slow_count'] == 0
        assert slow_stats['slow_count'] == 1

    def test_custom_slow_threshold(self, monitor):
        """Custom slow threshold should work."""
        monitor.record_operation("op", 75.0, slow_threshold_ms=100.0)
        stats = monitor.get_operation_stats("op")
        assert stats['slow_count'] == 0  # Not slow with higher threshold

        monitor.record_operation("op", 75.0, slow_threshold_ms=50.0)
        stats = monitor.get_operation_stats("op")
        assert stats['slow_count'] == 1  # Slow with lower threshold

    def test_cache_hit_recording(self, monitor):
        """Cache hits should be recorded."""
        monitor.record_cache_hit("test_cache")
        monitor.record_cache_hit("test_cache")
        monitor.record_cache_hit("test_cache")

        stats = monitor.get_cache_stats("test_cache")
        assert stats['hits'] == 3

    def test_cache_miss_recording(self, monitor):
        """Cache misses should be recorded."""
        monitor.record_cache_miss("test_cache")
        monitor.record_cache_miss("test_cache")

        stats = monitor.get_cache_stats("test_cache")
        assert stats['misses'] == 2

    def test_cache_eviction_recording(self, monitor):
        """Cache evictions should be recorded."""
        monitor.record_cache_eviction("test_cache", 5)

        stats = monitor.get_cache_stats("test_cache")
        assert stats['evictions'] == 5

    def test_time_operation_context_manager(self, monitor):
        """Context manager should time operations."""
        with monitor.time_operation("timed_op"):
            time.sleep(0.01)  # 10ms

        stats = monitor.get_operation_stats("timed_op")
        assert stats['call_count'] == 1
        assert stats['total_time_ms'] >= 10.0  # At least 10ms

    def test_get_all_statistics(self, monitor):
        """All statistics should be aggregated correctly."""
        monitor.record_operation("op1", 50.0)
        monitor.record_operation("op2", 100.0)
        monitor.record_cache_hit("cache1")
        monitor.record_cache_miss("cache1")

        stats = monitor.get_all_statistics()

        assert 'uptime_seconds' in stats
        assert 'operations' in stats
        assert 'caches' in stats
        assert 'summary' in stats
        assert stats['summary']['total_operations'] == 2
        assert stats['summary']['total_cache_requests'] == 2

    def test_reset(self, monitor):
        """Reset should clear all statistics."""
        monitor.record_operation("op", 50.0)
        monitor.record_cache_hit("cache")

        monitor.reset()

        assert monitor.get_operation_stats("op") is None
        assert monitor.get_cache_stats("cache") is None

    def test_disabled_monitoring(self, monitor):
        """When disabled, no stats should be recorded."""
        monitor.ENABLED = False
        try:
            monitor.record_operation("op", 50.0)
            monitor.record_cache_hit("cache")

            assert monitor.get_operation_stats("op") is None
            assert monitor.get_cache_stats("cache") is None
        finally:
            monitor.ENABLED = True  # Re-enable


class TestTimedOperationDecorator:
    """Tests for @timed_operation decorator."""

    @pytest.fixture(autouse=True)
    def reset_monitor(self):
        """Reset monitor before each test."""
        get_monitor().reset()

    def test_basic_decorator(self):
        """Decorator should time function execution."""
        @timed_operation("decorated_op")
        def test_func():
            time.sleep(0.01)
            return "result"

        result = test_func()
        assert result == "result"

        stats = get_monitor().get_operation_stats("decorated_op")
        assert stats['call_count'] == 1
        assert stats['total_time_ms'] >= 10.0

    def test_decorator_with_args(self):
        """Decorator should work with function arguments."""
        @timed_operation("add_op")
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5

        stats = get_monitor().get_operation_stats("add_op")
        assert stats['call_count'] == 1

    def test_decorator_uses_function_name(self):
        """Decorator should use function name if not specified."""
        @timed_operation()
        def my_function():
            pass

        my_function()

        stats = get_monitor().get_operation_stats("my_function")
        assert stats is not None
        assert stats['call_count'] == 1

    def test_decorator_with_custom_threshold(self):
        """Decorator should respect custom slow threshold."""
        @timed_operation("slow_check", slow_threshold_ms=5.0)
        def slow_func():
            time.sleep(0.01)

        slow_func()

        stats = get_monitor().get_operation_stats("slow_check")
        assert stats['slow_count'] == 1


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.fixture(autouse=True)
    def reset_monitor(self):
        """Reset monitor before each test."""
        get_monitor().reset()

    def test_record_cache_hit_convenience(self):
        """Convenience function should record cache hit."""
        record_cache_hit("test_cache")
        stats = get_monitor().get_cache_stats("test_cache")
        assert stats['hits'] == 1

    def test_record_cache_miss_convenience(self):
        """Convenience function should record cache miss."""
        record_cache_miss("test_cache")
        stats = get_monitor().get_cache_stats("test_cache")
        assert stats['misses'] == 1

    def test_get_performance_stats_convenience(self):
        """Convenience function should return all stats."""
        record_cache_hit("test")
        stats = get_performance_stats()
        assert 'caches' in stats
        assert 'test' in stats['caches']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
