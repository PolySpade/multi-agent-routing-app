"""
Tests for the Google Places API proxy endpoints.

Uses a minimal FastAPI app with just the places router mounted,
avoiding the full app.main initialization (which loads the graph,
agents, and heavy dependencies).
"""

import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.places_endpoints import router


@pytest.fixture
def client():
    """Create a test client with only the places router mounted."""
    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


@pytest.fixture
def client_with_key():
    """Test client with a fake GOOGLE_API_KEY so the key check passes."""
    from app.core.config import Settings

    test_app = FastAPI()
    test_app.include_router(router)
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-key-for-testing"}):
        fake_settings = Settings(_env_file=None)
        with patch("app.api.places_endpoints.settings", fake_settings):
            yield TestClient(test_app)


class TestAutocomplete:
    """Tests for POST /api/places/autocomplete."""

    def test_short_input_returns_zero_results(self, client_with_key):
        resp = client_with_key.post(
            "/api/places/autocomplete",
            json={"input": "ab", "sessionToken": "test-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ZERO_RESULTS"
        assert data["predictions"] == []

    def test_empty_input_returns_zero_results(self, client_with_key):
        resp = client_with_key.post(
            "/api/places/autocomplete",
            json={"input": "", "sessionToken": "test-token"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ZERO_RESULTS"

    def test_missing_api_key_returns_500(self, client):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
            from app.core.config import Settings

            with patch("app.api.places_endpoints.settings", Settings(_env_file=None)):
                resp = client.post(
                    "/api/places/autocomplete",
                    json={"input": "Marikina City Hall", "sessionToken": "tok"},
                )
                assert resp.status_code == 500


class TestGeocode:
    """Tests for POST /api/places/geocode."""

    def test_short_address_returns_zero_results(self, client_with_key):
        resp = client_with_key.post(
            "/api/places/geocode",
            json={"address": "a"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ZERO_RESULTS"
        assert data["results"] == []

    def test_empty_address_returns_zero_results(self, client_with_key):
        resp = client_with_key.post(
            "/api/places/geocode",
            json={"address": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ZERO_RESULTS"

    def test_missing_api_key_returns_500(self, client):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
            from app.core.config import Settings

            with patch("app.api.places_endpoints.settings", Settings(_env_file=None)):
                resp = client.post(
                    "/api/places/geocode",
                    json={"address": "Marikina City Hall"},
                )
                assert resp.status_code == 500


class TestDetails:
    """Tests for POST /api/places/details."""

    def test_missing_api_key_returns_500(self, client):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": ""}):
            from app.core.config import Settings

            with patch("app.api.places_endpoints.settings", Settings(_env_file=None)):
                resp = client.post(
                    "/api/places/details",
                    json={"placeId": "ChIJ123", "sessionToken": "tok"},
                )
                assert resp.status_code == 500


class TestRouterStructure:
    """Verify the router has the expected routes."""

    def test_router_has_three_routes(self):
        paths = [route.path for route in router.routes]
        assert "/api/places/autocomplete" in paths
        assert "/api/places/details" in paths
        assert "/api/places/geocode" in paths

    def test_all_routes_are_post(self):
        for route in router.routes:
            assert "POST" in route.methods
