
import unittest
from unittest.mock import MagicMock, patch
import logging
import sys
import os

# Ensure app modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.agents.scout_agent import ScoutAgent
from app.services.llm_service import LLMService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class MockLLMService:
    def __init__(self):
        self.text_model = "mock-model"
        self.vision_model = "mock-vision"
        # Mock responses
        self.text_responses = {}
        self.vision_responses = {}
        self.chat_responses = {}
    
    def is_available(self):
        return True
        
    def analyze_text_report(self, text):
        return self.text_responses.get(text)
        
    def analyze_flood_image(self, image_path):
        return self.vision_responses.get(image_path)
    
    # For Ollama chat mocking (Geocoding)
    # We won't rely on the real ollama, so we mock the method that calls it
    # But LocationGeocoder calls ollama.chat directly. We'll need to patch ollama in the test.

class TestScoutFusion(unittest.TestCase):
    
    def setUp(self):
        # Mock dependencies
        self.mock_env = MagicMock()
        self.mock_queue = MagicMock()
        
        # Initialize Scout Agent
        self.agent = ScoutAgent(
            agent_id="scout_test",
            environment=self.mock_env,
            message_queue=self.mock_queue,
            enable_llm=True
        )
        
        # Inject Mock LLM Service
        self.mock_llm = MockLLMService()
        self.agent.llm_service = self.mock_llm
        self.agent.use_llm = True
        
        # Re-initialize geocoder with specific mock logic if needed
        # For now, we'll let the agent use the real LocationGeocoder but we'll patch its internals during tests
        from app.ml_models.location_geocoder import LocationGeocoder
        self.agent.geocoder = LocationGeocoder(llm_service=self.mock_llm)
        
        # Ensure 'Marikina Sports Park' exists in the geocoder's database for the test lookup to succeed
        self.agent.geocoder.location_coordinates["Marikina Sports Park"] = (14.6346, 121.0985)
        self.agent.geocoder.location_names.append("Marikina Sports Park")

    def test_fusion_scenario_a_high_visual_low_text(self):
        """
        Scenario A: Text says 'low risk' but Image shows 'high risk'.
        Expected: Final Risk = 0.9 (Visual wins)
        """
        print("\n--- Running Test Scenario A: High Visual vs Low Text ---")
        
        tweet = {
            "text": "Just a bit of rain here.",
            "image_path": "deep_flood.jpg",
            "timestamp": "2026-02-04T12:00:00Z",
            "username": "user1"
        }
        
        # Mock LLM Text Analysis (Low Severity)
        self.mock_llm.text_responses["Just a bit of rain here."] = {
            "is_flood_related": True,
            "severity": 0.1,
            "location": "Marikina Bridge", # Known location
            "confidence": 0.8
        }
        
        # Mock Vision Analysis (High Severity)
        self.mock_llm.vision_responses["deep_flood.jpg"] = {
            "estimated_depth_m": 1.5,
            "risk_score": 0.9,
            "visual_passability": "impassable"
        }
        
        # Process
        result = self.agent._process_single_tweet(tweet)
        
        # Verify
        self.assertIsNotNone(result)
        logger.info(f"Result: Severity={result['severity']}, Confidence={result['confidence']}")
        
        self.assertEqual(result['severity'], 0.9, "Visual risk should override text risk")
        self.assertEqual(result['confidence'], 0.9, "Confidence should be boosted by visual evidence")

    def test_fusion_scenario_b_high_text_low_visual(self):
        """
        Scenario B: Text says 'HIGH risk' but Image is unclear/low risk.
        Expected: Final Risk = 0.9 (Text wins - safety first)
        """
        print("\n--- Running Test Scenario B: High Text vs Low Visual ---")
        
        tweet = {
            "text": "EMERGENCY! TRAPPED ON ROOF!",
            "image_path": "blurry.jpg",
            "timestamp": "2026-02-04T12:00:00Z"
        }
        
        # Mock LLM Text Analysis (High Severity)
        self.mock_llm.text_responses["EMERGENCY! TRAPPED ON ROOF!"] = {
            "is_flood_related": True,
            "severity": 0.9,
            "location": "Tumana",
            "confidence": 0.95
        }
        
        # Mock Vision Analysis (Low/Unknown Severity)
        self.mock_llm.vision_responses["blurry.jpg"] = {
            "estimated_depth_m": 0.0,
            "risk_score": 0.0
        }
        
        # Process
        result = self.agent._process_single_tweet(tweet)
        
        self.assertEqual(result['severity'], 0.9, "High text risk should persist even if image is unclear")

    def test_scenario_c_llm_geocoding(self):
        """
        Scenario C: Location is 'near the sports complex' (not in CSV).
        Expected: Geocodes to 'Marikina Sports Park' via LLM match.
        """
        print("\n--- Running Test Scenario C: LLM Geocoding Fallback ---")
        
        tweet = {
            "text": "Flood near the sports complex",
            "timestamp": "2026-02-04T12:00:00Z"
        }
        
        # Mock Text Analysis
        self.mock_llm.text_responses["Flood near the sports complex"] = {
            "is_flood_related": True,
            "severity": 0.5,
            "location": "near the sports complex",
            "confidence": 0.8
        }
        
        # Mock the internal fallback method of the geocoder directly
        # This avoids complex patching of the local 'ollama' import
        self.agent.geocoder._geocode_with_llm = MagicMock(return_value=(14.6346, 121.0985))
        
        # Process
        result = self.agent._process_single_tweet(tweet)
        
        logger.info(f"Result: {result}")
        # Ensure the geocoder fallback was actually called
        self.agent.geocoder._geocode_with_llm.assert_called_with("near the sports complex")
        
        self.assertTrue(result['has_coordinates'], f"Failed to geocode. Result: {result}")
        # Marikina Sports Park roughly (14.63, 121.09)
        self.assertAlmostEqual(result['coordinates'][0], 14.6346, delta=0.01)

    def test_scenario_d_vision_only(self):
        """
        Scenario D: Tweet has NO text, only Image.
        Expected: Processed based on image risk.
        """
        print("\n--- Running Test Scenario D: Vision Only ---")
        
        tweet = {
            "text": "",
            "image_path": "flood_only.jpg",
            "timestamp": "2026-02-04T12:00:00Z"
        }
        
        self.mock_llm.vision_responses["flood_only.jpg"] = {
            "estimated_depth_m": 1.0,
            "risk_score": 0.8,
            "visual_evidence": True
        }
        
        result = self.agent._process_single_tweet(tweet)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['severity'], 0.8)
        self.assertTrue(result['visual_evidence'])

if __name__ == '__main__':
    unittest.main()
