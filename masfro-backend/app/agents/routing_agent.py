# filename: app/agents/routing_agent.py

"""
Routing Agent for Multi-Agent System for Flood Route Optimization (MAS-FRO)

Updated version integrated with risk-aware A* algorithm and ACL communication.

VIRTUAL METERS APPROACH:
This implementation uses a "Risk Penalty" system instead of traditional 0-1 weights
to fix Heuristic Domination in A* search. Risk scores (0-1) are converted to
"Virtual Meters" so they operate in the same units as distance:

  - Safest Mode: risk_penalty = 100,000 (adds 100km per risk unit - prioritize safety)
  - Balanced Mode: risk_penalty = 2,000 (adds 2km per risk unit - balance safety/speed)
  - Fastest Mode: risk_penalty = 0 (ignores risk completely - pure shortest path)

Note: All modes still block truly impassable roads (risk >= 0.9) automatically.

This prevents the A* heuristic (pure distance in meters) from dominating the
risk component and producing dangerous "shortest" routes.

Author: MAS-FRO Development Team
Date: November 2025
"""

from .base_agent import BaseAgent
from typing import Dict, Any, List, Tuple, Optional, TYPE_CHECKING
import logging
import pandas as pd
import os
from pathlib import Path

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment

logger = logging.getLogger(__name__)


class RoutingAgent(BaseAgent):
    """
    Agent responsible for pathfinding computations in MAS-FRO system.

    This agent performs risk-aware route optimization using the A* algorithm
    integrated with real-time flood risk data from HazardAgent. It can calculate
    routes to specific destinations or to nearest evacuation centers.

    Uses "Virtual Meters" approach to prevent Heuristic Domination:
    Risk penalties are expressed in virtual meters (not 0-1 weights), ensuring
    the A* heuristic and risk penalties operate in compatible units.

    Attributes:
        agent_id: Unique identifier for this agent
        environment: Reference to DynamicGraphEnvironment
        evacuation_centers: DataFrame of evacuation center locations
        risk_penalty: Virtual meters added per risk unit (e.g., 2000.0 for balanced)
        distance_weight: Weight for distance component (always 1.0 for A* consistency)

    Example:
        >>> env = DynamicGraphEnvironment()
        >>> agent = RoutingAgent("routing_001", env, risk_penalty=2000.0)
        >>> route = agent.calculate_route((14.65, 121.10), (14.66, 121.11))
    """

    def __init__(
        self,
        agent_id: str,
        environment: "DynamicGraphEnvironment",
        risk_penalty: float = 2000.0,  # BALANCED MODE: 2000 virtual meters per risk unit
        distance_weight: float = 1.0   # Always 1.0 to preserve A* heuristic consistency
    ) -> None:
        """
        Initialize the RoutingAgent.

        Virtual Meters Approach:
        Instead of 0-1 weights, we use a "Risk Penalty" system that converts risk
        into "Virtual Meters" to fix Heuristic Domination in A* search. This ensures
        the distance heuristic and risk penalties work in the same units.

        Args:
            agent_id: Unique identifier for this agent
            environment: DynamicGraphEnvironment instance
            risk_penalty: Virtual meters per risk unit (default: 2000.0 for balanced)
                - Safest mode: 100000.0 (extreme penalty, prioritize safety)
                - Balanced mode: 2000.0 (moderate penalty, balance safety/speed)
                - Fastest mode: 0.0 (no penalty, ignore risk completely)
            distance_weight: Weight for distance (always 1.0 for A* consistency)
        """
        super().__init__(agent_id, environment)

        # Pathfinding configuration using Virtual Meters approach
        self.risk_penalty = risk_penalty
        self.distance_weight = distance_weight

        # Load evacuation centers
        self.evacuation_centers = self._load_evacuation_centers()

        logger.info(
            f"{self.agent_id} initialized with "
            f"risk_penalty={risk_penalty}, distance_weight={distance_weight}, "
            f"evacuation_centers={len(self.evacuation_centers)}"
        )

    def step(self):
        """
        Perform one step of agent's operation.

        In this implementation, the RoutingAgent is stateless and responds
        to route requests on-demand rather than running a continuous loop.
        """
        pass

    def calculate_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate optimal route from start to end coordinates.

        Args:
            start: Starting coordinates (latitude, longitude)
            end: Ending coordinates (latitude, longitude)
            preferences: Optional routing preferences

        Returns:
            Dict containing route information:
                {
                    "status": "success" | "impassable" | "no_safe_route",
                    "path": List of (lat, lon) coordinates,
                    "distance": Total distance in meters,
                    "estimated_time": Estimated time in minutes,
                    "risk_level": Average risk score (0-1),
                    "max_risk": Maximum risk score on route,
                    "num_segments": Number of road segments,
                    "warnings": List of warning messages
                }

            Status values:
                - "success": Route found successfully
                - "impassable": No route exists (fastest mode, all roads blocked)
                - "no_safe_route": No safe route found (safest/balanced mode)

        Raises:
            ValueError: If coordinates are invalid or graph not loaded
        """
        from ..algorithms.risk_aware_astar import (
            risk_aware_astar,
            calculate_path_metrics,
            get_path_coordinates
        )

        logger.info(f"{self.agent_id} calculating route: {start} -> {end}")

        # Validate inputs
        if not self.environment or not self.environment.graph:
            raise ValueError("Graph environment not loaded")

        # Find nearest nodes in graph
        start_node = self._find_nearest_node(start)
        end_node = self._find_nearest_node(end)

        if not start_node or not end_node:
            raise ValueError("Could not map coordinates to road network")

        # Apply preferences using Virtual Meters approach
        # Risk penalties convert risk (0-1) into "Virtual Meters" to match distance units
        # This prevents the A* heuristic (pure distance) from dominating risk scores
        risk_penalty = self.risk_penalty
        distance_weight = self.distance_weight  # Always 1.0

        if preferences:
            if preferences.get("avoid_floods"):
                # SAFEST MODE: Massive penalty makes risk dominate routing decisions
                # 100,000 virtual meters = prefer 100km detour over 1.0 risk road
                risk_penalty = 100000.0
                distance_weight = 1.0  # Must stay 1.0 to preserve A* heuristic
                logger.info(
                    f"SAFEST MODE: risk_penalty={risk_penalty}, "
                    f"distance_weight={distance_weight}"
                )
            elif preferences.get("fastest"):
                # FASTEST MODE: Ignore all risk, traverse any road
                # risk_penalty = 0.0 means pure distance-based routing
                # Note: Roads with risk >= 0.9 (impassable) are still blocked by A*
                risk_penalty = 0.0
                distance_weight = 1.0  # Must stay 1.0 to preserve A* heuristic
                logger.info(
                    f"FASTEST MODE: risk_penalty={risk_penalty}, "
                    f"distance_weight={distance_weight} (ignoring risk, blocking impassable only)"
                )
        else:
            logger.info(
                f"BALANCED MODE: risk_penalty={risk_penalty}, "
                f"distance_weight={distance_weight}"
            )

        # Calculate route using risk-aware A*
        # Note: risk_penalty is passed as risk_weight to maintain API compatibility
        path_nodes, edge_keys = risk_aware_astar(
            self.environment.graph,
            start_node,
            end_node,
            risk_weight=risk_penalty,  # Virtual meters per risk unit
            distance_weight=distance_weight  # Always 1.0
        )

        if not path_nodes:
            # Determine appropriate warning and status based on mode
            if preferences and preferences.get("fastest"):
                status = "impassable"
                warning_msg = (
                    "IMPASSABLE: No route found. All paths contain critically flooded "
                    "or impassable roads (risk >= 90%). Consider waiting for conditions "
                    "to improve or using evacuation assistance."
                )
            else:
                status = "no_safe_route"
                warning_msg = (
                    "No safe route found. Try 'Fastest' mode to see if any path exists, "
                    "or consider evacuation to a nearby shelter."
                )

            return {
                "status": status,
                "path": [],
                "distance": 0,
                "estimated_time": 0,
                "risk_level": 1.0,
                "max_risk": 1.0,
                "warnings": [warning_msg]
            }

        # Convert to coordinates
        path_coords = get_path_coordinates(self.environment.graph, path_nodes)

        # Calculate metrics using the CORRECT edge keys selected by A*
        metrics = calculate_path_metrics(self.environment.graph, path_nodes, edge_keys)

        # Generate warnings (pass preferences to customize warnings by mode)
        warnings = self._generate_warnings(metrics, preferences)

        logger.info(
            f"{self.agent_id} route calculated: "
            f"distance={metrics['total_distance']:.0f}m, "
            f"risk={metrics['average_risk']:.2f}"
        )

        return {
            "status": "success",
            "path": path_coords,
            "distance": metrics["total_distance"],
            "estimated_time": metrics["estimated_time"],
            "risk_level": metrics["average_risk"],
            "max_risk": metrics["max_risk"],
            "num_segments": metrics["num_segments"],
            "warnings": warnings
        }

    def find_nearest_evacuation_center(
        self,
        location: Tuple[float, float],
        max_centers: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Find nearest evacuation center and calculate route.

        Args:
            location: Current location (latitude, longitude)
            max_centers: Maximum number of centers to evaluate

        Returns:
            Dict with evacuation center info and route, or None if not found
        """
        from ..algorithms.path_optimizer import optimize_evacuation_route

        logger.info(f"{self.agent_id} finding nearest evacuation center from {location}")

        if self.evacuation_centers.empty:
            logger.warning("No evacuation centers loaded")
            return None

        # Prepare evacuation center data
        centers = []
        for _, row in self.evacuation_centers.head(max_centers).iterrows():
            center_location = (row['latitude'], row['longitude'])
            center_node = self._find_nearest_node(center_location)

            if center_node:
                centers.append({
                    "name": row['name'],
                    "location": center_location,
                    "capacity": row.get('capacity', 0),
                    "type": row.get('type', 'shelter'),
                    "node_id": center_node
                })

        if not centers:
            return None

        # Use path optimizer to find best evacuation route
        result = optimize_evacuation_route(
            self.environment.graph,
            location,
            centers,
            max_centers=max_centers
        )

        if result:
            # Convert path to coordinates
            from ..algorithms.risk_aware_astar import get_path_coordinates
            path_coords = get_path_coordinates(self.environment.graph, result["path"])
            result["path"] = path_coords

        return result

    def calculate_alternative_routes(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Calculate k alternative routes.

        Args:
            start: Starting coordinates
            end: Ending coordinates
            k: Number of alternative routes to find

        Returns:
            List of route dictionaries, sorted by combined score
        """
        from ..algorithms.path_optimizer import find_k_shortest_paths
        from ..algorithms.risk_aware_astar import get_path_coordinates

        logger.info(f"{self.agent_id} finding {k} alternative routes")

        start_node = self._find_nearest_node(start)
        end_node = self._find_nearest_node(end)

        if not start_node or not end_node:
            return []

        alternatives = find_k_shortest_paths(
            self.environment.graph,
            start_node,
            end_node,
            k=k,
            risk_weight=self.risk_penalty,  # Virtual meters per risk unit
            distance_weight=self.distance_weight  # Always 1.0
        )

        # Convert paths to coordinates and add warnings
        result = []
        for alt in alternatives:
            path_coords = get_path_coordinates(self.environment.graph, alt["path"])
            warnings = self._generate_warnings(alt["metrics"])

            result.append({
                "rank": alt["rank"],
                "path": path_coords,
                "distance": alt["metrics"]["total_distance"],
                "estimated_time": alt["metrics"]["estimated_time"],
                "risk_level": alt["metrics"]["average_risk"],
                "max_risk": alt["metrics"]["max_risk"],
                "warnings": warnings
            })

        return result

    def _find_nearest_node(
        self,
        coords: Tuple[float, float],
        max_distance: float = 500.0
    ) -> Optional[Any]:
        """
        Find nearest graph node to given coordinates using osmnx.

        Performance: O(log N) using spatial indexing instead of O(N) brute-force.

        Args:
            coords: Target coordinates (latitude, longitude)
            max_distance: Maximum search distance in meters

        Returns:
            Nearest node ID or None if not found
        """
        if not self.environment or not self.environment.graph:
            return None

        target_lat, target_lon = coords

        try:
            # Use osmnx for efficient nearest node lookup (O(log N) via spatial index)
            import osmnx as ox

            nearest_node = ox.distance.nearest_nodes(
                self.environment.graph,
                X=target_lon,  # osmnx uses X=longitude, Y=latitude
                Y=target_lat
            )

            # Verify distance is within max_distance threshold
            from ..algorithms.risk_aware_astar import haversine_distance
            node_lat = self.environment.graph.nodes[nearest_node]['y']
            node_lon = self.environment.graph.nodes[nearest_node]['x']

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

        except Exception as e:
            # Fallback to brute-force if osmnx fails (should be rare)
            logger.warning(
                f"osmnx nearest_nodes failed ({e}), falling back to brute-force search"
            )

            from ..algorithms.risk_aware_astar import haversine_distance
            nearest_node = None
            min_distance = float('inf')

            for node in self.environment.graph.nodes():
                node_lat = self.environment.graph.nodes[node]['y']
                node_lon = self.environment.graph.nodes[node]['x']

                distance = haversine_distance(
                    (target_lat, target_lon),
                    (node_lat, node_lon)
                )

                if distance < min_distance:
                    min_distance = distance
                    nearest_node = node

            if min_distance > max_distance:
                logger.warning(
                    f"Nearest node is {min_distance:.0f}m away "
                    f"(exceeds max_distance of {max_distance:.0f}m)"
                )
                return None

            return nearest_node

    def _generate_warnings(
        self,
        metrics: Dict[str, float],
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate warning messages based on route metrics.

        Args:
            metrics: Path metrics dictionary
            preferences: Optional routing preferences (to customize warnings by mode)

        Returns:
            List of warning messages
        """
        warnings = []

        avg_risk = metrics.get("average_risk", 0)
        max_risk = metrics.get("max_risk", 0)
        is_fastest_mode = preferences and preferences.get("fastest")

        # Special warning for fastest mode with high risk
        if is_fastest_mode and (max_risk >= 0.5 or avg_risk >= 0.3):
            warnings.append(
                "FASTEST MODE ACTIVE: This route ignores flood risk. "
                f"Max risk: {max_risk:.1%}, Avg risk: {avg_risk:.1%}. "
                "Expect flooded roads and hazardous conditions."
            )

        # Standard risk warnings (apply to all modes)
        if max_risk >= 0.9:
            warnings.append(
                "CRITICAL: Route contains impassable or extremely dangerous roads. "
                "Consider alternative route or evacuation."
            )
        elif max_risk >= 0.7:
            warnings.append(
                "WARNING: Route contains high-risk flood areas. "
                "Exercise extreme caution and monitor conditions."
            )
        elif avg_risk >= 0.5 and not is_fastest_mode:
            # Don't duplicate warning in fastest mode (already warned above)
            warnings.append(
                "CAUTION: Moderate flood risk on this route. "
                "Drive slowly and be prepared for water on roads."
            )

        if metrics.get("total_distance", 0) > 10000:
            warnings.append(
                "This is a long route. Consider fuel and time requirements."
            )

        return warnings

    def _load_evacuation_centers(self) -> pd.DataFrame:
        """
        Load evacuation center data from CSV file.

        Returns:
            DataFrame with evacuation center information
        """
        try:
            # Try multiple possible paths
            possible_paths = [
                Path(__file__).parent.parent / "data" / "evacuation_centers.csv",
                Path(__file__).parent.parent.parent / "data" / "evacuation_centers.csv",
            ]

            for csv_path in possible_paths:
                if csv_path.exists():
                    df = pd.read_csv(csv_path)
                    logger.info(f"Loaded {len(df)} evacuation centers from {csv_path}")
                    return df

            # If no file found, create sample data
            logger.warning("Evacuation centers file not found, creating sample data")
            return self._create_sample_evacuation_centers()

        except Exception as e:
            logger.error(f"Failed to load evacuation centers: {e}")
            return pd.DataFrame(
                columns=['name', 'latitude', 'longitude', 'capacity', 'type']
            )

    def _create_sample_evacuation_centers(self) -> pd.DataFrame:
        """
        Create sample evacuation center data for testing.

        Returns:
            DataFrame with sample evacuation centers
        """
        sample_data = [
            {
                "name": "Marikina Elementary School",
                "latitude": 14.6507,
                "longitude": 121.1029,
                "capacity": 200,
                "type": "school"
            },
            {
                "name": "Marikina Sports Center",
                "latitude": 14.6545,
                "longitude": 121.1089,
                "capacity": 500,
                "type": "gymnasium"
            },
            {
                "name": "Barangay Concepcion Covered Court",
                "latitude": 14.6480,
                "longitude": 121.0980,
                "capacity": 150,
                "type": "covered_court"
            },
        ]

        return pd.DataFrame(sample_data)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get routing agent statistics.

        Returns:
            Dict with agent statistics
        """
        return {
            "agent_id": self.agent_id,
            "risk_penalty": self.risk_penalty,  # Virtual meters per risk unit
            "distance_weight": self.distance_weight,
            "evacuation_centers": len(self.evacuation_centers),
            "graph_loaded": bool(self.environment and self.environment.graph)
        }
