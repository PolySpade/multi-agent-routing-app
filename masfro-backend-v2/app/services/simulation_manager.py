"""
Tick-Based Simulation Manager Service

Manages the simulation state and orchestrates multi-agent execution using
a tick-based synchronization pattern. This ensures agents execute in a
deterministic order with proper data flow and eliminates race conditions.

Architecture:
    - Tick-based loop with ordered agent execution
    - Shared data bus for inter-agent communication
    - Time step management for GeoTIFF scenario synchronization
    - Thread-safe graph updates

Author: MAS-FRO Development Team
Date: November 2025
"""

import json
import asyncio
from typing import Optional, Dict, Any, Literal, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
from threading import Lock
from pathlib import Path

logger = logging.getLogger(__name__)


class SimulationState(str, Enum):
    """Simulation state enumeration."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class SimulationMode(str, Enum):
    """Simulation flood scenario modes."""
    LIGHT = "light"   # 2-year return period (rr01)
    MEDIUM = "medium" # 5-year return period (rr02)
    HEAVY = "heavy"   # 25-year return period (rr04)


# Mapping from mode to GeoTIFF return period
MODE_TO_RETURN_PERIOD = {
    SimulationMode.LIGHT: "rr01",
    SimulationMode.MEDIUM: "rr02",
    SimulationMode.HEAVY: "rr04"
}


class SimulationManager:
    """
    Manages simulation lifecycle with tick-based synchronization.

    This class orchestrates all agents in the MAS-FRO system using a
    tick-based execution pattern. Each tick represents a time step in
    the simulation where:
    1. Data collection agents (FloodAgent, ScoutAgent) gather new data
    2. HazardAgent fuses data and updates the graph
    3. EvacuationManagerAgent processes route requests

    This ordering ensures the graph is always updated before routing
    calculations, preventing race conditions and ensuring consistency.

    Attributes:
        state: Current simulation state (stopped/running/paused)
        mode: Current flood scenario mode
        current_time_step: Current simulation time (1-18 for GeoTIFF)
        shared_data_bus: Dict for agent data exchange
        agents: Dict of agent references
    """

    def __init__(self):
        """Initialize simulation manager."""
        self._state: SimulationState = SimulationState.STOPPED
        self._mode: SimulationMode = SimulationMode.LIGHT
        self._started_at: Optional[datetime] = None
        self._paused_at: Optional[datetime] = None
        self._total_runtime_seconds: float = 0.0
        
        # Scenario-based simulation attributes
        self._scenario_data: Optional[Dict[str, Any]] = None
        self._event_queue: List[Dict[str, Any]] = []
        self._simulation_clock: float = 0.0
        self._last_tick_time: Optional[datetime] = None
        self._tick_loop_task: Optional[asyncio.Task] = None

        # Tick-based simulation state
        self.current_time_step: int = 1  # GeoTIFF time step (1-18 hours)
        self.tick_count: int = 0
        self.shared_data_bus: Dict[str, Any] = {
            "flood_data": {},
            "scout_data": [],
            "graph_updated": False,
            "pending_routes": []
        }

        # Agent references (set via dependency injection)
        self.flood_agent = None
        self.scout_agent = None
        self.hazard_agent = None
        self.routing_agent = None
        self.evacuation_manager = None
        self.environment = None

        # Thread safety
        self._lock = Lock()

        logger.info("SimulationManager initialized (tick-based architecture)")

    @property
    def state(self) -> SimulationState:
        """Get current simulation state."""
        return self._state

    @property
    def mode(self) -> SimulationMode:
        """Get current simulation mode."""
        return self._mode

    @property
    def is_running(self) -> bool:
        """Check if simulation is currently running."""
        return self._state == SimulationState.RUNNING

    @property
    def is_stopped(self) -> bool:
        """Check if simulation is stopped."""
        return self._state == SimulationState.STOPPED

    @property
    def is_paused(self) -> bool:
        """Check if simulation is paused."""
        return self._state == SimulationState.PAUSED

    def set_agents(
        self,
        flood_agent=None,
        scout_agent=None,
        hazard_agent=None,
        routing_agent=None,
        evacuation_manager=None,
        environment=None,
        ws_manager=None
    ) -> None:
        """
        Set agent references for orchestration.

        Args:
            flood_agent: FloodAgent instance
            scout_agent: ScoutAgent instance
            hazard_agent: HazardAgent instance
            routing_agent: RoutingAgent instance
            evacuation_manager: EvacuationManagerAgent instance
            environment: DynamicGraphEnvironment instance
            ws_manager: WebSocket ConnectionManager instance
        """
        self.flood_agent = flood_agent
        self.scout_agent = scout_agent
        self.hazard_agent = hazard_agent
        self.routing_agent = routing_agent
        self.evacuation_manager = evacuation_manager
        self.environment = environment
        self.ws_manager = ws_manager

        logger.info(
            f"SimulationManager configured with agents: "
            f"flood={flood_agent is not None}, "
            f"scout={scout_agent is not None}, "
            f"hazard={hazard_agent is not None}, "
            f"routing={routing_agent is not None}, "
            f"evacuation={evacuation_manager is not None}"
        )

    async def start(self, mode: str = "light") -> Dict[str, Any]:
        """
        Start the simulation (async).

        Args:
            mode: Simulation mode (light, medium, heavy)

        Returns:
            Dictionary with start result and metadata

        Raises:
            ValueError: If simulation is already running
        """
        if self._state == SimulationState.RUNNING:
            raise ValueError("Simulation is already running")

        # Validate mode
        try:
            self._mode = SimulationMode(mode.lower())
        except ValueError:
            raise ValueError(
                f"Invalid simulation mode: {mode}. "
                f"Must be light, medium, or heavy"
            )

        # Load scenario data
        self._load_scenario(self._mode)

        # Update state
        previous_state = self._state
        self._state = SimulationState.RUNNING

        if previous_state == SimulationState.STOPPED:
            self._started_at = datetime.now()
            self._simulation_clock = 0.0
            self.tick_count = 0
            self.current_time_step = 1

        self._last_tick_time = datetime.now()

        # Reset shared data bus
        self.shared_data_bus = {
            "flood_data": {},
            "scout_data": [],
            "graph_updated": False,
            "pending_routes": []
        }

        # Configure HazardAgent with GeoTIFF scenario based on mode
        if self.hazard_agent:
            return_period = MODE_TO_RETURN_PERIOD[self._mode]
            self.hazard_agent.set_flood_scenario(
                return_period=return_period,
                time_step=self.current_time_step
            )
            logger.info(
                f"HazardAgent configured: {return_period}, "
                f"time_step={self.current_time_step}"
            )

        # Start the simulation loop as a background task
        self._tick_loop_task = asyncio.create_task(self._simulation_loop())

        logger.info(
            f"Simulation STARTED - Mode: {self._mode.value.upper()}, "
            f"Previous state: {previous_state.value}"
        )

        return {
            "status": "success",
            "message": f"Simulation started in {self._mode.value} mode",
            "state": self._state.value,
            "mode": self._mode.value,
            "time_step": self.current_time_step,
            "return_period": MODE_TO_RETURN_PERIOD[self._mode],
            "started_at": self._started_at.isoformat(),
            "previous_state": previous_state.value
        }

    async def stop(self) -> Dict[str, Any]:
        """
        Stop (pause) the simulation (async).

        Returns:
            Dictionary with stop result and metadata

        Raises:
            ValueError: If simulation is not running
        """
        if self._state != SimulationState.RUNNING:
            raise ValueError("Simulation is not running")

        # Stop the simulation loop
        if self._tick_loop_task:
            self._tick_loop_task.cancel()
            try:
                await self._tick_loop_task
            except asyncio.CancelledError:
                pass
            self._tick_loop_task = None

        # Update runtime
        if self._last_tick_time:
            runtime = (datetime.now() - self._last_tick_time).total_seconds()
            self._total_runtime_seconds += runtime

        # Update state
        self._state = SimulationState.PAUSED
        self._paused_at = datetime.now()

        logger.info(
            f"Simulation STOPPED (paused) - "
            f"Total runtime: {self._total_runtime_seconds:.2f}s, "
            f"Ticks: {self.tick_count}, "
            f"Time step: {self.current_time_step}"
        )

        return {
            "status": "success",
            "message": "Simulation stopped (paused)",
            "state": self._state.value,
            "mode": self._mode.value,
            "paused_at": self._paused_at.isoformat(),
            "total_runtime_seconds": round(self._total_runtime_seconds, 2),
            "tick_count": self.tick_count,
            "time_step": self.current_time_step
        }

    async def reset(self) -> Dict[str, Any]:
        """
        Reset the simulation to initial state (async).

        Clears all simulation data, resets state to stopped, and
        clears runtime counters. Also resets the graph edges.

        Returns:
            Dictionary with reset result and metadata
        """
        if self._tick_loop_task:
            self._tick_loop_task.cancel()
            try:
                await self._tick_loop_task
            except asyncio.CancelledError:
                pass
            self._tick_loop_task = None

        previous_state = self._state
        previous_mode = self._mode
        previous_runtime = self._total_runtime_seconds
        previous_ticks = self.tick_count

        # Reset all state
        self._state = SimulationState.STOPPED
        self._mode = SimulationMode.LIGHT
        self._started_at = None
        self._paused_at = None
        self._total_runtime_seconds = 0.0
        self._scenario_data = None
        self._event_queue = []
        self._simulation_clock = 0.0
        self.tick_count = 0
        self.current_time_step = 1

        # Reset shared data bus
        self.shared_data_bus = {
            "flood_data": {},
            "scout_data": [],
            "graph_updated": False,
            "pending_routes": []
        }

        # Clear HazardAgent caches (accumulated scout/flood data)
        if self.hazard_agent:
            self.hazard_agent.clear_caches()
            logger.info("HazardAgent caches cleared")

        # Reset graph edges to baseline (risk = 0.0)
        if self.environment and self.environment.graph:
            edge_count = 0
            for u, v, key in self.environment.graph.edges(keys=True):
                self.environment.graph[u][v][key]["risk_score"] = 0.0
                edge_count += 1
            logger.info(f"Reset {edge_count} edges to baseline risk")

        # Reset evacuation center occupancy
        try:
            from app.services.evacuation_service import get_evacuation_service
            evacuation_service = get_evacuation_service()
            evacuation_service.reset_all_occupancy()
            logger.info("Evacuation center occupancy reset to 0")
        except Exception as e:
            logger.error(f"Failed to reset evacuation centers: {e}")

        logger.info(
            f"Simulation RESET - Previous state: {previous_state.value}, "
            f"Previous mode: {previous_mode.value}, "
            f"Previous runtime: {previous_runtime:.2f}s, "
            f"Previous ticks: {previous_ticks}"
        )

        return {
            "status": "success",
            "message": "Simulation reset to initial state",
            "state": self._state.value,
            "mode": self._mode.value,
            "previous_state": previous_state.value,
            "previous_mode": previous_mode.value,
            "previous_runtime_seconds": round(previous_runtime, 2),
            "previous_ticks": previous_ticks,
            "reset_at": datetime.now().isoformat()
        }

    def _load_scenario(self, mode: SimulationMode):
        """Load the simulation scenario file for the given mode."""
        scenario_file = Path(__file__).parent.parent / "data" / "simulation_scenarios" / f"{mode.value}_scenario.csv"
        if not scenario_file.exists():
            logger.error(f"Scenario file not found: {scenario_file}")
            self._scenario_data = {"events": []}
            self._event_queue = []
            return

        import csv
        
        events = []
        with open(scenario_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    payload = json.loads(row['payload'])
                    events.append({
                        "time_offset": int(row['time_offset']),
                        "agent": row['agent'],
                        "payload": payload
                    })
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON payload in {scenario_file} at row {reader.line_num}: {e}")
                except KeyError as e:
                    logger.error(f"Missing column in {scenario_file} at row {reader.line_num}: {e}")

        self._scenario_data = {"name": f"{mode.value.capitalize()} Flood Scenario (from CSV)", "events": events}
        
        # Sort events by time_offset and populate the event queue
        self._event_queue = sorted(events, key=lambda e: e["time_offset"])
        logger.info(f"Loaded scenario '{self._scenario_data.get('name')}' with {len(self._event_queue)} events.")

    async def _simulation_loop(self):
        """The main simulation loop that runs as a background task."""
        while self._state == SimulationState.RUNNING:
            await self.run_tick()
            if self.ws_manager:
                await self.ws_manager.broadcast({
                    "type": "simulation_state",
                    "event": "tick",
                    "data": self.get_status(),
                    "timestamp": datetime.now().isoformat()
                })
            await asyncio.sleep(1) # Tick every second

    async def run_tick(self, time_step: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute one simulation tick with ordered agent execution.

        Execution order:
        1. Collection Phase: FloodAgent and ScoutAgent collect data
        2. Fusion Phase: HazardAgent fuses data and updates graph
        3. Routing Phase: EvacuationManager processes route requests
        4. Evacuation Update Phase: Update evacuation center occupancy
        5. Time Step Advancement

        Args:
            time_step: Optional explicit time step (1-18). If None, auto-increment.

        Returns:
            Dict with tick execution results

        Raises:
            ValueError: If simulation is not running
        """
        if self._state != SimulationState.RUNNING:
            raise ValueError(
                "Cannot run tick: simulation is not running. "
                f"Current state: {self._state.value}"
            )

        # Update simulation clock
        now = datetime.now()
        if self._last_tick_time:
            delta = (now - self._last_tick_time).total_seconds()
            self._simulation_clock += delta
        self._last_tick_time = now

        # Update time step
        # if time_step is not None:
        #     if not 1 <= time_step <= 18:
        #         raise ValueError(
        #             f"Invalid time_step {time_step}. Must be between 1 and 18"
        #         )
        #     self.current_time_step = time_step
        # else:
        #     # Auto-increment, wrap around at 18
        #     self.current_time_step = (self.current_time_step % 18) + 1

        self.tick_count += 1

        logger.info(
            f"=== TICK {self.tick_count} START === "
            f"Clock: {self._simulation_clock:.2f}s, "
            f"Time step: {self.current_time_step}/18, "
            f"Mode: {self._mode.value}"
        )

        tick_result = {
            "tick": self.tick_count,
            "time_step": self.current_time_step,
            "mode": self._mode.value,
            "phases": {}
        }

        # Acquire lock for thread-safe execution
        with self._lock:
            # === PHASE 1: DATA COLLECTION ===
            logger.info("--- Phase 1: Data Collection ---")
            collection_result = self._run_collection_phase()
            tick_result["phases"]["collection"] = collection_result

            # === PHASE 2: DATA FUSION & GRAPH UPDATE ===
            logger.info("--- Phase 2: Data Fusion & Graph Update ---")
            fusion_result = await self._run_fusion_phase()
            tick_result["phases"]["fusion"] = fusion_result

            # === PHASE 3: ROUTING ===
            logger.info("--- Phase 3: Routing ---")
            routing_result = self._run_routing_phase()
            tick_result["phases"]["routing"] = routing_result

            # === PHASE 4: EVACUATION CENTER UPDATE ===
            logger.info("--- Phase 4: Evacuation Center Update ---")
            evacuation_result = self._run_evacuation_update_phase()
            tick_result["phases"]["evacuation"] = evacuation_result

            # === PHASE 5: TIME ADVANCEMENT ===
            logger.info("--- Phase 5: Time Advancement ---")
            advancement_result = self._run_advancement_phase()
            tick_result["phases"]["advancement"] = advancement_result

        logger.info(f"=== TICK {self.tick_count} COMPLETE ===\n")

        return tick_result

    def _run_collection_phase(self) -> Dict[str, Any]:
        """
        Phase 1: Data collection from the scenario event queue.

        Processes events from the queue whose time has come and places
        their payload onto the shared_data_bus.

        Returns:
            Dict with collection phase results
        """
        phase_result = {
            "events_processed": 0,
            "flood_data_collected": 0,
            "scout_reports_collected": 0,
            "errors": []
        }

        # ENHANCED: Log current queue state
        next_event_info = "None"
        if self._event_queue:
            next_event = self._event_queue[0]
            next_event_info = f"agent={next_event.get('agent')}, time={next_event.get('time_offset')}s"

        logger.info(
            f"Collection phase START - "
            f"Clock: {self._simulation_clock:.2f}s, "
            f"Queue size: {len(self._event_queue)}, "
            f"Next event: {next_event_info}"
        )

        # Clear previous tick's data
        self.shared_data_bus["flood_data"] = {}
        self.shared_data_bus["scout_data"] = []
        self.shared_data_bus["graph_updated"] = False

        # Process events from the queue
        events_processed_details = []
        while self._event_queue and self._event_queue[0]["time_offset"] <= self._simulation_clock:
            event = self._event_queue.pop(0)
            phase_result["events_processed"] += 1
            agent = event.get("agent")
            payload = event.get("payload")
            time_offset = event.get("time_offset")

            # ENHANCED: Log each event processed with details
            logger.info(
                f"Processing event #{phase_result['events_processed']}: "
                f"agent={agent}, time_offset={time_offset}s"
            )

            if agent == "flood_agent":
                self.shared_data_bus["flood_data"] = payload
                phase_result["flood_data_collected"] += 1
                logger.info(f"✓ Flood data collected: {len(payload)} data points")
                events_processed_details.append(f"flood_agent@{time_offset}s")

            elif agent == "scout_agent":
                # ENHANCED: Log scout data structure
                logger.debug(f"Scout report payload (raw): {payload}")

                # Process scout data through ML pipeline if scout agent available
                if self.scout_agent and hasattr(self.scout_agent, 'nlp_processor') and self.scout_agent.nlp_processor:
                    # Extract flood info using NLP processor
                    text = payload.get("text", "")
                    if text:
                        logger.debug(f"Processing scout text through ML: '{text}'")
                        flood_info = self.scout_agent.nlp_processor.extract_flood_info(text)

                        # Geocode the result
                        if self.scout_agent.geocoder:
                            enhanced_info = self.scout_agent.geocoder.geocode_nlp_result(flood_info)
                        else:
                            enhanced_info = flood_info

                        # Merge ML predictions with original payload
                        payload.update({
                            "coordinates": enhanced_info.get("coordinates"),
                            "severity": enhanced_info.get("severity", 0),
                            "confidence": enhanced_info.get("confidence", 0),
                            "report_type": enhanced_info.get("report_type", "unknown"),
                            "is_flood_related": enhanced_info.get("is_flood_related", False)
                        })
                        logger.debug(f"ML enhanced payload: coordinates={payload.get('coordinates')}, severity={payload.get('severity'):.2f}")

                # FIX: Update timestamp to current time for simulation data
                # This ensures reports pass the time-based filtering in the API
                if "timestamp" in payload:
                    payload["timestamp"] = datetime.now().isoformat()

                self.shared_data_bus["scout_data"].append(payload)
                phase_result["scout_reports_collected"] += 1

                # Log key scout data fields
                location = payload.get("location", "Unknown")
                severity = payload.get("severity", 0)
                has_coords = "coordinates" in payload and payload["coordinates"] is not None
                logger.info(
                    f"✓ Scout report collected: location='{location}', severity={severity:.2f}, has_coords={has_coords}"
                )
                events_processed_details.append(f"scout_agent@{time_offset}s[{location}]")

            else:
                error_msg = f"Unknown agent '{agent}' in scenario event."
                phase_result["errors"].append(error_msg)
                logger.warning(error_msg)

        # ENHANCED: Log phase summary
        logger.info(
            f"Collection phase COMPLETE - "
            f"Events processed: {phase_result['events_processed']} "
            f"({', '.join(events_processed_details) if events_processed_details else 'none'}), "
            f"Flood data: {phase_result['flood_data_collected']}, "
            f"Scout reports: {phase_result['scout_reports_collected']}")
        return phase_result

    async def _run_fusion_phase(self) -> Dict[str, Any]:
        """
        Phase 2: Data fusion and graph update by HazardAgent.

        HazardAgent receives data from shared_data_bus, fuses it,
        calculates risk scores, and updates the graph. This ensures
        the graph is updated BEFORE routing calculations.

        Returns:
            Dict with fusion phase results
        """
        phase_result = {
            "edges_updated": 0,
            "errors": []
        }

        if not self.hazard_agent:
            logger.warning("HazardAgent not configured, skipping fusion phase")
            return phase_result

        try:
            # Update HazardAgent's GeoTIFF scenario to current time step
            return_period = MODE_TO_RETURN_PERIOD[self._mode]
            self.hazard_agent.set_flood_scenario(
                return_period=return_period,
                time_step=self.current_time_step
            )

            # Pass collected data to HazardAgent
            flood_data = self.shared_data_bus.get("flood_data", {})
            scout_data = self.shared_data_bus.get("scout_data", [])

            # Call HazardAgent's update_risk method
            update_result = self.hazard_agent.update_risk(
                flood_data=flood_data,
                scout_data=scout_data,
                time_step=self.current_time_step
            )

            phase_result["edges_updated"] = update_result.get("edges_updated", 0)
            self.shared_data_bus["graph_updated"] = True

            if update_result.get("edges_updated", 0) > 0:
                await self._broadcast_graph_update(update_result)

            logger.info(
                f"HazardAgent updated {phase_result['edges_updated']} edges "
                f"(time_step={self.current_time_step})"
            )

        except Exception as e:
            logger.error(f"HazardAgent fusion failed: {e}")
            phase_result["errors"].append(f"HazardAgent: {str(e)}")

        return phase_result

    async def _broadcast_graph_update(self, update_result: Dict[str, Any]):
        """Broadcast graph risk update to WebSocket clients."""
        if not self.ws_manager:
            return

        await self.ws_manager.broadcast({
            "type": "risk_update",
            "data": {
                "edges_updated": update_result.get("edges_updated", 0),
                "average_risk": update_result.get("average_risk", 0.0),
                "risk_trend": update_result.get("risk_trend", "stable"),
                "time_step": update_result.get("time_step", 1)
            },
            "timestamp": datetime.now().isoformat()
        })


    def _run_routing_phase(self) -> Dict[str, Any]:
        """
        Phase 3: Process route requests via EvacuationManagerAgent.

        EvacuationManager processes pending route requests using the
        NOW UPDATED graph from Phase 2.

        Returns:
            Dict with routing phase results
        """
        phase_result = {
            "routes_processed": 0,
            "errors": []
        }

        if not self.routing_agent:
            logger.warning(
                "RoutingAgent not configured, skipping routing phase"
            )
            return phase_result

        # Process pending routes from shared_data_bus
        pending_routes = self.shared_data_bus.get("pending_routes", [])

        if not pending_routes:
            logger.debug("No pending route requests in this tick")
            return phase_result

        for route_request in pending_routes:
            try:
                start = route_request.get("start")
                end = route_request.get("end")
                preferences = route_request.get("preferences")

                route_result = self.routing_agent.calculate_route(
                    start, end, preferences
                )

                phase_result["routes_processed"] += 1
                logger.info(f"Processed route request: {start} -> {end}")

            except Exception as e:
                logger.error(f"Route request processing failed: {e}")
                phase_result["errors"].append(f"Route: {str(e)}")

        # Clear processed routes
        self.shared_data_bus["pending_routes"] = []

        return phase_result

    def _run_evacuation_update_phase(self) -> Dict[str, Any]:
        """
        Phase 4: Evacuation center occupancy update.

        Simulates gradual filling of evacuation centers as flood conditions
        worsen. The filling rate depends on:
        - Simulation mode (more filling in heavier floods)
        - Current time step (more filling as time progresses)
        - Current flood severity

        Returns:
            Dict with evacuation update phase results
        """
        from app.services.evacuation_service import get_evacuation_service

        phase_result = {
            "centers_updated": 0,
            "total_evacuees_added": 0,
            "errors": []
        }

        try:
            service = get_evacuation_service()
            all_centers = service.get_all_centers()

            # Calculate evacuation rate based on mode and time step
            # More severe floods = more people evacuating
            mode_multiplier = {
                SimulationMode.LIGHT: 1.0,    # 2-year: light flooding
                SimulationMode.MEDIUM: 2.0,   # 5-year: moderate flooding
                SimulationMode.HEAVY: 3.5     # 25-year: severe flooding
            }.get(self._mode, 1.0)

            # Time progression multiplier (more people evacuate as flood persists)
            time_multiplier = 1.0 + (self.current_time_step / 18.0) * 1.5

            # Base evacuation rate per tick (people per center per tick)
            base_rate = 5  # Conservative rate

            # Calculate evacuation rate
            evacuation_rate = int(base_rate * mode_multiplier * time_multiplier)

            logger.info(
                f"Evacuation rate: {evacuation_rate} people/center "
                f"(mode={mode_multiplier}x, time={time_multiplier:.2f}x)"
            )

            # Add evacuees to centers that aren't full
            for center in all_centers:
                if center['status'] == 'full':
                    continue  # Skip full centers

                # Add evacuees to this center
                result = service.add_evacuees(center['name'], evacuation_rate)

                if result['success']:
                    phase_result["centers_updated"] += 1
                    phase_result["total_evacuees_added"] += evacuation_rate
                    logger.debug(
                        f"Added {evacuation_rate} evacuees to {center['name']} "
                        f"({result['center']['current_occupancy']}/{result['center']['capacity']})"
                    )

            logger.info(
                f"Evacuation update complete: "
                f"Updated {phase_result['centers_updated']} centers, "
                f"Added {phase_result['total_evacuees_added']} total evacuees"
            )

        except Exception as e:
            error_msg = f"Error updating evacuation centers: {e}"
            logger.error(error_msg)
            phase_result["errors"].append(error_msg)

        return phase_result

    def _run_advancement_phase(self) -> Dict[str, Any]:
        """
        Phase 5: Time advancement and cleanup.

        Perform any necessary cleanup and prepare for next tick.

        Returns:
            Dict with advancement phase results
        """
        phase_result = {
            "next_time_step": (self.current_time_step % 18) + 1,
            "next_tick": self.tick_count + 1
        }

        logger.info(
            f"Time advancement complete. "
            f"Next time_step: {phase_result['next_time_step']}"
        )

        return phase_result

    def add_route_request(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        preferences: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a route request to be processed in the next tick.

        Args:
            start: Starting coordinates (lat, lon)
            end: Destination coordinates (lat, lon)
            preferences: Optional user preferences
        """
        route_request = {
            "start": start,
            "end": end,
            "preferences": preferences,
            "added_at": datetime.now()
        }

        self.shared_data_bus.setdefault("pending_routes", []).append(
            route_request
        )

        logger.info(f"Route request queued: {start} -> {end}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current simulation status.

        Returns:
            Dictionary with complete simulation status
        """
        status = {
            "state": self._state.value,
            "mode": self._mode.value,
            "is_running": self.is_running,
            "is_stopped": self.is_stopped,
            "is_paused": self.is_paused,
            "total_runtime_seconds": round(self._total_runtime_seconds, 2),
            "simulation_clock": round(self._simulation_clock, 2),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "paused_at": self._paused_at.isoformat() if self._paused_at else None,
            "tick_count": self.tick_count,
            "current_time_step": self.current_time_step,
            "return_period": MODE_TO_RETURN_PERIOD.get(self._mode),
            "pending_routes": len(self.shared_data_bus.get("pending_routes", [])),
            "scenario": self._scenario_data.get("name") if self._scenario_data else None,
            "events_in_queue": len(self._event_queue)
        }

        # Calculate current runtime if running
        if self.is_running and self._last_tick_time:
            current_runtime = (datetime.now() - self._last_tick_time).total_seconds()
            status["current_session_seconds"] = round(current_runtime, 2)

        return status

    def set_data(self, key: str, value: Any) -> None:
        """
        Store simulation data.

        Args:
            key: Data key
            value: Data value
        """
        self._simulation_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """
        Retrieve simulation data.

        Args:
            key: Data key
            default: Default value if key not found

        Returns:
            Data value or default
        """
        return self._simulation_data.get(key, default)

    def clear_data(self) -> None:
        """Clear all simulation data."""
        self._simulation_data.clear()


# Global simulation manager instance
_simulation_manager: Optional[SimulationManager] = None


def get_simulation_manager() -> SimulationManager:
    """
    Get or create the global simulation manager instance.

    Returns:
        SimulationManager instance
    """
    global _simulation_manager
    if _simulation_manager is None:
        _simulation_manager = SimulationManager()
    return _simulation_manager


def set_simulation_manager(manager: SimulationManager) -> None:
    """
    Set the global simulation manager instance.

    Args:
        manager: SimulationManager instance
    """
    global _simulation_manager
    _simulation_manager = manager
