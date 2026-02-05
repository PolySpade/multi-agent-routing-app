# filename: app/agents/evacuation_manager_agent.py

"""
Evacuation Manager Agent for Multi-Agent System for Flood Route Optimization

This module implements the EvacuationManagerAgent class, which serves as the
user interface coordinator in the MAS-FRO system. The agent handles incoming
route requests from users, coordinates with the RoutingAgent for pathfinding,
collects user feedback, and manages the feedback loop that improves system
accuracy over time.

Key Responsibilities:
- Handle user route requests
- Coordinate with RoutingAgent for optimal path calculation
- Collect and process user feedback (road status reports)
- Forward feedback to HazardAgent for graph updates
- Manage evacuation center recommendations

Author: MAS-FRO Development Team
Date: November 2025
"""

from .base_agent import BaseAgent
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING
from collections import deque
import logging
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from ..environment.graph_manager import DynamicGraphEnvironment
    from .routing_agent import RoutingAgent
    from .hazard_agent import HazardAgent

logger = logging.getLogger(__name__)


class EvacuationManagerAgent(BaseAgent):
    """
    Agent for managing user interactions and evacuation coordination.

    This agent serves as the primary interface between users and the MAS-FRO
    system. It handles route requests, manages user feedback, and coordinates
    evacuation activities. The agent implements a feedback loop where user
    reports about road conditions are used to improve the system's accuracy.

    The agent maintains a history of route requests and feedback to enable
    continuous improvement of the routing algorithm's risk assessments.

    Attributes:
        agent_id: Unique identifier for this agent instance
        environment: Reference to DynamicGraphEnvironment
        routing_agent: Reference to RoutingAgent for pathfinding
        hazard_agent: Reference to HazardAgent for feedback forwarding
        route_history: History of route requests and responses
        feedback_history: History of user feedback

    Example:
        >>> env = DynamicGraphEnvironment()
        >>> routing_agent = RoutingAgent(...)
        >>> manager = EvacuationManagerAgent("evac_mgr_001", env)
        >>> manager.set_routing_agent(routing_agent)
        >>> route = manager.handle_route_request((14.65, 121.10), (14.66, 121.11))
    """

    def __init__(
        self,
        agent_id: str,
        environment: "DynamicGraphEnvironment",
        message_queue: Optional[Any] = None
    ) -> None:
        """
        Initialize the EvacuationManagerAgent.

        Args:
            agent_id: Unique identifier for this agent
            environment: DynamicGraphEnvironment instance
            message_queue: MessageQueue for agent communication (NEW)
        """
        super().__init__(agent_id, environment)

        # Agent references (set after initialization)
        self.routing_agent: Optional["RoutingAgent"] = None
        # hazard_agent removed - now uses MessageQueue for communication

        # MessageQueue for agent communication (MAS architecture)
        self.message_queue = message_queue
        self.hazard_agent_id = "hazard_agent_001"  # Target agent ID for messages

        # Configuration
        self.max_history_size = 1000

        # Request and feedback tracking (use deque for O(1) automatic eviction)
        # Issue #15 fix: Prevents memory leaks and O(N) list slicing
        self.route_history: deque = deque(maxlen=self.max_history_size)
        self.feedback_history: deque = deque(maxlen=self.max_history_size)

        logger.info(f"{self.agent_id} initialized with MessageQueue support")

    def step(self):
        """
        Perform one step of the agent's operation.

        In each step, the agent processes any pending feedback and performs
        maintenance tasks like cleaning old history entries.
        """
        logger.debug(f"{self.agent_id} performing step at {datetime.now()}")

        # Note: History cleanup is now automatic via deque(maxlen=...)
        # No manual slicing needed - deque handles O(1) eviction

    def set_routing_agent(self, routing_agent) -> None:
        """
        Set reference to RoutingAgent.

        Args:
            routing_agent: RoutingAgent instance
        """
        self.routing_agent = routing_agent
        logger.info(f"{self.agent_id} linked to {routing_agent.agent_id}")

    # set_hazard_agent method removed - now uses MessageQueue for communication

    def handle_distress_call(
        self,
        location: Tuple[float, float],
        message: str
    ) -> Dict[str, Any]:
        """
        Handle a natural language distress call.

        Parses the message for context (injury, trapped, etc.) via RoutingAgent
        and routes to the nearest suitable evacuation center.

        Args:
            location: User coordinates
            message: Distress message (e.g., "Help! Trapped by flood")

        Returns:
            Dict with route and center info
        """
        logger.info(f"{self.agent_id} received distress call: '{message}' at {location}")

        if not self.routing_agent:
            return {
                "status": "error",
                "message": "Routing service unavailable"
            }

        # Delegate everything to RoutingAgent's smart finder
        try:
            result = self.routing_agent.find_nearest_evacuation_center(
                location=location,
                max_centers=5,
                query=message  # Pass the raw message
            )

            if result:
                return {
                    "status": "success",
                    "action": "evacuate",
                    "target_center": result["center"]["name"],
                    "route_summary": {
                        "distance": result["metrics"]["total_distance"],
                        "time_min": result["metrics"]["estimated_time"],
                        "risk": result["metrics"]["average_risk"]
                    },
                    "path": result["path"],
                    "explanation": result.get("explanation", "Proceed effectively to the nearest shelter.")
                }
            else:
                return {
                    "status": "warning",
                    "message": "No accessible evacuation centers found. Seek high ground immediately."
                }

        except Exception as e:
            logger.error(f"Distress call processing failed: {e}")
            return {
                "status": "error",
                "message": f"System error: {str(e)}"
            }

    def handle_route_request(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle a route request from a user.

        Coordinates with RoutingAgent to find the safest route from start
        to end, considering current flood conditions and user preferences.

        Args:
            start: Starting coordinates (latitude, longitude)
            end: Destination coordinates (latitude, longitude)
            preferences: Optional user preferences
                Format:
                {
                    "avoid_floods": bool,  # Prioritize flood avoidance
                    "fastest": bool,  # Prefer fastest route
                    "evacuation_center": bool  # Route to nearest shelter
                }

        Returns:
            Dict containing route information
                Format:
                {
                    "route_id": str,
                    "path": List[Tuple[float, float]],
                    "distance": float,
                    "estimated_time": float,
                    "risk_level": float,
                    "warnings": List[str],
                    "timestamp": datetime
                }
        """
        logger.info(f"{self.agent_id} received route request: {start} -> {end}")

        # Generate unique route ID
        route_id = str(uuid.uuid4())

        # Validate inputs
        if not self._validate_coordinates(start) or not self._validate_coordinates(end):
            return {
                "route_id": route_id,
                "status": "error",
                "message": "Invalid coordinates provided",
                "timestamp": datetime.now()
            }

        # Check if RoutingAgent is available
        if not self.routing_agent:
            logger.error("RoutingAgent not configured")
            return {
                "route_id": route_id,
                "status": "error",
                "message": "Routing service unavailable",
                "timestamp": datetime.now()
            }

        try:
            # Request route from RoutingAgent
            route = self._request_route_from_agent(start, end, preferences)

            # Add to history
            self.route_history.append({
                "route_id": route_id,
                "start": start,
                "end": end,
                "preferences": preferences,
                "route": route,
                "timestamp": datetime.now()
            })

            logger.info(f"Route {route_id} generated successfully")
            return route

        except Exception as e:
            logger.error(f"Failed to generate route: {e}")
            return {
                "route_id": route_id,
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now()
            }

    def collect_user_feedback(
        self,
        route_id: str,
        feedback_type: str,
        location: Optional[Tuple[float, float]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Collect user feedback about road conditions.

        Users can report:
        - Road clear (passable with no issues)
        - Road blocked (impassable due to flooding/debris)
        - Flood depth estimates
        - Traffic conditions

        Args:
            route_id: ID of the route the feedback relates to
            feedback_type: Type of feedback ("clear", "blocked", "flooded", "traffic")
            location: Optional coordinates where feedback applies
            data: Optional additional feedback data
                Format:
                {
                    "severity": float,  # 0-1 scale
                    "description": str,
                    "photo_url": str
                }

        Returns:
            True if feedback was successfully processed, False otherwise
        """
        logger.info(
            f"{self.agent_id} received feedback: {feedback_type} for route {route_id}"
        )

        # Validate feedback
        valid_types = ["clear", "blocked", "flooded", "traffic"]
        if feedback_type not in valid_types:
            logger.warning(f"Invalid feedback type: {feedback_type}")
            return False

        # Create feedback record
        feedback_record = {
            "feedback_id": str(uuid.uuid4()),
            "route_id": route_id,
            "type": feedback_type,
            "location": location,
            "data": data or {},
            "timestamp": datetime.now()
        }

        # Add to history
        self.feedback_history.append(feedback_record)

        # Forward to HazardAgent for graph updates
        self.forward_to_hazard_agent(feedback_record)

        logger.info(f"Feedback processed and forwarded to HazardAgent")
        return True

    def forward_to_hazard_agent(self, feedback: Dict[str, Any]) -> None:
        """
        Forward user feedback to HazardAgent for risk assessment updates via MessageQueue.

        Uses ACL message passing for proper MAS communication architecture.

        Args:
            feedback: Feedback record to forward
        """
        if not self.message_queue:
            logger.warning("MessageQueue not configured, feedback not forwarded")
            return

        logger.debug(
            f"{self.agent_id} forwarding feedback to HazardAgent via MessageQueue: "
            f"{feedback.get('type')}"
        )

        # Convert feedback to format HazardAgent expects (scout data format)
        scout_data_format = {
            "location": feedback.get("location"),
            "severity": feedback.get("data", {}).get("severity", 0.5),
            "report_type": feedback.get("type"),
            "confidence": 0.7,  # User feedback has moderate confidence
            "timestamp": feedback.get("timestamp"),
            "source": "user_feedback",
            "feedback_id": feedback.get("feedback_id")
        }

        # Use ACL message passing (MAS architecture)
        try:
            from ..communication.acl_protocol import ACLMessage, Performative

            # Create INFORM message with scout report batch
            message = ACLMessage(
                performative=Performative.INFORM,
                sender=self.agent_id,
                receiver=self.hazard_agent_id,
                content={
                    "scout_report_batch": [scout_data_format]
                }
            )

            # Send via MessageQueue
            self.message_queue.send_message(message)
            logger.info(
                f"Feedback forwarded successfully to {self.hazard_agent_id} via MessageQueue"
            )

        except Exception as e:
            logger.error(f"Failed to forward feedback to HazardAgent via MessageQueue: {e}")

    def find_nearest_evacuation_center(
        self,
        location: Tuple[float, float]
    ) -> Optional[Dict[str, Any]]:
        """
        Find the nearest evacuation center to a given location.

        Args:
            location: Coordinates to search from

        Returns:
            Dict with evacuation center information, or None if not found
                Format:
                {
                    "name": str,
                    "location": Tuple[float, float],
                    "distance": float,  # meters
                    "capacity": int,
                    "type": str,  # "school", "gymnasium", etc.
                    "contact": str,
                    "route": Dict  # Route information to the center
                }
        """
        logger.info(f"{self.agent_id} finding evacuation center near {location}")

        if not self.routing_agent:
            logger.error("RoutingAgent not configured")
            return None

        try:
            # Call RoutingAgent's find_nearest_evacuation_center method
            result = self.routing_agent.find_nearest_evacuation_center(
                location=location,
                max_centers=5
            )

            if result:
                logger.info(
                    f"Found evacuation center: {result.get('name')} "
                    f"at distance {result.get('distance', 0):.0f}m"
                )
                return result
            else:
                logger.warning("No evacuation centers found")
                return None

        except Exception as e:
            logger.error(f"Failed to find evacuation center: {e}")
            return None

    def get_route_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about routes and feedback.

        Returns:
            Dict containing statistics
                Format:
                {
                    "total_routes": int,
                    "total_feedback": int,
                    "feedback_by_type": Dict[str, int],
                    "average_risk_level": float
                }
        """
        feedback_by_type = {}
        for feedback in self.feedback_history:
            ftype = feedback.get("type")
            feedback_by_type[ftype] = feedback_by_type.get(ftype, 0) + 1

        return {
            "total_routes": len(self.route_history),
            "total_feedback": len(self.feedback_history),
            "feedback_by_type": feedback_by_type,
            "average_risk_level": self._calculate_average_risk()
        }

    def _request_route_from_agent(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        preferences: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Request route calculation from RoutingAgent.

        Args:
            start: Starting coordinates
            end: Ending coordinates
            preferences: User preferences

        Returns:
            Route information dict
        """
        if not self.routing_agent:
            raise ValueError("RoutingAgent not configured")

        # Direct method call to RoutingAgent's calculate_route
        # In a fully distributed system, this could use ACL messages via message queue
        route_result = self.routing_agent.calculate_route(start, end, preferences)

        # Format response to match expected structure
        return {
            "route_id": str(uuid.uuid4()),
            "path": route_result.get("path", []),
            "distance": route_result.get("distance", 0.0),
            "estimated_time": route_result.get("estimated_time", 0.0),
            "risk_level": route_result.get("risk_level", 0.0),
            "max_risk": route_result.get("max_risk", 0.0),
            "warnings": route_result.get("warnings", []),
            "timestamp": datetime.now()
        }

    def _validate_coordinates(self, coords: Tuple[float, float]) -> bool:
        """
        Validate coordinate tuple.

        Args:
            coords: Coordinates to validate (lat, lon)

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(coords, (tuple, list)) or len(coords) != 2:
            return False

        lat, lon = coords
        return -90 <= lat <= 90 and -180 <= lon <= 180

    def _calculate_average_risk(self) -> float:
        """
        Calculate average risk level from route history.

        Returns:
            Average risk level (0-1 scale)
        """
        if not self.route_history:
            return 0.0

        total_risk = sum(
            route.get("route", {}).get("risk_level", 0.0)
            for route in self.route_history
        )
        return total_risk / len(self.route_history)
