# filename: tests/unit/test_routing_agent.py

"""
Comprehensive unit tests for RoutingAgent.

Tests cover:
- Initialization and configuration
- Route calculation with risk-aware A*
- Nearest node finding
- Evacuation center routing
- Alternative route calculation
- Warning generation
- Preference handling
- Edge cases and error handling

Target Coverage: 80%+
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from pathlib import Path
import pandas as pd
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

from agents.routing_agent import RoutingAgent


class TestRoutingAgentInitialization:
    """Test RoutingAgent initialization."""

    def test_init_with_default_weights(self):
        """Test initialization with default risk/distance weights."""
        mock_env = Mock()
        mock_df = pd.DataFrame([
            {"name": "Center1", "latitude": 14.65, "longitude": 121.10, "capacity": 100, "type": "school"}
        ])

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=mock_df):
            agent = RoutingAgent("test_routing", mock_env)

            assert agent.agent_id == "test_routing"
            assert agent.environment == mock_env
            assert agent.risk_weight == 0.6
            assert agent.distance_weight == 0.4
            assert len(agent.evacuation_centers) == 1

    def test_init_with_custom_weights(self):
        """Test initialization with custom risk/distance weights."""
        mock_env = Mock()
        mock_df = pd.DataFrame()

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=mock_df):
            agent = RoutingAgent("test_routing", mock_env, risk_weight=0.8, distance_weight=0.2)

            assert agent.risk_weight == 0.8
            assert agent.distance_weight == 0.2

    def test_init_loads_evacuation_centers(self):
        """Test that initialization loads evacuation centers."""
        mock_env = Mock()

        with patch.object(RoutingAgent, '_load_evacuation_centers') as mock_load:
            mock_load.return_value = pd.DataFrame([
                {"name": "Center1", "latitude": 14.65, "longitude": 121.10}
            ])

            agent = RoutingAgent("test_routing", mock_env)

            mock_load.assert_called_once()
            assert len(agent.evacuation_centers) == 1


class TestRouteCalculation:
    """Test route calculation functionality."""

    def test_calculate_route_success(self):
        """Test successful route calculation."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        # Mock graph nodes for nearest node search
        mock_graph.nodes.return_value = [1, 2]
        mock_graph.nodes.__getitem__ = lambda self, x: {'x': 121.10, 'y': 14.65} if x == 1 else {'x': 121.11, 'y': 14.66}

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            # Mock the algorithm functions - patch where they're imported inside calculate_route
            with patch('app.algorithms.risk_aware_astar.risk_aware_astar') as mock_astar, \
                 patch('app.algorithms.risk_aware_astar.get_path_coordinates') as mock_coords, \
                 patch('app.algorithms.risk_aware_astar.calculate_path_metrics') as mock_metrics:

                mock_astar.return_value = [1, 2]
                mock_coords.return_value = [(14.65, 121.10), (14.66, 121.11)]
                mock_metrics.return_value = {
                    "total_distance": 1000,
                    "estimated_time": 5,
                    "average_risk": 0.3,
                    "max_risk": 0.5,
                    "num_segments": 1
                }

                result = agent.calculate_route((14.65, 121.10), (14.66, 121.11))

                assert "path" in result
                assert len(result["path"]) == 2
                assert result["distance"] == 1000
                assert result["risk_level"] == 0.3
                assert result["max_risk"] == 0.5

    def test_calculate_route_no_graph(self):
        """Test route calculation fails without graph."""
        mock_env = Mock()
        mock_env.graph = None

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            with pytest.raises(ValueError, match="Graph environment not loaded"):
                agent.calculate_route((14.65, 121.10), (14.66, 121.11))

    def test_calculate_route_no_path_found(self):
        """Test route calculation when no path exists."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.nodes.return_value = [1, 2]
        mock_graph.nodes.__getitem__ = lambda self, x: {'x': 121.10, 'y': 14.65}

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            with patch('app.algorithms.risk_aware_astar.risk_aware_astar') as mock_astar:
                mock_astar.return_value = None  # No path found

                result = agent.calculate_route((14.65, 121.10), (14.66, 121.11))

                assert result["path"] == []
                assert result["risk_level"] == 1.0
                assert "No safe route found" in result["warnings"]

    def test_calculate_route_with_avoid_floods_preference(self):
        """Test route calculation with avoid_floods preference."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.nodes.return_value = [1, 2]
        mock_graph.nodes.__getitem__ = lambda self, x: {'x': 121.10, 'y': 14.65}

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            with patch('app.algorithms.risk_aware_astar.risk_aware_astar') as mock_astar, \
                 patch('app.algorithms.risk_aware_astar.get_path_coordinates'), \
                 patch('app.algorithms.risk_aware_astar.calculate_path_metrics') as mock_metrics:

                mock_astar.return_value = [1, 2]
                mock_metrics.return_value = {
                    "total_distance": 1000,
                    "estimated_time": 5,
                    "average_risk": 0.1,
                    "max_risk": 0.2,
                    "num_segments": 1
                }

                preferences = {"avoid_floods": True}
                agent.calculate_route((14.65, 121.10), (14.66, 121.11), preferences)

                # Verify risk_weight was increased to 0.8
                call_kwargs = mock_astar.call_args[1]
                assert call_kwargs['risk_weight'] == 0.8
                assert call_kwargs['distance_weight'] == 0.2

    def test_calculate_route_with_fastest_preference(self):
        """Test route calculation with fastest preference."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.nodes.return_value = [1, 2]
        mock_graph.nodes.__getitem__ = lambda self, x: {'x': 121.10, 'y': 14.65}

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            with patch('app.algorithms.risk_aware_astar.risk_aware_astar') as mock_astar, \
                 patch('app.algorithms.risk_aware_astar.get_path_coordinates'), \
                 patch('app.algorithms.risk_aware_astar.calculate_path_metrics') as mock_metrics:

                mock_astar.return_value = [1, 2]
                mock_metrics.return_value = {
                    "total_distance": 800,
                    "estimated_time": 3,
                    "average_risk": 0.6,
                    "max_risk": 0.7,
                    "num_segments": 1
                }

                preferences = {"fastest": True}
                agent.calculate_route((14.65, 121.10), (14.66, 121.11), preferences)

                # Verify distance_weight was increased
                call_kwargs = mock_astar.call_args[1]
                assert call_kwargs['risk_weight'] == 0.3
                assert call_kwargs['distance_weight'] == 0.7


class TestNearestNodeFinding:
    """Test nearest node finding functionality."""

    def test_find_nearest_node_success(self):
        """Test finding nearest node to coordinates."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        # Create mock nodes
        mock_graph.nodes.return_value = [1, 2, 3]
        node_data = {
            1: {'x': 121.10, 'y': 14.65},
            2: {'x': 121.11, 'y': 14.66},
            3: {'x': 121.12, 'y': 14.67}
        }
        mock_graph.nodes.__getitem__ = lambda self, x: node_data[x]

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            # Find nearest node to coordinate close to node 1
            nearest = agent._find_nearest_node((14.65, 121.10))

            assert nearest == 1

    def test_find_nearest_node_exceeds_max_distance(self):
        """Test finding nearest node when all nodes exceed max distance."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.nodes.return_value = [1]
        mock_graph.nodes.__getitem__ = lambda self, x: {'x': 121.10, 'y': 14.65}

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            # Very far coordinate (should exceed 500m default max)
            nearest = agent._find_nearest_node((15.00, 122.00), max_distance=500)

            assert nearest is None

    def test_find_nearest_node_no_graph(self):
        """Test finding nearest node when graph is not loaded."""
        mock_env = Mock()
        mock_env.graph = None

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            nearest = agent._find_nearest_node((14.65, 121.10))

            assert nearest is None


class TestEvacuationCenterRouting:
    """Test evacuation center routing functionality."""

    def test_find_nearest_evacuation_center_success(self):
        """Test finding nearest evacuation center."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.nodes.return_value = [1, 2]
        mock_graph.nodes.__getitem__ = lambda self, x: {'x': 121.10, 'y': 14.65}

        # Mock evacuation centers
        centers_df = pd.DataFrame([
            {"name": "Center1", "latitude": 14.65, "longitude": 121.10, "capacity": 100, "type": "school"},
            {"name": "Center2", "latitude": 14.66, "longitude": 121.11, "capacity": 200, "type": "gym"}
        ])

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=centers_df):
            agent = RoutingAgent("test_routing", mock_env)

            with patch('app.algorithms.path_optimizer.optimize_evacuation_route') as mock_optimize, \
                 patch('app.algorithms.risk_aware_astar.get_path_coordinates') as mock_coords:

                mock_optimize.return_value = {
                    "center": {"name": "Center1"},
                    "path": [1, 2],
                    "distance": 500
                }
                mock_coords.return_value = [(14.65, 121.10), (14.65, 121.10)]

                result = agent.find_nearest_evacuation_center((14.65, 121.10))

                assert result is not None
                assert result["center"]["name"] == "Center1"
                assert "path" in result

    def test_find_nearest_evacuation_center_no_centers(self):
        """Test finding evacuation center when none are loaded."""
        mock_env = Mock()

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            result = agent.find_nearest_evacuation_center((14.65, 121.10))

            assert result is None

    def test_find_nearest_evacuation_center_max_centers_limit(self):
        """Test that max_centers parameter limits search."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.nodes.return_value = [1]
        mock_graph.nodes.__getitem__ = lambda self, x: {'x': 121.10, 'y': 14.65}

        # Create 10 centers
        centers_list = [
            {"name": f"Center{i}", "latitude": 14.65, "longitude": 121.10, "capacity": 100, "type": "school"}
            for i in range(10)
        ]
        centers_df = pd.DataFrame(centers_list)

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=centers_df):
            agent = RoutingAgent("test_routing", mock_env)

            with patch('app.algorithms.path_optimizer.optimize_evacuation_route') as mock_optimize:
                mock_optimize.return_value = None

                agent.find_nearest_evacuation_center((14.65, 121.10), max_centers=3)

                # Verify only first 3 centers were processed
                call_args = mock_optimize.call_args[0]
                centers_passed = call_args[2]
                assert len(centers_passed) <= 3


class TestAlternativeRoutes:
    """Test alternative routes calculation."""

    def test_calculate_alternative_routes_success(self):
        """Test calculating k alternative routes."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.nodes.return_value = [1, 2]
        mock_graph.nodes.__getitem__ = lambda self, x: {'x': 121.10, 'y': 14.65}

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            with patch('app.algorithms.path_optimizer.find_k_shortest_paths') as mock_k_paths, \
                 patch('app.algorithms.risk_aware_astar.get_path_coordinates') as mock_coords:

                mock_k_paths.return_value = [
                    {
                        "rank": 1,
                        "path": [1, 2],
                        "metrics": {
                            "total_distance": 1000,
                            "estimated_time": 5,
                            "average_risk": 0.3,
                            "max_risk": 0.5
                        }
                    },
                    {
                        "rank": 2,
                        "path": [1, 3, 2],
                        "metrics": {
                            "total_distance": 1200,
                            "estimated_time": 6,
                            "average_risk": 0.2,
                            "max_risk": 0.4
                        }
                    }
                ]
                mock_coords.return_value = [(14.65, 121.10), (14.66, 121.11)]

                routes = agent.calculate_alternative_routes((14.65, 121.10), (14.66, 121.11), k=2)

                assert len(routes) == 2
                assert routes[0]["rank"] == 1
                assert routes[0]["distance"] == 1000
                assert routes[1]["rank"] == 2
                assert routes[1]["distance"] == 1200

    def test_calculate_alternative_routes_no_mapping(self):
        """Test alternative routes when coordinates can't be mapped."""
        mock_env = Mock()
        mock_graph = MagicMock()
        mock_env.graph = mock_graph

        mock_graph.nodes.return_value = []

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            routes = agent.calculate_alternative_routes((14.65, 121.10), (14.66, 121.11))

            assert routes == []


class TestWarningGeneration:
    """Test warning message generation."""

    def test_generate_warnings_critical_risk(self):
        """Test warning generation for critical risk (>= 0.9)."""
        mock_env = Mock()

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            metrics = {
                "average_risk": 0.5,
                "max_risk": 0.95,
                "total_distance": 5000
            }

            warnings = agent._generate_warnings(metrics)

            assert len(warnings) > 0
            assert any("CRITICAL" in w for w in warnings)

    def test_generate_warnings_high_risk(self):
        """Test warning generation for high risk (>= 0.7)."""
        mock_env = Mock()

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            metrics = {
                "average_risk": 0.4,
                "max_risk": 0.75,
                "total_distance": 3000
            }

            warnings = agent._generate_warnings(metrics)

            assert len(warnings) > 0
            assert any("WARNING" in w for w in warnings)

    def test_generate_warnings_moderate_risk(self):
        """Test warning generation for moderate average risk (>= 0.5)."""
        mock_env = Mock()

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            metrics = {
                "average_risk": 0.55,
                "max_risk": 0.6,
                "total_distance": 2000
            }

            warnings = agent._generate_warnings(metrics)

            assert len(warnings) > 0
            assert any("CAUTION" in w for w in warnings)

    def test_generate_warnings_long_route(self):
        """Test warning generation for long routes (>10km)."""
        mock_env = Mock()

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            metrics = {
                "average_risk": 0.2,
                "max_risk": 0.3,
                "total_distance": 15000  # >10km
            }

            warnings = agent._generate_warnings(metrics)

            assert len(warnings) > 0
            assert any("long route" in w.lower() for w in warnings)

    def test_generate_warnings_low_risk(self):
        """Test warning generation for low risk routes."""
        mock_env = Mock()

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            metrics = {
                "average_risk": 0.1,
                "max_risk": 0.2,
                "total_distance": 1000
            }

            warnings = agent._generate_warnings(metrics)

            # Should have no warnings for low risk short routes
            assert len(warnings) == 0


class TestEvacuationCenterLoading:
    """Test evacuation center data loading."""

    def test_load_evacuation_centers_from_file(self):
        """Test loading evacuation centers from CSV file."""
        mock_env = Mock()
        csv_data = "name,latitude,longitude,capacity,type\nCenter1,14.65,121.10,100,school"

        with patch('pathlib.Path.exists', return_value=True), \
             patch('pandas.read_csv') as mock_read_csv:

            mock_read_csv.return_value = pd.DataFrame([
                {"name": "Center1", "latitude": 14.65, "longitude": 121.10, "capacity": 100, "type": "school"}
            ])

            agent = RoutingAgent("test_routing", mock_env)

            assert len(agent.evacuation_centers) == 1
            assert agent.evacuation_centers.iloc[0]['name'] == "Center1"

    def test_load_evacuation_centers_file_not_found(self):
        """Test loading evacuation centers when file doesn't exist."""
        mock_env = Mock()

        with patch('pathlib.Path.exists', return_value=False):
            agent = RoutingAgent("test_routing", mock_env)

            # Should create sample data
            assert len(agent.evacuation_centers) > 0
            assert 'name' in agent.evacuation_centers.columns

    def test_create_sample_evacuation_centers(self):
        """Test creating sample evacuation center data."""
        mock_env = Mock()

        with patch('pathlib.Path.exists', return_value=False):
            agent = RoutingAgent("test_routing", mock_env)

            sample_df = agent._create_sample_evacuation_centers()

            assert isinstance(sample_df, pd.DataFrame)
            assert len(sample_df) >= 3
            assert all(col in sample_df.columns for col in ['name', 'latitude', 'longitude', 'capacity', 'type'])

    def test_load_evacuation_centers_error_handling(self):
        """Test evacuation center loading handles errors gracefully."""
        mock_env = Mock()

        with patch('pathlib.Path.exists', side_effect=Exception("File error")):
            agent = RoutingAgent("test_routing", mock_env)

            # Should return empty DataFrame on error
            assert isinstance(agent.evacuation_centers, pd.DataFrame)


class TestStatistics:
    """Test agent statistics retrieval."""

    def test_get_statistics_with_graph(self):
        """Test getting agent statistics when graph is loaded."""
        mock_env = Mock()
        mock_env.graph = MagicMock()

        centers_df = pd.DataFrame([
            {"name": "Center1", "latitude": 14.65, "longitude": 121.10}
        ])

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=centers_df):
            agent = RoutingAgent("test_routing", mock_env, risk_weight=0.7, distance_weight=0.3)

            stats = agent.get_statistics()

            assert stats["agent_id"] == "test_routing"
            assert stats["risk_weight"] == 0.7
            assert stats["distance_weight"] == 0.3
            assert stats["evacuation_centers"] == 1
            assert stats["graph_loaded"] is True

    def test_get_statistics_without_graph(self):
        """Test getting agent statistics when graph is not loaded."""
        mock_env = Mock()
        mock_env.graph = None

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            stats = agent.get_statistics()

            assert stats["graph_loaded"] is False


class TestStepMethod:
    """Test agent step method."""

    def test_step_does_nothing(self):
        """Test that step method is stateless and does nothing."""
        mock_env = Mock()

        with patch.object(RoutingAgent, '_load_evacuation_centers', return_value=pd.DataFrame()):
            agent = RoutingAgent("test_routing", mock_env)

            # Should not raise any exceptions
            result = agent.step()

            assert result is None
