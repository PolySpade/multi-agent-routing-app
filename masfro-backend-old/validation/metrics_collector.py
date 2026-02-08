# filename: validation/metrics_collector.py

"""
Metrics Collector for Routing Algorithm Validation

Collects and aggregates performance metrics for baseline and risk-aware
routing algorithms, including computation time, risk scores, and path metrics.

Author: MAS-FRO Development Team
Date: November 2025
"""

import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class RouteMetrics:
    """
    Metrics for a single routing computation.

    Attributes:
        source_node: Starting node ID
        target_node: Destination node ID
        algorithm: Algorithm name ('baseline' or 'risk_aware')
        success: Whether path was found
        computation_time: Time taken in seconds
        path_length_nodes: Number of nodes in path
        total_distance: Total path distance in meters
        average_risk: Distance-weighted average risk (0-1)
        max_risk: Maximum risk on any segment (0-1)
        high_risk_segments: Number of segments with risk >= 0.6
        critical_risk_segments: Number of segments with risk >= 0.9
        num_segments: Total number of road segments
        error_message: Error message if failed
        timestamp: When metric was collected
    """
    source_node: Any
    target_node: Any
    algorithm: str
    success: bool
    computation_time: float
    path_length_nodes: int = 0
    total_distance: float = 0.0
    average_risk: float = 0.0
    max_risk: float = 0.0
    high_risk_segments: int = 0
    critical_risk_segments: int = 0
    num_segments: int = 0
    error_message: str = ""
    timestamp: str = ""

    def __post_init__(self):
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MetricsCollector:
    """
    Collects and manages routing algorithm performance metrics.

    Provides methods for collecting individual route metrics and computing
    aggregate statistics across multiple routes.

    Attributes:
        metrics: List of all collected RouteMetrics
        baseline_metrics: Filtered list of baseline algorithm metrics
        risk_aware_metrics: Filtered list of risk-aware algorithm metrics
    """

    def __init__(self):
        """Initialize the metrics collector."""
        self.metrics: List[RouteMetrics] = []
        self.baseline_metrics: List[RouteMetrics] = []
        self.risk_aware_metrics: List[RouteMetrics] = []

        logger.info("MetricsCollector initialized")

    def add_metric(self, metric: RouteMetrics) -> None:
        """
        Add a metric to the collection.

        Args:
            metric: RouteMetrics instance to add
        """
        self.metrics.append(metric)

        # Add to algorithm-specific lists
        if metric.algorithm == 'baseline':
            self.baseline_metrics.append(metric)
        elif metric.algorithm == 'risk_aware':
            self.risk_aware_metrics.append(metric)

    def collect_from_path(
        self,
        source: Any,
        target: Any,
        algorithm: str,
        path: Optional[List[Any]],
        computation_time: float,
        risk_metrics: Optional[Dict[str, float]] = None,
        error_message: str = ""
    ) -> RouteMetrics:
        """
        Create metrics from routing result and add to collection.

        Args:
            source: Source node ID
            target: Target node ID
            algorithm: Algorithm name ('baseline' or 'risk_aware')
            path: Computed path (None if failed)
            computation_time: Computation time in seconds
            risk_metrics: Risk metrics dict (from calculate_path_metrics)
            error_message: Error message if failed

        Returns:
            RouteMetrics instance
        """
        if path and risk_metrics:
            metric = RouteMetrics(
                source_node=source,
                target_node=target,
                algorithm=algorithm,
                success=True,
                computation_time=computation_time,
                path_length_nodes=len(path),
                total_distance=risk_metrics.get('total_distance', 0.0),
                average_risk=risk_metrics.get('average_risk', 0.0),
                max_risk=risk_metrics.get('max_risk', 0.0),
                high_risk_segments=risk_metrics.get('high_risk_segments', 0),
                critical_risk_segments=risk_metrics.get(
                    'critical_risk_segments', 0
                ),
                num_segments=risk_metrics.get('num_segments', 0)
            )
        else:
            metric = RouteMetrics(
                source_node=source,
                target_node=target,
                algorithm=algorithm,
                success=False,
                computation_time=computation_time,
                error_message=error_message
            )

        self.add_metric(metric)
        return metric

    def get_aggregate_statistics(
        self,
        algorithm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compute aggregate statistics for collected metrics.

        Args:
            algorithm: Filter by algorithm ('baseline', 'risk_aware', or None for all)

        Returns:
            Dictionary containing aggregate statistics
        """
        # Filter metrics
        if algorithm == 'baseline':
            metrics_list = self.baseline_metrics
        elif algorithm == 'risk_aware':
            metrics_list = self.risk_aware_metrics
        else:
            metrics_list = self.metrics

        if not metrics_list:
            return {}

        # Filter successful routes only
        successful = [m for m in metrics_list if m.success]
        failed = [m for m in metrics_list if not m.success]

        if not successful:
            return {
                "total_routes": len(metrics_list),
                "successful_routes": 0,
                "failed_routes": len(failed),
                "success_rate": 0.0
            }

        # Compute statistics
        stats = {
            # Route counts
            "total_routes": len(metrics_list),
            "successful_routes": len(successful),
            "failed_routes": len(failed),
            "success_rate": len(successful) / len(metrics_list) * 100,

            # Computation time (seconds)
            "avg_computation_time": sum(m.computation_time for m in successful) / len(successful),
            "min_computation_time": min(m.computation_time for m in successful),
            "max_computation_time": max(m.computation_time for m in successful),
            "total_computation_time": sum(m.computation_time for m in metrics_list),

            # Distance (meters)
            "avg_distance": sum(m.total_distance for m in successful) / len(successful),
            "min_distance": min(m.total_distance for m in successful),
            "max_distance": max(m.total_distance for m in successful),

            # Risk scores (0-1)
            "avg_risk": sum(m.average_risk for m in successful) / len(successful),
            "min_risk": min(m.average_risk for m in successful),
            "max_risk_avg": max(m.average_risk for m in successful),
            "avg_max_risk": sum(m.max_risk for m in successful) / len(successful),

            # High-risk segments
            "avg_high_risk_segments": sum(m.high_risk_segments for m in successful) / len(successful),
            "avg_critical_risk_segments": sum(m.critical_risk_segments for m in successful) / len(successful),

            # Path characteristics
            "avg_path_length": sum(m.path_length_nodes for m in successful) / len(successful),
            "avg_num_segments": sum(m.num_segments for m in successful) / len(successful)
        }

        return stats

    def compare_algorithms(self) -> Dict[str, Any]:
        """
        Compare baseline vs risk-aware algorithm performance.

        Returns:
            Dictionary containing comparison metrics
        """
        baseline_stats = self.get_aggregate_statistics('baseline')
        risk_aware_stats = self.get_aggregate_statistics('risk_aware')

        if not baseline_stats or not risk_aware_stats:
            return {}

        # Calculate differences and improvements
        comparison = {
            "baseline": baseline_stats,
            "risk_aware": risk_aware_stats,
            "comparison": {
                # Risk improvement (negative = safer)
                "risk_reduction": (
                    (baseline_stats['avg_risk'] - risk_aware_stats['avg_risk']) /
                    baseline_stats['avg_risk'] * 100
                    if baseline_stats['avg_risk'] > 0 else 0
                ),
                "max_risk_reduction": (
                    (baseline_stats['avg_max_risk'] - risk_aware_stats['avg_max_risk']) /
                    baseline_stats['avg_max_risk'] * 100
                    if baseline_stats['avg_max_risk'] > 0 else 0
                ),
                "high_risk_segments_reduction": (
                    baseline_stats['avg_high_risk_segments'] -
                    risk_aware_stats['avg_high_risk_segments']
                ),
                "critical_risk_segments_reduction": (
                    baseline_stats['avg_critical_risk_segments'] -
                    risk_aware_stats['avg_critical_risk_segments']
                ),

                # Distance overhead (positive = longer routes)
                "distance_overhead": (
                    (risk_aware_stats['avg_distance'] - baseline_stats['avg_distance']) /
                    baseline_stats['avg_distance'] * 100
                    if baseline_stats['avg_distance'] > 0 else 0
                ),

                # Computation time overhead
                "time_overhead": (
                    (risk_aware_stats['avg_computation_time'] -
                     baseline_stats['avg_computation_time']) /
                    baseline_stats['avg_computation_time'] * 100
                    if baseline_stats['avg_computation_time'] > 0 else 0
                ),

                # Success rates
                "baseline_success_rate": baseline_stats['success_rate'],
                "risk_aware_success_rate": risk_aware_stats['success_rate']
            }
        }

        return comparison

    def save_to_json(self, filepath: str) -> None:
        """
        Save all metrics to JSON file.

        Args:
            filepath: Path to output JSON file
        """
        data = {
            "metadata": {
                "total_metrics": len(self.metrics),
                "baseline_count": len(self.baseline_metrics),
                "risk_aware_count": len(self.risk_aware_metrics),
                "timestamp": datetime.now().isoformat()
            },
            "metrics": [asdict(m) for m in self.metrics],
            "statistics": {
                "baseline": self.get_aggregate_statistics('baseline'),
                "risk_aware": self.get_aggregate_statistics('risk_aware'),
                "comparison": self.compare_algorithms().get('comparison', {})
            }
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Metrics saved to {filepath}")

    def get_metrics_count(self) -> Dict[str, int]:
        """
        Get count of metrics by algorithm.

        Returns:
            Dictionary with metric counts
        """
        return {
            "total": len(self.metrics),
            "baseline": len(self.baseline_metrics),
            "risk_aware": len(self.risk_aware_metrics)
        }


if __name__ == "__main__":
    # Test the metrics collector
    print("Testing MetricsCollector...")

    collector = MetricsCollector()

    # Add sample metrics
    metric1 = RouteMetrics(
        source_node=123,
        target_node=456,
        algorithm='baseline',
        success=True,
        computation_time=0.025,
        total_distance=1000.0,
        average_risk=0.45
    )

    metric2 = RouteMetrics(
        source_node=123,
        target_node=456,
        algorithm='risk_aware',
        success=True,
        computation_time=0.032,
        total_distance=1100.0,
        average_risk=0.28
    )

    collector.add_metric(metric1)
    collector.add_metric(metric2)

    print(f"[OK] Added {collector.get_metrics_count()['total']} metrics")

    # Get statistics
    comparison = collector.compare_algorithms()
    if comparison:
        print(f"[OK] Risk reduction: {comparison['comparison']['risk_reduction']:.1f}%")
        print(f"[OK] Distance overhead: {comparison['comparison']['distance_overhead']:.1f}%")
