
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.agents.orchestrator_agent import OrchestratorAgent

@pytest.mark.xfail(reason="OrchestratorAgent.execute_mission was removed in v2 refactor")
class TestOrchestrator(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Create Mocks for sub-agents
        self.mock_scout = MagicMock()
        self.mock_flood = MagicMock()
        self.mock_routing = MagicMock()
        self.mock_evac = MagicMock()
        self.mock_hazard = MagicMock()
        
        # Mock Environment and MessageQueue
        self.mock_env = MagicMock()
        self.mock_mq = MagicMock()
        
        self.sub_agents = {
            'scout': self.mock_scout,
            'flood': self.mock_flood,
            'routing': self.mock_routing,
            'evacuation': self.mock_evac,
            'hazard': self.mock_hazard
        }
        
        self.orchestrator = OrchestratorAgent(
            "test_orch", 
            self.mock_env, 
            self.mock_mq, 
            self.sub_agents
        )

    async def test_assess_risk_workflow(self):
        """Test the 'assess_risk' playbook."""
        print("\n=== Testing Orchestrator: Assess Risk ===")
        
        # Setup specific mock return values
        self.mock_scout.geocoder.get_coordinates.return_value = (14.6, 121.1)
        self.mock_flood.collect_and_forward_data.return_value = {"station_1": 15.5}
        
        # Execute
        params = {"location": "Marikina Bridge"}
        result = await self.orchestrator.execute_mission("assess_risk", params)
        
        # Verify
        print(f"Result: {result}")
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['results']['location_coords'], (14.6, 121.1))
        self.assertEqual(result['results']['flood_update_count'], 1)
        
        # Check flow
        # 1. Scout tasked
        self.mock_scout.geocoder.get_coordinates.assert_called_with("Marikina Bridge")
        # 2. Flood agent tasked
        self.mock_flood.collect_and_forward_data.assert_called_once()
        
    async def test_evacuation_workflow(self):
        """Test the 'coordinated_evacuation' playbook."""
        print("\n=== Testing Orchestrator: Evacuation ===")
        
        # Mock Evac result
        self.mock_evac.handle_distress_call.return_value = {
            "status": "success",
            "action": "evacuate",
            "target_center": "Shelter A"
        }
        
        # Execute
        params = {
            "user_location": (14.6, 121.1),
            "message": "Trapped!"
        }
        result = await self.orchestrator.execute_mission("coordinated_evacuation", params)
        
        # Verify
        print(f"Result: {result}")
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['outcome']['target_center'], "Shelter A")
        
        # Check flow (Note: handle_distress_call is run in executor, but mock tracks call)
        self.mock_evac.handle_distress_call.assert_called_with((14.6, 121.1), "Trapped!")

    async def test_route_calculation_workflow(self):
        """Test the 'route_calculation' playbook."""
        print("\n=== Testing Orchestrator: Route Calculation ===")
        
        self.mock_routing.calculate_route.return_value = {"path": ["A", "B"], "distance": 100}
        
        params = {
            "start": (0,0),
            "end": (1,1),
            "preferences": {"safe": True}
        }
        result = await self.orchestrator.execute_mission("route_calculation", params)
        
        print(f"Result: {result}")
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['route']['distance'], 100)
        
        self.mock_routing.calculate_route.assert_called_with((0,0), (1,1), {"safe": True})

if __name__ == '__main__':
    unittest.main()
