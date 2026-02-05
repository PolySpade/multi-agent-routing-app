# filename: app/core/performance.py

"""
Performance Monitoring Utilities for MAS-FRO Agents

This module provides performance monitoring tools for tracking:
- Operation timing (slow operation detection)
- Cache hit/miss rates
- Memory usage tracking
- Performance statistics reporting

Issue #21: Add Performance Monitoring and Profiling

Usage:
    from app.core.performance import PerformanceMonitor, timed_operation

    # Use as decorator
    @timed_operation("calculate_route")
    def calculate_route(...):
        ...

    # Use as context manager
    with PerformanceMonitor.time_operation("data_fusion"):
        fuse_data(...)

    # Get statistics
    stats = PerformanceMonitor.get_statistics()

Author: MAS-FRO Development Team
Date: January 2026
"""

import time
import logging
import functools
from typing import Any, Callable, Dict, List, Optional, TypeVar
from dataclasses import dataclass, field
from collections import deque
from contextlib import contextmanager
import threading

logger = logging.getLogger(__name__)

# Type variable for generic function decorator
F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class OperationStats:
    """Statistics for a single operation type."""
    name: str
    call_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    slow_count: int = 0  # Count of operations exceeding threshold
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def avg_time_ms(self) -> float:
        """Average execution time in milliseconds."""
        if self.call_count == 0:
            return 0.0
        return self.total_time_ms / self.call_count

    @property
    def slow_percentage(self) -> float:
        """Percentage of calls that were slow."""
        if self.call_count == 0:
            return 0.0
        return (self.slow_count / self.call_count) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "name": self.name,
            "call_count": self.call_count,
            "total_time_ms": round(self.total_time_ms, 2),
            "avg_time_ms": round(self.avg_time_ms, 2),
            "min_time_ms": round(self.min_time_ms, 2) if self.min_time_ms != float('inf') else 0,
            "max_time_ms": round(self.max_time_ms, 2),
            "slow_count": self.slow_count,
            "slow_percentage": round(self.slow_percentage, 1),
        }


@dataclass
class CacheStats:
    """Statistics for cache performance."""
    name: str
    hits: int = 0
    misses: int = 0
    evictions: int = 0

    @property
    def total_requests(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            "name": self.name,
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "hit_rate_percent": round(self.hit_rate, 1),
            "evictions": self.evictions,
        }


class PerformanceMonitor:
    """
    Singleton performance monitor for tracking agent operations.

    Thread-safe implementation for use in multi-agent systems.
    """

    _instance: Optional['PerformanceMonitor'] = None
    _lock = threading.Lock()

    # Configuration
    SLOW_OPERATION_THRESHOLD_MS = 100  # Log operations > 100ms
    ENABLED = True  # Can be disabled in production for performance

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._operation_stats: Dict[str, OperationStats] = {}
        self._cache_stats: Dict[str, CacheStats] = {}
        self._stats_lock = threading.Lock()
        self._start_time = time.time()
        self._initialized = True

    def record_operation(
        self,
        name: str,
        duration_ms: float,
        slow_threshold_ms: Optional[float] = None
    ) -> None:
        """
        Record an operation execution.

        Args:
            name: Operation name
            duration_ms: Execution time in milliseconds
            slow_threshold_ms: Custom threshold for slow operation (uses default if None)
        """
        if not self.ENABLED:
            return

        threshold = slow_threshold_ms or self.SLOW_OPERATION_THRESHOLD_MS

        with self._stats_lock:
            if name not in self._operation_stats:
                self._operation_stats[name] = OperationStats(name=name)

            stats = self._operation_stats[name]
            stats.call_count += 1
            stats.total_time_ms += duration_ms
            stats.min_time_ms = min(stats.min_time_ms, duration_ms)
            stats.max_time_ms = max(stats.max_time_ms, duration_ms)
            stats.recent_times.append(duration_ms)

            if duration_ms > threshold:
                stats.slow_count += 1
                logger.warning(
                    f"Slow operation detected: {name} took {duration_ms:.1f}ms "
                    f"(threshold: {threshold}ms)"
                )

    def record_cache_hit(self, cache_name: str) -> None:
        """Record a cache hit."""
        if not self.ENABLED:
            return

        with self._stats_lock:
            if cache_name not in self._cache_stats:
                self._cache_stats[cache_name] = CacheStats(name=cache_name)
            self._cache_stats[cache_name].hits += 1

    def record_cache_miss(self, cache_name: str) -> None:
        """Record a cache miss."""
        if not self.ENABLED:
            return

        with self._stats_lock:
            if cache_name not in self._cache_stats:
                self._cache_stats[cache_name] = CacheStats(name=cache_name)
            self._cache_stats[cache_name].misses += 1

    def record_cache_eviction(self, cache_name: str, count: int = 1) -> None:
        """Record cache eviction(s)."""
        if not self.ENABLED:
            return

        with self._stats_lock:
            if cache_name not in self._cache_stats:
                self._cache_stats[cache_name] = CacheStats(name=cache_name)
            self._cache_stats[cache_name].evictions += count

    @contextmanager
    def time_operation(self, name: str, slow_threshold_ms: Optional[float] = None):
        """
        Context manager for timing operations.

        Usage:
            with monitor.time_operation("my_operation"):
                do_something()
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self.record_operation(name, duration_ms, slow_threshold_ms)

    def get_operation_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific operation."""
        with self._stats_lock:
            if name in self._operation_stats:
                return self._operation_stats[name].to_dict()
        return None

    def get_cache_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific cache."""
        with self._stats_lock:
            if name in self._cache_stats:
                return self._cache_stats[name].to_dict()
        return None

    def get_all_statistics(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        with self._stats_lock:
            uptime_seconds = time.time() - self._start_time

            return {
                "uptime_seconds": round(uptime_seconds, 1),
                "uptime_formatted": self._format_duration(uptime_seconds),
                "operations": {
                    name: stats.to_dict()
                    for name, stats in self._operation_stats.items()
                },
                "caches": {
                    name: stats.to_dict()
                    for name, stats in self._cache_stats.items()
                },
                "summary": {
                    "total_operations": sum(
                        s.call_count for s in self._operation_stats.values()
                    ),
                    "total_slow_operations": sum(
                        s.slow_count for s in self._operation_stats.values()
                    ),
                    "total_cache_requests": sum(
                        s.total_requests for s in self._cache_stats.values()
                    ),
                    "overall_cache_hit_rate": self._calculate_overall_hit_rate(),
                },
            }

    def _calculate_overall_hit_rate(self) -> float:
        """Calculate overall cache hit rate across all caches."""
        total_hits = sum(s.hits for s in self._cache_stats.values())
        total_requests = sum(s.total_requests for s in self._cache_stats.values())
        if total_requests == 0:
            return 0.0
        return round((total_hits / total_requests) * 100, 1)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    def reset(self) -> None:
        """Reset all statistics."""
        with self._stats_lock:
            self._operation_stats.clear()
            self._cache_stats.clear()
            self._start_time = time.time()

    def log_summary(self) -> None:
        """Log a summary of performance statistics."""
        stats = self.get_all_statistics()
        summary = stats["summary"]

        logger.info(
            f"Performance Summary (uptime: {stats['uptime_formatted']}): "
            f"{summary['total_operations']} ops, "
            f"{summary['total_slow_operations']} slow, "
            f"cache hit rate: {summary['overall_cache_hit_rate']}%"
        )

        # Log slow operations
        for name, op_stats in stats["operations"].items():
            if op_stats["slow_count"] > 0:
                logger.warning(
                    f"  {name}: {op_stats['slow_count']}/{op_stats['call_count']} slow "
                    f"(avg: {op_stats['avg_time_ms']:.1f}ms, max: {op_stats['max_time_ms']:.1f}ms)"
                )


# Global monitor instance
_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


def timed_operation(
    name: Optional[str] = None,
    slow_threshold_ms: Optional[float] = None
) -> Callable[[F], F]:
    """
    Decorator for timing function execution.

    Args:
        name: Operation name (uses function name if not provided)
        slow_threshold_ms: Custom threshold for slow operation warning

    Usage:
        @timed_operation("calculate_route")
        def calculate_route(start, end):
            ...

        @timed_operation(slow_threshold_ms=500)
        def slow_operation():
            ...
    """
    def decorator(func: F) -> F:
        operation_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_monitor()
            with monitor.time_operation(operation_name, slow_threshold_ms):
                return func(*args, **kwargs)

        return wrapper  # type: ignore
    return decorator


# Convenience functions
def record_cache_hit(cache_name: str) -> None:
    """Record a cache hit (convenience function)."""
    get_monitor().record_cache_hit(cache_name)


def record_cache_miss(cache_name: str) -> None:
    """Record a cache miss (convenience function)."""
    get_monitor().record_cache_miss(cache_name)


def get_performance_stats() -> Dict[str, Any]:
    """Get all performance statistics (convenience function)."""
    return get_monitor().get_all_statistics()


def log_performance_summary() -> None:
    """Log performance summary (convenience function)."""
    get_monitor().log_summary()
