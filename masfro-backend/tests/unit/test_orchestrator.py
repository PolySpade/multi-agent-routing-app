
import unittest
from unittest.mock import MagicMock
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.agents.orchestrator_agent import OrchestratorAgent, MissionState


class TestOrchestrator(unittest.TestCase):
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
        self.assertIn(result["state"], [s.value for s in MissionState])

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
        self.assertNotEqual(status["state"], MissionState.COMPLETED.value)

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


if __name__ == '__main__':
    unittest.main()
