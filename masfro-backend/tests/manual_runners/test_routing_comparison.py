
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure app modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.agents.routing_agent import RoutingAgent
from app.services.llm_service import LLMService

class TestRoutingComparison(unittest.TestCase):
    def setUp(self):
        self.mock_env = MagicMock()
        
    def test_without_llm(self):
        print("\n=== Scenario 1: Routing Agent WITHOUT LLM ===")
        # Initialize agent with NO LLM service
        agent = RoutingAgent("router_basic", self.mock_env, llm_service=None)
        
        # 1. Test Parsing
        query = "I am driving a huge truck in an emergency"
        prefs = agent.parse_routing_request(query)
        print(f"Query: '{query}'")
        print(f"Parsed Preferences: {prefs}")
        
        if not prefs:
            print("✅ Behavior Correct: Returns empty preferences (will use system defaults)")
        else:
            print("❌ Failure: Should not parse without LLM")

        # 2. Test Explanation
        route_result = {
            'distance': 5000,
            'estimated_time': 15.5,
            'risk_level': 0.1, 
            'max_risk': 0.2,
            'warnings': ["INFO: Long route"]
        }
        explanation = agent.explain_route(route_result)
        print(f"Explanation: '{explanation}'")
        
        if explanation == "Route calculated based on current flood risks and distance.":
            print("✅ Behavior Correct: Returns static fallback string")
        else:
            print(f"❌ Failure: Unexpected explanation: {explanation}")

    def test_with_llm(self):
        print("\n=== Scenario 2: Routing Agent WITH LLM ===")
        # Initialize agent WITH Mock LLM
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.is_available.return_value = True
        mock_llm.text_model = "llama3.2:latest"
        
        agent = RoutingAgent("router_smart", self.mock_env, llm_service=mock_llm)
        
        # 1. Test Parsing (Mocking the LLM response)
        query = "I am driving a huge truck in an emergency"
        mock_json_response = {
            'message': {
                'content': '```json\n{"vehicle_type": "truck", "mode": "fastest", "risk_tolerance": "high"}\n```'
            }
        }
        
        with patch('ollama.chat', return_value=mock_json_response):
            prefs = agent.parse_routing_request(query)
            print(f"Query: '{query}'")
            print(f"Parsed Preferences: {prefs}")
            
            if prefs.get('vehicle_type') == 'truck' and prefs.get('mode') == 'fastest':
                 print("✅ Behavior Correct: Extracted 'truck' and 'fastest' mode from natural language")
            else:
                 print("❌ Failure: Parsing failed")

        # 2. Test Explanation
        route_result = {
            'distance': 5000,
            'estimated_time': 15.5, 
            'risk_level': 0.1,
            'max_risk': 0.2,
            'warnings': ["INFO: Long route"]
        }
        
        mock_text_response = {
            'message': {
                'content': "I recommend this route because it is the fastest option for your truck, despite minor flooding."
            }
        }
        
        with patch('ollama.chat', return_value=mock_text_response):
            explanation = agent.explain_route(route_result)
            print(f"Explanation: '{explanation}'")
            
            if "fastest option" in explanation:
                print("✅ Behavior Correct: Generated context-aware explanation")
            else:
                 print("❌ Failure: Explanation did not match mock")

if __name__ == '__main__':
    unittest.main()
