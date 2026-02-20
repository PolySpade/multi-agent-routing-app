import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.agents.orchestrator_agent import OrchestratorAgent


# ---------------------------------------------------------------------------
# Tests for the NEW MQ-based FSM orchestrator API (start_mission / step)
# ---------------------------------------------------------------------------
class TestOrchestratorMQ(unittest.TestCase):
    """Tests for the OrchestratorAgent's mission lifecycle.

    The orchestrator uses an MQ-based FSM pattern:
    - start_mission() creates a mission and sends the first MQ request
    - step() polls MQ for replies and advances the FSM
    - get_mission_status() returns current state
    """

    def setUp(self):
        # Create Mocks for sub-agents
        self.mock_scout = MagicMock()
        self.mock_flood = MagicMock()
        self.mock_routing = MagicMock()
        self.mock_evac = MagicMock()
        self.mock_hazard = MagicMock()

        # Mock Environment and MessageQueue
        self.mock_env = MagicMock()
        self.mock_mq = MagicMock()
        # receive_message returns None (no pending replies) by default
        self.mock_mq.receive_message.return_value = None

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

    def test_start_mission_returns_mission_id(self):
        """start_mission() should return a dict with mission_id and state."""
        print("\n=== Testing Orchestrator: start_mission ===")

        params = {"location": "Marikina Bridge"}
        result = self.orchestrator.start_mission("assess_risk", params)

        print(f"Result: {result}")
        self.assertIn("mission_id", result)
        self.assertEqual(result["type"], "assess_risk")
        # Import MissionState only if available (new API)
        try:
            from app.agents.orchestrator_agent import MissionState
            self.assertIn(result["state"], [s.value for s in MissionState])
        except ImportError:
            pass

    def test_assess_risk_sends_scout_request(self):
        """assess_risk mission should send a REQUEST to scout agent via MQ."""
        print("\n=== Testing Orchestrator: Assess Risk -> Scout Request ===")

        params = {"location": "Marikina Bridge"}
        result = self.orchestrator.start_mission("assess_risk", params)

        # Verify MQ send_message was called (first FSM step sends scout request)
        self.assertTrue(self.mock_mq.send_message.called,
                        "start_mission should send at least one MQ message")

        # Verify the mission is in progress
        status = self.orchestrator.get_mission_status(result["mission_id"])
        self.assertIsNotNone(status)
        try:
            from app.agents.orchestrator_agent import MissionState
            self.assertNotEqual(status["state"], MissionState.COMPLETED.value)
        except ImportError:
            pass

    def test_evacuation_sends_mq_request(self):
        """coordinated_evacuation mission should send request via MQ."""
        print("\n=== Testing Orchestrator: Evacuation Mission ===")

        params = {
            "user_location": [14.6, 121.1],
            "message": "Trapped!"
        }
        result = self.orchestrator.start_mission("coordinated_evacuation", params)

        print(f"Result: {result}")
        self.assertIn("mission_id", result)
        self.assertTrue(self.mock_mq.send_message.called)

    def test_route_calculation_sends_mq_request(self):
        """route_calculation mission should send request via MQ."""
        print("\n=== Testing Orchestrator: Route Calculation ===")

        params = {
            "start": [14.6, 121.1],
            "end": [14.65, 121.12],
            "preferences": {"mode": "safest"}
        }
        result = self.orchestrator.start_mission("route_calculation", params)

        print(f"Result: {result}")
        self.assertIn("mission_id", result)
        self.assertTrue(self.mock_mq.send_message.called)

    def test_max_concurrent_missions(self):
        """Should reject missions when max concurrency is reached."""
        print("\n=== Testing Orchestrator: Max Concurrent ===")

        max_missions = self.orchestrator._config.max_concurrent_missions if self.orchestrator._config else 10

        # Fill up to max
        for i in range(max_missions):
            result = self.orchestrator.start_mission("assess_risk", {"location": f"loc_{i}"})
            self.assertIn("mission_id", result)

        # Next one should be rejected
        result = self.orchestrator.start_mission("assess_risk", {"location": "overflow"})
        self.assertEqual(result["status"], "error")
        print(f"Rejected as expected: {result['message']}")

    def test_get_active_missions(self):
        """get_active_missions() should return list of active missions."""
        print("\n=== Testing Orchestrator: Active Missions ===")

        self.orchestrator.start_mission("assess_risk", {"location": "test"})
        active = self.orchestrator.get_active_missions()

        self.assertIsInstance(active, list)
        self.assertGreater(len(active), 0)
        self.assertIn("mission_id", active[0])


# ---------------------------------------------------------------------------
# Tests for the OLD async execute_mission API (kept for regression coverage)
# ---------------------------------------------------------------------------
@pytest.mark.xfail(reason="OrchestratorAgent.execute_mission was removed in v2 refactor")
class TestOrchestratorLegacy(unittest.IsolatedAsyncioTestCase):
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
