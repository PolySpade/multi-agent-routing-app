"""
Test suite for ScoutAgent ML processing in simulation mode.

This test verifies that when use_ml_in_simulation=True:
1. Simulation tweets have ground truth stripped
2. ML models (NLP processor and geocoder) are actually called
3. Predictions are used instead of pre-computed values

Author: MAS-FRO Development Team
Date: November 2025
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.agents.scout_agent import ScoutAgent
from app.environment.graph_manager import DynamicGraphEnvironment


class TestScoutMLProcessing:
    """Test ML processing in simulation mode."""

    @pytest.fixture
    def mock_environment(self):
        """Create a mock environment."""
        env = MagicMock(spec=DynamicGraphEnvironment)
        env.graph = MagicMock()
        return env

    @pytest.fixture
    def mock_hazard_agent(self):
        """Create a mock hazard agent."""
        hazard = MagicMock()
        hazard.process_scout_data_with_coordinates = MagicMock()
        return hazard

    @pytest.fixture
    def sample_simulation_tweets(self):
        """Sample simulation tweets with ground truth."""
        return [
            {
                "tweet_id": "123456",
                "username": "test_user",
                "text": "Baha sa Nangka! Tuhod level, hindi madaan!",
                "timestamp": "2025-11-20T08:00:00Z",
                "url": "https://x.com/test/123456",
                "replies": "5",
                "retweets": "10",
                "likes": "20",
                "scraped_at": "2025-11-20T08:05:00",
                "_ground_truth": {
                    "location": "Nangka",
                    "severity_level": "dangerous",
                    "is_flood_related": True
                }
            },
            {
                "tweet_id": "789012",
                "username": "weather_ph",
                "text": "Light rain at SM Marikina. Roads still clear.",
                "timestamp": "2025-11-20T08:10:00Z",
                "url": "https://x.com/test/789012",
                "replies": "2",
                "retweets": "3",
                "likes": "8",
                "scraped_at": "2025-11-20T08:15:00",
                "_ground_truth": {
                    "location": "SM Marikina",
                    "severity_level": "minor",
                    "is_flood_related": True
                }
            }
        ]

    def test_initialization_with_ml_enabled(self, mock_environment):
        """Test that scout agent initializes with ML processing enabled."""
        agent = ScoutAgent(
            agent_id="test_scout",
            environment=mock_environment,
            simulation_mode=True,
            simulation_scenario=1,
            use_ml_in_simulation=True  # Enable ML processing
        )

        assert agent.use_ml_in_simulation is True
        assert agent.simulation_mode is True
        assert agent.nlp_processor is not None
        assert agent.geocoder is not None

    def test_initialization_with_ml_disabled(self, mock_environment):
        """Test that scout agent initializes with ML processing disabled (legacy mode)."""
        agent = ScoutAgent(
            agent_id="test_scout",
            environment=mock_environment,
            simulation_mode=True,
            simulation_scenario=1,
            use_ml_in_simulation=False  # Disable ML, use ground truth
        )

        assert agent.use_ml_in_simulation is False

    def test_ground_truth_stripped_when_ml_enabled(self, mock_environment, sample_simulation_tweets):
        """Test that _ground_truth is removed when use_ml_in_simulation=True."""
        agent = ScoutAgent(
            agent_id="test_scout",
            environment=mock_environment,
            simulation_mode=True,
            use_ml_in_simulation=True
        )

        # Prepare tweets for ML processing
        prepared_tweets = agent._prepare_simulation_tweets_for_ml(sample_simulation_tweets)

        # Verify ground truth is removed
        for tweet in prepared_tweets:
            assert "_ground_truth" not in tweet
            assert "text" in tweet  # Raw text should be present
            assert "username" in tweet
            assert "timestamp" in tweet

    def test_ground_truth_preserved_when_ml_disabled(self, mock_environment, sample_simulation_tweets):
        """Test that _ground_truth is kept when use_ml_in_simulation=False."""
        agent = ScoutAgent(
            agent_id="test_scout",
            environment=mock_environment,
            simulation_mode=True,
            use_ml_in_simulation=False
        )

        # Prepare tweets (should return as-is)
        prepared_tweets = agent._prepare_simulation_tweets_for_ml(sample_simulation_tweets)

        # Verify ground truth is preserved
        for i, tweet in enumerate(prepared_tweets):
            assert "_ground_truth" in tweet
            assert tweet["_ground_truth"] == sample_simulation_tweets[i]["_ground_truth"]

    @patch('app.agents.scout_agent.ScoutAgent._process_and_forward_tweets')
    def test_ml_processing_called_in_step(
        self,
        mock_process_forward,
        mock_environment,
        mock_hazard_agent,
        sample_simulation_tweets
    ):
        """Test that step() method processes tweets through ML when enabled."""
        agent = ScoutAgent(
            agent_id="test_scout",
            environment=mock_environment,
            hazard_agent=mock_hazard_agent,
            simulation_mode=True,
            use_ml_in_simulation=True
        )

        # Mock the simulation tweet getter
        agent.simulation_tweets = sample_simulation_tweets
        agent.simulation_index = 0

        # Execute one step
        result = agent.step()

        # Verify processing was called
        assert mock_process_forward.called
        assert len(result) > 0

        # Get the tweets that were passed to processing
        processed_tweets = mock_process_forward.call_args[0][0]

        # Verify ground truth was stripped
        for tweet in processed_tweets:
            assert "_ground_truth" not in tweet

    def test_nlp_processor_extracts_flood_info(self, mock_environment):
        """Test that NLP processor actually processes text and extracts info."""
        agent = ScoutAgent(
            agent_id="test_scout",
            environment=mock_environment,
            simulation_mode=True,
            use_ml_in_simulation=True
        )

        # Test with a sample flood-related text
        test_text = "Baha sa Nangka! Tuhod level, hindi madaan ng kotse!"

        if agent.nlp_processor:
            flood_info = agent.nlp_processor.extract_flood_info(test_text)

            # Verify NLP extracted information
            assert "is_flood_related" in flood_info
            assert "location" in flood_info
            assert "severity" in flood_info
            assert "confidence" in flood_info
            assert "report_type" in flood_info

            # Verify it detected flood-related content
            assert flood_info["is_flood_related"] is True or flood_info["severity"] > 0

    def test_geocoder_adds_coordinates(self, mock_environment):
        """Test that geocoder adds coordinates to NLP results."""
        agent = ScoutAgent(
            agent_id="test_scout",
            environment=mock_environment,
            simulation_mode=True,
            use_ml_in_simulation=True
        )

        if agent.nlp_processor and agent.geocoder:
            # Extract flood info from text
            test_text = "Baha sa Nangka! Tuhod level!"
            flood_info = agent.nlp_processor.extract_flood_info(test_text)

            # Geocode the result
            enhanced_info = agent.geocoder.geocode_nlp_result(flood_info)

            # Verify coordinates were added if location was found
            if enhanced_info.get("location"):
                # Should have coordinates or has_coordinates flag
                assert "coordinates" in enhanced_info or "has_coordinates" in enhanced_info

    def test_full_ml_pipeline(self, mock_environment, mock_hazard_agent):
        """Integration test: Full ML pipeline from raw text to processed report."""
        agent = ScoutAgent(
            agent_id="test_scout",
            environment=mock_environment,
            hazard_agent=mock_hazard_agent,
            simulation_mode=True,
            use_ml_in_simulation=True
        )

        # Create a simple test tweet without ground truth
        test_tweet = {
            "tweet_id": "999999",
            "username": "test_user",
            "text": "Baha sa SM Marikina! Ankle-deep na!",
            "timestamp": "2025-11-20T10:00:00Z",
            "url": "https://x.com/test/999999",
            "replies": "1",
            "retweets": "2",
            "likes": "3",
            "scraped_at": "2025-11-20T10:05:00"
        }

        # Process through NLP and geocoding
        if agent.nlp_processor and agent.geocoder:
            flood_info = agent.nlp_processor.extract_flood_info(test_tweet["text"])
            enhanced_info = agent.geocoder.geocode_nlp_result(flood_info)

            # Verify ML pipeline produced output
            assert enhanced_info["is_flood_related"] is not None
            assert enhanced_info["severity"] is not None
            assert enhanced_info["confidence"] is not None
            assert enhanced_info["report_type"] is not None

            print("\n=== ML Pipeline Output ===")
            print(f"Text: {test_tweet['text']}")
            print(f"Flood-related: {enhanced_info['is_flood_related']}")
            print(f"Location: {enhanced_info.get('location')}")
            print(f"Severity: {enhanced_info['severity']}")
            print(f"Report Type: {enhanced_info['report_type']}")
            print(f"Confidence: {enhanced_info['confidence']:.2f}")
            if enhanced_info.get('coordinates'):
                print(f"Coordinates: {enhanced_info['coordinates']}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
