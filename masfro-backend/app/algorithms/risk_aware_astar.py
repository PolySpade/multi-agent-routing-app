# filename: app/algorithms/risk_aware_astar.py

"""
Risk-Aware A* Pathfinding Algorithm for MAS-FRO

This module implements a modified A* search algorithm that incorporates
flood risk scores into path cost calculations. Unlike traditional A* that
optimizes purely for distance, this algorithm balances distance with safety
by treating high-risk road segments as more costly to traverse.

The algorithm is based on NetworkX's A* implementation with custom weight
and heuristic functions that account for:
- Base distance (road segment length)
- Flood risk scores (0-1 scale, from HazardAgent)
- Road passability (impassable roads have infinite cost)

Research Foundation:
- Traditional A*: Hart, Nilsson & Raphael (1968)
- Risk-aware routing: Adapted for flood evacuation scenarios
- Heuristic: Haversine distance for geographic coordinates

Author: MAS-FRO Development Team
Date: November 2025
"""

import networkx as nx
import math
from typing import Tuple, List, Optional, Callable, Any, Dict
import logging

logger = logging.getLogger(__name__)


def haversine_distance(
    coord1: Tuple[float, float],
    coord2: Tuple[float, float]
) -> float:
    """
    Calculate the great circle distance between two points on Earth.

    Uses the Haversine formula to compute the distance between two
    geographic coordinates. This serves as the heuristic function for
    A* search in geographic routing.

    Args:
        coord1: First coordinate (latitude, longitude) in degrees
        coord2: Second coordinate (latitude, longitude) in degrees

    Returns:
        Distance in meters

    Example:
        >>> dist = haversine_distance((14.6507, 121.1029), (14.6545, 121.1089))
        >>> print(f"{dist:.2f} meters")
    """
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Earth's radius in meters
    radius = 6371000

    return radius * c


def create_heuristic(graph: nx.MultiDiGraph, target_node: Any) -> Callable:
    """
    Create a heuristic function for A* search.

    The heuristic estimates the cost from any node to the target node
    using Haversine distance. This is admissible (never overestimates)
    for geographic routing.

    Args:
        graph: NetworkX graph with 'y' (lat) and 'x' (lon) node attributes
        target_node: Target node ID

    Returns:
        Heuristic function that takes a node ID and returns estimated cost

    Example:
        >>> heuristic = create_heuristic(graph, target_node)
        >>> estimated_cost = heuristic(current_node)
    """
    target_lat = graph.nodes[target_node]['y']
    target_lon = graph.nodes[target_node]['x']

    def heuristic(node, target):
        """Estimate cost from node to target using Haversine distance."""
        # Note: NetworkX astar_path passes both node and target, but we use the
        # target_node from the closure since it's already bound
        if node == target_node:
            return 0.0

        node_lat = graph.nodes[node]['y']
        node_lon = graph.nodes[node]['x']

        return haversine_distance(
            (node_lat, node_lon),
            (target_lat, target_lon)
        )

    return heuristic


def risk_aware_astar(
    graph: nx.MultiDiGraph,
    start: Any,
    end: Any,
    risk_weight: float = 0.5,
    distance_weight: float = 1.0,
    max_risk_threshold: Optional[float] = None
) -> Tuple[Optional[List[Any]], Optional[List[int]]]:
    """
    Find the safest path using risk-aware A* algorithm.

    This modified A* algorithm finds paths that balance distance and safety
    by incorporating flood risk scores into edge costs. Roads with high
    flood risk are treated as more expensive to traverse.

    The total cost of an edge is calculated as:
        cost = length * distance_weight + length * risk_score * risk_weight
             = length * (1 + risk_score * risk_weight)   [when distance_weight=1.0]

    The risk_weight acts as a cost multiplier: risk_weight=3.0 means a fully
    flooded edge (risk=1.0) costs 4x its physical length. This is length-
    proportional, so longer flooded roads are penalized more (physically correct).

    Roads exceeding max_risk_threshold are considered impassable (infinite cost).

    Args:
        graph: NetworkX MultiDiGraph with road network
            Required node attributes: 'x' (longitude), 'y' (latitude)
            Required edge attributes: 'length' (meters), 'risk_score' (0-1)
        start: Start node ID
        end: End node ID
        risk_weight: Risk cost multiplier (default: 0.5)
            - Safest: 100.0 (risk=0.8 -> 81x edge length)
            - Balanced: 3.0 (risk=0.8 -> 3.4x edge length)
            - Fastest: 0.0 (pure shortest path)
        distance_weight: Weight for distance component (default: 1.0)
        max_risk_threshold: Maximum acceptable risk (default: from config critical_risk_threshold)
            Edges with risk >= threshold are considered impassable (critical flood danger)

    Returns:
        Tuple of (path, edge_keys):
            path: List of node IDs representing the path, or None if no path exists
            edge_keys: List of edge keys (integers) corresponding to selected parallel edges, or None

    Raises:
        nx.NetworkXNoPath: If no path exists between start and end
        KeyError: If required node/edge attributes are missing

    Example:
        >>> path, edge_keys = risk_aware_astar(
        ...     graph,
        ...     start_node,
        ...     end_node,
        ...     risk_weight=0.6,
        ...     distance_weight=0.4
        ... )
        >>> if path:
        ...     print(f"Found safe path with {len(path)} nodes")
    """
    if max_risk_threshold is None:
        from app.core.agent_config import AgentConfigLoader
        max_risk_threshold = AgentConfigLoader().get_routing_config().critical_risk_threshold

    logger.info(
        f"Computing risk-aware A* path from {start} to {end} "
        f"(risk_weight={risk_weight}, distance_weight={distance_weight})"
    )

    # Validate inputs
    if start not in graph:
        raise ValueError(f"Start node {start} not in graph")
    if end not in graph:
        raise ValueError(f"End node {end} not in graph")

    # Create heuristic function
    heuristic = create_heuristic(graph, end)

    # Track weight function calls for debugging
    blocked_edges_count = 0

    # Track which edge key was selected for each (u,v) pair
    selected_edges = {}

    # Define weight function that combines distance and risk
    def weight_function(u, v, edge_data):
        """
        Calculate edge weight considering both distance and risk.

        For MultiDiGraph, we need to find the best (lowest risk) edge among parallel edges.

        Args:
            u: Source node
            v: Target node
            edge_data: Dict of edge attributes (may not have risk_score for MultiDiGraph!)

        Returns:
            Combined weight (distance + risk cost) or inf if impassable
        """
        # For MultiDiGraph, access edge data directly from graph
        # Find the edge with lowest risk among all parallel edges between u and v
        best_length = 1.0
        best_risk = 1.0
        best_key = 0

        if v in graph[u]:
            # Get all parallel edges between u and v
            for key, data in graph[u][v].items():
                edge_length = data.get('length', 1.0)
                edge_risk = data.get('risk_score', 0.0)

                # Choose edge with lowest risk (or shortest if risks are equal)
                if edge_risk < best_risk or (edge_risk == best_risk and edge_length < best_length):
                    best_length = edge_length
                    best_risk = edge_risk
                    best_key = key

        # RECORD the selected edge key for this (u,v) pair
        selected_edges[(u, v)] = best_key

        length = best_length
        risk_score = best_risk

        # Check if road is impassable
        if risk_score >= max_risk_threshold:
            nonlocal blocked_edges_count
            blocked_edges_count += 1
            if blocked_edges_count <= 10:  # Log first 10 blocked edges
                logger.debug(f"[A*] BLOCKING edge ({u}, {v}): risk={risk_score:.3f} >= {max_risk_threshold}")
            return float('inf')

        # Calculate combined cost: length + length-proportional risk penalty
        # Formula matches graph_manager.py pre-computed weights when risk_weight=1.0:
        #   cost = length * (1.0 + risk_score * risk_weight)
        # This ensures A* heuristic (Haversine distance) remains admissible
        # since cost >= length for any non-negative risk_weight.
        total_cost = length * (distance_weight + risk_score * risk_weight)

        return total_cost

    try:
        # Run A* with custom weight and heuristic
        path = nx.astar_path(
            graph,
            start,
            end,
            heuristic=heuristic,
            weight=weight_function
        )

        # Extract the edge keys that were actually selected by A*
        edge_keys = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge_keys.append(selected_edges.get((u, v), 0))

        logger.info(
            f"Path found with {len(path)} nodes. "
            f"Blocked {blocked_edges_count} edges during search."
        )
        return path, edge_keys

    except nx.NetworkXNoPath:
        logger.warning(
            f"No path exists from {start} to {end}. "
            f"Blocked {blocked_edges_count} edges."
        )
        return None, None
    except Exception as e:
        logger.error(f"Error in A* pathfinding: {e}")
        raise


def calculate_path_metrics(
    graph: nx.MultiDiGraph,
    path: List[Any],
    edge_keys: Optional[List[int]] = None
) -> Dict[str, float]:
    """
    Calculate metrics for a computed path using the ACTUAL edges selected by A*.

    Computes total distance, average risk level, and estimated travel time
    for a given path through the road network.

    Args:
        graph: NetworkX graph containing the path
        path: List of node IDs representing the path
        edge_keys: List of edge keys (integers) for parallel edges (REQUIRED for accurate metrics)

    Returns:
        Dict containing path metrics:
            {
                "total_distance": float,  # meters
                "average_risk": float,  # 0-1 scale
                "max_risk": float,  # 0-1 scale
                "estimated_time": float,  # minutes (assumes 30 km/h avg)
                "num_segments": int
            }

    Example:
        >>> path, edge_keys = risk_aware_astar(graph, start, end)
        >>> metrics = calculate_path_metrics(graph, path, edge_keys)
        >>> print(f"Distance: {metrics['total_distance']:.0f}m")
        >>> print(f"Avg Risk: {metrics['average_risk']:.2f}")
    """
    if not path or len(path) < 2:
        return {
            "total_distance": 0.0,
            "average_risk": 0.0,
            "max_risk": 0.0,
            "estimated_time": 0.0,
            "num_segments": 0
        }

    total_distance = 0.0
    total_weighted_risk = 0.0  # Changed: Now weighted by distance
    max_risk = 0.0
    num_segments = 0

    # Iterate through path edges
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]

        # Get edge data using the CORRECT edge key selected by A*
        if graph.has_edge(u, v):
            # Use the edge key that was actually selected by A* (not always 0!)
            key = edge_keys[i] if edge_keys and i < len(edge_keys) else 0
            edge_data = graph[u][v][key]

            length = edge_data.get('length', 0.0)
            risk = edge_data.get('risk_score', 0.0)

            total_distance += length
            total_weighted_risk += risk * length  # Weight risk by segment length
            max_risk = max(max_risk, risk)
            num_segments += 1

    # Calculate distance-weighted average risk
    average_risk = total_weighted_risk / total_distance if total_distance > 0 else 0.0

    # Estimate time using config-driven speed and risk reduction
    from app.core.agent_config import AgentConfigLoader
    _algo_config = AgentConfigLoader().get_algorithms_config()
    base_speed_kmh = _algo_config.base_speed_kmh
    risk_factor = 1.0 - (average_risk * _algo_config.speed_reduction_factor)
    adjusted_speed_kmh = base_speed_kmh * risk_factor

    estimated_time_hours = (total_distance / 1000) / adjusted_speed_kmh
    estimated_time_minutes = estimated_time_hours * 60

    return {
        "total_distance": total_distance,
        "average_risk": average_risk,
        "max_risk": max_risk,
        "estimated_time": estimated_time_minutes,
        "num_segments": num_segments
    }


def get_path_coordinates(
    graph: nx.MultiDiGraph,
    path: List[Any]
) -> List[Tuple[float, float]]:
    """
    Convert path node IDs to geographic coordinates.

    Extracts latitude/longitude coordinates for each node in the path,
    suitable for visualization on a map.

    Args:
        graph: NetworkX graph with 'x' (lon) and 'y' (lat) attributes
        path: List of node IDs

    Returns:
        List of (latitude, longitude) tuples

    Example:
        >>> coords = get_path_coordinates(graph, path)
        >>> for lat, lon in coords:
        ...     print(f"Point: {lat:.4f}, {lon:.4f}")
    """
    coordinates = []

    for node in path:
        lat = graph.nodes[node]['y']
        lon = graph.nodes[node]['x']
        coordinates.append((lat, lon))

    return coordinates
