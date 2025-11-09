# filename: tests/unit/test_hazard_agent.py

"""
Comprehensive unit tests for HazardAgent.

Tests cover:
- Initialization with GeoTIFF service
- Flood scenario configuration
- Data validation (flood and scout data)
- Data processing and fusion
- GeoTIFF-based flood depth queries
- Risk score calculation
- Environment updates
- Data cache management

Target Coverage: 80%+
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

from agents.hazard_agent import HazardAgent


class TestHazardAgentInitialization:
    """Test HazardAgent initialization."""

    def test_init_with_geotiff_service(self):
        """Test initialization when GeoTIFF service is available."""
        mock_env = Mock()
        mock_geotiff = Mock()

        with patch('agents.hazard_agent.get_geotiff_service', return_value=mock_geotiff):
            agent = HazardAgent("test_agent", mock_env)

            assert agent.agent_id == "test_agent"
            assert agent.environment == mock_env
            assert agent.geotiff_service == mock_geotiff
            assert agent.return_period == "rr01"
            assert agent.time_step == 1
            assert agent.flood_data_cache == {}
            assert agent.scout_data_cache == []
            assert agent.risk_weights == {
                "flood_depth": 0.5,
                "crowdsourced": 0.3,
                "historical": 0.2
            }

    def test_init_without_geotiff_service(self):
        """Test initialization when GeoTIFF service fails."""
        mock_env = Mock()

        with patch('agents.hazard_agent.get_geotiff_service', side_effect=Exception("Service unavailable")):
            agent = HazardAgent("test_agent", mock_env)

            assert agent.agent_id == "test_agent"
            assert agent.geotiff_service is None


class TestFloodScenarioConfiguration:
    """Test flood scenario configuration methods."""

    def test_set_flood_scenario_valid_rr01(self):
        """Test setting valid flood scenario rr01."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            agent.set_flood_scenario("rr01", 5)

            assert agent.return_period == "rr01"
            assert agent.time_step == 5

    def test_set_flood_scenario_valid_rr04(self):
        """Test setting valid flood scenario rr04."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            agent.set_flood_scenario("rr04", 18)

            assert agent.return_period == "rr04"
            assert agent.time_step == 18

    def test_set_flood_scenario_invalid_return_period(self):
        """Test setting invalid return period raises ValueError."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            with pytest.raises(ValueError, match="Invalid return_period"):
                agent.set_flood_scenario("rr99", 1)

    def test_set_flood_scenario_invalid_time_step_too_low(self):
        """Test setting time step below 1 raises ValueError."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            with pytest.raises(ValueError, match="Invalid time_step"):
                agent.set_flood_scenario("rr01", 0)

    def test_set_flood_scenario_invalid_time_step_too_high(self):
        """Test setting time step above 18 raises ValueError."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            with pytest.raises(ValueError, match="Invalid time_step"):
                agent.set_flood_scenario("rr01", 19)


class TestDataValidation:
    """Test data validation methods."""

    def test_validate_flood_data_valid(self):
        """Test validation of valid flood data."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            valid_data = {
                "location": "Test Station",
                "flood_depth": 1.5,
                "timestamp": datetime.now()
            }

            assert agent._validate_flood_data(valid_data) is True

    def test_validate_flood_data_missing_location(self):
        """Test validation fails when location is missing."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            invalid_data = {
                "flood_depth": 1.5,
                "timestamp": datetime.now()
            }

            assert agent._validate_flood_data(invalid_data) is False

    def test_validate_flood_data_negative_depth(self):
        """Test validation fails for negative flood depth."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            invalid_data = {
                "location": "Test Station",
                "flood_depth": -1.0,
                "timestamp": datetime.now()
            }

            assert agent._validate_flood_data(invalid_data) is False

    def test_validate_flood_data_excessive_depth(self):
        """Test validation fails for flood depth > 10m."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            invalid_data = {
                "location": "Test Station",
                "flood_depth": 15.0,
                "timestamp": datetime.now()
            }

            assert agent._validate_flood_data(invalid_data) is False

    def test_validate_scout_data_valid(self):
        """Test validation of valid scout data."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            valid_data = {
                "location": "Test Area",
                "severity": 0.7,
                "confidence": 0.8,
                "timestamp": datetime.now()
            }

            assert agent._validate_scout_data(valid_data) is True

    def test_validate_scout_data_invalid_severity(self):
        """Test validation fails for severity > 1.0."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            invalid_data = {
                "location": "Test Area",
                "severity": 1.5,
                "timestamp": datetime.now()
            }

            assert agent._validate_scout_data(invalid_data) is False

    def test_validate_scout_data_invalid_confidence(self):
        """Test validation fails for confidence > 1.0."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            invalid_data = {
                "location": "Test Area",
                "severity": 0.5,
                "confidence": 1.2,
                "timestamp": datetime.now()
            }

            assert agent._validate_scout_data(invalid_data) is False


class TestDataProcessing:
    """Test flood and scout data processing."""

    def test_process_flood_data_valid(self):
        """Test processing valid flood data adds to cache."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            # Mock process_hazard_data to avoid triggering full workflow
            agent.process_hazard_data = Mock()

            flood_data = {
                "location": "Station A",
                "flood_depth": 2.0,
                "timestamp": datetime.now()
            }

            agent.process_flood_data(flood_data)

            assert "Station A" in agent.flood_data_cache
            assert agent.flood_data_cache["Station A"]["flood_depth"] == 2.0

    def test_process_flood_data_invalid_rejected(self):
        """Test invalid flood data is rejected."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            invalid_data = {
                "flood_depth": -1.0,  # Missing location, negative depth
                "timestamp": datetime.now()
            }

            agent.process_flood_data(invalid_data)

            assert len(agent.flood_data_cache) == 0

    def test_process_scout_data_valid(self):
        """Test processing valid scout reports."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            scout_reports = [
                {
                    "location": "Area 1",
                    "severity": 0.6,
                    "confidence": 0.7,
                    "timestamp": datetime.now()
                },
                {
                    "location": "Area 2",
                    "severity": 0.8,
                    "confidence": 0.9,
                    "timestamp": datetime.now()
                }
            ]

            agent.process_scout_data(scout_reports)

            assert len(agent.scout_data_cache) == 2
            assert agent.scout_data_cache[0]["location"] == "Area 1"

    def test_process_scout_data_filters_invalid(self):
        """Test invalid scout reports are filtered out."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            scout_reports = [
                {
                    "location": "Valid Area",
                    "severity": 0.5,
                    "timestamp": datetime.now()
                },
                {
                    "location": "Invalid Area",
                    "severity": 1.5,  # Invalid severity
                    "timestamp": datetime.now()
                }
            ]

            agent.process_scout_data(scout_reports)

            assert len(agent.scout_data_cache) == 1
            assert agent.scout_data_cache[0]["location"] == "Valid Area"


class TestDataFusion:
    """Test data fusion from multiple sources."""

    def test_fuse_data_flood_only(self):
        """Test data fusion with only flood data."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            agent.flood_data_cache = {
                "Station A": {
                    "location": "Station A",
                    "flood_depth": 1.0,
                    "timestamp": datetime.now()
                }
            }

            fused = agent.fuse_data()

            assert "Station A" in fused
            assert fused["Station A"]["flood_depth"] == 1.0
            assert "flood_agent" in fused["Station A"]["sources"]
            assert fused["Station A"]["risk_level"] > 0

    def test_fuse_data_scout_only(self):
        """Test data fusion with only scout data."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            agent.scout_data_cache = [
                {
                    "location": "Area B",
                    "severity": 0.7,
                    "confidence": 0.8,
                    "timestamp": datetime.now()
                }
            ]

            fused = agent.fuse_data()

            assert "Area B" in fused
            assert "scout_agent" in fused["Area B"]["sources"]
            assert fused["Area B"]["risk_level"] > 0

    def test_fuse_data_combined_sources(self):
        """Test data fusion combining flood and scout data."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            agent.flood_data_cache = {
                "Location X": {
                    "location": "Location X",
                    "flood_depth": 1.5,
                    "timestamp": datetime.now()
                }
            }

            agent.scout_data_cache = [
                {
                    "location": "Location X",
                    "severity": 0.6,
                    "confidence": 0.7,
                    "timestamp": datetime.now()
                }
            ]

            fused = agent.fuse_data()

            assert "Location X" in fused
            assert len(fused["Location X"]["sources"]) == 2
            assert "flood_agent" in fused["Location X"]["sources"]
            assert "scout_agent" in fused["Location X"]["sources"]

    def test_fuse_data_risk_normalized(self):
        """Test fused data risk levels are normalized to 0-1."""
        mock_env = Mock()
        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            # Create data that would exceed 1.0 without normalization
            agent.flood_data_cache = {
                "High Risk": {
                    "location": "High Risk",
                    "flood_depth": 5.0,  # Very high depth
                    "timestamp": datetime.now()
                }
            }

            fused = agent.fuse_data()

            # Risk should be capped at 1.0
            assert fused["High Risk"]["risk_level"] <= 1.0


class TestGeoTIFFQueries:
    """Test GeoTIFF flood depth queries."""

    def test_get_flood_depth_at_edge_success(self):
        """Test successful flood depth query for an edge."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        # Mock graph nodes
        mock_graph.nodes = {
            1: {'x': 121.10, 'y': 14.65},
            2: {'x': 121.11, 'y': 14.66}
        }

        mock_geotiff = Mock()
        mock_geotiff.get_flood_depth_at_point = Mock(side_effect=[0.5, 0.7])

        with patch('agents.hazard_agent.get_geotiff_service', return_value=mock_geotiff):
            agent = HazardAgent("test_agent", mock_env)

            depth = agent.get_flood_depth_at_edge(1, 2)

            assert depth == 0.6  # Average of 0.5 and 0.7
            assert mock_geotiff.get_flood_depth_at_point.call_count == 2

    def test_get_flood_depth_at_edge_no_service(self):
        """Test flood depth query returns None when service unavailable."""
        mock_env = Mock()

        with patch('agents.hazard_agent.get_geotiff_service', side_effect=Exception):
            agent = HazardAgent("test_agent", mock_env)

            depth = agent.get_flood_depth_at_edge(1, 2)

            assert depth is None

    def test_get_flood_depth_at_edge_custom_scenario(self):
        """Test flood depth query with custom return period and time step."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.nodes = {
            1: {'x': 121.10, 'y': 14.65},
            2: {'x': 121.11, 'y': 14.66}
        }

        mock_geotiff = Mock()
        mock_geotiff.get_flood_depth_at_point = Mock(return_value=1.2)

        with patch('agents.hazard_agent.get_geotiff_service', return_value=mock_geotiff):
            agent = HazardAgent("test_agent", mock_env)

            depth = agent.get_flood_depth_at_edge(1, 2, "rr03", 12)

            # Verify custom parameters were passed
            calls = mock_geotiff.get_flood_depth_at_point.call_args_list
            assert calls[0][0][2] == "rr03"  # return_period
            assert calls[0][0][3] == 12      # time_step

    def test_get_edge_flood_depths_bulk_query(self):
        """Test bulk flood depth query for all edges."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        # Mock 3 edges
        mock_graph.edges = Mock(return_value=[
            (1, 2, 0),
            (2, 3, 0),
            (3, 4, 0)
        ])

        mock_graph.nodes = {
            1: {'x': 121.10, 'y': 14.65},
            2: {'x': 121.11, 'y': 14.66},
            3: {'x': 121.12, 'y': 14.67},
            4: {'x': 121.13, 'y': 14.68}
        }

        mock_geotiff = Mock()
        # Return depths: 0.5m, 0.7m (edge 1-2), 0.0m, 0.0m (edge 2-3), 1.5m, 1.2m (edge 3-4)
        mock_geotiff.get_flood_depth_at_point = Mock(
            side_effect=[0.5, 0.7, 0.0, 0.0, 1.5, 1.2]
        )

        with patch('agents.hazard_agent.get_geotiff_service', return_value=mock_geotiff):
            agent = HazardAgent("test_agent", mock_env)

            depths = agent.get_edge_flood_depths()

            # Only edges with depth > 0.01m should be included
            assert len(depths) == 2  # Edge 1-2 and 3-4
            assert (1, 2, 0) in depths
            assert (3, 4, 0) in depths
            assert depths[(1, 2, 0)] == 0.6   # Average of 0.5 and 0.7
            assert depths[(3, 4, 0)] == 1.35  # Average of 1.5 and 1.2


class TestRiskCalculation:
    """Test risk score calculation with GeoTIFF integration."""

    def test_calculate_risk_scores_depth_mapping_low(self):
        """Test risk score calculation for low flood depth (0-0.3m)."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.edges = Mock(return_value=[(1, 2, 0)])

        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            # Mock get_edge_flood_depths to return low depth
            agent.get_edge_flood_depths = Mock(return_value={
                (1, 2, 0): 0.2  # 0.2m depth
            })

            risk_scores = agent.calculate_risk_scores({})

            # Risk = depth * 0.5 (weight) = 0.2 * 0.5 = 0.1
            assert (1, 2, 0) in risk_scores
            assert risk_scores[(1, 2, 0)] == pytest.approx(0.1, rel=0.01)

    def test_calculate_risk_scores_depth_mapping_moderate(self):
        """Test risk score calculation for moderate flood depth (0.3-0.6m)."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.edges = Mock(return_value=[(1, 2, 0)])

        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            agent.get_edge_flood_depths = Mock(return_value={
                (1, 2, 0): 0.5  # 0.5m depth
            })

            risk_scores = agent.calculate_risk_scores({})

            # Risk = (0.3 + (0.5 - 0.3) * 1.0) * 0.5 = 0.5 * 0.5 = 0.25
            assert (1, 2, 0) in risk_scores
            assert risk_scores[(1, 2, 0)] == pytest.approx(0.25, rel=0.01)

    def test_calculate_risk_scores_depth_mapping_high(self):
        """Test risk score calculation for high flood depth (0.6-1.0m)."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.edges = Mock(return_value=[(1, 2, 0)])

        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            agent.get_edge_flood_depths = Mock(return_value={
                (1, 2, 0): 0.8  # 0.8m depth
            })

            risk_scores = agent.calculate_risk_scores({})

            # Risk = (0.6 + (0.8 - 0.6) * 0.5) * 0.5 = 0.7 * 0.5 = 0.35
            assert (1, 2, 0) in risk_scores
            assert risk_scores[(1, 2, 0)] == pytest.approx(0.35, rel=0.01)

    def test_calculate_risk_scores_depth_mapping_critical(self):
        """Test risk score calculation for critical flood depth (>1.0m)."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.edges = Mock(return_value=[(1, 2, 0)])

        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            agent.get_edge_flood_depths = Mock(return_value={
                (1, 2, 0): 2.0  # 2.0m depth - critical
            })

            risk_scores = agent.calculate_risk_scores({})

            # Risk = min(0.8 + (2.0 - 1.0) * 0.2, 1.0) * 0.5 = 1.0 * 0.5 = 0.5
            assert (1, 2, 0) in risk_scores
            assert risk_scores[(1, 2, 0)] == pytest.approx(0.5, rel=0.01)

    def test_calculate_risk_scores_with_environmental_factors(self):
        """Test risk calculation combines GeoTIFF + environmental data."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.edges = Mock(return_value=[(1, 2, 0)])

        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            agent.get_edge_flood_depths = Mock(return_value={
                (1, 2, 0): 0.5  # Base GeoTIFF risk
            })

            # Fused data with high environmental risk
            fused_data = {
                "Station A": {
                    "risk_level": 0.8,  # High environmental risk
                    "sources": ["flood_agent"]
                }
            }

            risk_scores = agent.calculate_risk_scores(fused_data)

            # Should combine GeoTIFF risk with environmental factor
            assert (1, 2, 0) in risk_scores
            assert risk_scores[(1, 2, 0)] > 0.25  # Greater than base GeoTIFF risk alone


class TestEnvironmentUpdate:
    """Test environment updates with risk scores."""

    def test_update_environment_success(self):
        """Test successful environment update."""
        mock_env = Mock()
        mock_env.update_edge_risk = Mock()

        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            risk_scores = {
                (1, 2, 0): 0.5,
                (2, 3, 0): 0.7
            }

            agent.update_environment(risk_scores)

            assert mock_env.update_edge_risk.call_count == 2

    def test_update_environment_no_update_method(self):
        """Test environment update handles missing update method gracefully."""
        mock_env = Mock()
        del mock_env.update_edge_risk  # Remove the method

        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            risk_scores = {(1, 2, 0): 0.5}

            # Should not raise exception
            agent.update_environment(risk_scores)


class TestDataCacheManagement:
    """Test cache management and data cleanup."""

    def test_clear_old_data_removes_expired_flood_data(self):
        """Test old flood data is removed from cache."""
        mock_env = Mock()

        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            # Add old and new data
            old_time = datetime.now() - timedelta(hours=2)
            new_time = datetime.now()

            agent.flood_data_cache = {
                "Old Station": {
                    "location": "Old Station",
                    "flood_depth": 1.0,
                    "timestamp": old_time
                },
                "New Station": {
                    "location": "New Station",
                    "flood_depth": 0.5,
                    "timestamp": new_time
                }
            }

            agent.clear_old_data(max_age_seconds=3600)  # 1 hour

            assert "Old Station" not in agent.flood_data_cache
            assert "New Station" in agent.flood_data_cache

    def test_clear_old_data_removes_expired_scout_data(self):
        """Test old scout data is removed from cache."""
        mock_env = Mock()

        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            old_time = datetime.now() - timedelta(hours=2)
            new_time = datetime.now()

            agent.scout_data_cache = [
                {
                    "location": "Old Report",
                    "severity": 0.6,
                    "timestamp": old_time
                },
                {
                    "location": "New Report",
                    "severity": 0.5,
                    "timestamp": new_time
                }
            ]

            agent.clear_old_data(max_age_seconds=3600)

            assert len(agent.scout_data_cache) == 1
            assert agent.scout_data_cache[0]["location"] == "New Report"


class TestProcessAndUpdate:
    """Test complete process and update workflow."""

    def test_process_and_update_workflow(self):
        """Test complete hazard processing workflow."""
        mock_env = Mock()
        mock_env.update_edge_risk = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.edges = Mock(return_value=[(1, 2, 0)])

        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            # Setup test data
            agent.flood_data_cache = {
                "Station A": {
                    "location": "Station A",
                    "flood_depth": 1.0,
                    "timestamp": datetime.now()
                }
            }

            agent.get_edge_flood_depths = Mock(return_value={
                (1, 2, 0): 0.5
            })

            result = agent.process_and_update()

            assert result["locations_processed"] == 1
            assert result["edges_updated"] == 1
            assert "timestamp" in result

    def test_step_calls_process_and_update(self):
        """Test agent step calls process_and_update when data available."""
        mock_env = Mock()

        with patch('agents.hazard_agent.get_geotiff_service'):
            agent = HazardAgent("test_agent", mock_env)

            agent.process_and_update = Mock(return_value={"edges_updated": 5})

            # Add some data to trigger processing
            agent.flood_data_cache = {"Station": {"location": "Station", "flood_depth": 1.0, "timestamp": datetime.now()}}

            agent.step()

            agent.process_and_update.assert_called_once()
