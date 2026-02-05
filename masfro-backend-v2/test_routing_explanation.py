
import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Ensure app modules are importable
sys.path.append(os.getcwd())

from app.agents.routing_agent import RoutingAgent, RouteWarning, WarningSeverity
from app.services.llm_service import LLMService

class TestSmartRouting(unittest.TestCase):
    def setUp(self):
        self.mock_env = MagicMock()
        self.mock_llm = MagicMock(spec=LLMService)
        self.mock_llm.is_available.return_value = True
        self.mock_llm.text_model = "llama3.2:latest"
        
        self.agent = RoutingAgent("test_router", self.mock_env, llm_service=self.mock_llm)

    def test_parse_routing_request(self):
        """Test converting natural language to preferences."""
        # Mock LLM response for "I'm driving a truck"
        mock_response = {
            'message': {
                'content': '```json\n{"vehicle_type": "truck", "mode": "balanced", "avoid_floods": false}\n```'
            }
        }
        
        with patch('ollama.chat', return_value=mock_response):
            prefs = self.agent.parse_routing_request("I'm driving a big truck, need to get there fast")
            
            self.assertEqual(prefs['vehicle_type'], 'truck')
            self.assertEqual(prefs['mode'], 'balanced')
            print(f"\n✅ Parsed 'Big Truck' request: {prefs}")

    def test_explain_route(self):
        """Test generating natural language explanation."""
        # Simulated route result
        route_result = {
            'distance': 5000,
            'estimated_time': 15.5,
            'risk_level': 0.1,
            'max_risk': 0.2,
            'warnings': [
                "INFO: This is a long route"
            ]
        }
        
        # Mock LLM explanation
        mock_explanation = {
            'message': {
                'content': "I chose this route because it is the safest option with minimal flood risk (average 0.1), even though it takes 15 minutes."
            }
        }
        
        with patch('ollama.chat', return_value=mock_explanation):
            explanation = self.agent.explain_route(route_result)
            self.assertIn("safest option", explanation)
            print(f"\n✅ Generated Explanation: {explanation}")

if __name__ == '__main__':
    unittest.main()
