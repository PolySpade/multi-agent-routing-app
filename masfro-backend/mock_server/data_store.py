"""
In-memory data store for the mock server.

Thread-safe singleton that holds all mock data for PAGASA, weather,
news, and social media endpoints.
"""

import threading
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from email.utils import format_datetime


class MockDataStore:
    """Thread-safe in-memory data store for all mock endpoints."""

    _instance: Optional["MockDataStore"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._data_lock = threading.Lock()
        self._reset_data()
        self._initialized = True

    def _reset_data(self):
        """Reset all data to empty state."""
        self.river_stations: List[Dict[str, Any]] = []
        self.dam_levels: List[Dict[str, Any]] = []
        self.current_weather: Dict[str, Any] = {}
        self.forecast: Dict[str, Any] = {}
        self.advisories: List[Dict[str, Any]] = []
        self.social_posts: List[Dict[str, Any]] = []
        self._next_advisory_id = 1

    def reset(self):
        """Thread-safe full reset."""
        with self._data_lock:
            self._reset_data()

    # --- River stations ---

    def get_river_stations(self) -> List[Dict[str, Any]]:
        with self._data_lock:
            return list(self.river_stations)

    def update_river_station(self, station_name: str, data: Dict[str, Any]):
        with self._data_lock:
            for station in self.river_stations:
                if station["station_name"].lower() == station_name.lower():
                    station.update(data)
                    return
            # New station
            data["station_name"] = station_name
            self.river_stations.append(data)

    # --- Dam levels ---

    def get_dam_levels(self) -> List[Dict[str, Any]]:
        with self._data_lock:
            return list(self.dam_levels)

    def update_dam(self, dam_name: str, data: Dict[str, Any]):
        with self._data_lock:
            for dam in self.dam_levels:
                if dam["dam_name"].lower() == dam_name.lower():
                    dam.update(data)
                    return
            data["dam_name"] = dam_name
            self.dam_levels.append(data)

    # --- Weather ---

    def get_current_weather(self) -> Dict[str, Any]:
        with self._data_lock:
            return dict(self.current_weather)

    def get_forecast(self) -> Dict[str, Any]:
        with self._data_lock:
            return dict(self.forecast)

    def update_weather(self, data: Dict[str, Any]):
        with self._data_lock:
            if "current" in data:
                self.current_weather = data["current"]
            if "forecast" in data:
                self.forecast = data["forecast"]

    # --- Advisories ---

    def get_advisories(self) -> List[Dict[str, Any]]:
        with self._data_lock:
            return list(self.advisories)

    def add_advisory(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._data_lock:
            advisory_id = self._next_advisory_id
            self._next_advisory_id += 1
            advisory = {
                "id": advisory_id,
                "title": data.get("title", "Flood Advisory"),
                "text": data.get("text", ""),
                "pub_date": data.get("pub_date", format_datetime(datetime.now(timezone.utc))),
                "link": data.get("link", f"/pagasa/advisory/{advisory_id}"),
            }
            self.advisories.append(advisory)
            return advisory

    # --- Social posts ---

    def get_social_posts(self, limit: int = 50, since: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._data_lock:
            posts = list(self.social_posts)
            if since:
                posts = [p for p in posts if p.get("timestamp", "") > since]
            return posts[:limit]

    def add_social_post(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._data_lock:
            post_id = data.get("tweet_id") or str(uuid.uuid4())
            post = {
                "tweet_id": post_id,
                "username": data.get("username", "mock_user"),
                "text": data.get("text", ""),
                "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "url": data.get("url", f"https://x.com/mock_user/status/{post_id}"),
                "image_path": data.get("image_path"),
            }
            self.social_posts.append(post)
            return post


def get_data_store() -> MockDataStore:
    """Get the singleton data store instance."""
    return MockDataStore()
