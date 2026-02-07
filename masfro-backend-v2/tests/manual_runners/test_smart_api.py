
import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import sys
import os

# Ensure app modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.main import app

class TestSmartAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        
    @patch('app.main.environment')
    @patch('app.agents.routing_agent.RoutingAgent.explain_route')
    @patch('app.agents.routing_agent.RoutingAgent.calculate_route')
    @patch('app.agents.routing_agent.RoutingAgent.parse_routing_request')
    def test_smart_route_api(self, mock_parse, mock_calc, mock_explain, mock_env):
        print("\n=== Testing Smart Routing API Endpoint ===")
        
        # 1. Setup Mock Environment
        mock_env.graph = MagicMock() 

        # 2. Setup Mock Routing Agent behavior via Class Patches
        mock_parse.return_value = {
            "vehicle_type": "truck",
            "mode": "fastest"
        }
        
        mock_calc.return_value = {
            "path": [[14.6, 121.1], [14.7, 121.2]],
            "distance": 5000,
            "estimated_time": 10,
            "risk_level": 0.2,
            "warnings": [],
            "max_risk": 0.3
        }
        
        mock_explain.return_value = "I chose this route because it is optimal for your truck."

        # 3. Make Request with Query
        payload = {
            "start_location": [14.6, 121.1],
            "end_location": [14.7, 121.2],
            "query": "I am driving a truck in an emergency"
        }
        
        # Add preferences explicitly if needed to avoid defaults issues, though query should handle it
        
        response = self.client.post("/api/route", json=payload)
        
        # 4. Verify Response
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
             try:
                 print(f"ERROR DETAIL: {response.json().get('detail')}")
             except:
                 print(f"RAW RESPONSE: {response.text}")
             print(f"SENT PAYLOAD: {payload}")
        
        data = response.json()
        print(f"Response Explanation: '{data.get('explanation')}'")
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(data.get('explanation'))
        self.assertEqual(data['explanation'], "I chose this route because it is optimal for your truck.")
        
        # Verify Agent Interaction
        mock_parse.assert_called_with("I am driving a truck in an emergency")
        mock_calc.assert_called()
        
        # Check that preferences passed to calculate_route include parsed values
        call_args = mock_calc.call_args
        passed_prefs = call_args.kwargs['preferences']
        print(f"Preferences passed to agent: {passed_prefs}")
        self.assertEqual(passed_prefs['vehicle_type'], 'truck')
        
        print("✅ API successfully accepted query, parsed it, used prefs, and returned explanation!")

if __name__ == '__main__':
    unittest.main()
