# filename: tests/conftest.py
"""
Shared pytest fixtures for MAS-FRO Backend tests.

Provides properly mocked environments, graphs, and agent dependencies
to enable isolated unit testing without external dependencies.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch
from datetime import datetime
import networkx as nx

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_graph():
    """
    Create a mock NetworkX MultiDiGraph for testing.

    Simulates a small road network with nodes and edges that have
    the expected attributes (coordinates, distances, risk scores).
    """
    G = nx.MultiDiGraph()

    # Add nodes with coordinates (Marikina City area)
    nodes = [
        (1, {'x': 121.100, 'y': 14.650, 'street_count': 2}),
        (2, {'x': 121.101, 'y': 14.651, 'street_count': 3}),
        (3, {'x': 121.102, 'y': 14.652, 'street_count': 2}),
        (4, {'x': 121.103, 'y': 14.653, 'street_count': 4}),
        (5, {'x': 121.104, 'y': 14.654, 'street_count': 2}),
        (6, {'x': 121.105, 'y': 14.655, 'street_count': 3}),
        (7, {'x': 121.106, 'y': 14.656, 'street_count': 2}),
        (8, {'x': 121.107, 'y': 14.657, 'street_count': 2}),
        (9, {'x': 121.108, 'y': 14.658, 'street_count': 3}),
        (10, {'x': 121.109, 'y': 14.659, 'street_count': 2}),
    ]
    G.add_nodes_from(nodes)

    # Add edges with attributes
    edges = [
        (1, 2, 0, {'length': 150.0, 'risk_score': 0.0, 'highway': 'primary'}),
        (2, 3, 0, {'length': 150.0, 'risk_score': 0.2, 'highway': 'secondary'}),
        (3, 4, 0, {'length': 150.0, 'risk_score': 0.5, 'highway': 'primary'}),
        (4, 5, 0, {'length': 150.0, 'risk_score': 0.8, 'highway': 'tertiary'}),
        (5, 6, 0, {'length': 150.0, 'risk_score': 0.3, 'highway': 'primary'}),
        (2, 4, 0, {'length': 200.0, 'risk_score': 0.1, 'highway': 'secondary'}),
        (4, 6, 0, {'length': 200.0, 'risk_score': 0.2, 'highway': 'secondary'}),
        (6, 7, 0, {'length': 150.0, 'risk_score': 0.0, 'highway': 'primary'}),
        (7, 8, 0, {'length': 150.0, 'risk_score': 0.4, 'highway': 'tertiary'}),
        (8, 9, 0, {'length': 150.0, 'risk_score': 0.6, 'highway': 'secondary'}),
        (9, 10, 0, {'length': 150.0, 'risk_score': 0.1, 'highway': 'primary'}),
        (1, 3, 0, {'length': 300.0, 'risk_score': 0.0, 'highway': 'residential'}),
    ]
    G.add_edges_from([(u, v, k, d) for u, v, k, d in edges])

    return G


@pytest.fixture
def mock_environment(mock_graph):
    """
    Create a mock DynamicGraphEnvironment for testing.

    Provides a properly configured mock that supports graph operations
    needed by agents (node iteration, edge queries, risk updates).
    """
    env = MagicMock()
    env.graph = mock_graph

    # Mock update_edge_risk method
    def update_edge_risk(u, v, key, risk):
        if (u, v, key) in mock_graph.edges:
            mock_graph[u][v][key]['risk_score'] = risk

    env.update_edge_risk = MagicMock(side_effect=update_edge_risk)

    # Mock maybe_snapshot method
    env.maybe_snapshot = MagicMock()

    return env


@pytest.fixture
def mock_message_queue():
    """
    Create a mock MessageQueue for testing MAS communication.
    """
    queue = MagicMock()
    queue.register_agent = MagicMock()
    queue.send_message = MagicMock()
    queue.receive_message = MagicMock(return_value=None)
    return queue


@pytest.fixture
def mock_geotiff_service():
    """
    Create a mock GeoTIFF service for testing flood depth queries.
    """
    service = MagicMock()
    service.get_flood_depth_at_point = MagicMock(return_value=0.3)
    return service


@pytest.fixture
def sample_scout_reports():
    """
    Sample scout reports for testing.
    """
    return [
        {
            'location': 'Nangka',
            'coordinates': {'lat': 14.6507, 'lon': 121.1009},
            'severity': 0.8,
            'confidence': 0.9,
            'report_type': 'flood',
            'timestamp': datetime.now(),
            'text': 'Baha sa Nangka! Tuhod level!',
            'source': 'user1'
        },
        {
            'location': 'Parang',
            'coordinates': {'lat': 14.6520, 'lon': 121.1020},
            'severity': 0.6,
            'confidence': 0.7,
            'report_type': 'flood',
            'timestamp': datetime.now(),
            'text': 'Flooded streets in Parang area',
            'source': 'user2'
        },
        {
            'location': 'Concepcion',
            'coordinates': {'lat': 14.6480, 'lon': 121.0980},
            'severity': 0.3,
            'confidence': 0.8,
            'report_type': 'rain_report',
            'timestamp': datetime.now(),
            'text': 'Light rain, roads still passable',
            'source': 'user3'
        }
    ]


@pytest.fixture
def sample_flood_data():
    """
    Sample flood data for testing.
    """
    return {
        'IPO': {
            'flood_depth': 0.5,
            'rainfall_1h': 15.0,
            'rainfall_24h': 45.0,
            'timestamp': datetime.now()
        },
        'LA MESA': {
            'flood_depth': 0.8,
            'rainfall_1h': 25.0,
            'rainfall_24h': 80.0,
            'timestamp': datetime.now()
        },
        'STO NINO': {
            'flood_depth': 0.2,
            'rainfall_1h': 5.0,
            'rainfall_24h': 20.0,
            'timestamp': datetime.now()
        }
    }


@pytest.fixture
def hazard_config():
    """
    Mock hazard configuration for testing.
    """
    from app.core.agent_config import HazardConfig
    return HazardConfig(
        max_flood_cache=100,
        max_scout_cache=1000,
        weight_flood_depth=0.5,
        weight_crowdsourced=0.3,
        weight_historical=0.2,
        decay_function='gaussian',
        sigmoid_steepness=8.0,
        sigmoid_inflection=0.3,
        risk_radius_m=800,
        grid_size_degrees=0.01,
        enable_spatial_filtering=True
    )
