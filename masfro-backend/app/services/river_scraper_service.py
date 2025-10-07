"""
River Scraper Service
---------------------
This module contains a service class for scraping river level data from the
PAGASA Pasig-Marikina-Tullahan Flood Forecasting and Warning System.

Instead of scraping the HTML, this service targets the internal API that the
website uses to load its data dynamically.
"""

import requests
from datetime import datetime

class RiverScraperService:
    """
    A service to get river level data by calling the website's internal API.
    """
    def __init__(self):
        # This is the internal API endpoint we discovered in the HTML.
        self.target_url = "https://pasig-marikina-tullahanffws.pagasa.dost.gov.ph/water/map_list.do"

    def get_river_levels(self) -> list[dict]:
        """
        Calls the internal API to get the latest river level data.

        Returns:
            A list of dictionaries, where each dictionary represents a monitoring station.
            Returns an empty list if the request fails.
        """
        print(f"Fetching river data from API: {self.target_url}")
        
        try:
            # We need to send a 'ymdhm' parameter with the current date and time.
            # The format seems to be YearMonthDayHourMinute (e.g., 202510071755)
            # We will generate this dynamically.
            current_time_str = datetime.now().strftime("%Y%m%d%H%M")

            params = {
                'ymdhm': current_time_str,
                'basin': '' # An empty basin parameter seems to return all stations
            }
            
            # The website might require a specific User-Agent, so we'll mimic a browser.
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
            }

            # Make the request to the API endpoint
            response = requests.get(self.target_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            # The response is directly in JSON format, which is very easy to work with!
            api_data = response.json()
            
            # Now, we just need to clean up the keys to match our desired format.
            formatted_data = []
            for station in api_data:
                # The water level sometimes has an asterisk, let's remove it.
                water_level_str = (station.get('wl') or '').replace('(*)', '')
                
                # Convert numeric fields safely
                try:
                    water_level = float(water_level_str)
                except (ValueError, TypeError):
                    water_level = None # Use None for invalid data

                formatted_data.append({
                    "station_name": station.get("obsnm"),
                    "water_level_m": water_level,
                    "alert_level_m": station.get("alertwl"),
                    "alarm_level_m": station.get("alarmwl"),
                    "critical_level_m": station.get("criticalwl")
                })
                
            return formatted_data

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from the API: {e}")
            return []
        except Exception as e:
            print(f"An error occurred while processing the river data: {e}")
            return []

# This block allows you to run this file directly to test the scraper
if __name__ == "__main__":
    print("--- Testing River Scraper Service ---")
    scraper = RiverScraperService()
    river_levels = scraper.get_river_levels()
    
    if river_levels:
        print("Successfully fetched river data:")
        for station in river_levels:
            print(station)
    else:
        print("Scraping returned no data.")