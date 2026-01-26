# filename: validation/route_pair_generator.py

"""
Route Pair Generator for Algorithm Validation

Generates random source-target node pairs with distance constraints for
testing routing algorithms. Ensures evacuation centers are targets and
validates 1km distance requirement.

Author: MAS-FRO Development Team
Date: November 2025
"""

import networkx as nx
import pandas as pd
import random
import logging
from typing import List, Tuple, Optional, Any
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.algorithms.risk_aware_astar import haversine_distance

logger = logging.getLogger(__name__)


class RoutePairGenerator:
    """
    Generates random source-target pairs for routing algorithm validation.

    Creates pairs where:
    - Targets are evacuation center nodes
    - Sources are random nodes in the graph
    - Distance between source and target is approximately 1km (±200m)

    Attributes:
        graph: NetworkX graph of road network
        evacuation_centers: DataFrame of evacuation centers
        target_nodes: List of node IDs for evacuation centers
        distance_target: Target distance in meters (default: 1000m)
        distance_tolerance: Tolerance in meters (default: ±200m)
    """

    def __init__(
        self,
        graph: nx.MultiDiGraph,
        evacuation_centers_csv: Path,
        distance_target: float = 1000.0,
        distance_tolerance: float = 200.0
    ):
        """
        Initialize the route pair generator.

        Args:
            graph: NetworkX MultiDiGraph of road network
            evacuation_centers_csv: Path to evacuation centers CSV
            distance_target: Target distance in meters (default: 1000m)
            distance_tolerance: Distance tolerance in meters (default: ±200m)
        """
        self.graph = graph
        self.distance_target = distance_target
        self.distance_tolerance = distance_tolerance

        # Load evacuation centers
        logger.info(f"Loading evacuation centers from {evacuation_centers_csv}")
        self.evacuation_centers = pd.read_csv(evacuation_centers_csv)
        logger.info(f"Loaded {len(self.evacuation_centers)} evacuation centers")

        # Find nearest graph nodes for each evacuation center
        self.target_nodes = self._map_centers_to_nodes()
        logger.info(f"Mapped to {len(self.target_nodes)} target nodes")

        # Cache all graph nodes for source selection
        self.all_nodes = list(self.graph.nodes())
        logger.info(f"Graph contains {len(self.all_nodes)} total nodes")

        # Statistics
        self.generation_attempts = 0
        self.successful_generations = 0

    def _map_centers_to_nodes(self) -> List[Any]:
        """
        Map evacuation centers to nearest graph nodes.

        Returns:
            List of node IDs corresponding to evacuation centers
        """
        target_nodes = []

        for _, center in self.evacuation_centers.iterrows():
            center_lat = center['latitude']
            center_lon = center['longitude']

            # Find nearest node in graph
            nearest_node = None
            min_distance = float('inf')

            for node in self.graph.nodes():
                node_lat = self.graph.nodes[node]['y']
                node_lon = self.graph.nodes[node]['x']

                distance = haversine_distance(
                    (center_lat, center_lon),
                    (node_lat, node_lon)
                )

                if distance < min_distance:
                    min_distance = distance
                    nearest_node = node

            if nearest_node and min_distance < 500:  # Within 500m
                target_nodes.append(nearest_node)
                logger.debug(
                    f"Mapped '{center['name']}' to node {nearest_node} "
                    f"(distance: {min_distance:.1f}m)"
                )
            else:
                logger.warning(
                    f"Could not map '{center['name']}' to graph "
                    f"(nearest: {min_distance:.1f}m)"
                )

        return target_nodes

    def generate_pair(
        self,
        max_attempts: int = 100
    ) -> Optional[Tuple[Any, Any, float]]:
        """
        Generate a single source-target pair with ~1km distance.

        Randomly selects a target (evacuation center) and finds a source node
        approximately 1km away (±200m tolerance).

        Args:
            max_attempts: Maximum attempts to find valid pair (default: 100)

        Returns:
            Tuple of (source_node, target_node, actual_distance) or None if failed
        """
        if not self.target_nodes:
            logger.error("No target nodes available")
            return None

        # Randomly select target (evacuation center)
        target = random.choice(self.target_nodes)
        target_lat = self.graph.nodes[target]['y']
        target_lon = self.graph.nodes[target]['x']

        # Try to find source node with correct distance
        for attempt in range(max_attempts):
            self.generation_attempts += 1

            # Randomly select potential source
            source = random.choice(self.all_nodes)

            # Skip if source == target
            if source == target:
                continue

            # Calculate distance
            source_lat = self.graph.nodes[source]['y']
            source_lon = self.graph.nodes[source]['x']

            distance = haversine_distance(
                (source_lat, source_lon),
                (target_lat, target_lon)
            )

            # Check if distance is within tolerance
            min_dist = self.distance_target - self.distance_tolerance
            max_dist = self.distance_target + self.distance_tolerance

            if min_dist <= distance <= max_dist:
                # Verify path exists (quick check using NetworkX)
                try:
                    if nx.has_path(self.graph, source, target):
                        self.successful_generations += 1
                        logger.debug(
                            f"Generated pair: {source} -> {target} "
                            f"(distance: {distance:.1f}m)"
                        )
                        return (source, target, distance)
                except Exception as e:
                    logger.debug(f"Path check failed: {e}")
                    continue

        logger.warning(
            f"Failed to generate valid pair after {max_attempts} attempts"
        )
        return None

    def generate_pairs(
        self,
        count: int,
        max_attempts_per_pair: int = 100,
        show_progress: bool = True
    ) -> List[Tuple[Any, Any, float]]:
        """
        Generate multiple source-target pairs.

        Args:
            count: Number of pairs to generate
            max_attempts_per_pair: Max attempts per pair (default: 100)
            show_progress: Show progress during generation (default: True)

        Returns:
            List of tuples (source_node, target_node, distance)
        """
        pairs = []
        failed_count = 0

        logger.info(f"Generating {count} route pairs...")

        for i in range(count):
            pair = self.generate_pair(max_attempts=max_attempts_per_pair)

            if pair:
                pairs.append(pair)

                if show_progress and (i + 1) % 100 == 0:
                    success_rate = (len(pairs) / (i + 1)) * 100
                    print(
                        f"  Progress: {i + 1}/{count} pairs generated "
                        f"({success_rate:.1f}% success rate)"
                    )
            else:
                failed_count += 1

        logger.info(
            f"Generation complete: {len(pairs)} successful, "
            f"{failed_count} failed"
        )

        return pairs

    def get_statistics(self) -> dict:
        """
        Get generation statistics.

        Returns:
            Dictionary containing generation statistics
        """
        success_rate = (
            (self.successful_generations / self.generation_attempts * 100)
            if self.generation_attempts > 0
            else 0.0
        )

        return {
            "total_attempts": self.generation_attempts,
            "successful_generations": self.successful_generations,
            "success_rate": success_rate,
            "target_nodes_count": len(self.target_nodes),
            "graph_nodes_count": len(self.all_nodes),
            "distance_target": self.distance_target,
            "distance_tolerance": self.distance_tolerance
        }


def test_generator():
    """Test the route pair generator."""
    from app.environment.graph_manager import DynamicGraphEnvironment

    print("Testing Route Pair Generator...")

    # Load graph
    env = DynamicGraphEnvironment()
    graph = env.get_graph()

    if graph is None:
        print("❌ Failed to load graph")
        return

    print(f"[OK] Loaded graph with {len(graph.nodes())} nodes")

    # Initialize generator
    evac_csv = Path(__file__).parent.parent / "app" / "data" / "evacuation_centers.csv"
    generator = RoutePairGenerator(graph, evac_csv)

    print(f"[OK] Initialized generator")
    print(f"  Target nodes: {len(generator.target_nodes)}")

    # Generate test pairs
    print("\nGenerating 10 test pairs...")
    pairs = generator.generate_pairs(10, show_progress=False)

    print(f"\n[OK] Generated {len(pairs)} pairs:")
    for i, (source, target, dist) in enumerate(pairs[:5], 1):
        print(f"  {i}. {source} -> {target} ({dist:.1f}m)")

    # Show statistics
    stats = generator.get_statistics()
    print(f"\nStatistics:")
    print(f"  Success rate: {stats['success_rate']:.1f}%")
    print(f"  Total attempts: {stats['total_attempts']}")


if __name__ == "__main__":
    test_generator()
