# filename: tests/unit/test_evacuation_manager_agent.py

"""
Comprehensive unit tests for EvacuationManagerAgent.

Tests cover:
- Initialization and agent linking
- Route request handling
- User feedback collection and forwarding
- Evacuation center lookup
- Route history and statistics
- Coordinate validation
- Error handling

Target Coverage: 80%+
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Mock the logging_config import before importing agents
import logging
sys.modules['app.core.logging_config'] = Mock()
sys.modules['app.core.logging_config'].get_logger = Mock(return_value=logging.getLogger())

from app.agents.evacuation_manager_agent import EvacuationManagerAgent


class TestEvacuationManagerAgentInitialization:
    """Test EvacuationManagerAgent initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        assert agent.agent_id == "evac_mgr_001"
        assert agent.environment == mock_env
        assert agent.routing_agent is None
        assert agent.hazard_agent is None
        assert agent.route_history == []
        assert agent.feedback_history == []
        assert agent.max_history_size == 1000

    def test_set_routing_agent(self):
        """Test linking RoutingAgent."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        mock_routing = Mock()
        mock_routing.agent_id = "routing_001"

        agent.set_routing_agent(mock_routing)

        assert agent.routing_agent == mock_routing

    def test_set_hazard_agent(self):
        """Test linking HazardAgent."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        mock_hazard = Mock()
        mock_hazard.agent_id = "hazard_001"

        agent.set_hazard_agent(mock_hazard)

        assert agent.hazard_agent == mock_hazard


class TestRouteRequestHandling:
    """Test route request handling."""

    def test_handle_route_request_success(self):
        """Test successful route request."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        # Set up mock routing agent
        mock_routing = Mock()
        mock_routing.agent_id = "routing_001"
        mock_routing.calculate_route.return_value = {
            "path": [(14.65, 121.10), (14.66, 121.11)],
            "distance": 1500.0,
            "estimated_time": 10.0,
            "risk_level": 0.3,
            "max_risk": 0.5,
            "warnings": ["Minor flooding on JP Rizal Avenue"]
        }
        agent.set_routing_agent(mock_routing)

        # Make request
        start = (14.65, 121.10)
        end = (14.66, 121.11)
        preferences = {"avoid_floods": True}

        result = agent.handle_route_request(start, end, preferences)

        # Verify result
        assert "route_id" in result
        assert result["path"] == [(14.65, 121.10), (14.66, 121.11)]
        assert result["distance"] == 1500.0
        assert result["estimated_time"] == 10.0
        assert result["risk_level"] == 0.3
        assert result["max_risk"] == 0.5
        assert len(result["warnings"]) == 1

        # Verify routing agent was called
        mock_routing.calculate_route.assert_called_once_with(start, end, preferences)

        # Verify history was updated
        assert len(agent.route_history) == 1
        assert agent.route_history[0]["start"] == start
        assert agent.route_history[0]["end"] == end

    def test_handle_route_request_invalid_coordinates(self):
        """Test route request with invalid coordinates."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        # Invalid latitude (> 90)
        start = (95.0, 121.10)
        end = (14.66, 121.11)

        result = agent.handle_route_request(start, end)

        assert result["status"] == "error"
        assert "Invalid coordinates" in result["message"]

    def test_handle_route_request_no_routing_agent(self):
        """Test route request without RoutingAgent configured."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        # No routing agent set
        start = (14.65, 121.10)
        end = (14.66, 121.11)

        result = agent.handle_route_request(start, end)

        assert result["status"] == "error"
        assert "unavailable" in result["message"].lower()

    def test_handle_route_request_routing_exception(self):
        """Test route request when RoutingAgent raises exception."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        # Set up mock routing agent that raises exception
        mock_routing = Mock()
        mock_routing.agent_id = "routing_001"
        mock_routing.calculate_route.side_effect = Exception("Graph not loaded")
        agent.set_routing_agent(mock_routing)

        start = (14.65, 121.10)
        end = (14.66, 121.11)

        result = agent.handle_route_request(start, end)

        assert result["status"] == "error"
        assert "Graph not loaded" in result["message"]

    def test_handle_route_request_with_preferences(self):
        """Test route request with different preferences."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        mock_routing = Mock()
        mock_routing.agent_id = "routing_001"
        mock_routing.calculate_route.return_value = {
            "path": [(14.65, 121.10), (14.66, 121.11)],
            "distance": 1200.0,
            "estimated_time": 8.0,
            "risk_level": 0.2,
            "max_risk": 0.3,
            "warnings": []
        }
        agent.set_routing_agent(mock_routing)

        start = (14.65, 121.10)
        end = (14.66, 121.11)
        preferences = {"fastest": True, "avoid_floods": False}

        result = agent.handle_route_request(start, end, preferences)

        # Verify preferences were passed
        mock_routing.calculate_route.assert_called_once_with(start, end, preferences)
        assert result["risk_level"] == 0.2


class TestFeedbackCollection:
    """Test user feedback collection."""

    def test_collect_user_feedback_valid(self):
        """Test collecting valid user feedback."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        # Set up mock hazard agent
        mock_hazard = Mock()
        mock_hazard.agent_id = "hazard_001"
        mock_hazard.process_scout_data = Mock()
        agent.set_hazard_agent(mock_hazard)

        route_id = "route_123"
        location = (14.65, 121.10)
        data = {"severity": 0.8, "description": "Deep water on road"}

        result = agent.collect_user_feedback(
            route_id=route_id,
            feedback_type="flooded",
            location=location,
            data=data
        )

        assert result is True
        assert len(agent.feedback_history) == 1

        feedback = agent.feedback_history[0]
        assert feedback["route_id"] == route_id
        assert feedback["type"] == "flooded"
        assert feedback["location"] == location
        assert feedback["data"]["severity"] == 0.8

        # Verify hazard agent was called
        mock_hazard.process_scout_data.assert_called_once()

    def test_collect_user_feedback_invalid_type(self):
        """Test collecting feedback with invalid type."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        result = agent.collect_user_feedback(
            route_id="route_123",
            feedback_type="invalid_type",
            location=(14.65, 121.10)
        )

        assert result is False
        assert len(agent.feedback_history) == 0

    def test_collect_user_feedback_all_types(self):
        """Test collecting all valid feedback types."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        mock_hazard = Mock()
        mock_hazard.process_scout_data = Mock()
        agent.set_hazard_agent(mock_hazard)

        valid_types = ["clear", "blocked", "flooded", "traffic"]

        for ftype in valid_types:
            result = agent.collect_user_feedback(
                route_id=f"route_{ftype}",
                feedback_type=ftype,
                location=(14.65, 121.10)
            )
            assert result is True

        assert len(agent.feedback_history) == 4


class TestFeedbackForwarding:
    """Test feedback forwarding to HazardAgent."""

    def test_forward_to_hazard_agent_success(self):
        """Test successful feedback forwarding."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        mock_hazard = Mock()
        mock_hazard.agent_id = "hazard_001"
        mock_hazard.process_scout_data = Mock()
        agent.set_hazard_agent(mock_hazard)

        feedback = {
            "feedback_id": "fb_001",
            "route_id": "route_123",
            "type": "flooded",
            "location": (14.65, 121.10),
            "data": {"severity": 0.7},
            "timestamp": datetime.now()
        }

        agent.forward_to_hazard_agent(feedback)

        # Verify hazard agent received correct data
        mock_hazard.process_scout_data.assert_called_once()
        call_args = mock_hazard.process_scout_data.call_args[0][0]

        assert len(call_args) == 1
        scout_data = call_args[0]
        assert scout_data["location"] == (14.65, 121.10)
        assert scout_data["severity"] == 0.7
        assert scout_data["report_type"] == "flooded"
        assert scout_data["confidence"] == 0.7
        assert scout_data["source"] == "user_feedback"
        assert scout_data["feedback_id"] == "fb_001"

    def test_forward_to_hazard_agent_no_agent(self):
        """Test forwarding without HazardAgent configured."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        feedback = {
            "feedback_id": "fb_001",
            "type": "flooded",
            "location": (14.65, 121.10),
            "data": {},
            "timestamp": datetime.now()
        }

        # Should not raise exception
        agent.forward_to_hazard_agent(feedback)

    def test_forward_to_hazard_agent_exception(self):
        """Test forwarding when HazardAgent raises exception."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        mock_hazard = Mock()
        mock_hazard.agent_id = "hazard_001"
        mock_hazard.process_scout_data = Mock(side_effect=Exception("Processing error"))
        agent.set_hazard_agent(mock_hazard)

        feedback = {
            "feedback_id": "fb_001",
            "type": "flooded",
            "location": (14.65, 121.10),
            "data": {"severity": 0.5},
            "timestamp": datetime.now()
        }

        # Should not raise exception (error is logged)
        agent.forward_to_hazard_agent(feedback)


class TestEvacuationCenterLookup:
    """Test evacuation center lookup."""

    def test_find_nearest_evacuation_center_success(self):
        """Test successful evacuation center lookup."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        # Set up mock routing agent
        mock_routing = Mock()
        mock_routing.agent_id = "routing_001"
        mock_routing.find_nearest_evacuation_center.return_value = {
            "name": "Marikina Sports Center",
            "location": (14.638056, 121.099722),
            "distance": 500.0,
            "capacity": 1000,
            "type": "sports_complex",
            "contact": "+63-2-8682-2116",
            "path": [(14.65, 121.10), (14.64, 121.10)],
            "estimated_time": 5.0,
            "risk_level": 0.2
        }
        agent.set_routing_agent(mock_routing)

        location = (14.65, 121.10)
        result = agent.find_nearest_evacuation_center(location)

        # Verify result
        assert result is not None
        assert result["name"] == "Marikina Sports Center"
        assert result["distance"] == 500.0
        assert result["capacity"] == 1000
        assert "path" in result

        # Verify routing agent was called
        mock_routing.find_nearest_evacuation_center.assert_called_once_with(
            location=location,
            max_centers=5
        )

    def test_find_nearest_evacuation_center_no_routing_agent(self):
        """Test evacuation center lookup without RoutingAgent."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        location = (14.65, 121.10)
        result = agent.find_nearest_evacuation_center(location)

        assert result is None

    def test_find_nearest_evacuation_center_none_found(self):
        """Test when no evacuation centers are found."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        mock_routing = Mock()
        mock_routing.agent_id = "routing_001"
        mock_routing.find_nearest_evacuation_center.return_value = None
        agent.set_routing_agent(mock_routing)

        location = (14.65, 121.10)
        result = agent.find_nearest_evacuation_center(location)

        assert result is None

    def test_find_nearest_evacuation_center_exception(self):
        """Test evacuation center lookup with exception."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        mock_routing = Mock()
        mock_routing.agent_id = "routing_001"
        mock_routing.find_nearest_evacuation_center.side_effect = Exception("Database error")
        agent.set_routing_agent(mock_routing)

        location = (14.65, 121.10)
        result = agent.find_nearest_evacuation_center(location)

        assert result is None


class TestStatistics:
    """Test statistics and history management."""

    def test_get_route_statistics_empty(self):
        """Test statistics with empty history."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        stats = agent.get_route_statistics()

        assert stats["total_routes"] == 0
        assert stats["total_feedback"] == 0
        assert stats["feedback_by_type"] == {}
        assert stats["average_risk_level"] == 0.0

    def test_get_route_statistics_with_data(self):
        """Test statistics with route and feedback data."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        # Add mock route history
        agent.route_history = [
            {
                "route_id": "r1",
                "route": {"risk_level": 0.3}
            },
            {
                "route_id": "r2",
                "route": {"risk_level": 0.5}
            }
        ]

        # Add mock feedback history
        agent.feedback_history = [
            {"type": "flooded"},
            {"type": "flooded"},
            {"type": "clear"},
            {"type": "blocked"}
        ]

        stats = agent.get_route_statistics()

        assert stats["total_routes"] == 2
        assert stats["total_feedback"] == 4
        assert stats["feedback_by_type"]["flooded"] == 2
        assert stats["feedback_by_type"]["clear"] == 1
        assert stats["feedback_by_type"]["blocked"] == 1
        assert stats["average_risk_level"] == 0.4  # (0.3 + 0.5) / 2

    def test_history_size_limit(self):
        """Test that history is limited to max_history_size."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)
        agent.max_history_size = 10

        # Add more than max_history_size entries
        for i in range(15):
            agent.route_history.append({"route_id": f"r{i}"})
            agent.feedback_history.append({"feedback_id": f"f{i}"})

        # Trigger cleanup via step()
        agent.step()

        assert len(agent.route_history) == 10
        assert len(agent.feedback_history) == 10

        # Verify only most recent entries are kept
        assert agent.route_history[0]["route_id"] == "r5"
        assert agent.feedback_history[0]["feedback_id"] == "f5"


class TestCoordinateValidation:
    """Test coordinate validation."""

    def test_validate_coordinates_valid(self):
        """Test validation of valid coordinates."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        assert agent._validate_coordinates((14.65, 121.10)) is True
        assert agent._validate_coordinates([14.65, 121.10]) is True
        assert agent._validate_coordinates((0, 0)) is True
        assert agent._validate_coordinates((-90, -180)) is True
        assert agent._validate_coordinates((90, 180)) is True

    def test_validate_coordinates_invalid(self):
        """Test validation of invalid coordinates."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        # Invalid latitude
        assert agent._validate_coordinates((91, 121.10)) is False
        assert agent._validate_coordinates((-91, 121.10)) is False

        # Invalid longitude
        assert agent._validate_coordinates((14.65, 181)) is False
        assert agent._validate_coordinates((14.65, -181)) is False

        # Invalid format
        assert agent._validate_coordinates((14.65,)) is False
        assert agent._validate_coordinates((14.65, 121.10, 0)) is False
        assert agent._validate_coordinates("14.65,121.10") is False
        assert agent._validate_coordinates(None) is False


class TestAgentStep:
    """Test agent step function."""

    def test_step_basic(self):
        """Test basic step execution."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)

        # Should not raise exception
        agent.step()

    def test_step_with_history_cleanup(self):
        """Test step performs history cleanup."""
        mock_env = Mock()
        agent = EvacuationManagerAgent("evac_mgr_001", mock_env)
        agent.max_history_size = 5

        # Add entries
        for i in range(10):
            agent.route_history.append({"route_id": f"r{i}"})

        agent.step()

        assert len(agent.route_history) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
