"""
River Scraper Service
---------------------
This module contains a service class for scraping river level data from the
PAGASA Pasig-Marikina-Tullahan Flood Forecasting and Warning System.

Uses Selenium and Pandas for robust data extraction from JavaScript-rendered content.
"""

import logging
import re
from typing import List, Dict, Optional, Any
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger(__name__)


class RiverScraperService:
    """
    A service to get river level data from PAGASA using HTML scraping.

    Provides access to:
    - Current water levels
    - Alert levels
    - Alarm levels
    - Critical levels
    """

    def __init__(self):
        """Initialize the scraper service."""
        self.base_url = "https://pasig-marikina-tullahanffws.pagasa.dost.gov.ph"
        self.html_url = f"{self.base_url}/water/map.do"
        logger.info("RiverScraperService initialized")

    def get_river_levels(self) -> List[Dict[str, Any]]:
        """
        Get river level data using Selenium and pandas.
        Uses headless Chrome to handle JavaScript-rendered content.

        Returns:
            A list of dictionaries, where each dictionary represents a monitoring station.
            Returns an empty list if the request fails.
        """
        logger.info("Fetching river data from PAGASA website using Selenium")

        driver = None
        try:
            # Step 1: Set up headless Chrome
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument(
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
            )

            logger.info("Launching Chrome browser...")
            driver = webdriver.Chrome(options=chrome_options)

            # Step 2: Navigate to the page
            logger.info(f"Navigating to {self.html_url}...")
            driver.get(self.html_url)

            # Step 3: Wait for the table to load with JavaScript
            logger.info("Waiting for table to load...")
            wait = WebDriverWait(driver, 15)
            table_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-type1 tbody#tblList"))
            )

            # Wait a bit more for data to populate
            import time
            time.sleep(2)

            # Step 4: Get the page source after JavaScript execution
            html_content = driver.page_source

            # Step 5: Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table', class_='table-type1')

            if not table:
                logger.warning("Could not find table with class 'table-type1'")
                return []

            logger.info("Found table 'table-type1'. Parsing with Pandas...")

            # Step 6: Use Pandas to read the table HTML
            df_list = pd.read_html(StringIO(str(table)))
            df = df_list[0]

            # Step 7: Process the DataFrame into clean JSON
            stations_data = self._process_dataframe(df)

            logger.info(f"Successfully scraped {len(stations_data)} stations")
            return stations_data

        except TimeoutException:
            logger.error("Timeout waiting for table to load")
            return []
        except WebDriverException as e:
            logger.error(f"WebDriver error: {e}")
            return []
        except Exception as e:
            logger.error(f"An error occurred during scraping: {e}")
            return []
        finally:
            # Always close the browser
            if driver:
                driver.quit()
                logger.debug("Browser closed")

    def _process_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Process the raw pandas DataFrame into clean station data.

        Args:
            df: Raw DataFrame from pandas.read_html

        Returns:
            List of station data dictionaries
        """
        logger.info("Processing DataFrame into clean station data")
        stations_data = []

        # The DataFrame should have columns:
        # ['Station', 'Current [EL.m]', 'Alert [EL.m]', 'Alarm [EL.m]', 'Critical [EL.m]']
        # or similar variations

        for index, row in df.iterrows():
            try:
                # Get station name (first column)
                station_name = str(row.iloc[0]).strip()

                # Skip header rows or empty rows
                if station_name in ['Station', 'nan', '', '-'] or pd.isna(station_name):
                    continue

                # Extract values and clean them
                current_level = self._clean_value(row.iloc[1])
                alert_level = self._clean_value(row.iloc[2])
                alarm_level = self._clean_value(row.iloc[3])
                critical_level = self._clean_value(row.iloc[4])

                station_data = {
                    "station_name": station_name,
                    "water_level_m": current_level,
                    "alert_level_m": alert_level,
                    "alarm_level_m": alarm_level,
                    "critical_level_m": critical_level
                }

                stations_data.append(station_data)
                logger.debug(f"Parsed station: {station_name} - WL: {current_level}m")

            except Exception as e:
                logger.error(f"Error parsing row {index}: {e}")
                continue

        return stations_data

    def _clean_value(self, value) -> Optional[float]:
        """
        Clean and convert a table value to float.

        Args:
            value: Raw value from the table

        Returns:
            Float value or None if invalid
        """
        if pd.isna(value):
            return None

        # Convert to string and clean
        value_str = str(value).strip()

        # Check for empty or dash values
        if value_str in ['', '-', 'nan', 'No Data']:
            return None

        # Remove (*) if present (indicates estimated data)
        value_str = re.sub(r'\(\*\)', '', value_str).strip()

        try:
            return float(value_str)
        except (ValueError, TypeError):
            logger.debug(f"Could not convert value to float: {value_str}")
            return None

    def get_station_data(self, station_name: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific station.

        Args:
            station_name: Name of the station to find

        Returns:
            Station data dictionary or None if not found
        """
        stations = self.get_river_levels()

        for station in stations:
            if station.get("station_name", "").lower() == station_name.lower():
                return station

        logger.warning(f"Station '{station_name}' not found")
        return None

    def get_marikina_stations(self) -> List[Dict[str, Any]]:
        """
        Get data for key Marikina River monitoring stations.

        Returns:
            List of Marikina River station data
        """
        marikina_station_names = [
            "Sto Nino",
            "Nangka",
            "Tumana Bridge",
            "Montalban",
            "Rosario Bridge"
        ]

        all_stations = self.get_river_levels()
        marikina_stations = []

        for station in all_stations:
            station_name = station.get("station_name", "")
            if station_name in marikina_station_names:
                marikina_stations.append(station)

        logger.info(
            f"Found {len(marikina_stations)} Marikina stations "
            f"out of {len(marikina_station_names)} expected"
        )
        return marikina_stations

    def get_critical_stations(self, threshold: str = "alert") -> List[Dict[str, Any]]:
        """
        Get stations where water level exceeds a threshold.

        Args:
            threshold: "alert", "alarm", or "critical"

        Returns:
            List of stations exceeding the threshold
        """
        all_stations = self.get_river_levels()
        critical_stations = []

        for station in all_stations:
            water_level = station.get("water_level_m")
            if water_level is None:
                continue

            threshold_level = None
            if threshold == "alert":
                threshold_level = station.get("alert_level_m")
            elif threshold == "alarm":
                threshold_level = station.get("alarm_level_m")
            elif threshold == "critical":
                threshold_level = station.get("critical_level_m")

            if threshold_level is not None and water_level >= threshold_level:
                critical_stations.append(station)

        logger.info(
            f"Found {len(critical_stations)} stations exceeding {threshold} level"
        )
        return critical_stations


# Test the scraper when run directly
if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)

    print("--- Testing River Scraper Service ---")

    # Test the service
    service = RiverScraperService()
    river_data = service.get_river_levels()

    if river_data:
        print(f"\nSuccess! Fetched {len(river_data)} stations")
        print("\nFirst 5 stations:")
        print(json.dumps(river_data[:5], indent=2))

        # Test Marikina stations
        print("\n--- Marikina River Stations ---")
        marikina_data = service.get_marikina_stations()
        for station in marikina_data:
            name = station.get('station_name')
            water_level = station.get('water_level_m')
            alert_level = station.get('alert_level_m')
            print(f"  {name}: {water_level}m (Alert: {alert_level}m)")

        # Test critical stations
        print("\n--- Stations at Alert Level ---")
        critical = service.get_critical_stations("alert")
        if critical:
            for station in critical:
                print(
                    f"  {station['station_name']}: "
                    f"{station['water_level_m']}m "
                    f"(Alert: {station['alert_level_m']}m)"
                )
        else:
            print("  No stations at alert level")
    else:
        print("\nFailed to fetch river data")
