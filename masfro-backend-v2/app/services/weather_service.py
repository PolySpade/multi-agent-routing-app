"""
Weather Service Module
----------------------
This module encapsulates the logic for interacting with the OpenWeatherMap (OWM) API.
It provides a clean interface for the FloodAgent to fetch weather data.

Updated to support Free Tier (API 2.5) by emulating One Call response structure.
"""

import os
import requests
from dotenv import load_dotenv
import logging

# Load environment variables from the .env file in the root directory
load_dotenv()

logger = logging.getLogger(__name__)

class OpenWeatherMapService:
    """
    A service class to interact with the OpenWeatherMap API (v2.5 Free Tier).
    Emulates the specific One Call API 3.0 structure required by FloodAgent.
    """

    def __init__(self, base_url: str = None):
        """
        Initializes the service and retrieves the API key from environment variables.

        Args:
            base_url: Override base URL (e.g. mock server weather URL).
                      When provided, API key validation is skipped.
        """
        if base_url:
            # Mock mode - no API key needed
            self.api_key = "mock-key"
            base = base_url.rstrip("/")
            self.current_url = f"{base}/data/2.5/weather"
            self.forecast_url = f"{base}/data/2.5/forecast"
            logger.info(f"OpenWeatherMapService initialized with mock URL: {base}")
        else:
            self.api_key = os.getenv("OPENWEATHERMAP_API_KEY")
            if not self.api_key:
                # Fallback check for different env var name
                self.api_key = os.getenv("OPENWEATHER_API_KEY")

            if not self.api_key:
                raise ValueError("OpenWeatherMap API key is not set in the .env file.")

            # Free tier endpoints
            self.current_url = "https://api.openweathermap.org/data/2.5/weather"
            self.forecast_url = "https://api.openweathermap.org/data/2.5/forecast"

    def get_forecast(self, lat: float, lon: float) -> dict:
        """
        Fetches weather data using Free Tier APIs and stitches them to resemble One Call API.

        Args:
            lat (float): Latitude
            lon (float): Longitude

        Returns:
            dict: A dictionary mimicking the One Call API response structure:
                  {
                      "current": { ... },
                      "hourly": [ ... ]  (Approximated from 3hr forecast)
                  }
        """
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric"
        }
        
        try:
            # 1. Fetch Current Weather
            current_resp = requests.get(self.current_url, params=params)
            current_resp.raise_for_status()
            current_data = current_resp.json()
            
            # 2. Fetch 5-Day/3-Hour Forecast
            forecast_resp = requests.get(self.forecast_url, params=params)
            forecast_resp.raise_for_status()
            forecast_data = forecast_resp.json()
            
            return self._transform_to_onecall_format(current_data, forecast_data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from OpenWeatherMap API: {e}")
            # Try to log response text if available for debugging
            if hasattr(e, 'response') and e.response:
                 logger.error(f"API Response: {e.response.text}")
            return {}

    def _transform_to_onecall_format(self, current: dict, forecast: dict) -> dict:
        """
        Transforms 2.5 API data into a partial One Call API structure
        collected by FloodAgent.fetch_real_weather_data
        """
        
        # Structure 'current' block
        # FloodAgent expects: current.rain.1h, current.temp, current.humidity, current.pressure
        
        current_obj = {
            "temp": current.get("main", {}).get("temp"),
            "humidity": current.get("main", {}).get("humidity"),
            "pressure": current.get("main", {}).get("pressure"),
            "dt": current.get("dt"),
            "weather": current.get("weather", []),
            "rain": current.get("rain", {}) # might be {"1h": 0.5}
        }
        
        # Structure 'hourly' block (using 3h forecast items as hourly proxy)
        # FloodAgent expects: rain.1h, temp, humidity, pop
        hourly_list = []
        
        if "list" in forecast:
            for item in forecast["list"]:
                # 2.5 API provides 'rain': {'3h': val}
                # We need to normalize this to 'rain': {'1h': val/3} for the agent logic
                rain_3h = item.get("rain", {}).get("3h", 0.0)
                rain_1h = rain_3h / 3.0 if rain_3h else 0.0
                
                hourly_item = {
                    "dt": item.get("dt"),
                    "temp": item.get("main", {}).get("temp"),
                    "humidity": item.get("main", {}).get("humidity"),
                    "pop": item.get("pop", 0.0),
                    "rain": {"1h": rain_1h}
                }
                hourly_list.append(hourly_item)
                
        return {
            "current": current_obj,
            "hourly": hourly_list
        }