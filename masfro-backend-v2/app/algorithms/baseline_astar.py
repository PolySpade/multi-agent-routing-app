# filename: app/algorithms/baseline_astar.py

"""
Baseline A* Pathfinding Algorithm (No Risk Consideration)

This module implements a standard A* search algorithm that ONLY considers
distance, completely ignoring flood risk scores. This serves as a baseline
for comparison against the risk-aware A* algorithm.

The baseline algorithm finds the shortest path purely based on distance,
which is the traditional routing approach used by GPS navigation systems
in normal (non-emergency) conditions.

Author: MAS-FRO Development Team
Date: November 2025
"""

import networkx as nx
import logging
from typing import List, Optional, Any, Dict
from app.algorithms.risk_aware_astar import (
    create_heuristic,
    calculate_path_metrics,
    get_path_coordinates
)

logger = logging.getLogger(__name__)


def baseline_astar(
    graph: nx.MultiDiGraph,
    start: Any,
    end: Any
) -> Optional[List[Any]]:
    """
    Find the shortest path using baseline A* algorithm (no risk consideration).

    This is a standard A* implementation that finds the shortest path based
    purely on distance. It completely ignores flood risk scores and serves
    as a baseline for comparison with risk-aware routing.

    The cost of an edge is simply its length in meters. No risk penalty is applied.

    Args:
        graph: NetworkX MultiDiGraph with road network
            Required node attributes: 'x' (longitude), 'y' (latitude)
            Required edge attributes: 'length' (meters)
        start: Start node ID
        end: End node ID

    Returns:
        List of node IDs representing the shortest path, or None if no path exists

    Raises:
        nx.NetworkXNoPath: If no path exists between start and end
        ValueError: If start or end node not in graph

    Example:
        >>> path = baseline_astar(graph, start_node, end_node)
        >>> if path:
        ...     print(f"Found shortest path with {len(path)} nodes")
    """
    logger.info(
        f"Computing baseline A* path from {start} to {end} "
        f"(distance-only, no risk consideration)"
    )

    # Validate inputs
    if start not in graph:
        raise ValueError(f"Start node {start} not in graph")
    if end not in graph:
        raise ValueError(f"End node {end} not in graph")

    # Create heuristic function (same as risk-aware)
    heuristic = create_heuristic(graph, end)

    # Define weight function that ONLY uses distance
    def weight_function(u, v, edge_data):
        """
        Calculate edge weight based ONLY on distance (ignore risk).

        For MultiDiGraph, we select the shortest edge among parallel edges.

        Args:
            u: Source node
            v: Target node
            edge_data: Dict of edge attributes

        Returns:
            Edge length in meters
        """
        # For MultiDiGraph, find the shortest edge among parallel edges
        best_length = float('inf')

        if v in graph[u]:
            # Get all parallel edges between u and v
            for key, data in graph[u][v].items():
                edge_length = data.get('length', 1.0)
                # Select shortest edge
                if edge_length < best_length:
                    best_length = edge_length

        # Return only distance (no risk component)
        return best_length

    try:
        # Run A* with distance-only weight and heuristic
        path = nx.astar_path(
            graph,
            start,
            end,
            heuristic=heuristic,
            weight=weight_function
        )

        logger.info(f"Baseline path found with {len(path)} nodes")
        return path

    except nx.NetworkXNoPath:
        logger.warning(f"No path exists from {start} to {end} in baseline routing")
        return None
    except Exception as e:
        logger.error(f"Error in baseline A* pathfinding: {e}")
        raise


def calculate_baseline_path_risk(
    graph: nx.MultiDiGraph,
    path: List[Any]
) -> Dict[str, float]:
    """
    Calculate risk metrics for a baseline path.

    Since baseline routing ignores risk during pathfinding, this function
    calculates what the actual risk exposure is on the chosen path. This
    allows comparison with risk-aware routing.

    Args:
        graph: NetworkX graph containing the path
        path: List of node IDs representing the path

    Returns:
        Dict containing risk metrics:
            {
                "average_risk": float,  # Distance-weighted average (0-1)
                "max_risk": float,  # Maximum risk on any segment (0-1)
                "total_distance": float,  # Total path length (meters)
                "num_segments": int,  # Number of road segments
                "high_risk_segments": int,  # Count of segments with risk >= 0.6
                "critical_risk_segments": int  # Count of segments with risk >= 0.9
            }

    Example:
        >>> risk_metrics = calculate_baseline_path_risk(graph, baseline_path)
        >>> print(f"Baseline path average risk: {risk_metrics['average_risk']:.3f}")
    """
    if not path or len(path) < 2:
        return {
            "average_risk": 0.0,
            "max_risk": 0.0,
            "total_distance": 0.0,
            "num_segments": 0,
            "high_risk_segments": 0,
            "critical_risk_segments": 0
        }

    total_distance = 0.0
    total_weighted_risk = 0.0  # Weighted by distance
    max_risk = 0.0
    num_segments = 0
    high_risk_count = 0  # risk >= 0.6
    critical_risk_count = 0  # risk >= 0.9

    # Iterate through path edges
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]

        # Get edge data (handle MultiDiGraph with multiple edges)
        if graph.has_edge(u, v):
            # Get first edge if multiple exist
            edge_data = graph[u][v][0]

            length = edge_data.get('length', 0.0)
            risk = edge_data.get('risk_score', 0.0)

            total_distance += length
            total_weighted_risk += risk * length  # Weight by segment length
            max_risk = max(max_risk, risk)
            num_segments += 1

            # Count high-risk segments
            if risk >= 0.6:
                high_risk_count += 1
            if risk >= 0.9:
                critical_risk_count += 1

    # Calculate distance-weighted average risk
    average_risk = total_weighted_risk / total_distance if total_distance > 0 else 0.0

    return {
        "average_risk": average_risk,
        "max_risk": max_risk,
        "total_distance": total_distance,
        "num_segments": num_segments,
        "high_risk_segments": high_risk_count,
        "critical_risk_segments": critical_risk_count
    }
