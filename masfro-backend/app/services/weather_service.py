"""
Weather Service Module
----------------------
This module encapsulates the logic for interacting with the OpenWeatherMap (OWM) API.
It provides a clean interface for the FloodAgent to fetch weather data without
needing to know the implementation details of the API calls.
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file in the root directory
load_dotenv()

class OpenWeatherMapService:
    """
    A service class to interact with the OpenWeatherMap One Call API 3.0.
    """

    def __init__(self):
        """
        Initializes the service and retrieves the API key from environment variables.
        """
        self.api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        if not self.api_key:
            raise ValueError("OpenWeatherMap API key is not set in the .env file.")
        self.base_url = "https://api.openweathermap.org/data/3.0/onecall"

    def get_forecast(self, lat: float, lon: float) -> dict:
        """
        Fetches the weather forecast for a given latitude and longitude.

        Args:
            lat (float): The latitude of the location.
            lon (float): The longitude of the location.

        Returns:
            dict: The JSON response from the API as a dictionary, or an empty
                  dictionary if an error occurs.
        """
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",  # Use Celsius, meters/sec, etc.
            "exclude": "minutely,alerts"  # We can exclude data we don't need
        }
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()  # This will raise an HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from OpenWeatherMap API: {e}")
            return {}