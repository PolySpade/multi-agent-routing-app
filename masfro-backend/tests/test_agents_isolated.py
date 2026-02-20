
import sys
import os
import unittest
from unittest.mock import MagicMock
import logging

# Add project root to path
# Assuming this file is in tests/ directory, project root is one level up
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.llm_service import LLMService
from app.agents.scout_agent import ScoutAgent
from app.environment.graph_manager import DynamicGraphEnvironment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestAgentsIsolated")

class MockMessageQueue:
    def register_agent(self, agent_id):
        pass
    def send_message(self, message):
        pass

class TestAgentsIsolated(unittest.TestCase):
    def setUp(self):
        # Mock Environment
        self.mock_env = MagicMock(spec=DynamicGraphEnvironment)
        self.mock_mq = MockMessageQueue()
        
    def test_01_llm_service_health(self):
        """Test if the LLM Service can connect to Ollama."""
        print("\n--- Testing LLM Service Health ---")
        llm = LLMService(enabled=True)
        is_available = llm.is_available()
        
        if is_available:
            print("✅ LLM Service is AVAILABLE.")
            health = llm.get_health()
            print(f"   Success! Connected to base_url: {health.get('base_url')}")
            print(f"   Models Loaded: {health.get('models_loaded')}")
            self.assertTrue(health.get('available'))
        else:
            print("⚠️ LLM Service is UNAVAILABLE (Ollama might be down or not installed).")
            print("   Skipping detailed assertions for LLM health.")

    def test_02_scout_agent_llm_analysis(self):
        """Test ScoutAgent's ability to use LLM for text analysis."""
        print("\n--- Testing ScoutAgent Text Analysis (LLM) ---")
        
        # Explicitly set models based on user environment
        os.environ["LLM_TEXT_MODEL"] = "llama3.2:latest"
        os.environ["LLM_VISION_MODEL"] = "moondream:latest"
        
        agent = ScoutAgent(
            agent_id="test_scout",
            environment=self.mock_env,
            message_queue=self.mock_mq,
            enable_llm=True
        )
        
        # Verify LLM is enabled in agent
        print(f"Agent LLM Enabled: {agent.is_llm_enabled()}")
        if not agent.is_llm_enabled():
            print("⚠️ Agent LLM not enabled/available. Skipping logic verification.")
            return

        # Test Data
        test_text = "Urgent: Flood waters rising rapidly at Tumana Bridge, Marikina. Currently chest deep. Vehicles cannot pass."
        print(f"Input Text: '{test_text}'")
        
        # Access private method for testing isolation
        # Use _analyze_text directly to bypass simulation loop
        print("Sending to LLM (this may take a moment)...")
        result = agent._analyze_text(test_text)
        print("LLM returned.")
        
        if result:
            print("✅ LLM Analysis Result:")
            print(result)
            
            # Assertions
            self.assertIn("location", result)
            self.assertTrue("Tumana" in result.get("location") or "Marikina" in result.get("location"))
            self.assertIn("severity", result)
            self.assertIn("is_flood_related", result)
            self.assertTrue(result["is_flood_related"])
        else:
            print("❌ LLM output was None.")
            self.fail("LLM failed to analyze text")

if __name__ == '__main__':
    unittest.main()
