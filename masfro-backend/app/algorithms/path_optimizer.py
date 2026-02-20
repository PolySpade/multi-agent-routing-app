# filename: app/algorithms/path_optimizer.py

"""
Path Optimization Utilities for MAS-FRO

This module provides additional path optimization and analysis functions
to complement the risk-aware A* algorithm. Includes utilities for:
- Alternative route generation
- Path comparison and ranking
- Route smoothing and simplification
- Evacuation center integration

Author: MAS-FRO Development Team
Date: November 2025
"""

import networkx as nx
from typing import List, Tuple, Dict, Any, Optional
import logging
from .risk_aware_astar import risk_aware_astar, calculate_path_metrics, haversine_distance

logger = logging.getLogger(__name__)


def find_k_shortest_paths(
    graph: nx.MultiDiGraph,
    start: Any,
    end: Any,
    k: int = 3
) -> List[Dict[str, Any]]:
    """
    Find k alternative paths between start and end.

    Provides users with multiple route options, allowing them to choose
    based on their preferences for safety vs. speed.

    Args:
        graph: Road network graph
        start: Start node ID
        end: End node ID
        k: Number of alternative paths to find

    Returns:
        List of path dictionaries sorted by total cost
            Format:
            [
                {
                    "path": List[node_ids],
                    "metrics": Dict[str, float],
                    "rank": int
                },
                ...
            ]

    Example:
        >>> alternatives = find_k_shortest_paths(graph, start, end, k=3)
        >>> for i, route in enumerate(alternatives):
        ...     print(f"Route {i+1}: {route['metrics']['total_distance']}m")
    """
    logger.info(f"Finding {k} alternative paths from {start} to {end}")

    paths = []

    try:
        # Use NetworkX's k_shortest_paths as base
        # Note: This finds paths by simple length, we'll re-rank by risk
        path_generator = nx.shortest_simple_paths(graph, start, end, weight='weight')

        count = 0
        for path in path_generator:
            if count >= k:
                break

            metrics = calculate_path_metrics(graph, path)
            paths.append({
                "path": path,
                "metrics": metrics,
                "rank": count + 1
            })
            count += 1

        logger.info(f"Found {len(paths)} alternative paths")

    except nx.NetworkXNoPath:
        logger.warning(f"No paths found from {start} to {end}")
    except Exception as e:
        logger.error(f"Error finding alternative paths: {e}")

    return paths


def optimize_evacuation_route(
    graph: nx.MultiDiGraph,
    start: Tuple[float, float],
    evacuation_centers: List[Dict[str, Any]],
    max_centers: int = 5
) -> Optional[Dict[str, Any]]:
    """
    Find optimal route to nearest evacuation center.

    Identifies the safest evacuation center considering both distance
    and route safety, then computes the optimal path.

    Args:
        graph: Road network graph
        start: Starting coordinates (lat, lon)
        evacuation_centers: List of evacuation center dicts
            Format:
            [
                {
                    "name": str,
                    "location": Tuple[float, float],
                    "capacity": int,
                    "node_id": Any  # Nearest graph node
                },
                ...
            ]
        max_centers: Maximum number of centers to evaluate

    Returns:
        Dict with optimal evacuation route:
            {
                "center": Dict,  # Selected evacuation center
                "path": List[node_ids],
                "metrics": Dict,
                "alternatives": List  # Other considered centers
            }
        Or None if no route found
    """
    logger.info(f"Optimizing evacuation route from {start}")

    if not evacuation_centers:
        logger.warning("No evacuation centers provided")
        return None

    # Find nearest node to start coordinates
    start_node = _find_nearest_node(graph, start)
    if not start_node:
        logger.error("Could not find start node in graph")
        return None

    # Evaluate routes to each center
    routes = []
    for center in evacuation_centers[:max_centers]:
        center_node = center.get("node_id")
        if not center_node:
            continue

        try:
            path, edge_keys = risk_aware_astar(graph, start_node, center_node)
            if path:
                metrics = calculate_path_metrics(graph, path, edge_keys)
                routes.append({
                    "center": center,
                    "path": path,
                    "metrics": metrics,
                    "score": _calculate_evacuation_score(metrics, center)
                })
        except Exception as e:
            logger.warning(f"Failed to route to {center.get('name')}: {e}")
            continue

    if not routes:
        logger.warning("No valid evacuation routes found")
        return None

    # Sort by score (lower is better)
    routes.sort(key=lambda x: x["score"])

    best_route = routes[0]
    alternatives = routes[1:] if len(routes) > 1 else []

    logger.info(
        f"Selected evacuation center: {best_route['center']['name']} "
        f"(distance: {best_route['metrics']['total_distance']:.0f}m)"
    )

    return {
        "center": best_route["center"],
        "path": best_route["path"],
        "metrics": best_route["metrics"],
        "alternatives": alternatives
    }


def _find_nearest_node(
    graph: nx.MultiDiGraph,
    coords: Tuple[float, float],
    max_distance: Optional[float] = None
) -> Optional[Any]:
    """
    Find nearest graph node to given coordinates using OSMnx spatial index.

    Uses a KD-tree internally for O(log n) lookup instead of O(n) brute force.

    Args:
        graph: Road network graph
        coords: Target coordinates (lat, lon)
        max_distance: Maximum search distance in meters (default: from config)

    Returns:
        Nearest node ID or None if none found within max_distance
    """
    if max_distance is None:
        from app.core.agent_config import AgentConfigLoader
        max_distance = AgentConfigLoader().get_routing_config().max_node_distance_m

    import osmnx as ox

    target_lat, target_lon = coords

    try:
        nearest_node = ox.nearest_nodes(graph, target_lon, target_lat)
    except Exception:
        # Fallback to manual search if OSMnx spatial index fails
        logger.warning("ox.nearest_nodes failed, falling back to brute-force search")
        nearest_node = None
        min_distance = float('inf')
        for node in graph.nodes():
            node_lat = graph.nodes[node]['y']
            node_lon = graph.nodes[node]['x']
            distance = haversine_distance(
                (target_lat, target_lon),
                (node_lat, node_lon)
            )
            if distance < min_distance:
                min_distance = distance
                nearest_node = node
        if min_distance > max_distance:
            return None
        return nearest_node

    # Verify distance is within threshold
    node_lat = graph.nodes[nearest_node]['y']
    node_lon = graph.nodes[nearest_node]['x']
    distance = haversine_distance(
        (target_lat, target_lon),
        (node_lat, node_lon)
    )

    if distance > max_distance:
        logger.warning(
            f"Nearest node is {distance:.0f}m away "
            f"(exceeds max_distance of {max_distance:.0f}m)"
        )
        return None

    return nearest_node


def _calculate_evacuation_score(
    metrics: Dict[str, float],
    center: Dict[str, Any]
) -> float:
    """
    Calculate score for evacuation center route.

    Lower score is better. Considers:
    - Route safety (risk level)
    - Distance
    - Center capacity

    Args:
        metrics: Path metrics
        center: Evacuation center info

    Returns:
        Combined score (lower is better)
    """
    # Normalize components
    distance_score = metrics["total_distance"] / 1000  # km
    risk_score = metrics["average_risk"] * 10  # Scale up risk
    capacity_score = 1.0 / (center.get("capacity", 100) / 100)  # Prefer high capacity

    # Weighted combination (prioritize safety and distance)
    from app.core.agent_config import AgentConfigLoader
    _algo_config = AgentConfigLoader().get_algorithms_config()
    score = (
        distance_score * _algo_config.evac_weight_distance +
        risk_score * _algo_config.evac_weight_risk +
        capacity_score * _algo_config.evac_weight_capacity
    )

    return score
