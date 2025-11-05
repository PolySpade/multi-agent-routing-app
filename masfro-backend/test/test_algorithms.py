# filename: test/test_algorithms.py

"""
Tests for Risk-Aware A* and Path Optimization Algorithms
"""

import pytest
import networkx as nx
from app.algorithms.risk_aware_astar import (
    haversine_distance,
    risk_aware_astar,
    calculate_path_metrics,
    get_path_coordinates
)


class TestHaversineDistance:
    """Test Haversine distance calculation."""

    def test_same_point(self):
        """Test distance between same point."""
        coord = (14.6507, 121.1029)
        distance = haversine_distance(coord, coord)
        assert distance == 0.0

    def test_known_distance(self):
        """Test distance between two known points."""
        # Two points in Marikina (approximately 1km apart)
        point1 = (14.6507, 121.1029)
        point2 = (14.6545, 121.1089)

        distance = haversine_distance(point1, point2)

        # Should be roughly 500-800 meters
        assert 400 < distance < 1000

    def test_symmetry(self):
        """Test that distance is symmetric."""
        point1 = (14.6507, 121.1029)
        point2 = (14.6545, 121.1089)

        dist1 = haversine_distance(point1, point2)
        dist2 = haversine_distance(point2, point1)

        assert abs(dist1 - dist2) < 0.01


class TestRiskAwareAstar:
    """Test risk-aware A* algorithm."""

    @pytest.fixture
    def simple_graph(self):
        """Create a simple test graph."""
        G = nx.MultiDiGraph()

        # Add nodes with coordinates
        nodes = {
            1: {"x": 121.1000, "y": 14.6500},
            2: {"x": 121.1020, "y": 14.6510},
            3: {"x": 121.1040, "y": 14.6520},
            4: {"x": 121.1060, "y": 14.6530},
        }

        for node_id, attrs in nodes.items():
            G.add_node(node_id, **attrs)

        # Add edges with length and risk_score
        edges = [
            (1, 2, 0, {"length": 200, "risk_score": 0.2}),
            (2, 3, 0, {"length": 200, "risk_score": 0.3}),
            (3, 4, 0, {"length": 200, "risk_score": 0.4}),
            (1, 3, 0, {"length": 350, "risk_score": 0.1}),  # Alternative safer route
        ]

        for u, v, key, attrs in edges:
            G.add_edge(u, v, key, **attrs)

        return G

    def test_basic_path(self, simple_graph):
        """Test finding a basic path."""
        path = risk_aware_astar(
            simple_graph,
            start=1,
            end=3,
            risk_weight=0.5,
            distance_weight=0.5
        )

        assert path is not None
        assert path[0] == 1
        assert path[-1] == 3

    def test_invalid_start_node(self, simple_graph):
        """Test with invalid start node."""
        with pytest.raises(ValueError):
            risk_aware_astar(simple_graph, start=999, end=3)

    def test_invalid_end_node(self, simple_graph):
        """Test with invalid end node."""
        with pytest.raises(ValueError):
            risk_aware_astar(simple_graph, start=1, end=999)

    def test_impassable_road(self):
        """Test that high-risk roads are avoided."""
        G = nx.MultiDiGraph()

        # Create graph with impassable route
        nodes = {
            1: {"x": 121.1000, "y": 14.6500},
            2: {"x": 121.1020, "y": 14.6510},
            3: {"x": 121.1040, "y": 14.6520},
        }

        for node_id, attrs in nodes.items():
            G.add_node(node_id, **attrs)

        # Direct route has very high risk (impassable)
        G.add_edge(1, 2, 0, length=100, risk_score=0.95)
        G.add_edge(2, 3, 0, length=100, risk_score=0.95)

        # Alternative route is safe but longer
        G.add_edge(1, 3, 0, length=300, risk_score=0.1)

        path = risk_aware_astar(
            G,
            start=1,
            end=3,
            risk_weight=0.6,
            distance_weight=0.4,
            max_risk_threshold=0.9
        )

        # Should take direct safe route
        assert len(path) == 2  # Direct from 1 to 3


class TestPathMetrics:
    """Test path metrics calculation."""

    @pytest.fixture
    def test_graph_with_path(self):
        """Create test graph with a known path."""
        G = nx.MultiDiGraph()

        nodes = {
            1: {"x": 121.1000, "y": 14.6500},
            2: {"x": 121.1020, "y": 14.6510},
            3: {"x": 121.1040, "y": 14.6520},
        }

        for node_id, attrs in nodes.items():
            G.add_node(node_id, **attrs)

        G.add_edge(1, 2, 0, length=500, risk_score=0.3)
        G.add_edge(2, 3, 0, length=600, risk_score=0.5)

        path = [1, 2, 3]

        return G, path

    def test_calculate_metrics(self, test_graph_with_path):
        """Test calculating path metrics."""
        graph, path = test_graph_with_path

        metrics = calculate_path_metrics(graph, path)

        assert metrics["total_distance"] == 1100  # 500 + 600
        assert metrics["num_segments"] == 2
        assert 0.3 <= metrics["average_risk"] <= 0.5
        assert metrics["max_risk"] == 0.5
        assert metrics["estimated_time"] > 0

    def test_empty_path_metrics(self):
        """Test metrics for empty path."""
        G = nx.MultiDiGraph()
        metrics = calculate_path_metrics(G, [])

        assert metrics["total_distance"] == 0.0
        assert metrics["average_risk"] == 0.0
        assert metrics["num_segments"] == 0

    def test_single_node_path(self):
        """Test metrics for single-node path."""
        G = nx.MultiDiGraph()
        G.add_node(1, x=121.1000, y=14.6500)

        metrics = calculate_path_metrics(G, [1])

        assert metrics["total_distance"] == 0.0
        assert metrics["num_segments"] == 0


class TestPathCoordinates:
    """Test path coordinate extraction."""

    def test_get_coordinates(self):
        """Test extracting coordinates from path."""
        G = nx.MultiDiGraph()

        nodes = {
            1: {"x": 121.1000, "y": 14.6500},
            2: {"x": 121.1020, "y": 14.6510},
            3: {"x": 121.1040, "y": 14.6520},
        }

        for node_id, attrs in nodes.items():
            G.add_node(node_id, **attrs)

        path = [1, 2, 3]
        coords = get_path_coordinates(G, path)

        assert len(coords) == 3
        assert coords[0] == (14.6500, 121.1000)
        assert coords[1] == (14.6510, 121.1020)
        assert coords[2] == (14.6520, 121.1040)

    def test_empty_path_coordinates(self):
        """Test coordinates for empty path."""
        G = nx.MultiDiGraph()
        coords = get_path_coordinates(G, [])

        assert len(coords) == 0
