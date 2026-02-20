# filename: app/agents/orchestrator_agent.py

"""
Orchestrator Agent for MAS-FRO Multi-Agent System

Central coordinator that manages multi-step workflows via MessageQueue.
Uses finite state machines to track mission progress across agent interactions.
Integrates LLM for natural language interpretation and mission summarization.

This orchestrator:
- Participates in the MQ as a first-class agent
- Sends REQUEST messages and processes INFORM replies
- Tracks missions with conversation_id correlation
- Handles timeouts for unresponsive agents
- Uses LLM to interpret natural language requests into missions
- Generates human-readable summaries of mission outcomes
"""

import json
import logging
import threading
import uuid
from collections import deque
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.communication.acl_protocol import (
    ACLMessage,
    Performative,
    create_inform_message,
    create_request_message,
)
from app.communication.message_queue import MessageQueue
from app.core.agent_config import OrchestratorConfig
from app.core.llm_utils import parse_llm_json

logger = logging.getLogger(__name__)


class MissionState(str, Enum):
    """Finite state machine states for orchestrator missions."""

    PENDING = "PENDING"
    AWAITING_SCOUT = "AWAITING_SCOUT"
    AWAITING_FLOOD = "AWAITING_FLOOD"
    AWAITING_HAZARD = "AWAITING_HAZARD"
    AWAITING_ROUTING = "AWAITING_ROUTING"
    AWAITING_EVACUATION = "AWAITING_EVACUATION"
    AWAITING_RISK_QUERY = "AWAITING_RISK_QUERY"
    AWAITING_SUB_MISSION = "AWAITING_SUB_MISSION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class OrchestratorAgent(BaseAgent):
    """
    Central coordinator for the Multi-Agent System.

    Participates in the MessageQueue as a first-class agent, coordinating
    multi-step workflows via FIPA-ACL protocol. Uses finite state machines
    to track mission progress across multiple agent interactions.

    Supported mission types:
    - assess_risk: Scout -> Flood -> Hazard (sequential pipeline)
    - coordinated_evacuation: EvacuationManager handles distress call
    - route_calculation: RoutingAgent calculates a route
    - cascade_risk_update: Flood -> Hazard (data refresh pipeline)
    - multi_step: Sequential sub-missions (max 3 steps)
    """

    # Map agent roles to status method names for health reporting
    _STATUS_METHODS = {
        "scout": "get_processing_stats",
        "flood": "get_agent_stats",
        "routing": "get_statistics",
        "evacuation": "get_route_statistics",
    }

    def __init__(
        self,
        agent_id: str,
        environment,
        message_queue: MessageQueue,
        sub_agents: Dict[str, Any],
        llm_service: Optional[Any] = None,
    ) -> None:
        """
        Initialize the Orchestrator with MQ support and sub-agent references.

        Args:
            agent_id: Unique ID (e.g., "orchestrator_main")
            environment: Shared DynamicGraphEnvironment
            message_queue: System MessageQueue for ACL communication
            sub_agents: Dict of {'role': agent_instance}
            llm_service: Optional LLMService for natural language interpretation
        """
        super().__init__(agent_id, environment, message_queue=message_queue)
        self.sub_agents = sub_agents
        self.llm_service = llm_service

        # Load config from YAML
        self._config = self._load_config()

        # Mission tracking (thread-safe: accessed from MQ processing and API threads)
        # RLock allows reentrant acquisition so _advance_mission can hold the lock
        # while calling handlers that also acquire it for individual mutations
        self._missions_lock = threading.RLock()
        self._missions: Dict[str, Dict[str, Any]] = {}
        self._max_completed_history = self._config.max_completed_history
        self._completed_missions: deque = deque(maxlen=self._max_completed_history)
        self._completed_missions_index: Dict[str, Dict[str, Any]] = {}

        # Verify required agents
        required = ["scout", "routing", "flood", "evacuation", "hazard"]
        for role in required:
            if role not in sub_agents:
                logger.warning(f"Orchestrator missing '{role}' agent")

        # Conversation history for multi-turn chat
        self._chat_history: list = []
        self._max_chat_turns = self._config.max_chat_turns

        llm_status = "enabled" if self.llm_service else "disabled"
        logger.info(
            f"Orchestrator {agent_id} initialized with MQ support, "
            f"agents: {list(sub_agents.keys())}, llm={llm_status}"
        )

    def reload_config(self) -> None:
        """Hot-reload configuration from the singleton config loader."""
        self._config = self._load_config()
        self._max_chat_turns = self._config.max_chat_turns
        logger.info(f"{self.agent_id} configuration reloaded")

    def _load_config(self) -> OrchestratorConfig:
        """Load orchestrator config from YAML (always returns a valid config)."""
        try:
            from app.core.agent_config import AgentConfigLoader

            return AgentConfigLoader().get_orchestrator_config()
        except Exception as e:
            logger.warning(
                f"Failed to load orchestrator config: {e}, using defaults"
            )
            return OrchestratorConfig()

    # ---------------------------------------------------------------
    # BaseAgent interface
    # ---------------------------------------------------------------

    def step(self) -> None:
        """
        Process MQ messages and advance mission state machines.

        Called periodically by AgentLifecycleManager. Each tick:
        1. Polls all pending MQ messages and dispatches by performative
        2. Checks for timed-out missions and fails them
        """
        if self.message_queue:
            self._process_pending_messages()
        self._check_timeouts()

    # ---------------------------------------------------------------
    # MQ message processing
    # ---------------------------------------------------------------

    def _process_pending_messages(self) -> None:
        """Poll MQ and dispatch incoming messages."""
        processed = 0
        while True:
            msg = self.message_queue.receive_message(
                agent_id=self.agent_id, timeout=0.0, block=False
            )
            if msg is None:
                break
            processed += 1
            try:
                if msg.performative == Performative.INFORM:
                    self._handle_inform(msg)
                elif msg.performative == Performative.FAILURE:
                    self._handle_failure(msg)
                elif msg.performative == Performative.REFUSE:
                    self._handle_refuse(msg)
                else:
                    logger.warning(
                        f"{self.agent_id}: unhandled performative "
                        f"{msg.performative} from {msg.sender}"
                    )
            except Exception as e:
                logger.error(
                    f"{self.agent_id} error processing message from "
                    f"{msg.sender}: {e}",
                    exc_info=True,
                )
        if processed:
            logger.debug(f"{self.agent_id} processed {processed} messages")

    def _handle_inform(self, msg: ACLMessage) -> None:
        """Handle INFORM reply from a sub-agent, advancing the mission FSM."""
        conv_id = msg.conversation_id
        if not conv_id or conv_id not in self._missions:
            logger.debug(
                f"{self.agent_id}: INFORM with unknown conversation_id "
                f"{conv_id} from {msg.sender}"
            )
            return

        mission = self._missions[conv_id]
        data = msg.content.get("data", {})
        info_type = msg.content.get("info_type", "")

        # Use info_type as key when available to avoid overwriting
        # multiple responses from the same agent (e.g. hazard sends
        # both risk_update_result and location_risk_result)
        if info_type == "location_risk_result":
            result_key = "map_risk"
        else:
            result_key = msg.sender
        mission["results"][result_key] = data

        logger.info(
            f"Mission {conv_id}: received INFORM from {msg.sender} "
            f"(info_type={info_type}), state={mission['state']}"
        )
        self._advance_mission(conv_id)

    def _handle_failure(self, msg: ACLMessage) -> None:
        """Handle FAILURE from a sub-agent."""
        conv_id = msg.conversation_id
        if not conv_id or conv_id not in self._missions:
            return

        error = msg.content.get("error", "Unknown error")
        self._missions[conv_id]["results"][msg.sender] = {"error": error}
        logger.warning(
            f"Mission {conv_id}: FAILURE from {msg.sender}: {error}"
        )
        self._complete_mission(conv_id, MissionState.FAILED, error=error)

    def _handle_refuse(self, msg: ACLMessage) -> None:
        """Handle REFUSE from a sub-agent."""
        conv_id = msg.conversation_id
        if not conv_id or conv_id not in self._missions:
            return

        reason = msg.content.get("reason", "Unknown reason")
        logger.warning(
            f"Mission {conv_id}: REFUSE from {msg.sender}: {reason}"
        )
        self._complete_mission(
            conv_id,
            MissionState.FAILED,
            error=f"Refused by {msg.sender}: {reason}",
        )

    # ---------------------------------------------------------------
    # Timeout handling
    # ---------------------------------------------------------------

    def _check_timeouts(self) -> None:
        """Fail missions that have exceeded their deadline."""
        now = datetime.now()
        timed_out = []
        with self._missions_lock:
            for mid, mission in self._missions.items():
                if mission["state"] in (
                    MissionState.COMPLETED,
                    MissionState.FAILED,
                    MissionState.TIMED_OUT,
                ):
                    continue
                elapsed = (now - mission["created_at"]).total_seconds()
                if elapsed > mission["timeout_seconds"]:
                    timed_out.append((mid, mission["state"], mission["type"]))

        for mid, mstate, mtype in timed_out:
            logger.warning(
                f"Mission {mid} timed out "
                f"(state={mstate}, type={mtype})"
            )
            self._complete_mission(
                mid, MissionState.TIMED_OUT, error="Mission timed out"
            )

    # ---------------------------------------------------------------
    # Mission lifecycle
    # ---------------------------------------------------------------

    def start_mission(
        self, mission_type: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create and start a new mission.

        Args:
            mission_type: One of assess_risk, coordinated_evacuation,
                          route_calculation, cascade_risk_update
            params: Mission-specific parameters

        Returns:
            Dict with mission_id, type, state for tracking
        """
        with self._missions_lock:
            max_concurrent = self._config.max_concurrent_missions
            if len(self._missions) >= max_concurrent:
                return {
                    "status": "error",
                    "message": (
                        f"Max concurrent missions ({max_concurrent}) reached"
                    ),
                }

            mission_id = uuid.uuid4().hex[:8]
            timeout = self._get_timeout(mission_type)

            mission = {
                "id": mission_id,
                "type": mission_type,
                "state": MissionState.PENDING,
                "params": params,
                "results": {},
                "created_at": datetime.now(),
                "timeout_seconds": timeout,
                "error": None,
                "completed_at": None,
            }

            # Multi-step missions track sub-mission progress
            if mission_type == "multi_step":
                mission["steps"] = params.get("steps", [])
                mission["current_step_index"] = 0
                mission["step_mission_ids"] = []
                mission["step_results"] = []

            self._missions[mission_id] = mission

        logger.info(
            f"Mission {mission_id} created: "
            f"type={mission_type}, timeout={timeout}s"
        )

        # Kick off the first FSM step
        self._advance_mission(mission_id)

        return {
            "mission_id": mission_id,
            "type": mission_type,
            "state": mission["state"].value,
            "created_at": mission["created_at"].isoformat(),
        }

    def get_mission_status(
        self, mission_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current status of a mission (active or completed)."""
        with self._missions_lock:
            if mission_id in self._missions:
                return self._mission_to_dict(self._missions[mission_id])

        m = self._completed_missions_index.get(mission_id)
        if m:
            return self._mission_to_dict(m)

        return None

    def get_active_missions(self) -> List[Dict[str, Any]]:
        """Get list of all active missions."""
        with self._missions_lock:
            return [
                {
                    "mission_id": m["id"],
                    "type": m["type"],
                    "state": self._state_str(m["state"]),
                    "elapsed_seconds": round((
                        datetime.now() - m["created_at"]
                    ).total_seconds(), 1),
                }
                for m in self._missions.values()
            ]

    @staticmethod
    def _state_str(state) -> str:
        """Convert a MissionState (or string) to its string value."""
        return state.value if isinstance(state, MissionState) else str(state)

    def _mission_to_dict(self, m: Dict[str, Any]) -> Dict[str, Any]:
        """Convert mission dict to API-friendly format."""
        return {
            "mission_id": m["id"],
            "type": m["type"],
            "state": self._state_str(m["state"]),
            "results": m["results"],
            "error": m["error"],
            "created_at": m["created_at"].isoformat(),
            "completed_at": (
                m["completed_at"].isoformat() if m["completed_at"] else None
            ),
            "elapsed_seconds": round((
                (m["completed_at"] or datetime.now()) - m["created_at"]
            ).total_seconds(), 1),
        }

    def _complete_mission(
        self,
        mission_id: str,
        state: MissionState,
        error: Optional[str] = None,
    ) -> None:
        """Move mission to a terminal state and archive it."""
        parent_to_advance = None
        with self._missions_lock:
            mission = self._missions.get(mission_id)
            if not mission:
                return

            mission["state"] = state
            mission["completed_at"] = datetime.now()
            if error:
                mission["error"] = error

            # Archive to completed history
            # If deque is at capacity, the oldest will be evicted — remove from index
            if len(self._completed_missions) == self._completed_missions.maxlen:
                evicted = self._completed_missions[0]
                self._completed_missions_index.pop(evicted["id"], None)
            self._completed_missions.append(mission)
            self._completed_missions_index[mission["id"]] = mission

            del self._missions[mission_id]

            # Check if this sub-mission belongs to a multi_step parent
            for mid, m in self._missions.items():
                if (
                    m["type"] == "multi_step"
                    and mission_id in m.get("step_mission_ids", [])
                ):
                    step_idx = len(m["step_results"])
                    m["step_results"].append({
                        "mission_id": mission_id,
                        "type": mission["type"],
                        "state": self._state_str(state),
                        "error": error,
                    })
                    m["results"][f"step_{step_idx}"] = mission["results"]
                    parent_to_advance = mid
                    break

        logger.info(
            f"Mission {mission_id} -> {state} "
            f"(type={mission['type']}, error={error})"
        )

        # Advance the parent multi_step mission outside the lock
        if parent_to_advance:
            self._advance_mission(parent_to_advance)

    def _get_timeout(self, mission_type: str) -> float:
        """Get timeout for a mission type from config."""
        timeouts = {
            "assess_risk": self._config.assess_risk_timeout,
            "coordinated_evacuation": self._config.evacuation_timeout,
            "route_calculation": self._config.route_timeout,
            "cascade_risk_update": self._config.cascade_timeout,
            "multi_step": self._config.multi_step_timeout,
        }
        return timeouts.get(mission_type, self._config.default_timeout)

    # ---------------------------------------------------------------
    # State machine advancement
    # ---------------------------------------------------------------

    def _advance_mission(self, mission_id: str) -> None:
        """Route to the appropriate FSM handler based on mission type.

        Holds the RLock for the entire handler execution so the full
        state-machine transition is atomic. Sub-calls (e.g. _send_request,
        _complete_mission) re-acquire the same RLock without deadlocking.
        """
        handlers = {
            "assess_risk": self._advance_assess_risk,
            "coordinated_evacuation": self._advance_evacuation,
            "route_calculation": self._advance_route_calculation,
            "cascade_risk_update": self._advance_cascade_update,
            "multi_step": self._advance_multi_step,
        }

        with self._missions_lock:
            mission = self._missions.get(mission_id)
            if not mission:
                return
            mission_type = mission["type"]

            handler = handlers.get(mission_type)
            if handler:
                handler(mission)
            else:
                self._complete_mission(
                    mission_id,
                    MissionState.FAILED,
                    error=f"Unknown mission type: {mission_type}",
                )

    def _advance_assess_risk(self, mission: Dict[str, Any]) -> None:
        """
        assess_risk FSM:
        PENDING -> AWAITING_SCOUT -> AWAITING_FLOOD -> AWAITING_HAZARD
               -> AWAITING_RISK_QUERY -> COMPLETED

        If no location is provided, skips AWAITING_SCOUT and goes to AWAITING_FLOOD.
        After hazard processes data, queries current map risk at the location
        so the results include what's actually displayed on the map.
        """
        with self._missions_lock:
            mid = mission["id"]
            state = mission["state"]
            location = mission["params"].get("location")
            scout_data = mission["results"].get("scout", {})

        if state == MissionState.PENDING:
            if location:
                self._send_request(
                    "scout", "scan_location", {"location": location}, mid
                )
                with self._missions_lock:
                    mission["state"] = MissionState.AWAITING_SCOUT
            else:
                self._send_request("flood", "collect_data", {}, mid)
                with self._missions_lock:
                    mission["state"] = MissionState.AWAITING_FLOOD

        elif state == MissionState.AWAITING_SCOUT:
            self._send_request("flood", "collect_data", {}, mid)
            with self._missions_lock:
                mission["state"] = MissionState.AWAITING_FLOOD

        elif state == MissionState.AWAITING_FLOOD:
            self._send_request("hazard", "process_and_update", {}, mid)
            with self._missions_lock:
                mission["state"] = MissionState.AWAITING_HAZARD

        elif state == MissionState.AWAITING_HAZARD:
            # After hazard updates the map, query the current risk at the location
            coords = scout_data.get("coordinates")
            if coords and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                lat, lon = float(coords[0]), float(coords[1])
            elif location:
                # Fallback: use known barangay coordinates
                lat, lon = self._location_to_coords(location)
            else:
                lat, lon = None, None

            if lat is not None and lon is not None:
                self._send_request(
                    "hazard",
                    "query_risk_at_location",
                    {"lat": lat, "lon": lon, "radius_m": 500},
                    mid,
                )
                with self._missions_lock:
                    mission["state"] = MissionState.AWAITING_RISK_QUERY
            else:
                self._complete_mission(mid, MissionState.COMPLETED)

        elif state == MissionState.AWAITING_RISK_QUERY:
            self._complete_mission(mid, MissionState.COMPLETED)

    def _advance_evacuation(self, mission: Dict[str, Any]) -> None:
        """
        coordinated_evacuation FSM:
        PENDING -> AWAITING_EVACUATION -> COMPLETED
        """
        with self._missions_lock:
            mid = mission["id"]
            state = mission["state"]
            user_loc = mission["params"].get("user_location")
            message = mission["params"].get("message")

        if state == MissionState.PENDING:
            if not user_loc or not message:
                self._complete_mission(
                    mid,
                    MissionState.FAILED,
                    error="Missing 'user_location' or 'message'",
                )
                return
            self._send_request(
                "evacuation",
                "handle_distress_call",
                {"user_location": user_loc, "message": message},
                mid,
            )
            with self._missions_lock:
                mission["state"] = MissionState.AWAITING_EVACUATION

        elif state == MissionState.AWAITING_EVACUATION:
            self._complete_mission(mid, MissionState.COMPLETED)

    def _advance_route_calculation(self, mission: Dict[str, Any]) -> None:
        """
        route_calculation FSM:
        PENDING -> AWAITING_ROUTING -> COMPLETED
        """
        with self._missions_lock:
            mid = mission["id"]
            state = mission["state"]
            start = mission["params"].get("start")
            end = mission["params"].get("end")
            prefs = mission["params"].get("preferences", {})

        if state == MissionState.PENDING:
            if not start or not end:
                self._complete_mission(
                    mid,
                    MissionState.FAILED,
                    error="Missing 'start' or 'end' coordinates",
                )
                return
            self._send_request(
                "routing",
                "calculate_route",
                {"start": start, "end": end, "preferences": prefs},
                mid,
            )
            with self._missions_lock:
                mission["state"] = MissionState.AWAITING_ROUTING

        elif state == MissionState.AWAITING_ROUTING:
            self._complete_mission(mid, MissionState.COMPLETED)

    def _advance_cascade_update(self, mission: Dict[str, Any]) -> None:
        """
        cascade_risk_update FSM:
        PENDING -> AWAITING_FLOOD -> AWAITING_HAZARD -> COMPLETED
        """
        with self._missions_lock:
            mid = mission["id"]
            state = mission["state"]

        if state == MissionState.PENDING:
            self._send_request("flood", "collect_data", {}, mid)
            with self._missions_lock:
                mission["state"] = MissionState.AWAITING_FLOOD

        elif state == MissionState.AWAITING_FLOOD:
            self._send_request("hazard", "process_and_update", {}, mid)
            with self._missions_lock:
                mission["state"] = MissionState.AWAITING_HAZARD

        elif state == MissionState.AWAITING_HAZARD:
            self._complete_mission(mid, MissionState.COMPLETED)

    def _advance_multi_step(self, mission: Dict[str, Any]) -> None:
        """
        multi_step FSM:
        PENDING -> launch step 0 -> AWAITING_SUB_MISSION
        AWAITING_SUB_MISSION (step N done) -> launch step N+1 -> AWAITING_SUB_MISSION
        AWAITING_SUB_MISSION (last step done) -> COMPLETED

        Each step is a real sub-mission that runs through its own FSM.
        """
        with self._missions_lock:
            mid = mission["id"]
            state = mission["state"]
            steps = mission.get("steps", [])
            step_results = mission.get("step_results", [])
            current_idx = len(step_results)  # Next step to launch

        if state == MissionState.PENDING:
            if not steps:
                self._complete_mission(
                    mid, MissionState.FAILED, error="No steps defined"
                )
                return
            self._launch_step(mission, 0)

        elif state == MissionState.AWAITING_SUB_MISSION:
            # Check if the last sub-mission failed
            if step_results and step_results[-1].get("state") in (
                "FAILED", "TIMED_OUT"
            ):
                error_msg = step_results[-1].get("error", "Sub-mission failed")
                self._complete_mission(
                    mid, MissionState.FAILED,
                    error=f"Step {current_idx - 1} failed: {error_msg}",
                )
                return

            if current_idx >= len(steps):
                # All steps completed
                self._complete_mission(mid, MissionState.COMPLETED)
            else:
                # Launch next step
                self._launch_step(mission, current_idx)

    def _launch_step(
        self, parent_mission: Dict[str, Any], step_index: int
    ) -> None:
        """Launch a sub-mission for a multi_step parent."""
        steps = parent_mission.get("steps", [])
        if step_index >= len(steps):
            return

        step = steps[step_index]
        step_type = step.get("mission_type", "")
        step_params = step.get("params", {})

        # Fix params for this individual step
        step_params = self._fix_params(step_type, step_params)

        logger.info(
            f"Multi-step mission {parent_mission['id']}: "
            f"launching step {step_index} ({step_type})"
        )

        sub_result = self.start_mission(step_type, step_params)
        sub_mission_id = sub_result.get("mission_id")

        if sub_mission_id:
            with self._missions_lock:
                parent_mission["step_mission_ids"].append(sub_mission_id)
                parent_mission["current_step_index"] = step_index
                parent_mission["state"] = MissionState.AWAITING_SUB_MISSION
        else:
            # Sub-mission creation failed
            error = sub_result.get("message", "Failed to create sub-mission")
            self._complete_mission(
                parent_mission["id"], MissionState.FAILED,
                error=f"Step {step_index} failed to start: {error}",
            )

    # ---------------------------------------------------------------
    # MQ helpers
    # ---------------------------------------------------------------

    def _send_request(
        self,
        role: str,
        action: str,
        data: Dict[str, Any],
        conversation_id: str,
    ) -> None:
        """Send a REQUEST message to a sub-agent by role name."""
        agent_id = self._resolve_agent_id(role)
        if not agent_id:
            logger.error(
                f"Cannot send request: no agent for role '{role}'"
            )
            if conversation_id in self._missions:
                self._complete_mission(
                    conversation_id,
                    MissionState.FAILED,
                    error=f"Agent for role '{role}' not available",
                )
            return

        msg = create_request_message(
            sender=self.agent_id,
            receiver=agent_id,
            action=action,
            data=data,
            conversation_id=conversation_id,
        )

        try:
            self.message_queue.send_message(msg)
            logger.info(
                f"{self.agent_id} -> {agent_id}: REQUEST {action} "
                f"(mission={conversation_id})"
            )
        except Exception as e:
            logger.error(f"Failed to send REQUEST to {agent_id}: {e}")
            if conversation_id in self._missions:
                self._complete_mission(
                    conversation_id,
                    MissionState.FAILED,
                    error=f"Failed to send request to {role}: {e}",
                )

    def _resolve_agent_id(self, role: str) -> Optional[str]:
        """Resolve a role name to the actual agent_id."""
        agent = self.sub_agents.get(role)
        if agent:
            return agent.agent_id
        return None

    # ---------------------------------------------------------------
    # Location helpers
    # ---------------------------------------------------------------

    # Known barangay coordinates for fallback geocoding
    _BARANGAY_COORDS = {
        "tumana": (14.6608, 121.1004),
        "malanday": (14.6653, 121.1023),
        "concepcion uno": (14.6416, 121.0978),
        "concepcion dos": (14.6440, 121.0958),
        "nangka": (14.6568, 121.1107),
        "sto. nino": (14.6395, 121.0908),
        "santo nino": (14.6395, 121.0908),
        "industrial valley": (14.6332, 121.0959),
        "jesus dela pena": (14.6283, 121.0985),
        "marikina heights": (14.6350, 121.1080),
        "parang": (14.6475, 121.0955),
        "kalumpang": (14.6540, 121.0970),
        "shoe ave": (14.6380, 121.1010),
        "sta. elena": (14.6490, 121.1060),
        "santa elena": (14.6490, 121.1060),
        "barangka": (14.6445, 121.1020),
        "tañong": (14.6520, 121.0990),
        "tanong": (14.6520, 121.0990),
    }

    def _location_to_coords(
        self, location: str
    ) -> tuple:
        """
        Convert a location name to (lat, lon) using known barangay list.
        Uses scored matching to prevent false positives (e.g. "Paragua" matching "Parang").
        Returns (None, None) if not found.
        """
        loc_lower = location.lower().strip()

        # Strip common prefixes first
        for prefix in ("barangay ", "brgy. ", "brgy "):
            if loc_lower.startswith(prefix):
                loc_lower = loc_lower[len(prefix):]
                break

        # Try exact match first
        if loc_lower in self._BARANGAY_COORDS:
            return self._BARANGAY_COORDS[loc_lower]

        # Scored substring matching — require > 50% overlap
        best_score = 0.0
        best_coords = (None, None)
        for name, coords in self._BARANGAY_COORDS.items():
            if name in loc_lower or loc_lower in name:
                # Score by how much of the query the match covers
                score = len(name) / max(len(loc_lower), 1)
                if score > best_score:
                    best_score = score
                    best_coords = coords

        if best_score > self._config.location_match_threshold:
            return best_coords

        return (None, None)

    # ---------------------------------------------------------------
    # System status
    # ---------------------------------------------------------------

    def get_system_status(self) -> Dict[str, Any]:
        """Get aggregated status of all sub-agents and mission counts."""
        status = {
            "orchestrator": "online",
            "timestamp": datetime.now().isoformat(),
            "active_missions": len(self._missions),
            "completed_missions": len(self._completed_missions),
            "agents": {},
        }

        for role, agent in self.sub_agents.items():
            try:
                method_name = self._STATUS_METHODS.get(role)
                if method_name and hasattr(agent, method_name):
                    method = getattr(agent, method_name)
                    agent_status = method()
                else:
                    agent_status = {"status": "online"}
                status["agents"][role] = agent_status
            except Exception as e:
                status["agents"][role] = {
                    "status": "error",
                    "detail": str(e),
                }

        return status

    # ---------------------------------------------------------------
    # LLM-powered intelligence
    # ---------------------------------------------------------------

    _SYSTEM_PROMPT = """You are the brain of a multi-agent flood routing system EXCLUSIVELY for Marikina City, Philippines.
Your job is to interpret a user's natural language request and decide which mission to create.
You have conversation history, so you can understand follow-up messages like "now route me there" or "what about Nangka instead?".

SCOPE RESTRICTION - VERY IMPORTANT:
You ONLY handle queries related to Marikina City flood routing, risk assessment, evacuation, and navigation.
If the user asks about topics unrelated to flood routing/risk/evacuation in Marikina City (e.g., general knowledge questions, coding help, weather in other cities, math problems, jokes), you MUST respond with:
{"mission_type": "off_topic", "params": {}, "reasoning": "This query is outside my scope. I only handle flood routing, risk assessment, and evacuation for Marikina City."}

Available mission types:
1. "assess_risk" - Full risk assessment pipeline (Scout scans a location -> Flood collects data -> Hazard updates risk).
   Required params: "location" (string, a place in Marikina like "Barangay Tumana" or "J.P. Rizal Street")
   Optional: omit location to just refresh flood+hazard data.

2. "route_calculation" - Calculate a safe route between two points.
   Required params: "start" (array of [lat, lng]), "end" (array of [lat, lng])
   IMPORTANT: You MUST provide BOTH "start" AND "end" as separate coordinate arrays.
   If the user mentions two places, map the first to "start" and the second to "end".
   If you only know one location, use City Center [14.6507, 121.1029] for the other.
   Optional params: "preferences" (object with routing preferences)

3. "coordinated_evacuation" - Handle a distress call / evacuation request.
   Required params: "user_location" (array of [lat, lng]), "message" (string describing the situation)

4. "cascade_risk_update" - Refresh flood data and recalculate hazard risk scores across the map.
   No required params.

5. "needs_clarification" - The user's request is missing critical information you need.
   Required: "question" (string, a short follow-up question to ask the user)
   Use when:
   - Route requested but no start point and no map pin context
   - Ambiguous location (e.g. "Concepcion" could be Uno or Dos)
   - Evacuation requested but no location and no map pin
   DO NOT use this if you can infer from conversation history or map pin context.

6. "multi_step" - The request needs multiple sequential operations.
   Required: "steps" (array of mission objects, each with "mission_type" and "params")
   Maximum 3 steps. Order matters - earlier steps inform later ones.
   Examples:
   - "Is it safe to go from Tumana to Concepcion?" ->
     [{"mission_type": "assess_risk", "params": {"location": "Tumana"}},
      {"mission_type": "route_calculation", "params": {"start": [14.6608,121.1004], "end": [14.6416,121.0978]}}]
   - "Check risk then route me to Nangka" ->
     [{"mission_type": "assess_risk", "params": {"location": "Nangka"}},
      {"mission_type": "route_calculation", "params": {"start": ..., "end": [14.6568,121.1107]}}]

Marikina City reference coordinates:
- City center: [14.6507, 121.1029]
- Barangay Tumana: [14.6608, 121.1004]
- Barangay Malanday: [14.6653, 121.1023]
- Barangay Concepcion Uno: [14.6416, 121.0978]
- Barangay Nangka: [14.6568, 121.1107]
- Barangay Sto. Nino: [14.6395, 121.0908]
- Barangay Industrial Valley: [14.6332, 121.0959]

If the user mentions a place by name but you don't know exact coordinates, use "assess_risk" with the location name as a string.
If the user asks about flooding, risk, or danger at a location, use "assess_risk".
If the user asks to go somewhere or needs a route, use "route_calculation".
If the user is in danger or needs evacuation, use "coordinated_evacuation".
If the user asks to refresh or update data, use "cascade_risk_update".
If the user references something from a previous message (like "there", "that place", "same route"), use the conversation history to resolve what they mean.
If the user asks about safety of traveling between places, or asks to check then route, use "multi_step" to combine assess_risk and route_calculation.

ROBUSTNESS: If mission_type would be "none", "unknown", "general", or any non-standard type, use "off_topic" instead.

Respond with ONLY valid JSON (no markdown, no explanation):
{
  "mission_type": "<one of the 6 types, or off_topic>",
  "params": { ... },
  "reasoning": "<1-sentence explanation of your choice>"
}

For multi_step, respond with:
{"mission_type": "multi_step", "steps": [...], "reasoning": "..."}"""

    def interpret_request(
        self, user_message: str, user_location: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to interpret a natural language request into a mission.

        Uses multi-turn conversation history so follow-up messages
        like "now route me there" resolve correctly.

        Args:
            user_message: Natural language request from user
            user_location: Optional dict with lat/lng from the user's map pin

        Returns:
            Dict with mission_type, params, and reasoning, or error info
        """
        if not self.llm_service:
            return {
                "status": "error",
                "message": "LLM service not available for orchestrator",
            }

        if not self.llm_service.is_available():
            return {
                "status": "error",
                "message": "LLM service is not currently reachable",
            }

        try:
            # Build multi-turn messages: system + history + current user msg
            messages = [{"role": "system", "content": self._SYSTEM_PROMPT}]
            messages.extend(self._chat_history)

            # Augment user message with map location context
            if user_location and user_location.get("lat") and user_location.get("lng"):
                location_context = (
                    f"[USER CONTEXT: My current location on the map is at "
                    f"[{user_location['lat']}, {user_location['lng']}]. "
                    f"Use this as 'start' for route_calculation if I don't specify a start point.]"
                )
            else:
                location_context = (
                    "[USER CONTEXT: I have not set a location pin on the map. "
                    "If I ask for a route and I specify both start and end locations in my message, "
                    "proceed normally. But if I only mention a destination without a start point, "
                    "use needs_clarification to ask where I want to start from, "
                    "or suggest I set my location pin on the map.]"
                )
            augmented_message = f"{location_context}\n\n{user_message}"
            messages.append({"role": "user", "content": augmented_message})

            raw_response = self.llm_service.text_chat_multi(messages)

            if not raw_response:
                return {
                    "status": "error",
                    "message": "LLM returned empty response",
                }

            # Parse the JSON response
            parsed = parse_llm_json(raw_response)
            if not parsed:
                logger.warning(
                    f"LLM returned unparseable response: {raw_response[:200]}"
                )
                return {
                    "status": "error",
                    "message": "LLM response was not valid JSON",
                    "raw_response": raw_response[:500],
                }

            mission_type = parsed.get("mission_type")

            # Handle off-topic rejection
            if mission_type == "off_topic":
                reasoning = parsed.get("reasoning", "Query outside scope.")
                # Still save to history so LLM remembers the exchange
                self._append_to_history(user_message, raw_response)
                return {
                    "status": "off_topic",
                    "message": reasoning,
                }

            # Handle clarification requests
            if mission_type == "needs_clarification":
                question = parsed.get("question", "Could you provide more details?")
                self._append_to_history(user_message, raw_response)
                return {
                    "status": "needs_clarification",
                    "message": question,
                    "reasoning": parsed.get("reasoning", ""),
                }

            # Handle multi-step missions
            if mission_type == "multi_step":
                steps = parsed.get("steps", [])
                if not steps or not isinstance(steps, list):
                    self._append_to_history(user_message, raw_response)
                    return {
                        "status": "off_topic",
                        "message": "I couldn't break that request into steps. Could you rephrase?",
                    }
                steps = steps[:3]  # Cap at 3 steps
                self._append_to_history(user_message, raw_response)
                return {
                    "status": "ok",
                    "mission_type": "multi_step",
                    "params": {"steps": steps},
                    "reasoning": parsed.get("reasoning", ""),
                }

            valid_types = {
                "assess_risk",
                "coordinated_evacuation",
                "route_calculation",
                "cascade_risk_update",
            }
            if mission_type not in valid_types:
                # Normalize unknown types to off_topic instead of erroring
                logger.warning(
                    f"LLM returned unknown mission type '{mission_type}', "
                    f"normalizing to off_topic"
                )
                self._append_to_history(user_message, raw_response)
                reasoning = parsed.get("reasoning", "I'm not sure how to handle that request.")
                return {
                    "status": "off_topic",
                    "message": reasoning,
                }

            # Save successful exchange to history
            self._append_to_history(user_message, raw_response)

            logger.info(
                f"LLM interpreted request as {mission_type}: "
                f"{parsed.get('reasoning', 'no reasoning')}"
            )

            return {
                "status": "ok",
                "mission_type": mission_type,
                "params": parsed.get("params", {}),
                "reasoning": parsed.get("reasoning", ""),
            }

        except Exception as e:
            logger.error(f"LLM interpret_request failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def _append_to_history(self, user_msg: str, assistant_msg: str) -> None:
        """Append a user/assistant exchange to chat history, capping at max turns."""
        self._chat_history.append({"role": "user", "content": user_msg})
        self._chat_history.append({"role": "assistant", "content": assistant_msg})
        # Cap: each turn = 2 messages, keep last N turns
        max_messages = self._max_chat_turns * 2
        if len(self._chat_history) > max_messages:
            self._chat_history = self._chat_history[-max_messages:]

    def clear_chat_history(self) -> None:
        """Clear the conversation history."""
        self._chat_history.clear()
        logger.info("Orchestrator chat history cleared")

    _SUMMARIZE_PROMPT = """You are the AI assistant for a flood routing system in Marikina City.
Write a SHORT, friendly 2-3 sentence summary of this mission result for the user.

Rules:
- For routes: mention distance, estimated time, risk level, and any warnings about impassable or dangerous roads.
- For risk assessments: state the risk level and key findings.
- For evacuations: mention the evacuation center and route details.
- If the mission failed or timed out, explain simply what went wrong.
- If there are warnings about impassable roads or high flood risk, prominently warn the user.
- If map_risk data is present, mention the current risk level on the road.
- Do NOT describe JSON structure or explain what fields mean. Just give the user useful information.
- Keep it conversational and concise, like a helpful navigation assistant.

Mission data:
"""

    _SUMMARIZE_MULTI_STEP_PROMPT = """You are the AI assistant for a flood routing system in Marikina City.
The user's request required multiple steps. Summarize ALL step results together
as a coherent 3-5 sentence response combining risk assessment, routing, and/or
evacuation findings. Keep it conversational, like a helpful navigation assistant.

Rules:
- Combine findings from all steps into one unified answer.
- For risk + route combos: lead with the risk situation, then describe the route.
- Mention specific numbers: distance, risk levels, warnings.
- If any step failed, mention what went wrong but still summarize what succeeded.
- Do NOT describe JSON structure. Just give the user useful information.

Multi-step mission data:
"""

    def summarize_mission(self, mission_id: str) -> Dict[str, Any]:
        """
        Use LLM to generate a human-readable summary of a mission.

        Args:
            mission_id: The mission to summarize

        Returns:
            Dict with summary text or error info
        """
        mission_data = self.get_mission_status(mission_id)
        if not mission_data:
            return {"status": "error", "message": "Mission not found"}

        if not self.llm_service or not self.llm_service.is_available():
            # Fallback: return structured data without LLM summary
            return {
                "status": "ok",
                "summary": self._fallback_summary(mission_data),
                "mission": mission_data,
                "llm_used": False,
            }

        try:
            # Trim large path arrays to avoid flooding the LLM with coordinates
            trimmed = json.loads(json.dumps(mission_data, default=str))
            for agent_key, agent_val in (trimmed.get("results") or {}).items():
                if isinstance(agent_val, dict):
                    route = agent_val.get("route", agent_val)
                    if isinstance(route, dict) and isinstance(route.get("path"), list):
                        path = route["path"]
                        route["path"] = f"[{len(path)} coordinate points]"

            # Choose prompt based on mission type
            if mission_data.get("type") == "multi_step":
                base_prompt = self._SUMMARIZE_MULTI_STEP_PROMPT
            else:
                base_prompt = self._SUMMARIZE_PROMPT
            prompt = base_prompt + json.dumps(trimmed, indent=2)
            raw_response = self.llm_service.text_chat(prompt)

            if raw_response:
                return {
                    "status": "ok",
                    "summary": raw_response,
                    "mission": mission_data,
                    "llm_used": True,
                }
            else:
                return {
                    "status": "ok",
                    "summary": self._fallback_summary(mission_data),
                    "mission": mission_data,
                    "llm_used": False,
                }

        except Exception as e:
            logger.error(f"LLM summarize_mission failed: {e}")
            return {
                "status": "ok",
                "summary": self._fallback_summary(mission_data),
                "mission": mission_data,
                "llm_used": False,
            }

    def chat_and_execute(
        self, user_message: str, user_location: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        End-to-end: interpret user message via LLM, create mission, return tracking info.

        Args:
            user_message: Natural language request
            user_location: Optional dict with lat/lng from the user's map pin

        Returns:
            Dict with interpretation, mission creation result, and reasoning
        """
        interpretation = self.interpret_request(user_message, user_location=user_location)

        if interpretation.get("status") == "off_topic":
            return {
                "status": "off_topic",
                "interpretation": interpretation,
                "mission": None,
            }

        if interpretation.get("status") == "needs_clarification":
            return {
                "status": "needs_clarification",
                "interpretation": interpretation,
                "mission": None,
                "message": interpretation.get("message", "Could you provide more details?"),
            }

        if interpretation.get("status") != "ok":
            return {
                "status": "error",
                "interpretation": interpretation,
                "mission": None,
            }

        # Fix common LLM param formatting issues
        # Skip _fix_params for multi_step — each sub-step gets fixed when launched
        if interpretation["mission_type"] == "multi_step":
            params = interpretation["params"]
        else:
            params = self._fix_params(
                interpretation["mission_type"],
                interpretation["params"],
                user_location=user_location,
            )
        interpretation["params"] = params

        mission_result = self.start_mission(
            interpretation["mission_type"], params
        )

        return {
            "status": "ok",
            "interpretation": {
                "mission_type": interpretation["mission_type"],
                "params": params,
                "reasoning": interpretation.get("reasoning", ""),
            },
            "mission": mission_result,
        }

    @staticmethod
    def _fix_params(
        mission_type: str,
        params: Dict[str, Any],
        user_location: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Fix common LLM formatting issues in mission params."""
        if mission_type == "route_calculation":
            for key in ("start", "end"):
                val = params.get(key)
                # Parse string coords like "[14.65, 121.10]"
                if isinstance(val, str):
                    try:
                        val = json.loads(val)
                        params[key] = val
                    except (json.JSONDecodeError, ValueError):
                        pass
                # Unwrap nested arrays like [[lat,lng],[lat,lng]]
                if isinstance(val, list) and len(val) > 0:
                    if isinstance(val[0], list):
                        params[key] = val[0] if key == "start" else val[-1]

            # If start == end, check alternate key names
            if params.get("start") == params.get("end"):
                origin = params.pop("origin", None)
                dest = params.pop("destination", None)
                if origin:
                    params["start"] = origin
                if dest:
                    params["end"] = dest

            # Fallback: if start or end still missing, use user location or city center
            city_center = [14.6507, 121.1029]
            if not params.get("start"):
                if user_location and user_location.get("lat") and user_location.get("lng"):
                    params["start"] = [user_location["lat"], user_location["lng"]]
                    logger.info("Using user map location as route start point")
                else:
                    params["start"] = city_center
                    logger.warning(
                        "No start location provided and no user location set — "
                        "defaulting to Marikina city center"
                    )
            if not params.get("end"):
                params["end"] = city_center
                logger.warning(
                    "No end location provided — defaulting to Marikina city center"
                )

        elif mission_type == "coordinated_evacuation":
            loc = params.get("user_location")
            if isinstance(loc, str):
                try:
                    loc = json.loads(loc)
                    params["user_location"] = loc
                except (json.JSONDecodeError, ValueError):
                    pass
            if isinstance(loc, list) and len(loc) > 0 and isinstance(loc[0], list):
                params["user_location"] = loc[0]

        return params

    @staticmethod
    def _fallback_summary(mission_data: Dict[str, Any]) -> str:
        """Generate a basic summary without LLM."""
        state = mission_data.get("state", "unknown")
        mtype = mission_data.get("type", "unknown")
        elapsed = mission_data.get("elapsed_seconds", 0)
        results = mission_data.get("results", {})

        if state == "COMPLETED":
            summary = (
                f"Mission '{mtype}' completed successfully "
                f"in {elapsed:.1f} seconds."
            )
            # Include map risk data if available
            map_risk = results.get("map_risk", {})
            if map_risk and map_risk.get("status") == "ok":
                risk_level = map_risk.get("risk_level", "unknown")
                avg_risk = map_risk.get("avg_risk", 0)
                max_risk = map_risk.get("max_risk", 0)
                high = map_risk.get("high_risk_edges", 0)
                impassable = map_risk.get("impassable_edges", 0)
                summary += (
                    f" Current map risk: {risk_level} "
                    f"(avg={avg_risk:.2f}, max={max_risk:.2f}, "
                    f"{high} high-risk edges, {impassable} impassable)."
                )
            return summary
        elif state in ("FAILED", "TIMED_OUT"):
            error = mission_data.get("error", "unknown error")
            return f"Mission '{mtype}' {state.lower()}: {error}"
        else:
            return f"Mission '{mtype}' is in progress (state: {state})."
