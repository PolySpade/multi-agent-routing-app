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
        environment: "DynamicGraphEnvironment"
    ) -> None:
        """
        Initialize the EvacuationManagerAgent.

        Args:
            agent_id: Unique identifier for this agent
            environment: DynamicGraphEnvironment instance
        """
        super().__init__(agent_id, environment)

        # Agent references (set after initialization)
        self.routing_agent: Optional["RoutingAgent"] = None
        self.hazard_agent: Optional["HazardAgent"] = None

        # Request and feedback tracking
        self.route_history: List[Dict[str, Any]] = []
        self.feedback_history: List[Dict[str, Any]] = []

        # Configuration
        self.max_history_size = 1000

        logger.info(f"{self.agent_id} initialized")

    def step(self):
        """
        Perform one step of the agent's operation.

        In each step, the agent processes any pending feedback and performs
        maintenance tasks like cleaning old history entries.
        """
        logger.debug(f"{self.agent_id} performing step at {datetime.now()}")

        # Maintenance: Clean old history if needed
        if len(self.route_history) > self.max_history_size:
            self.route_history = self.route_history[-self.max_history_size:]

        if len(self.feedback_history) > self.max_history_size:
            self.feedback_history = self.feedback_history[-self.max_history_size:]

    def set_routing_agent(self, routing_agent) -> None:
        """
        Set reference to RoutingAgent.

        Args:
            routing_agent: RoutingAgent instance
        """
        self.routing_agent = routing_agent
        logger.info(f"{self.agent_id} linked to {routing_agent.agent_id}")

    def set_hazard_agent(self, hazard_agent) -> None:
        """
        Set reference to HazardAgent.

        Args:
            hazard_agent: HazardAgent instance
        """
        self.hazard_agent = hazard_agent
        logger.info(f"{self.agent_id} linked to {hazard_agent.agent_id}")

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
            # TODO: Implement actual agent communication via ACL
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
        Forward user feedback to HazardAgent for risk assessment updates.

        Args:
            feedback: Feedback record to forward
        """
        if not self.hazard_agent:
            logger.warning("HazardAgent not configured, feedback not forwarded")
            return

        logger.debug(
            f"{self.agent_id} forwarding feedback to HazardAgent: "
            f"{feedback.get('type')}"
        )

        # TODO: Implement ACL message passing
        # Example:
        # message = create_inform_message(
        #     sender=self.agent_id,
        #     receiver=self.hazard_agent.agent_id,
        #     info_type="user_feedback",
        #     data=feedback
        # )
        # message_queue.send_message(message)

        # Placeholder: Convert feedback to format HazardAgent expects
        scout_data_format = {
            "location": feedback.get("location"),
            "severity": feedback.get("data", {}).get("severity", 0.5),
            "report_type": feedback.get("type"),
            "confidence": 0.7,  # User feedback has moderate confidence
            "timestamp": feedback.get("timestamp")
        }

        # self.hazard_agent.process_scout_data([scout_data_format])

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
                    "contact": str
                }
        """
        logger.info(f"{self.agent_id} finding evacuation center near {location}")

        # TODO: Implement actual evacuation center lookup
        # This would query the RoutingAgent's evacuation center database

        # Placeholder response
        return {
            "name": "Marikina Elementary School",
            "location": (14.6507, 121.1029),
            "distance": 500.0,
            "capacity": 200,
            "type": "school",
            "contact": "+63-2-8941-6754"
        }

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
        # TODO: Implement actual ACL communication with RoutingAgent

        # Placeholder: Direct method call
        # path = self.routing_agent.find_safest_route(start, end)

        # For now, return a simulated route
        return {
            "route_id": str(uuid.uuid4()),
            "path": [start, end],  # Simplified
            "distance": 1500.0,
            "estimated_time": 10.0,
            "risk_level": 0.3,
            "warnings": ["Minor flooding reported on J.P. Rizal Avenue"],
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
