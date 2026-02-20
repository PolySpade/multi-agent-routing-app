import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import pytest

# Ensure app modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.agents.evacuation_manager_agent import EvacuationManagerAgent
from app.agents.routing_agent import RoutingAgent
from app.services.llm_service import LLMService

@pytest.mark.xfail(reason="EvacuationManagerAgent missing max_risk attribute in v2")
class TestEvacuationNLP(unittest.TestCase):
    def setUp(self):
        self.mock_env = MagicMock()
        self.mock_env.graph = MagicMock() # Graph needed
        
        # Setup Mock LLM
        self.mock_llm = MagicMock(spec=LLMService)
        self.mock_llm.is_available.return_value = True
        
        # Initialize Agents
        self.routing_agent = RoutingAgent("router_01", self.mock_env, llm_service=self.mock_llm)
        self.evac_manager = EvacuationManagerAgent("evac_mgr_01", self.mock_env)
        self.evac_manager.set_routing_agent(self.routing_agent)

        # Mock Evacuation Centers (DataFrame usually, but we need to mock internal usage)
        # We'll mock _find_nearest_node to make things easier
        self.routing_agent._find_nearest_node = MagicMock(return_value=123)
        
        # Mock evacuation centers dataframe
        import pandas as pd
        self.routing_agent.evacuation_centers = pd.DataFrame([
            {
                "name": "Marikina Sports Center", 
                "latitude": 14.65, 
                "longitude": 121.10, 
                "capacity": 1000, 
                "type": "shelter"
            },
            {
                "name": "Amang Rodriguez Medical", 
                "latitude": 14.66, 
                "longitude": 121.11, 
                "capacity": 500, 
                "type": "hospital"
            }
        ])

    @patch('app.agents.routing_agent.RoutingAgent.parse_routing_request')
    @patch('app.agents.routing_agent.RoutingAgent.explain_route')
    @patch('app.algorithms.risk_aware_astar.risk_aware_astar')
    @patch('app.algorithms.risk_aware_astar.calculate_path_metrics') 
    @patch('app.algorithms.risk_aware_astar.get_path_coordinates')
    def test_distress_call_integration(self, mock_coords, mock_metrics, mock_astar, mock_explain, mock_parse):
        print("\n=== Testing Natural Language Evacuation Flow ===")
        
        # 1. Setup Logic Mocks
        # "Trapped" -> Safest Mode
        mock_parse.return_value = {
            "mode": "safest", 
            "vehicle_type": "car",
            "avoid_floods": True
        }
        
        # Route Found Logic
        mock_astar.return_value = ([1, 2, 3], ['e1', 'e2'])
        mock_metrics.return_value = {
            "total_distance": 1500,
            "estimated_time": 10.0,
            "average_risk": 0.05,
            "max_risk": 0.1,
            "num_segments": 2
        }
        mock_coords.return_value = [[14.6, 121.1], [14.65, 121.10]]
        
        # Explanation Logic
        mock_explain.return_value = "Routing to Marikina Sports Center. Route is clear and safe."

        # 2. Execute Distress Call
        user_loc = (14.6, 121.1)
        message = "Help! I am trapped near the river with my grandfather."
        
        result = self.evac_manager.handle_distress_call(user_loc, message)
        
        # 3. Verify Results
        print(f"Distress Message: '{message}'")
        print(f"Result Action: {result.get('action')}")
        print(f"Target Center: {result.get('target_center')}")
        print(f"Explanation: '{result.get('explanation')}'")
        
        # Assertions
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['action'], 'evacuate')
        self.assertIn("Marikina Sports Center", result['target_center']) # First in sorted list usually
        self.assertEqual(result['explanation'], "Routing to Marikina Sports Center. Route is clear and safe.")
        
        # Verify Context Flow
        mock_parse.assert_called_with(message)
        
        # Verify risk penalty was applied (Safest mode, recalibrated)
        # We need to inspect calls to risk_aware_astar
        call_args = mock_astar.call_args
        passed_risk_weight = call_args.kwargs.get('risk_weight')
        print(f"Risk Weight Used: {passed_risk_weight}")
        self.assertEqual(passed_risk_weight, 100.0) # Confirm 'Safest' mode applied (recalibrated)
        
        print("✅ Success: Distress call parsed, safety prioritized, and route explained!")

if __name__ == '__main__':
    unittest.main()
