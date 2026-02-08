# filename: validation/algorithm_comparison.py

"""
Algorithm Comparison Script for MAS-FRO Routing Validation

Compares baseline A* (distance-only) vs risk-aware A* routing algorithms
across 20,000 source-target pairs. Measures average risk and computation time
to validate that risk-aware routing produces safer paths.

Usage:
    python validation/algorithm_comparison.py --pairs 20000 --output results/

Author: MAS-FRO Development Team
Date: November 2025
"""

import sys
import time
import logging
import argparse
from pathlib import Path
from typing import List, Tuple, Any
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import project modules
from app.environment.graph_manager import DynamicGraphEnvironment
from app.algorithms.baseline_astar import baseline_astar, calculate_baseline_path_risk
from app.algorithms.risk_aware_astar import risk_aware_astar, calculate_path_metrics
from validation.route_pair_generator import RoutePairGenerator
from validation.metrics_collector import MetricsCollector, RouteMetrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlgorithmComparison:
    """
    Manages comparison between baseline and risk-aware routing algorithms.

    Generates source-target pairs, computes routes using both algorithms,
    collects metrics, and produces comparison statistics.

    Attributes:
        graph: NetworkX road network graph
        generator: RoutePairGenerator instance
        collector: MetricsCollector instance
        risk_weight: Weight for risk component (default: 0.6)
        distance_weight: Weight for distance component (default: 0.4)
    """

    def __init__(
        self,
        graph_env: DynamicGraphEnvironment,
        evacuation_csv: Path,
        risk_weight: float = 0.6,
        distance_weight: float = 0.4
    ):
        """
        Initialize the algorithm comparison.

        Args:
            graph_env: DynamicGraphEnvironment instance
            evacuation_csv: Path to evacuation centers CSV
            risk_weight: Risk weight for risk-aware A* (default: 0.6)
            distance_weight: Distance weight for risk-aware A* (default: 0.4)
        """
        self.graph = graph_env.get_graph()
        self.risk_weight = risk_weight
        self.distance_weight = distance_weight

        logger.info("Initializing algorithm comparison...")
        logger.info(f"  Graph nodes: {len(self.graph.nodes())}")
        logger.info(f"  Graph edges: {len(self.graph.edges())}")
        logger.info(f"  Risk weight: {risk_weight}")
        logger.info(f"  Distance weight: {distance_weight}")

        # Initialize components
        self.generator = RoutePairGenerator(
            self.graph,
            evacuation_csv,
            distance_target=1000.0,  # 1km target
            distance_tolerance=200.0  # ±200m tolerance
        )

        self.collector = MetricsCollector()

        logger.info("✓ Initialization complete")

    def compute_route_with_timing(
        self,
        source: Any,
        target: Any,
        algorithm: str
    ) -> Tuple[List[Any], float, dict]:
        """
        Compute route and measure computation time.

        Args:
            source: Source node ID
            target: Target node ID
            algorithm: 'baseline' or 'risk_aware'

        Returns:
            Tuple of (path, computation_time, risk_metrics)
        """
        start_time = time.time()

        try:
            if algorithm == 'baseline':
                path = baseline_astar(self.graph, source, target)
                computation_time = time.time() - start_time

                if path:
                    risk_metrics = calculate_baseline_path_risk(self.graph, path)
                else:
                    risk_metrics = {}

            elif algorithm == 'risk_aware':
                path = risk_aware_astar(
                    self.graph,
                    source,
                    target,
                    risk_weight=self.risk_weight,
                    distance_weight=self.distance_weight
                )
                computation_time = time.time() - start_time

                if path:
                    risk_metrics = calculate_path_metrics(self.graph, path)
                else:
                    risk_metrics = {}

            else:
                raise ValueError(f"Unknown algorithm: {algorithm}")

            return path, computation_time, risk_metrics

        except Exception as e:
            computation_time = time.time() - start_time
            logger.error(f"{algorithm} failed for {source}->{target}: {e}")
            return None, computation_time, {}

    def run_single_comparison(
        self,
        source: Any,
        target: Any,
        pair_index: int,
        total_pairs: int
    ) -> Tuple[RouteMetrics, RouteMetrics]:
        """
        Run both algorithms on a single source-target pair.

        Args:
            source: Source node ID
            target: Target node ID
            pair_index: Current pair index (for logging)
            total_pairs: Total number of pairs

        Returns:
            Tuple of (baseline_metric, risk_aware_metric)
        """
        # Compute baseline route
        baseline_path, baseline_time, baseline_risk = self.compute_route_with_timing(
            source, target, 'baseline'
        )

        baseline_metric = self.collector.collect_from_path(
            source=source,
            target=target,
            algorithm='baseline',
            path=baseline_path,
            computation_time=baseline_time,
            risk_metrics=baseline_risk,
            error_message="" if baseline_path else "No path found"
        )

        # Compute risk-aware route
        risk_path, risk_time, risk_metrics = self.compute_route_with_timing(
            source, target, 'risk_aware'
        )

        risk_aware_metric = self.collector.collect_from_path(
            source=source,
            target=target,
            algorithm='risk_aware',
            path=risk_path,
            computation_time=risk_time,
            risk_metrics=risk_metrics,
            error_message="" if risk_path else "No path found"
        )

        # Log progress
        if (pair_index + 1) % 100 == 0:
            logger.info(
                f"Progress: {pair_index + 1}/{total_pairs} pairs "
                f"({(pair_index + 1) / total_pairs * 100:.1f}%)"
            )

        return baseline_metric, risk_aware_metric

    def run_comparison(
        self,
        num_pairs: int = 20000,
        batch_size: int = 100
    ) -> MetricsCollector:
        """
        Run full comparison across multiple route pairs.

        Args:
            num_pairs: Number of source-target pairs to test (default: 20000)
            batch_size: Batch size for progress reporting (default: 100)

        Returns:
            MetricsCollector with all results
        """
        logger.info(f"\n{'=' * 60}")
        logger.info(f"STARTING ALGORITHM COMPARISON")
        logger.info(f"  Target pairs: {num_pairs}")
        logger.info(f"  Algorithms: Baseline A* vs Risk-Aware A*")
        logger.info(f"{'=' * 60}\n")

        # Generate all route pairs
        logger.info("Step 1: Generating route pairs...")
        start_time = time.time()

        pairs = self.generator.generate_pairs(
            count=num_pairs,
            max_attempts_per_pair=100,
            show_progress=True
        )

        generation_time = time.time() - start_time

        logger.info(f"✓ Generated {len(pairs)} valid pairs in {generation_time:.1f}s")

        if len(pairs) < num_pairs:
            logger.warning(
                f"⚠ Only generated {len(pairs)}/{num_pairs} pairs "
                f"({len(pairs)/num_pairs*100:.1f}%)"
            )

        # Run comparison on each pair
        logger.info("\nStep 2: Computing routes for all pairs...")
        computation_start = time.time()

        for i, (source, target, distance) in enumerate(pairs):
            self.run_single_comparison(source, target, i, len(pairs))

        total_computation_time = time.time() - computation_start

        logger.info(
            f"\n✓ Completed all route computations in {total_computation_time:.1f}s"
        )

        # Summary
        counts = self.collector.get_metrics_count()
        logger.info(f"\nMetrics collected:")
        logger.info(f"  Baseline: {counts['baseline']}")
        logger.info(f"  Risk-aware: {counts['risk_aware']}")
        logger.info(f"  Total: {counts['total']}")

        return self.collector

    def print_summary(self):
        """Print comparison summary to console."""
        comparison = self.collector.compare_algorithms()

        if not comparison:
            print("\n❌ No comparison data available")
            return

        print(f"\n{'=' * 80}")
        print("ALGORITHM COMPARISON SUMMARY")
        print(f"{'=' * 80}")

        baseline = comparison['baseline']
        risk_aware = comparison['risk_aware']
        comp = comparison['comparison']

        # Success rates
        print(f"\n[SUCCESS RATES]")
        print(f"  Baseline A*:    {baseline['successful_routes']}/{baseline['total_routes']} ({baseline['success_rate']:.1f}%)")
        print(f"  Risk-Aware A*:  {risk_aware['successful_routes']}/{risk_aware['total_routes']} ({risk_aware['success_rate']:.1f}%)")

        # Risk comparison
        print(f"\n[RISK SCORES] (0-1 scale, lower = safer)")
        print(f"  Baseline A* average risk:    {baseline['avg_risk']:.4f}")
        print(f"  Risk-Aware A* average risk:  {risk_aware['avg_risk']:.4f}")
        print(f"  -> Risk reduction:           {comp['risk_reduction']:.2f}%")

        print(f"\n  Baseline A* max risk:        {baseline['avg_max_risk']:.4f}")
        print(f"  Risk-Aware A* max risk:      {risk_aware['avg_max_risk']:.4f}")
        print(f"  -> Max risk reduction:       {comp['max_risk_reduction']:.2f}%")

        # High-risk segments
        print(f"\n[HIGH-RISK SEGMENTS] (risk >= 0.6)")
        print(f"  Baseline A*:    {baseline['avg_high_risk_segments']:.2f} segments/route")
        print(f"  Risk-Aware A*:  {risk_aware['avg_high_risk_segments']:.2f} segments/route")
        print(f"  -> Reduction:   {comp['high_risk_segments_reduction']:.2f} segments/route")

        print(f"\n[CRITICAL-RISK SEGMENTS] (risk >= 0.9)")
        print(f"  Baseline A*:    {baseline['avg_critical_risk_segments']:.2f} segments/route")
        print(f"  Risk-Aware A*:  {risk_aware['avg_critical_risk_segments']:.2f} segments/route")
        print(f"  -> Reduction:   {comp['critical_risk_segments_reduction']:.2f} segments/route")

        # Distance overhead
        print(f"\n[ROUTE DISTANCE]")
        print(f"  Baseline A*:    {baseline['avg_distance']:.1f}m average")
        print(f"  Risk-Aware A*:  {risk_aware['avg_distance']:.1f}m average")
        print(f"  -> Overhead:    {comp['distance_overhead']:.2f}%")

        # Computation time
        print(f"\n[COMPUTATION TIME]")
        print(f"  Baseline A*:    {baseline['avg_computation_time']*1000:.2f}ms average")
        print(f"  Risk-Aware A*:  {risk_aware['avg_computation_time']*1000:.2f}ms average")
        print(f"  -> Overhead:    {comp['time_overhead']:.2f}%")

        print(f"\n  Total computation time:")
        print(f"    Baseline:     {baseline['total_computation_time']:.2f}s")
        print(f"    Risk-Aware:   {risk_aware['total_computation_time']:.2f}s")

        print(f"\n{'=' * 80}")

        # Validation result
        print(f"\n[VALIDATION RESULT]")
        if comp['risk_reduction'] > 0:
            print(f"  [OK] Risk-Aware A* successfully reduces average risk by {comp['risk_reduction']:.2f}%")
            print(f"  while adding only {comp['distance_overhead']:.2f}% distance overhead.")
        else:
            print(f"  [WARNING] Risk-Aware A* did not reduce average risk")

        print()


def main():
    """Main entry point for algorithm comparison."""
    parser = argparse.ArgumentParser(
        description='Compare baseline vs risk-aware routing algorithms'
    )
    parser.add_argument(
        '--pairs',
        type=int,
        default=20000,
        help='Number of route pairs to test (default: 20000)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='validation/results',
        help='Output directory for results (default: validation/results)'
    )
    parser.add_argument(
        '--risk-weight',
        type=float,
        default=0.6,
        help='Risk weight for risk-aware A* (default: 0.6)'
    )
    parser.add_argument(
        '--distance-weight',
        type=float,
        default=0.4,
        help='Distance weight for risk-aware A* (default: 0.4)'
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load graph environment
    logger.info("Loading graph environment...")
    graph_env = DynamicGraphEnvironment()

    if graph_env.get_graph() is None:
        logger.error("❌ Failed to load graph. Ensure marikina_graph.graphml exists.")
        return 1

    # Load risk scores from GeoTIFF
    logger.info("Loading risk scores from GeoTIFF...")
    try:
        from app.agents.hazard_agent import HazardAgent

        hazard_agent = HazardAgent(
            agent_id="validation_hazard",
            environment=graph_env,
            enable_geotiff=True
        )

        # Set flood scenario (default: rr01, time_step 6)
        hazard_agent.set_flood_scenario(return_period="rr01", time_step=6)

        # Update graph with risk scores
        result = hazard_agent.update_risk(
            flood_data={},
            scout_data=[],
            time_step=6
        )

        logger.info(f"✓ Risk scores loaded: {result['edges_updated']} edges updated")
        logger.info(f"  Average risk: {result.get('average_risk', 0):.4f}")
    except Exception as e:
        logger.warning(f"⚠ Could not load risk scores: {e}")
        logger.warning("  Validation will proceed with risk_score=0.0 on all edges")

    # Evacuation centers path
    evac_csv = Path(__file__).parent.parent / "app" / "data" / "evacuation_centers.csv"

    if not evac_csv.exists():
        logger.error(f"❌ Evacuation centers CSV not found: {evac_csv}")
        return 1

    # Initialize comparison
    comparison = AlgorithmComparison(
        graph_env=graph_env,
        evacuation_csv=evac_csv,
        risk_weight=args.risk_weight,
        distance_weight=args.distance_weight
    )

    # Run comparison
    start_time = time.time()
    collector = comparison.run_comparison(num_pairs=args.pairs)
    total_time = time.time() - start_time

    # Print summary
    comparison.print_summary()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = output_dir / f"comparison_results_{timestamp}.json"

    collector.save_to_json(str(results_file))

    logger.info(f"\n✓ Results saved to: {results_file}")
    logger.info(f"✓ Total execution time: {total_time:.1f}s ({total_time/60:.1f} minutes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
