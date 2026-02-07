# filename: app/agents/routing_agent.py

"""
Routing Agent for Multi-Agent System for Flood Route Optimization (MAS-FRO)

Updated version integrated with risk-aware A* algorithm and ACL communication.

VIRTUAL METERS APPROACH - SCIENTIFIC JUSTIFICATION (Issue #14)
==============================================================

Problem: Heuristic Domination in Multi-Objective A*
---------------------------------------------------
Traditional weighted A* with risk uses: f(n) = g(n) + h(n)
where g(n) = distance + risk_weight * risk

When risk_weight is small (0.0-1.0), the distance component dominates because:
- Typical edge distance: 50-500 meters
- Risk score: 0.0-1.0
- Result: Risk contribution is negligible compared to distance

This causes A* to find the shortest path, ignoring flood risk entirely.

Solution: Risk Penalty in "Virtual Meters"
------------------------------------------
Convert risk scores to the same unit as distance (meters):

    edge_cost = distance_meters + (risk_penalty * risk_score)

This ensures risk and distance are comparable in magnitude.

Derivation of Penalty Values
----------------------------
For Marikina City road network:
- Average edge length: ~150m
- Typical route: 20-50 edges
- Total route distance: 3,000 - 7,500m (3-7.5 km)

To make a high-risk edge (risk=0.8) "feel" like a significant detour:

1. SAFEST MODE (risk_penalty = 100,000)
   - High-risk edge (0.8): adds 80,000 virtual meters (80km)
   - Effect: Will take ANY detour to avoid flooded roads
   - Use case: Emergency evacuation, vulnerable users
   - Math: 100,000 * 0.8 = 80,000m >> typical route (5,000m)

2. BALANCED MODE (risk_penalty = 2,000)
   - High-risk edge (0.8): adds 1,600 virtual meters (1.6km)
   - Effect: Prefers safer routes but accepts minor risk for efficiency
   - Use case: General navigation, most users
   - Math: 2,000 * 0.8 = 1,600m ≈ detour threshold (~1.5km)

3. FASTEST MODE (risk_penalty = 0)
   - Effect: Pure shortest path, ignores risk completely
   - Use case: Emergency responders who must reach destination
   - Note: Still blocks truly impassable roads (risk >= 0.9)

Calibration Methodology
-----------------------
Values were calibrated using:
1. Marikina City road network statistics (40,000+ nodes, 100,000+ edges)
2. Average detour distance analysis
3. User preference studies (safety vs. time trade-off)

Formula: risk_penalty = detour_tolerance_meters / acceptable_risk_threshold
- Balanced: 2000 = 1600m / 0.8 (accept 1.6km detour to avoid 0.8 risk)
- Safest: 100000 = virtually infinite (avoid all risk)

References
----------
- Dijkstra, E.W. (1959). "A Note on Two Problems in Connexion with Graphs"
- Hart, P.E., Nilsson, N.J., Raphael, B. (1968). "A* Algorithm"
- MAS-FRO Technical Documentation: AGENTS_DETAILED_REVIEW.md Section 2.2

Author: MAS-FRO Development Team
Date: November 2025 (Updated January 2026)
"""

from .base_agent import BaseAgent
from typing import Dict, Any, List, Tuple, Optional, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass, field
import logging
import time
import pandas as pd
import os
from pathlib import Path

from ..communication.acl_protocol import Performative

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment

logger = logging.getLogger(__name__)


class WarningSeverity(Enum):
    """Warning severity levels for route safety."""
    INFO = "info"           # FYI - informational
    CAUTION = "caution"     # Be aware - minor concerns
    WARNING = "warning"     # Dangerous - significant risk
    CRITICAL = "critical"   # Life-threatening - do not proceed


@dataclass
class RouteWarning:
    """Structured warning with severity and actionable recommendations."""
    severity: WarningSeverity
    message: str
    details: str
    recommended_actions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'severity': self.severity.value,
            'message': self.message,
            'details': self.details,
            'recommended_actions': self.recommended_actions
        }

    def to_legacy_string(self) -> str:
        """Convert to legacy string format for backward compatibility."""
        prefix = {
            WarningSeverity.INFO: "INFO",
            WarningSeverity.CAUTION: "CAUTION",
            WarningSeverity.WARNING: "WARNING",
            WarningSeverity.CRITICAL: "CRITICAL"
        }.get(self.severity, "INFO")
        return f"{prefix}: {self.message}"


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
        distance_weight: float = 1.0,   # Always 1.0 to preserve A* heuristic consistency
        llm_service: Optional[Any] = None,
        message_queue: Optional[Any] = None
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
            llm_service: Optional LLMService instance for smart routing features
            message_queue: Optional MessageQueue for MAS communication
        """
        super().__init__(agent_id, environment)

        # Pathfinding configuration using Virtual Meters approach
        self.risk_penalty = risk_penalty
        self.distance_weight = distance_weight
        self.llm_service = llm_service

        # MessageQueue for orchestrator communication
        self.message_queue = message_queue
        if self.message_queue:
            try:
                self.message_queue.register_agent(self.agent_id)
                logger.info(f"{self.agent_id} registered with MessageQueue")
            except ValueError:
                logger.warning(f"{self.agent_id} already registered with MQ")

        # Node lookup cache for O(1) repeated lookups (Issue #6 fix)
        # Cache key: (rounded_lat, rounded_lon) -> (node_id, timestamp)
        self._node_cache: Dict[Tuple[float, float], Tuple[Any, float]] = {}
        self._cache_precision = 4  # Decimal places (~11m precision)
        self._cache_ttl_seconds = 3600  # Cache TTL: 1 hour
        self._cache_hits = 0
        self._cache_misses = 0
        self._max_cache_size = 10000

        # Load evacuation centers
        self.evacuation_centers = self._load_evacuation_centers()

        logger.info(
            f"{self.agent_id} initialized with "
            f"risk_penalty={risk_penalty}, distance_weight={distance_weight}, "
            f"evacuation_centers={len(self.evacuation_centers)}, "
            f"llm_enabled={bool(self.llm_service)}, "
            f"mq_enabled={bool(self.message_queue)}"
        )

    def step(self):
        """
        Perform one step of agent's operation.

        Processes any pending MQ requests from orchestrator.
        The RoutingAgent is otherwise stateless and responds
        to route requests on-demand.
        """
        self._process_mq_requests()

    def _process_mq_requests(self) -> None:
        """Process incoming REQUEST messages from orchestrator via MQ."""
        if not self.message_queue:
            return

        while True:
            msg = self.message_queue.receive_message(
                agent_id=self.agent_id, timeout=0.0, block=False
            )
            if msg is None:
                break

            if msg.performative == Performative.REQUEST:
                action = msg.content.get("action")
                data = msg.content.get("data", {})

                if action == "calculate_route":
                    self._handle_route_request(msg, data)
                elif action == "find_evacuation_center":
                    self._handle_evac_center_request(msg, data)
                else:
                    logger.warning(
                        f"{self.agent_id}: unknown REQUEST action '{action}' "
                        f"from {msg.sender}"
                    )
            else:
                logger.debug(
                    f"{self.agent_id}: ignoring {msg.performative} from {msg.sender}"
                )

    def _handle_route_request(self, msg, data: dict) -> None:
        """Handle calculate_route REQUEST from orchestrator."""
        from app.communication.acl_protocol import create_inform_message

        start = data.get("start")
        end = data.get("end")
        prefs = data.get("preferences", {})
        result = {"status": "unknown"}

        try:
            if not start or not end:
                result["status"] = "error"
                result["error"] = "Missing start or end coordinates"
            else:
                route = self.calculate_route(start, end, prefs)
                result["status"] = "success"
                result["route"] = route
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        logger.info(f"{self.agent_id}: calculate_route -> {result['status']}")

        reply = create_inform_message(
            sender=self.agent_id,
            receiver=msg.sender,
            info_type="route_calculation_result",
            data=result,
            conversation_id=msg.conversation_id,
            in_reply_to=msg.reply_with,
        )
        try:
            self.message_queue.send_message(reply)
        except Exception as e:
            logger.error(f"{self.agent_id}: failed to reply to {msg.sender}: {e}")

    def _handle_evac_center_request(self, msg, data: dict) -> None:
        """Handle find_evacuation_center REQUEST from orchestrator."""
        from app.communication.acl_protocol import create_inform_message

        location = data.get("location")
        query = data.get("query")
        prefs = data.get("preferences", {})
        max_centers = data.get("max_centers", 5)
        result = {"status": "unknown"}

        try:
            if not location:
                result["status"] = "error"
                result["error"] = "Missing location"
            else:
                evac_result = self.find_nearest_evacuation_center(
                    location, max_centers, query, prefs
                )
                result["status"] = "success"
                result["evacuation_result"] = evac_result
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        logger.info(f"{self.agent_id}: find_evacuation_center -> {result['status']}")

        reply = create_inform_message(
            sender=self.agent_id,
            receiver=msg.sender,
            info_type="evacuation_center_result",
            data=result,
            conversation_id=msg.conversation_id,
            in_reply_to=msg.reply_with,
        )
        try:
            self.message_queue.send_message(reply)
        except Exception as e:
            logger.error(f"{self.agent_id}: failed to reply to {msg.sender}: {e}")

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
        max_centers: int = 5,
        query: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find nearest evacuation center and calculate route with NLP support.

        Args:
            location: Current location (latitude, longitude)
            max_centers: Maximum number of centers to evaluate
            query: Natural language distress call/query
            preferences: Structured preferences override

        Returns:
            Dict with evacuation center info and route, or None if not found
        """
        from ..algorithms.path_optimizer import optimize_evacuation_route
        from ..algorithms.risk_aware_astar import get_path_coordinates, calculate_path_metrics, risk_aware_astar

        logger.info(f"{self.agent_id} finding nearest evacuation center from {location}")

        if self.evacuation_centers.empty:
            logger.warning("No evacuation centers loaded")
            return None

        # 1. Parse Query into Preferences
        final_preferences = preferences or {}
        if query:
            try:
                smart_prefs = self.parse_routing_request(query)
                if smart_prefs:
                    logger.info(f"Evacuation query parsed: {smart_prefs}")
                    final_preferences = {**smart_prefs, **final_preferences}
            except Exception as e:
                logger.warning(f"Failed to parse evacuation query: {e}")

        # Prepare evacuation center data — sort by straight-line distance first
        from ..algorithms.risk_aware_astar import haversine_distance as _haversine

        ec = self.evacuation_centers.copy()
        ec['_dist'] = ec.apply(
            lambda r: _haversine(location, (r['latitude'], r['longitude'])), axis=1
        )
        ec = ec.sort_values('_dist').head(max_centers)

        centers = []
        for _, row in ec.iterrows():
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

        # Note: optimize_evacuation_route currently doesn't support preferences directly
        # So we manually iterate to apply risk penalties correctly
        # This overrides the batch optimizer for NLP-aware routing
        
        start_node = self._find_nearest_node(location)
        if not start_node:
            return None

        # Apply risk penalty from preferences
        risk_penalty = self.risk_penalty
        if final_preferences.get("mode") == "safest":
            risk_penalty = 100000.0
        elif final_preferences.get("mode") == "fastest":
            risk_penalty = 0.0

        candidates = []
        for center in centers:
            # Calculate route with custom risk penalty
            path_nodes, edge_keys = risk_aware_astar(
                self.environment.graph,
                start_node,
                center["node_id"],
                risk_weight=risk_penalty,
                distance_weight=self.distance_weight
            )

            if path_nodes:
                metrics = calculate_path_metrics(self.environment.graph, path_nodes, edge_keys)
                path_coords = get_path_coordinates(self.environment.graph, path_nodes)
                candidates.append({
                    "center": center,
                    "metrics": metrics,
                    "path": path_coords,
                    "risk_penalty_used": risk_penalty
                })

        if not candidates:
            return None

        # Select best based on risk and time
        # Prioritize lowest risk, then time
        best_result = sorted(candidates, key=lambda x: (x["metrics"]["average_risk"], x["metrics"]["estimated_time"]))[0]

        # Generate explanation if query present
        if query and self.llm_service:
            explanation = self.explain_route({
                "distance": best_result["metrics"]["total_distance"],
                "estimated_time": best_result["metrics"]["estimated_time"],
                "risk_level": best_result["metrics"]["average_risk"],
                "max_risk": best_result["metrics"]["max_risk"],
                "warnings": []
            })
            best_result["explanation"] = explanation

        return best_result

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

        # Check cache first (O(1) lookup)
        cache_key = (
            round(target_lat, self._cache_precision),
            round(target_lon, self._cache_precision)
        )

        if cache_key in self._node_cache:
            cached_node, cached_time = self._node_cache[cache_key]
            if time.time() - cached_time < self._cache_ttl_seconds:
                self._cache_hits += 1
                logger.debug(f"Node cache hit for {cache_key} (hits: {self._cache_hits})")
                return cached_node
            else:
                # Cache expired, remove it
                del self._node_cache[cache_key]

        self._cache_misses += 1

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

            # Cache the result
            self._node_cache[cache_key] = (nearest_node, time.time())
            self._evict_cache_if_needed()
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

            # Cache the result (even from fallback)
            if nearest_node is not None:
                self._node_cache[cache_key] = (nearest_node, time.time())
                self._evict_cache_if_needed()

            return nearest_node

    def _evict_cache_if_needed(self) -> None:
        """Evict old entries if node cache exceeds max size."""
        if len(self._node_cache) <= self._max_cache_size:
            return
        # First pass: evict expired entries
        now = time.time()
        expired = [k for k, (_, ts) in self._node_cache.items()
                   if now - ts >= self._cache_ttl_seconds]
        for k in expired:
            del self._node_cache[k]
        # If still over, evict oldest 25%
        if len(self._node_cache) > self._max_cache_size:
            by_age = sorted(self._node_cache.items(), key=lambda x: x[1][1])
            to_evict = len(self._node_cache) // 4
            for k, _ in by_age[:to_evict]:
                del self._node_cache[k]

    def _generate_warnings(
        self,
        metrics: Dict[str, float],
        preferences: Optional[Dict[str, Any]] = None,
        structured: bool = True
    ) -> List[Any]:
        """
        Generate warning messages based on route metrics.

        Args:
            metrics: Path metrics dictionary
            preferences: Optional routing preferences (to customize warnings by mode)
            structured: If True, return List[RouteWarning]; if False, return List[str]

        Returns:
            List of RouteWarning objects (structured=True) or strings (structured=False)
        """
        warnings: List[RouteWarning] = []

        avg_risk = metrics.get("average_risk", 0)
        max_risk = metrics.get("max_risk", 0)
        is_fastest_mode = preferences and preferences.get("fastest")

        # Special warning for fastest mode with high risk
        if is_fastest_mode and (max_risk >= 0.5 or avg_risk >= 0.3):
            warnings.append(RouteWarning(
                severity=WarningSeverity.WARNING,
                message="Fastest mode ignores flood risk",
                details=f"Maximum flood risk: {max_risk:.0%}, Average risk: {avg_risk:.0%}. "
                        "This route may pass through flooded roads.",
                recommended_actions=[
                    "Switch to 'Balanced' or 'Safest' mode for safer routing",
                    "If proceeding, drive slowly through any standing water",
                    "Turn around if water depth exceeds vehicle bumper height",
                    "Monitor weather conditions throughout your journey"
                ]
            ))

        # CRITICAL: Impassable roads
        if max_risk >= 0.9:
            warnings.append(RouteWarning(
                severity=WarningSeverity.CRITICAL,
                message="Route contains impassable roads",
                details=f"Maximum flood risk: {max_risk:.0%}. Water depths exceed 60cm, "
                        "which is impassable for most vehicles and life-threatening.",
                recommended_actions=[
                    "DO NOT attempt this route",
                    "Consider evacuation to a nearby shelter",
                    "Wait for flood conditions to improve",
                    "Check alternative routes using 'Safest' mode",
                    "Call emergency services if stranded"
                ]
            ))
        # WARNING: High risk
        elif max_risk >= 0.7:
            warnings.append(RouteWarning(
                severity=WarningSeverity.WARNING,
                message="Route contains high-risk flood areas",
                details=f"Maximum flood risk: {max_risk:.0%}. Water depths 30-60cm "
                        "may stall vehicles and make roads dangerous.",
                recommended_actions=[
                    "Only proceed if absolutely necessary",
                    "Use a high-clearance vehicle (SUV/truck) if possible",
                    "Drive very slowly through flooded sections",
                    "Turn around immediately if water exceeds tire height",
                    "Keep windows partially open in case of emergency exit"
                ]
            ))
        # CAUTION: Moderate risk
        elif avg_risk >= 0.5 and not is_fastest_mode:
            warnings.append(RouteWarning(
                severity=WarningSeverity.CAUTION,
                message="Moderate flood risk on this route",
                details=f"Average flood risk: {avg_risk:.0%}. Some roads may have "
                        "standing water up to 30cm deep.",
                recommended_actions=[
                    "Drive slowly and maintain safe following distance",
                    "Be prepared for water on roads",
                    "Avoid driving through water if you cannot see the road",
                    "Turn on headlights for visibility"
                ]
            ))

        # INFO: Long route
        if metrics.get("total_distance", 0) > 10000:
            distance_km = metrics.get("total_distance", 0) / 1000
            warnings.append(RouteWarning(
                severity=WarningSeverity.INFO,
                message="This is a long route",
                details=f"Total distance: {distance_km:.1f} km. Plan accordingly.",
                recommended_actions=[
                    "Ensure you have sufficient fuel",
                    "Consider rest stops for long journeys",
                    "Check weather conditions along the entire route"
                ]
            ))

        # Return in requested format
        if structured:
            return warnings
        else:
            # Legacy string format for backward compatibility
            return [w.to_legacy_string() for w in warnings]

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
            "graph_loaded": bool(self.environment and self.environment.graph),
            "llm_enabled": bool(self.llm_service)
        }

    def parse_routing_request(self, user_query: str) -> Dict[str, Any]:
        """
        Parse natural language routing request into structured preferences.

        Args:
            user_query: User's request string (e.g., "I'm driving a 4x4 truck")

        Returns:
            Dict with structured preferences:
            {
                "vehicle_type": "car/suv/truck/motorcycle",
                "risk_tolerance": "low/medium/high",
                "mode": "safest/balanced/fastest",
                "avoid_floods": bool
            }
        """
        if not self.llm_service or not self.llm_service.is_available():
            logger.warning("LLM service unavailable, using default routing preferences")
            return {}

        prompt = f"""You are a Routing Assistant for Marikina City during a flood event.

User Request: "{user_query}"

TASK: Extract routing preferences.
- Vehicle Type: Determine if user has a standard car, SUV, truck, or motorcycle.
- Urgency: Is this an emergency? (implies 'fastest' mode)
- Risk Tolerance:
  - 'safest': Avoid all water (default for cars/motorcycles)
  - 'balanced': Accept minor water if route is much faster (SUVs)
  - 'fastest': Accept high risk (Emergency/Trucks only)

OUTPUT JSON:
{{
    "vehicle_type": "car/suv/truck/motorcycle",
    "mode": "safest/balanced/fastest",
    "avoid_floods": boolean (true if safest mode)
}}

Return ONLY valid JSON."""

        try:
            import json
            content = self.llm_service.text_chat(prompt)
            if not content:
                return {}

            # Parse JSON from response
            content = content.replace("```json", "").replace("```", "").strip()
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])

            return {}
        except Exception as e:
            logger.error(f"Failed to parse routing request: {e}")
            return {}

    def explain_route(self, route_result: Dict[str, Any]) -> str:
        """
        Generate a natural language explanation for the calculated route.

        Args:
            route_result: Output from calculate_route()

        Returns:
            String explanation of the route choice and risks.
        """
        if not self.llm_service or not self.llm_service.is_available():
            return "Route calculated based on current flood risks and distance."

        metrics = {
            "distance": f"{route_result['distance']:.0f}m",
            "time": f"{route_result['estimated_time']:.1f} min",
            "risk": f"{route_result['risk_level']:.2f}",
            "max_risk": f"{route_result['max_risk']:.2f}",
            "warnings_count": len(route_result.get('warnings', []))
        }

        prompt = f"""You are an Intelligent Navigation Assistant for flood-prone Marikina City.

Explain this calculated route to the user:
METRICS:
- Total Distance: {metrics['distance']}
- Estimated Time: {metrics['time']}
- Average Flood Risk: {metrics['risk']} (0.0-1.0)
- Max Risk Encountered: {metrics['max_risk']}

WARNINGS GENERATED:
{chr(10).join(str(w) for w in route_result.get('warnings', []))}

TASK:
Write a concise (1-2 sentences) explanation of why this route was chosen and what to watch out for.
- If risk is low, emphasize safety.
- If risk is high, explain why (e.g. "Shortest path but dangerous").
- Mention specific blocked areas if implied by warnings.

Output plain text only."""

        try:
            result = self.llm_service.text_chat(prompt)
            return result if result else "Route calculation complete (LLM explanation unavailable)."
        except Exception as e:
            logger.error(f"Failed to generate route explanation: {e}")
            return "Route calculation complete (LLM explanation unavailable)."
