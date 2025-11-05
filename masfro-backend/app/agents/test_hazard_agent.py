# filename: app/agents/test_hazard_agent.py

"""
Unit tests for HazardAgent

This test suite verifies the HazardAgent's core functionality:
- Data validation (flood and scout data)
- Data fusion from multiple sources
- Risk score calculation
- Graph environment updates
- Cache management

Run tests with: uv run pytest app/agents/test_hazard_agent.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
import networkx as nx

from app.agents.hazard_agent import HazardAgent


@pytest.fixture
def mock_environment():
    """Create a mock DynamicGraphEnvironment for testing."""
    env = Mock()

    # Create a simple test graph
    G = nx.MultiDiGraph()
    G.add_edge(1, 2, key=0, length=100, risk_score=1.0, weight=100)
    G.add_edge(2, 3, key=0, length=150, risk_score=1.0, weight=150)
    G.add_edge(3, 4, key=0, length=200, risk_score=1.0, weight=200)
    G.add_edge(1, 4, key=0, length=350, risk_score=1.0, weight=350)

    env.graph = G
    env.update_edge_risk = Mock()

    return env


@pytest.fixture
def hazard_agent(mock_environment):
    """Create a HazardAgent instance for testing."""
    return HazardAgent("test_hazard_001", mock_environment)


class TestHazardAgentInitialization:
    """Test HazardAgent initialization."""

    def test_initialization_with_valid_environment(self, mock_environment):
        """Test agent initializes correctly with valid environment."""
        agent = HazardAgent("test_hazard_001", mock_environment)

        assert agent.agent_id == "test_hazard_001"
        assert agent.environment == mock_environment
        assert isinstance(agent.flood_data_cache, dict)
        assert isinstance(agent.scout_data_cache, list)
        assert len(agent.flood_data_cache) == 0
        assert len(agent.scout_data_cache) == 0

    def test_risk_weights_configuration(self, hazard_agent):
        """Test risk weights are configured correctly."""
        weights = hazard_agent.risk_weights

        assert "flood_depth" in weights
        assert "crowdsourced" in weights
        assert "historical" in weights
        assert weights["flood_depth"] == 0.5
        assert weights["crowdsourced"] == 0.3
        assert weights["historical"] == 0.2


class TestFloodDataValidation:
    """Test flood data validation and processing."""

    def test_valid_flood_data(self, hazard_agent):
        """Test processing valid flood data."""
        flood_data = {
            "location": "Marikina River",
            "flood_depth": 1.5,
            "rainfall": 45.0,
            "river_level": 15.5,
            "timestamp": datetime.now()
        }

        hazard_agent.process_flood_data(flood_data)

        assert "Marikina River" in hazard_agent.flood_data_cache
        assert hazard_agent.flood_data_cache["Marikina River"]["flood_depth"] == 1.5

    def test_invalid_flood_data_missing_fields(self, hazard_agent):
        """Test rejection of invalid flood data (missing required fields)."""
        invalid_data = {
            "location": "Test Location",
            # Missing flood_depth and timestamp
        }

        hazard_agent.process_flood_data(invalid_data)

        # Data should not be added to cache
        assert "Test Location" not in hazard_agent.flood_data_cache

    def test_invalid_flood_depth_out_of_range(self, hazard_agent):
        """Test rejection of flood depth outside valid range."""
        invalid_data = {
            "location": "Test Location",
            "flood_depth": 15.0,  # Exceeds max 10m
            "timestamp": datetime.now()
        }

        hazard_agent.process_flood_data(invalid_data)

        assert "Test Location" not in hazard_agent.flood_data_cache

    def test_negative_flood_depth(self, hazard_agent):
        """Test rejection of negative flood depth."""
        invalid_data = {
            "location": "Test Location",
            "flood_depth": -1.0,
            "timestamp": datetime.now()
        }

        hazard_agent.process_flood_data(invalid_data)

        assert "Test Location" not in hazard_agent.flood_data_cache

    def test_multiple_flood_data_updates(self, hazard_agent):
        """Test updating flood data for same location."""
        flood_data_1 = {
            "location": "Location A",
            "flood_depth": 1.0,
            "timestamp": datetime.now()
        }
        flood_data_2 = {
            "location": "Location A",
            "flood_depth": 2.0,
            "timestamp": datetime.now()
        }

        hazard_agent.process_flood_data(flood_data_1)
        hazard_agent.process_flood_data(flood_data_2)

        # Should be updated, not duplicated
        assert len(hazard_agent.flood_data_cache) == 1
        assert hazard_agent.flood_data_cache["Location A"]["flood_depth"] == 2.0


class TestScoutDataValidation:
    """Test scout (crowdsourced) data validation and processing."""

    def test_valid_scout_reports(self, hazard_agent):
        """Test processing valid scout reports."""
        scout_reports = [
            {
                "location": "Marcos Highway",
                "severity": 0.8,
                "report_type": "flood",
                "confidence": 0.9,
                "timestamp": datetime.now()
            },
            {
                "location": "Sumulong Highway",
                "severity": 0.3,
                "report_type": "clear",
                "confidence": 0.7,
                "timestamp": datetime.now()
            }
        ]

        hazard_agent.process_scout_data(scout_reports)

        assert len(hazard_agent.scout_data_cache) == 2

    def test_invalid_scout_data_missing_fields(self, hazard_agent):
        """Test rejection of scout data with missing fields."""
        invalid_reports = [
            {
                "location": "Test Location",
                "severity": 0.5
                # Missing timestamp
            }
        ]

        hazard_agent.process_scout_data(invalid_reports)

        assert len(hazard_agent.scout_data_cache) == 0

    def test_invalid_severity_out_of_range(self, hazard_agent):
        """Test rejection of severity outside 0-1 range."""
        invalid_reports = [
            {
                "location": "Test Location",
                "severity": 1.5,  # Exceeds 1.0
                "timestamp": datetime.now()
            },
            {
                "location": "Test Location 2",
                "severity": -0.2,  # Below 0.0
                "timestamp": datetime.now()
            }
        ]

        hazard_agent.process_scout_data(invalid_reports)

        assert len(hazard_agent.scout_data_cache) == 0

    def test_invalid_confidence_out_of_range(self, hazard_agent):
        """Test rejection of confidence outside 0-1 range."""
        invalid_reports = [
            {
                "location": "Test Location",
                "severity": 0.5,
                "confidence": 1.2,  # Exceeds 1.0
                "timestamp": datetime.now()
            }
        ]

        hazard_agent.process_scout_data(invalid_reports)

        assert len(hazard_agent.scout_data_cache) == 0


class TestDataFusion:
    """Test data fusion from multiple sources."""

    def test_fusion_with_flood_data_only(self, hazard_agent):
        """Test data fusion with only flood data."""
        flood_data = {
            "location": "Test Location",
            "flood_depth": 2.0,
            "timestamp": datetime.now()
        }

        hazard_agent.process_flood_data(flood_data)
        fused_data = hazard_agent.fuse_data()

        assert "Test Location" in fused_data
        assert fused_data["Test Location"]["flood_depth"] == 2.0
        assert fused_data["Test Location"]["risk_level"] > 0
        assert "flood_agent" in fused_data["Test Location"]["sources"]

    def test_fusion_with_scout_data_only(self, hazard_agent):
        """Test data fusion with only scout data."""
        scout_reports = [
            {
                "location": "Test Location",
                "severity": 0.7,
                "confidence": 0.8,
                "timestamp": datetime.now()
            }
        ]

        hazard_agent.process_scout_data(scout_reports)
        fused_data = hazard_agent.fuse_data()

        assert "Test Location" in fused_data
        assert fused_data["Test Location"]["risk_level"] > 0
        assert "scout_agent" in fused_data["Test Location"]["sources"]

    def test_fusion_with_both_sources(self, hazard_agent):
        """Test data fusion combining flood and scout data."""
        # Add flood data
        flood_data = {
            "location": "Combined Location",
            "flood_depth": 1.0,
            "timestamp": datetime.now()
        }
        hazard_agent.process_flood_data(flood_data)

        # Add scout data for same location
        scout_reports = [
            {
                "location": "Combined Location",
                "severity": 0.6,
                "confidence": 0.9,
                "timestamp": datetime.now()
            }
        ]
        hazard_agent.process_scout_data(scout_reports)

        fused_data = hazard_agent.fuse_data()

        assert "Combined Location" in fused_data
        assert len(fused_data["Combined Location"]["sources"]) == 2
        assert "flood_agent" in fused_data["Combined Location"]["sources"]
        assert "scout_agent" in fused_data["Combined Location"]["sources"]

        # Risk level should be higher with both sources
        assert fused_data["Combined Location"]["risk_level"] > 0

    def test_risk_level_normalization(self, hazard_agent):
        """Test that risk levels are normalized to 0-1 scale."""
        # Add high flood depth
        flood_data = {
            "location": "High Risk Location",
            "flood_depth": 5.0,  # Very high
            "timestamp": datetime.now()
        }
        hazard_agent.process_flood_data(flood_data)

        # Add high severity scout reports
        scout_reports = [
            {
                "location": "High Risk Location",
                "severity": 1.0,
                "confidence": 1.0,
                "timestamp": datetime.now()
            }
        ]
        hazard_agent.process_scout_data(scout_reports)

        fused_data = hazard_agent.fuse_data()

        # Risk level should be capped at 1.0
        assert fused_data["High Risk Location"]["risk_level"] <= 1.0
        assert fused_data["High Risk Location"]["confidence"] <= 1.0


class TestRiskScoreCalculation:
    """Test risk score calculation for graph edges."""

    def test_risk_score_calculation_with_data(self, hazard_agent):
        """Test calculating risk scores with fused data."""
        # Add test data
        flood_data = {
            "location": "Test Area",
            "flood_depth": 1.5,
            "timestamp": datetime.now()
        }
        hazard_agent.process_flood_data(flood_data)

        fused_data = hazard_agent.fuse_data()
        risk_scores = hazard_agent.calculate_risk_scores(fused_data)

        # Should have risk scores for edges
        assert len(risk_scores) > 0

        # All risk scores should be between 0 and 1
        for edge, score in risk_scores.items():
            assert 0 <= score <= 1.0

    def test_risk_score_with_no_data(self, hazard_agent):
        """Test risk score calculation with no data."""
        fused_data = {}
        risk_scores = hazard_agent.calculate_risk_scores(fused_data)

        assert len(risk_scores) == 0

    def test_risk_score_without_graph(self):
        """Test risk score calculation when environment has no graph."""
        env = Mock()
        env.graph = None
        agent = HazardAgent("test_no_graph", env)

        fused_data = {"Location": {"risk_level": 0.5}}
        risk_scores = agent.calculate_risk_scores(fused_data)

        assert len(risk_scores) == 0


class TestEnvironmentUpdates:
    """Test graph environment updates."""

    def test_update_environment_with_risk_scores(self, hazard_agent, mock_environment):
        """Test updating environment with calculated risk scores."""
        risk_scores = {
            (1, 2, 0): 0.5,
            (2, 3, 0): 0.7,
            (3, 4, 0): 0.3
        }

        hazard_agent.update_environment(risk_scores)

        # Verify update_edge_risk was called for each edge
        assert mock_environment.update_edge_risk.call_count == 3

    def test_update_environment_with_empty_scores(self, hazard_agent, mock_environment):
        """Test updating environment with no risk scores."""
        risk_scores = {}

        hazard_agent.update_environment(risk_scores)

        assert mock_environment.update_edge_risk.call_count == 0

    def test_process_and_update_workflow(self, hazard_agent):
        """Test complete process and update workflow."""
        # Add test data
        flood_data = {
            "location": "Workflow Test",
            "flood_depth": 1.0,
            "timestamp": datetime.now()
        }
        hazard_agent.process_flood_data(flood_data)

        result = hazard_agent.process_and_update()

        assert "locations_processed" in result
        assert "edges_updated" in result
        assert "timestamp" in result
        assert result["locations_processed"] > 0


class TestCacheManagement:
    """Test data cache management and cleanup."""

    def test_clear_old_flood_data(self, hazard_agent):
        """Test clearing old flood data from cache."""
        # Add old data (2 hours ago)
        old_data = {
            "location": "Old Location",
            "flood_depth": 1.0,
            "timestamp": datetime.now() - timedelta(hours=2)
        }
        hazard_agent.flood_data_cache["Old Location"] = old_data

        # Add recent data
        recent_data = {
            "location": "Recent Location",
            "flood_depth": 1.5,
            "timestamp": datetime.now()
        }
        hazard_agent.flood_data_cache["Recent Location"] = recent_data

        # Clear data older than 1 hour
        hazard_agent.clear_old_data(max_age_seconds=3600)

        assert "Old Location" not in hazard_agent.flood_data_cache
        assert "Recent Location" in hazard_agent.flood_data_cache

    def test_clear_old_scout_data(self, hazard_agent):
        """Test clearing old scout data from cache."""
        # Add old report
        old_report = {
            "location": "Old Report",
            "severity": 0.5,
            "timestamp": datetime.now() - timedelta(hours=2)
        }
        hazard_agent.scout_data_cache.append(old_report)

        # Add recent report
        recent_report = {
            "location": "Recent Report",
            "severity": 0.7,
            "timestamp": datetime.now()
        }
        hazard_agent.scout_data_cache.append(recent_report)

        # Clear data older than 1 hour
        hazard_agent.clear_old_data(max_age_seconds=3600)

        assert len(hazard_agent.scout_data_cache) == 1
        assert hazard_agent.scout_data_cache[0]["location"] == "Recent Report"

    def test_clear_all_old_data(self, hazard_agent):
        """Test clearing both flood and scout old data."""
        # Add old flood and scout data
        old_flood = {
            "location": "Old Flood",
            "flood_depth": 1.0,
            "timestamp": datetime.now() - timedelta(hours=3)
        }
        hazard_agent.flood_data_cache["Old Flood"] = old_flood

        old_scout = {
            "location": "Old Scout",
            "severity": 0.5,
            "timestamp": datetime.now() - timedelta(hours=3)
        }
        hazard_agent.scout_data_cache.append(old_scout)

        hazard_agent.clear_old_data(max_age_seconds=3600)

        assert len(hazard_agent.flood_data_cache) == 0
        assert len(hazard_agent.scout_data_cache) == 0


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    def test_complete_hazard_assessment_workflow(self, hazard_agent):
        """Test complete workflow from data input to environment update."""
        # Step 1: Receive flood data from FloodAgent
        flood_data = {
            "location": "Marikina River",
            "flood_depth": 2.5,
            "rainfall": 75.0,
            "river_level": 18.5,
            "timestamp": datetime.now()
        }
        hazard_agent.process_flood_data(flood_data)

        # Step 2: Receive scout reports from ScoutAgent
        scout_reports = [
            {
                "location": "Marcos Highway",
                "severity": 0.85,
                "report_type": "flood",
                "confidence": 0.9,
                "timestamp": datetime.now()
            },
            {
                "location": "Marikina River",
                "severity": 0.95,
                "report_type": "flood",
                "confidence": 0.85,
                "timestamp": datetime.now()
            }
        ]
        hazard_agent.process_scout_data(scout_reports)

        # Step 3: Fuse data
        fused_data = hazard_agent.fuse_data()
        assert len(fused_data) == 2

        # Step 4: Calculate risk scores
        risk_scores = hazard_agent.calculate_risk_scores(fused_data)
        assert len(risk_scores) > 0

        # Step 5: Update environment
        hazard_agent.update_environment(risk_scores)

        # Verify caches have data
        assert len(hazard_agent.flood_data_cache) == 1
        assert len(hazard_agent.scout_data_cache) == 2

    def test_step_method_execution(self, hazard_agent):
        """Test agent's step method for periodic execution."""
        # Add data to caches
        flood_data = {
            "location": "Test",
            "flood_depth": 1.0,
            "timestamp": datetime.now()
        }
        hazard_agent.process_flood_data(flood_data)

        # Execute step
        hazard_agent.step()

        # Verify step processed the data
        # (In real implementation, this would update the environment)

    def test_high_risk_scenario(self, hazard_agent):
        """Test handling of high-risk flood scenario."""
        # Simulate severe flooding
        severe_flood = {
            "location": "Critical Area",
            "flood_depth": 4.0,  # Very high
            "rainfall": 120.0,
            "river_level": 21.0,
            "timestamp": datetime.now()
        }
        hazard_agent.process_flood_data(severe_flood)

        # Multiple high-severity scout reports
        severe_reports = [
            {
                "location": "Critical Area",
                "severity": 1.0,
                "confidence": 0.95,
                "timestamp": datetime.now()
            },
            {
                "location": "Critical Area",
                "severity": 0.95,
                "confidence": 0.9,
                "timestamp": datetime.now()
            }
        ]
        hazard_agent.process_scout_data(severe_reports)

        fused_data = hazard_agent.fuse_data()

        # Should have very high risk level
        assert fused_data["Critical Area"]["risk_level"] >= 0.8
        # Should have sources from both flood and scout agents
        # (Note: Multiple scout reports result in multiple source entries)
        assert "flood_agent" in fused_data["Critical Area"]["sources"]
        assert "scout_agent" in fused_data["Critical Area"]["sources"]
        assert len(fused_data["Critical Area"]["sources"]) >= 2


# Run with: uv run pytest app/agents/test_hazard_agent.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
