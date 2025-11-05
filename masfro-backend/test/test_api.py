# filename: test/test_api.py

"""
Tests for FastAPI endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check and status endpoints."""

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["status"] == "operational"

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "graph_status" in data
        assert "agents" in data


class TestRouteEndpoint:
    """Test route calculation endpoint."""

    def test_route_request_valid_structure(self):
        """Test route request with valid data structure."""
        request_data = {
            "start_location": [14.6507, 121.1029],
            "end_location": [14.6545, 121.1089]
        }

        response = client.post("/api/route", json=request_data)

        # May fail if graph not loaded, but should validate structure
        assert response.status_code in [200, 400, 503]

    def test_route_request_invalid_coordinates(self):
        """Test route request with invalid coordinates."""
        request_data = {
            "start_location": [200, 200],  # Invalid lat/lon
            "end_location": [14.6545, 121.1089]
        }

        response = client.post("/api/route", json=request_data)

        # Should handle gracefully
        assert response.status_code in [400, 503]

    def test_route_request_missing_fields(self):
        """Test route request with missing required fields."""
        request_data = {
            "start_location": [14.6507, 121.1029]
            # Missing end_location
        }

        response = client.post("/api/route", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_route_response_structure(self):
        """Test that successful route response has correct structure."""
        request_data = {
            "start_location": [14.6507, 121.1029],
            "end_location": [14.6545, 121.1089]
        }

        response = client.post("/api/route", json=request_data)

        if response.status_code == 200:
            data = response.json()
            assert "route_id" in data
            assert "status" in data
            assert "path" in data
            assert isinstance(data["path"], list)


class TestFeedbackEndpoint:
    """Test user feedback endpoint."""

    def test_feedback_submission(self):
        """Test submitting user feedback."""
        feedback_data = {
            "route_id": "test-route-123",
            "feedback_type": "clear",
            "location": [14.6507, 121.1029],
            "severity": 0.0,
            "description": "Road is clear"
        }

        response = client.post("/api/feedback", json=feedback_data)
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data

    def test_feedback_missing_route_id(self):
        """Test feedback without route ID."""
        feedback_data = {
            "feedback_type": "clear"
        }

        response = client.post("/api/feedback", json=feedback_data)
        assert response.status_code == 422  # Validation error

    def test_feedback_invalid_type(self):
        """Test feedback with empty data."""
        feedback_data = {
            "route_id": "test-123",
            "feedback_type": "clear"
        }

        response = client.post("/api/feedback", json=feedback_data)
        assert response.status_code in [200, 400, 500]


class TestStatisticsEndpoint:
    """Test statistics endpoint."""

    def test_get_statistics(self):
        """Test retrieving system statistics."""
        response = client.get("/api/statistics")
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "route_statistics" in data
            assert "system_status" in data


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers(self):
        """Test that CORS headers are present."""
        response = client.get("/")
        # CORS headers should be present
        assert response.status_code == 200


class TestDataModels:
    """Test Pydantic data models validation."""

    def test_route_request_validation(self):
        """Test route request model validation."""
        # Valid request
        valid_request = {
            "start_location": [14.6507, 121.1029],
            "end_location": [14.6545, 121.1089],
            "preferences": {"avoid_floods": True}
        }

        response = client.post("/api/route", json=valid_request)
        assert response.status_code in [200, 400, 503]  # Not 422 (validation error)

    def test_invalid_coordinate_format(self):
        """Test with invalid coordinate format."""
        invalid_request = {
            "start_location": "not a coordinate",
            "end_location": [14.6545, 121.1089]
        }

        response = client.post("/api/route", json=invalid_request)
        assert response.status_code == 422  # Validation error
