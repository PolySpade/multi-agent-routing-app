
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.communication.message_queue import MessageQueue
from app.communication.acl_protocol import ACLMessage, Performative

# Import other agent types for type hinting if needed
# from app.agents.scout_agent import ScoutAgent 
# ...

logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    """
    The 'Brain' of the Monolithic Multi-Agent System.
    
    Responsibilities:
    1. Central Registry: Holds references to all specialized agents.
    2. Mission Coordination: Breaks down high-level User Commands into sub-tasks.
    3. Error Handling: Manages failures in sub-agent execution.
    
    This agent coordinates synchronous method calls in a monolith but is designed 
    with async interfaces to support future distribution.
    """

    def __init__(self, agent_id: str, environment, message_queue: MessageQueue, sub_agents: Dict[str, Any]):
        """
        Initialize the Orchestrator with references to all other agents.
        
        Args:
            agent_id: Unique ID (e.g., "orchestrator_01")
            environment: Shared DynamicGraphEnvironment
            message_queue: System MessageQueue
            sub_agents: Dict of {'role': agent_instance}
        """
        super().__init__(agent_id, environment)
        self.message_queue = message_queue
        self.sub_agents = sub_agents
        
        # Verify critical agents are present
        required_roles = ['scout', 'routing', 'flood', 'evacuation', 'hazard']
        for role in required_roles:
            if role not in sub_agents:
                logger.warning(f"Orchestrator initialized without '{role}' agent!")
        
        logger.info(f"Orchestrator {agent_id} initialized with agents: {list(sub_agents.keys())}")

    def step(self) -> None:
        """
        Orchestrator is event-driven, not loop-driven in this monolith.
        """
        pass

    # Map each agent role to its actual status method name
    _STATUS_METHODS = {
        'scout': 'get_processing_stats',
        'flood': 'get_agent_stats',
        'routing': 'get_statistics',
        'evacuation': 'get_route_statistics',
        'hazard': None,  # No public status method
    }

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get aggregated status of all sub-agents using their real status methods.
        """
        status_report = {
            "orchestrator": "online",
            "timestamp": datetime.now().isoformat(),
            "agents": {}
        }

        for role, agent in self.sub_agents.items():
            try:
                method_name = self._STATUS_METHODS.get(role)
                if method_name and hasattr(agent, method_name):
                    method = getattr(agent, method_name)
                    if asyncio.iscoroutinefunction(method):
                        agent_status = await method()
                    else:
                        agent_status = await asyncio.to_thread(method)
                else:
                    agent_status = {"status": "online"}

                status_report["agents"][role] = agent_status
            except Exception as e:
                status_report["agents"][role] = {"status": "error", "detail": str(e)}

        return status_report

    async def execute_mission(self, mission_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a high-level mission by coordinating sub-agents.
        
        Args:
            mission_type: Mission identifier
            params: Dict of parameters for the mission
            
        Returns:
            Dict containing the mission results
        """
        logger.info(f"Orchestrator executing mission: {mission_type} with params: {params}")
        
        try:
            if mission_type == "assess_risk":
                return await self._run_risk_assessment_playbook(params)
            elif mission_type == "coordinated_evacuation":
                return await self._run_evacuation_playbook(params)
            elif mission_type == "route_calculation":
                return await self._run_route_calculation(params)
            elif mission_type == "find_evacuation_center":
                return await self._run_evac_center_lookup(params)
            else:
                return {"status": "error", "message": f"Unknown mission type: {mission_type}"}
        except Exception as e:
             logger.error(f"Mission '{mission_type}' failed: {e}", exc_info=True)
             return {"status": "error", "message": f"Mission failed: {str(e)}"}

    # --- PLAYBOOKS (Async Workflows) ---

    async def _run_risk_assessment_playbook(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Workflow: 
        1. Scout -> Scan location (Visual/Text).
        2. Flood -> Trigger data collection/update.
        3. Hazard -> Recalculate risk map.
        """
        location = params.get('location') # Optional specific location
        
        scout = self.sub_agents.get('scout')
        flood = self.sub_agents.get('flood')
        hazard = self.sub_agents.get('hazard')
        
        results = {}
        
        # 1. Scout Scan (if location provided)
        if location and scout:
            logger.info(f"Tasking Scout to scan: {location}")
            if scout.geocoder:
                coords = scout.geocoder.get_coordinates(location)
                if coords:
                    results['location_coords'] = coords
                    results['scout_status'] = f"Scanned {location} at {coords}"
                else:
                    results['scout_status'] = f"Location '{location}' not found by geocoder"
            else:
                results['scout_status'] = "Geocoder not available on Scout agent"
        
        # 2. Flood Update
        if flood:
             logger.info("Tasking Flood Agent to update risk map")
             flood_data = await asyncio.to_thread(flood.collect_flood_data)
             results['flood_update_count'] = len(flood_data) if flood_data else 0
             
        # 3. Hazard Assessment — process pending messages and recalculate risk
        if hazard:
            logger.info("Tasking Hazard Agent to process data and update risk map")
            update_result = await asyncio.to_thread(hazard.process_and_update)
            results['hazard_update'] = update_result
            
        return {"status": "success", "mission": "assess_risk", "results": results}

    async def _run_evacuation_playbook(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Workflow:
        1. Evacuation Manager -> Handle Distress Call.
        """
        user_loc = params.get('user_location')
        distress_msg = params.get('message')
        
        # Validation
        if not user_loc or not distress_msg:
             return {"status": "error", "message": "Missing 'user_location' or 'message'"}
        
        evac_mgr = self.sub_agents.get('evacuation')
        if not evac_mgr:
            return {"status": "error", "message": "Evacuation Manager not available"}
            
        logger.info(f"Tasking Evacuation Manager with distress call: {distress_msg}")
        
        # Run in threadpool if it's CPU intensive synchronous code
        result = await asyncio.to_thread(evac_mgr.handle_distress_call, user_loc, distress_msg)
        
        return {
            "status": "success", 
            "mission": "coordinated_evacuation", 
            "outcome": result
        }

    async def _run_route_calculation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Direct Route Calculation via Routing Agent.
        """
        start = params.get('start')
        end = params.get('end')
        prefs = params.get('preferences', {})

        if not start or not end:
            return {"status": "error", "message": "Missing 'start' or 'end' coordinates"}

        routing = self.sub_agents.get('routing')
        if not routing:
            return {"status": "error", "message": "Routing Agent not available"}

        result = await asyncio.to_thread(routing.calculate_route, start, end, prefs)

        return {"status": "success", "mission": "route_calculation", "route": result}

    async def _run_evac_center_lookup(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find nearest evacuation center.
        """
        location = params.get('location')
        query = params.get('query')
        prefs = params.get('preferences', {})
        max_centers = params.get('max_centers', 5)

        if not location:
            return {"status": "error", "message": "Missing 'location' coordinates"}

        routing = self.sub_agents.get('routing')
        if not routing:
            return {"status": "error", "message": "Routing Agent not available"}

        result = await asyncio.to_thread(
            routing.find_nearest_evacuation_center,
            location,
            max_centers,
            query,
            prefs
        )

        return {"status": "success", "mission": "find_evacuation_center", "result": result}
