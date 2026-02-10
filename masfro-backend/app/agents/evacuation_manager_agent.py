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
- Classify distress severity via LLM
- Generate evacuation instructions via LLM

Author: MAS-FRO Development Team
Date: November 2025
"""

from .base_agent import BaseAgent
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING
from collections import deque
import logging
from datetime import datetime
import uuid

from ..communication.acl_protocol import Performative
from ..core.agent_config import get_config, EvacuationConfig, GlobalConfig
from ..core.llm_utils import parse_llm_json as _parse_llm_json

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
        route_history: History of route requests and responses
        feedback_history: History of user feedback
        distress_history: History of distress calls

    Example:
        >>> env = DynamicGraphEnvironment()
        >>> routing_agent = RoutingAgent(...)
        >>> manager = EvacuationManagerAgent("evac_mgr_001", env)
        >>> manager.set_routing_agent(routing_agent)
        >>> route = manager.handle_distress_call((14.65, 121.10), "Help!")
    """

    def __init__(
        self,
        agent_id: str,
        environment: "DynamicGraphEnvironment",
        message_queue: Optional[Any] = None,
        hazard_agent_id: str = "hazard_agent_001",
        llm_service: Optional[Any] = None,
    ) -> None:
        """
        Initialize the EvacuationManagerAgent.

        Args:
            agent_id: Unique identifier for this agent
            environment: DynamicGraphEnvironment instance
            message_queue: MessageQueue for agent communication
            hazard_agent_id: Target HazardAgent ID for MQ messages
            llm_service: LLMService instance for NL classification/generation
        """
        super().__init__(agent_id, environment)

        # Agent references (set after initialization)
        self.routing_agent: Optional["RoutingAgent"] = None

        # MessageQueue for agent communication (MAS architecture)
        self.message_queue = message_queue
        self.hazard_agent_id = hazard_agent_id

        # LLM service for distress classification and instruction generation
        self.llm_service = llm_service

        # Register with MessageQueue for receiving orchestrator requests
        if self.message_queue:
            try:
                self.message_queue.register_agent(self.agent_id)
                logger.info(f"{self.agent_id} registered with MessageQueue")
            except ValueError:
                logger.debug(f"{self.agent_id} already registered with MQ")

        # Load configuration from YAML (pattern: hazard_agent.py)
        try:
            loader = get_config()
            self._config: EvacuationConfig = loader.get_evacuation_config()
            self._global_config: GlobalConfig = loader.get_global_config()
        except Exception as e:
            logger.warning(f"Failed to load config, using defaults: {e}")
            self._config = EvacuationConfig()
            self._global_config = GlobalConfig()

        # Request, feedback, and distress tracking (deque for O(1) eviction)
        self.route_history: deque = deque(maxlen=self._config.max_route_history)
        self.feedback_history: deque = deque(maxlen=self._config.max_feedback_history)
        self.distress_history: deque = deque(maxlen=self._config.max_route_history)

        logger.info(
            f"{self.agent_id} initialized (config: history={self._config.max_route_history}, "
            f"safest_mode={self._config.always_use_safest_mode}, "
            f"llm={'yes' if self.llm_service else 'no'})"
        )

    def step(self):
        """
        Perform one step of the agent's operation.

        Processes any pending MQ requests from orchestrator, then performs
        maintenance tasks like cleaning old history entries.
        """
        # Process any orchestrator REQUEST messages first
        self._process_mq_requests()

        logger.debug(f"{self.agent_id} performing step at {datetime.now()}")

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

                if action == "handle_distress_call":
                    self._handle_distress_call_request(msg, data)
                elif action == "collect_feedback":
                    self._handle_collect_feedback_mq(msg, data)
                else:
                    logger.warning(
                        f"{self.agent_id}: unknown REQUEST action '{action}' "
                        f"from {msg.sender}"
                    )
            else:
                logger.debug(
                    f"{self.agent_id}: ignoring {msg.performative} from {msg.sender}"
                )

    def _handle_distress_call_request(self, msg, data: dict) -> None:
        """Handle handle_distress_call REQUEST from orchestrator."""
        from ..communication.acl_protocol import ACLMessage, Performative, create_inform_message

        user_location = data.get("user_location")
        message_text = data.get("message", "")
        result = {"status": "unknown"}

        try:
            if not user_location:
                result["status"] = "error"
                result["error"] = "Missing user_location"
            elif not self.routing_agent:
                result["status"] = "error"
                result["error"] = "RoutingAgent not configured"
            else:
                outcome = self.handle_distress_call(user_location, message_text)
                result["status"] = "success"
                result["outcome"] = outcome
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        logger.info(
            f"{self.agent_id}: handle_distress_call -> {result['status']}"
        )

        # Send INFORM reply to requester
        reply = create_inform_message(
            sender=self.agent_id,
            receiver=msg.sender,
            info_type="distress_call_result",
            data=result,
            conversation_id=msg.conversation_id,
            in_reply_to=msg.reply_with,
        )
        try:
            self.message_queue.send_message(reply)
        except Exception as e:
            logger.error(f"{self.agent_id}: failed to reply to {msg.sender}: {e}")

    def _handle_collect_feedback_mq(self, msg, data: dict) -> None:
        """Handle collect_feedback REQUEST from orchestrator via MQ."""
        from ..communication.acl_protocol import create_inform_message

        route_id = data.get("route_id", "")
        feedback_type = data.get("feedback_type", "")
        location = data.get("location")
        extra_data = data.get("data")
        result = {"status": "unknown"}

        try:
            if location:
                location = tuple(location)
            success = self.collect_user_feedback(route_id, feedback_type, location, extra_data)
            result = {"status": "success" if success else "failed", "accepted": success}
        except Exception as e:
            result = {"status": "error", "error": str(e)}

        reply = create_inform_message(
            sender=self.agent_id,
            receiver=msg.sender,
            info_type="feedback_result",
            data=result,
            conversation_id=msg.conversation_id,
            in_reply_to=msg.reply_with,
        )
        try:
            self.message_queue.send_message(reply)
        except Exception as e:
            logger.error(f"{self.agent_id}: failed to reply feedback to {msg.sender}: {e}")

    def set_routing_agent(self, routing_agent) -> None:
        """
        Set reference to RoutingAgent.

        Args:
            routing_agent: RoutingAgent instance
        """
        self.routing_agent = routing_agent
        logger.info(f"{self.agent_id} linked to {routing_agent.agent_id}")

    # ------------------------------------------------------------------ #
    #  LLM integration methods                                            #
    # ------------------------------------------------------------------ #

    def _classify_distress_severity(self, message: str) -> Dict[str, Any]:
        """
        Classify distress message severity via LLM.

        Returns dict with urgency level and context flags. Falls back to
        defaults if LLM is unavailable or fails.

        Args:
            message: Raw distress message text

        Returns:
            Dict with keys: urgency, injury, children, elderly, mobility, location_name
        """
        defaults = {
            "urgency": "medium",
            "injury": False,
            "children": False,
            "elderly": False,
            "mobility": False,
            "location_name": "",
        }

        if not self.llm_service or not message.strip():
            return defaults

        prompt = (
            "You are a flood emergency dispatcher for Marikina City, Philippines.\n"
            "Classify this distress message and extract context.\n\n"
            f"Message: \"{message}\"\n\n"
            "Return ONLY a JSON object with these fields:\n"
            "- urgency: one of \"critical\", \"high\", \"medium\", \"low\"\n"
            "- injury: true/false (anyone injured?)\n"
            "- children: true/false (children present?)\n"
            "- elderly: true/false (elderly present?)\n"
            "- mobility: true/false (mobility-impaired person?)\n"
            "- location_name: string (extracted location/barangay if mentioned, else empty)\n\n"
            "Rules:\n"
            "- \"critical\": life-threatening, trapped, injured, rising water\n"
            "- \"high\": imminent danger, children/elderly, water entering home\n"
            "- \"medium\": requesting evacuation, moderate flooding\n"
            "- \"low\": precautionary, asking for info\n"
        )

        try:
            raw = self.llm_service.text_chat(prompt)
            if not raw:
                return defaults

            parsed = _parse_llm_json(raw)
            if not parsed:
                return defaults

            # Merge with defaults so missing keys fall back
            for key in defaults:
                if key not in parsed:
                    parsed[key] = defaults[key]

            # Validate urgency
            if parsed["urgency"] not in ("critical", "high", "medium", "low"):
                parsed["urgency"] = "medium"

            return parsed

        except Exception as e:
            logger.warning(f"LLM distress classification failed: {e}")
            return defaults

    def _generate_evacuation_instructions(
        self, result: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """
        Generate human-friendly evacuation instructions via LLM.

        Args:
            result: Route/evacuation result dict
            context: Distress classification context

        Returns:
            Filipino-friendly instruction string, or generic fallback
        """
        fallback = (
            "Pumunta sa pinakamalapit na evacuation center. "
            "Mag-ingat sa malalim na baha at malakas na agos."
        )

        if not self.llm_service:
            return fallback

        target = result.get("target_center", "nearest evacuation center")
        distance = result.get("route_summary", {}).get("distance", 0)
        risk = result.get("route_summary", {}).get("risk", 0)
        urgency = context.get("urgency", "medium")
        has_children = context.get("children", False)
        has_elderly = context.get("elderly", False)

        prompt = (
            "You are a flood evacuation assistant for Marikina City.\n"
            "Generate 2-3 sentences of evacuation instructions in simple, "
            "clear English with Filipino terms where helpful.\n\n"
            f"Target center: {target}\n"
            f"Distance: {distance:.0f} meters\n"
            f"Route risk level: {risk:.2f}\n"
            f"Urgency: {urgency}\n"
            f"Children present: {has_children}\n"
            f"Elderly present: {has_elderly}\n\n"
            "Include safety tips relevant to the situation. "
            "Keep it concise and actionable. Return ONLY the instruction text, no JSON."
        )

        try:
            instructions = self.llm_service.text_chat(prompt)
            if instructions and len(instructions.strip()) > 10:
                return instructions.strip()
            return fallback
        except Exception as e:
            logger.warning(f"LLM instruction generation failed: {e}")
            return fallback

    # ------------------------------------------------------------------ #
    #  Core business methods                                              #
    # ------------------------------------------------------------------ #

    def handle_distress_call(
        self,
        location: Tuple[float, float],
        message: str
    ) -> Dict[str, Any]:
        """
        Handle a natural language distress call.

        1. Classify severity via LLM (graceful fallback)
        2. Force safest mode if config says so
        3. Find evacuation center via RoutingAgent
        4. Generate LLM instructions (graceful fallback)
        5. Record in distress_history

        Args:
            location: User coordinates
            message: Distress message (e.g., "Help! Trapped by flood")

        Returns:
            Dict with route and center info, enriched with urgency/instructions
        """
        if not self._validate_coordinates(location):
            error_result = {
                "status": "error",
                "message": f"Invalid coordinates: {location}. Must be within Philippines bounds."
            }
            self.distress_history.append({
                "location": location,
                "message": message,
                "result": error_result,
                "timestamp": datetime.now(),
            })
            return error_result

        logger.info(f"{self.agent_id} received distress call: '{message}' at {location}")

        if not self.routing_agent:
            error_result = {
                "status": "error",
                "message": "Routing service unavailable"
            }
            self.distress_history.append({
                "location": location,
                "message": message,
                "result": error_result,
                "timestamp": datetime.now(),
            })
            return error_result

        # Step 1: Classify distress severity via LLM
        distress_context = self._classify_distress_severity(message)
        urgency = distress_context.get("urgency", "medium")

        # Step 2: Force safest mode for distress calls if configured
        preferences = None
        if self._config.always_use_safest_mode:
            preferences = {"mode": "safest"}

        # Step 3: Find evacuation center (existing logic)
        try:
            result = self.routing_agent.find_nearest_evacuation_center(
                location=location,
                max_centers=5,
                query=message,
                preferences=preferences,
            )

            if result:
                response = {
                    "status": "success",
                    "action": "evacuate",
                    "urgency": urgency,
                    "distress_context": distress_context,
                    "target_center": result["center"]["name"],
                    "route_summary": {
                        "distance": round(result["metrics"]["total_distance"], 1),
                        "time_min": round(result["metrics"]["estimated_time"], 1),
                        "risk": round(result["metrics"]["average_risk"], 2)
                    },
                    "path": result["path"],
                    "explanation": result.get("explanation", "Proceed effectively to the nearest shelter."),
                }

                # Step 4: Generate LLM evacuation instructions
                response["instructions"] = self._generate_evacuation_instructions(
                    response, distress_context
                )

                # Step 5: Record in distress_history and route_history
                now = datetime.now()
                self.distress_history.append({
                    "location": location,
                    "message": message,
                    "urgency": urgency,
                    "distress_context": distress_context,
                    "result": response,
                    "timestamp": now,
                })
                self.route_history.append({
                    "route_id": result.get("route_id", str(uuid.uuid4())),
                    "origin": location,
                    "destination": response["target_center"],
                    "route": {
                        "risk_level": response["route_summary"]["risk"],
                        "distance": response["route_summary"]["distance"],
                        "time_min": response["route_summary"]["time_min"],
                    },
                    "source": "distress_call",
                    "urgency": urgency,
                    "timestamp": now,
                })
                return response
            else:
                warning_result = {
                    "status": "warning",
                    "urgency": urgency,
                    "distress_context": distress_context,
                    "message": "No accessible evacuation centers found. Seek high ground immediately.",
                    "instructions": "Pumunta sa mataas na lugar. Huwag tumawid sa malalim na baha.",
                }
                self.distress_history.append({
                    "location": location,
                    "message": message,
                    "urgency": urgency,
                    "result": warning_result,
                    "timestamp": datetime.now(),
                })
                return warning_result

        except Exception as e:
            logger.error(f"Distress call processing failed: {e}")
            error_result = {
                "status": "error",
                "urgency": urgency,
                "distress_context": distress_context,
                "message": f"System error: {str(e)}"
            }
            self.distress_history.append({
                "location": location,
                "message": message,
                "urgency": urgency,
                "result": error_result,
                "timestamp": datetime.now(),
            })
            return error_result

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

    def _calculate_feedback_confidence(self, feedback: Dict[str, Any]) -> float:
        """
        Calculate confidence score for user feedback based on type and evidence.

        Args:
            feedback: Feedback record dict

        Returns:
            Confidence score (0.0-1.0)
        """
        feedback_type = feedback.get("type", "")
        feedback_data = feedback.get("data", {})
        has_photo = bool(feedback_data.get("photo_url"))

        if feedback_type == "blocked":
            return 0.9 if has_photo else 0.8
        elif feedback_type == "flooded":
            has_severity = "severity" in feedback_data
            return 0.8 if has_severity else self._config.default_confidence
        elif feedback_type == "clear":
            return self._config.default_confidence
        elif feedback_type == "traffic":
            return 0.5
        else:
            return self._config.default_confidence

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

        # Variable confidence based on feedback type and evidence
        confidence = self._calculate_feedback_confidence(feedback)

        # Convert feedback to format HazardAgent expects (scout data format)
        scout_data_format = {
            "location": feedback.get("location"),
            "severity": feedback.get("data", {}).get("severity", 0.5),
            "report_type": feedback.get("type"),
            "confidence": confidence,
            "timestamp": feedback.get("timestamp"),
            "source": "user_feedback",
            "feedback_id": feedback.get("feedback_id")
        }

        # Use ACL message passing (MAS architecture)
        try:
            from ..communication.acl_protocol import ACLMessage, Performative, create_inform_message

            # Create INFORM message with scout report batch
            message = create_inform_message(
                sender=self.agent_id,
                receiver=self.hazard_agent_id,
                info_type="scout_report_batch",
                data={
                    "reports": [scout_data_format],
                    "has_coordinates": bool(scout_data_format.get("location")),
                    "report_count": 1,
                },
            )

            # Send via MessageQueue
            self.message_queue.send_message(message)
            logger.info(
                f"Feedback forwarded to {self.hazard_agent_id} via MQ "
                f"(type={feedback.get('type')}, confidence={confidence:.2f})"
            )

        except Exception as e:
            logger.error(f"Failed to forward feedback to HazardAgent via MessageQueue: {e}")

    # find_nearest_evacuation_center removed — zero external callers,
    # main.py:864 calls routing_agent directly

    def get_route_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about routes, feedback, and distress calls.

        Returns:
            Dict containing statistics
        """
        feedback_by_type = {}
        for feedback in self.feedback_history:
            ftype = feedback.get("type")
            feedback_by_type[ftype] = feedback_by_type.get(ftype, 0) + 1

        return {
            "total_routes": len(self.route_history),
            "total_feedback": len(self.feedback_history),
            "total_distress_calls": len(self.distress_history),
            "feedback_by_type": feedback_by_type,
            "average_risk_level": self._calculate_average_risk()
        }

    def _validate_coordinates(self, coords: Tuple[float, float]) -> bool:
        """
        Validate coordinate tuple against Philippines bounds.

        Uses GlobalConfig bounds (lat 4-21, lon 116-127) instead of
        global (-90 to 90, -180 to 180).

        Args:
            coords: Coordinates to validate (lat, lon)

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(coords, (tuple, list)) or len(coords) != 2:
            return False

        lat, lon = coords
        return (
            self._global_config.min_latitude <= lat <= self._global_config.max_latitude
            and self._global_config.min_longitude <= lon <= self._global_config.max_longitude
        )

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
