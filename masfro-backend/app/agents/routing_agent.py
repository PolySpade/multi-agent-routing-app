# filename: app/agents/routing_agent.py

"""
Routing Agent for Multi-Agent System for Flood Route Optimization (MAS-FRO)

Updated version integrated with risk-aware A* algorithm and ACL communication.

Author: MAS-FRO Development Team
Date: November 2025
"""

from .base_agent import BaseAgent
from typing import Dict, Any, List, Tuple, Optional
import logging
import pandas as pd
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class RoutingAgent(BaseAgent):
    """
    Agent responsible for pathfinding computations in MAS-FRO system.

    This agent performs risk-aware route optimization using the A* algorithm
    integrated with real-time flood risk data from HazardAgent. It can calculate
    routes to specific destinations or to nearest evacuation centers.

    Attributes:
        agent_id: Unique identifier for this agent
        environment: Reference to DynamicGraphEnvironment
        evacuation_centers: DataFrame of evacuation center locations
        risk_weight: Weight for risk component in pathfinding (0-1)
        distance_weight: Weight for distance component in pathfinding (0-1)

    Example:
        >>> env = DynamicGraphEnvironment()
        >>> agent = RoutingAgent("routing_001", env)
        >>> route = agent.calculate_route((14.65, 121.10), (14.66, 121.11))
    """

    def __init__(
        self,
        agent_id: str,
        environment,
        risk_weight: float = 0.6,
        distance_weight: float = 0.4
    ):
        """
        Initialize the RoutingAgent.

        Args:
            agent_id: Unique identifier for this agent
            environment: DynamicGraphEnvironment instance
            risk_weight: Weight for risk in pathfinding (default: 0.6)
            distance_weight: Weight for distance in pathfinding (default: 0.4)
        """
        super().__init__(agent_id, environment)

        # Pathfinding configuration
        self.risk_weight = risk_weight
        self.distance_weight = distance_weight

        # Load evacuation centers
        self.evacuation_centers = self._load_evacuation_centers()

        logger.info(
            f"{self.agent_id} initialized with "
            f"risk_weight={risk_weight}, distance_weight={distance_weight}, "
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
                    "path": List of (lat, lon) coordinates,
                    "distance": Total distance in meters,
                    "estimated_time": Estimated time in minutes,
                    "risk_level": Average risk score (0-1),
                    "max_risk": Maximum risk score on route,
                    "warnings": List of warning messages
                }

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

        # Apply preferences
        risk_weight = self.risk_weight
        distance_weight = self.distance_weight

        if preferences:
            if preferences.get("avoid_floods"):
                risk_weight = 0.8
                distance_weight = 0.2
            elif preferences.get("fastest"):
                risk_weight = 0.3
                distance_weight = 0.7

        # Calculate route using risk-aware A*
        path_nodes = risk_aware_astar(
            self.environment.graph,
            start_node,
            end_node,
            risk_weight=risk_weight,
            distance_weight=distance_weight
        )

        if not path_nodes:
            return {
                "path": [],
                "distance": 0,
                "estimated_time": 0,
                "risk_level": 1.0,
                "max_risk": 1.0,
                "warnings": ["No safe route found"]
            }

        # Convert to coordinates
        path_coords = get_path_coordinates(self.environment.graph, path_nodes)

        # Calculate metrics
        metrics = calculate_path_metrics(self.environment.graph, path_nodes)

        # Generate warnings
        warnings = self._generate_warnings(metrics)

        logger.info(
            f"{self.agent_id} route calculated: "
            f"distance={metrics['total_distance']:.0f}m, "
            f"risk={metrics['average_risk']:.2f}"
        )

        return {
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
            risk_weight=self.risk_weight,
            distance_weight=self.distance_weight
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
        Find nearest graph node to given coordinates.

        Args:
            coords: Target coordinates (latitude, longitude)
            max_distance: Maximum search distance in meters

        Returns:
            Nearest node ID or None if not found
        """
        from ..algorithms.risk_aware_astar import haversine_distance

        if not self.environment or not self.environment.graph:
            return None

        target_lat, target_lon = coords
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

    def _generate_warnings(self, metrics: Dict[str, float]) -> List[str]:
        """
        Generate warning messages based on route metrics.

        Args:
            metrics: Path metrics dictionary

        Returns:
            List of warning messages
        """
        warnings = []

        avg_risk = metrics.get("average_risk", 0)
        max_risk = metrics.get("max_risk", 0)

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
        elif avg_risk >= 0.5:
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
            "risk_weight": self.risk_weight,
            "distance_weight": self.distance_weight,
            "evacuation_centers": len(self.evacuation_centers),
            "graph_loaded": bool(self.environment and self.environment.graph)
        }
