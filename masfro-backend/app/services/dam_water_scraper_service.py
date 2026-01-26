# filename: app/services/dam_water_scraper_service.py

"""
Dam Water Level Scraper Service for MAS-FRO

This service scrapes dam water level data from PAGASA's flood monitoring page.
Provides real-time reservoir water levels, deviations from normal high water
levels, and rule curve information for flood prediction.

Author: MAS-FRO Development Team
Date: November 2025
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
import json
import numpy as np
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from io import StringIO

logger = logging.getLogger(__name__)

# PAGASA Website to scrape
URL = "https://www.pagasa.dost.gov.ph/flood"

# Set a User-Agent to pretend to be a real browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
}

def convert_to_float(value):
    """Helper function to safely convert values to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def process_dataframe_to_json(df):
    print("Processing the raw DataFrame...")
    
    df['Dam Name'] = df['Dam Name'].ffill()
    
    shared_cols = [
        'Hr',
        'Amount', 
        'Normal High Water Level (NHWL) (m)'
    ]


    for col in shared_cols:
        # Check if column exists before trying to fill it
        if col in df.columns:
            df[col] = df[col].ffill()
        else:
            print(f"[!] Warning: Column '{col}' not found. Skipping ffill().")

    results = []
    
    # Group the DataFrame by 'Dam Name'. Each group will have 4 rows.
    for dam_name, group in df.groupby('Dam Name'):
        
        # Check if the group has 4 rows, otherwise skip it 
        if len(group) != 4:
            print(f"[!] Skipping {dam_name}: expected 4 rows, found {len(group)}")
            continue

        # Extract the 4 rows for "Latest" and "Previous" data
        latest_time_row = group.iloc[0]
        latest_date_row = group.iloc[1]
        prev_time_row   = group.iloc[2]
        prev_date_row   = group.iloc[3]
        
        # Build the clean JSON object for dam
        dam_data = {
            "Dam Name": dam_name.upper(),
            
            "Latest Time": latest_time_row['Observation Time & Date'],
            "Latest Date": latest_date_row['Observation Time & Date'],
            "Latest RWL (m)": convert_to_float(latest_time_row['Reservoir Water Level (RWL) (m)']),
            "Latest Dev from NHWL (m)": convert_to_float(latest_time_row['Deviation from NHWL (m)']),
            "Latest Rule Curve (m)": convert_to_float(latest_time_row['Rule Curve Elevation (m)']),
            "Latest Dev from Rule Curve (m)": convert_to_float(latest_time_row['Deviation from Rule Curve (m)']),

            "Previous Time": prev_time_row['Observation Time & Date'],
            "Previous Date": prev_date_row['Observation Time & Date'],
            "Previous RWL (m)": convert_to_float(prev_time_row['Reservoir Water Level (RWL) (m)']),
            "Previous Dev from NHWL (m)": convert_to_float(prev_time_row['Deviation from NHWL (m)']),
            "Previous Rule Curve (m)": convert_to_float(prev_time_row['Rule Curve Elevation (m)']),
            "Previous Dev from Rule Curve (m)": convert_to_float(prev_time_row['Deviation from Rule Curve (m)']),
            
            "Water Level Deviation (Hr)": convert_to_float(latest_time_row['Hr']),
            "Water Level Deviation (Amt)": convert_to_float(latest_time_row['Amount']),
            "NHWL (m)": convert_to_float(latest_time_row['Normal High Water Level (NHWL) (m)']),
        }
        results.append(dam_data)
        
    return results

def scrape_and_process():
    """
    Main function to scrape the site and return the clean JSON.
    """
    print(f"Fetching {URL}...")
    try:
        # Step 1: Download the HTML content
        response = requests.get(URL, headers=HEADERS)
        response.raise_for_status()  # Check for download errors
        html_content = response.text
        
        # Step 2: Use BeautifulSoup to find the dam table
        soup = BeautifulSoup(html_content, 'html.parser')
        dam_table = soup.find('table', {'class': 'dam-table'})
        
        if dam_table:
            print("Found table 'table dam-table'. Parsing with Pandas...")
            
            # Step 3: Use Pandas to read the table HTML
            # We use header=1 to grab the *second* row of the header (with Hr, Amount, etc.)
            # Wrap HTML string in StringIO to avoid FutureWarning
            df_list = pd.read_html(StringIO(str(dam_table)), header=1)
            df = df_list[0]
            
            # Step 4: Process the messy DataFrame into clean JSON
            clean_json_data = process_dataframe_to_json(df)
            
            return clean_json_data
        
        else:
            print("\nFAILED")
            print("Could not find a table with class 'dam-table' in the HTML.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"[!] Error downloading the page: {e}")
        return None
    except Exception as e:
        print(f"[!] An error occurred during parsing: {e}")
        return None

class DamWaterScraperService:
    """
    Service for scraping dam water level data from PAGASA.

    Provides access to:
    - Reservoir Water Level (RWL)
    - Normal High Water Level (NHWL)
    - Rule Curve Elevation
    - Water level deviations and trends

    Example:
        >>> service = DamWaterScraperService()
        >>> dam_levels = service.get_dam_levels()
        >>> for dam in dam_levels:
        ...     print(f"{dam['Dam Name']}: {dam['Latest RWL (m)']}m")
    """

    def __init__(self):
        """Initialize the DamWaterScraperService."""
        self.url = URL
        self.headers = HEADERS
        logger.info("DamWaterScraperService initialized")

    def get_dam_levels(self) -> List[Dict[str, Any]]:
        """
        Fetch current dam water levels from PAGASA.

        Returns:
            List of dicts containing dam water level data
            Returns empty list if scraping fails

        Raises:
            None - errors are logged and empty list returned
        """
        try:
            dam_data = scrape_and_process()
            if dam_data:
                logger.info(f"Successfully scraped {len(dam_data)} dam water levels")
                return dam_data
            else:
                logger.warning("No dam data returned from scraper")
                return []
        except Exception as e:
            logger.error(f"Error fetching dam levels: {e}")
            return []

    def get_dam_by_name(self, dam_name: str) -> Optional[Dict[str, Any]]:
        """
        Get water level data for a specific dam.

        Args:
            dam_name: Name of the dam (case-insensitive)

        Returns:
            Dict with dam data or None if not found
        """
        dam_levels = self.get_dam_levels()
        dam_name_upper = dam_name.upper()

        for dam in dam_levels:
            if dam.get("Dam Name", "").upper() == dam_name_upper:
                return dam

        logger.warning(f"Dam '{dam_name}' not found in scraped data")
        return None

    def get_critical_dams(self, threshold_deviation: float = 0.0) -> List[Dict[str, Any]]:
        """
        Get dams with water levels above Normal High Water Level.

        Args:
            threshold_deviation: Minimum deviation from NHWL in meters

        Returns:
            List of dams with high water levels
        """
        dam_levels = self.get_dam_levels()
        critical_dams = []

        for dam in dam_levels:
            deviation = dam.get("Latest Dev from NHWL (m)")
            if deviation is not None and deviation >= threshold_deviation:
                critical_dams.append(dam)

        logger.info(
            f"Found {len(critical_dams)} dams with deviation >= {threshold_deviation}m"
        )
        return critical_dams


# Run the scraper and print the final JSON
if __name__ == "__main__":
    # Test the service
    service = DamWaterScraperService()
    dam_data = service.get_dam_levels()

    if dam_data:
        print("\nSuccess! Final JSON Output")
        print(json.dumps(dam_data, indent=4))

        # Test critical dams
        print("\n--- Critical Dams (above NHWL) ---")
        critical = service.get_critical_dams(0.0)
        for dam in critical:
            print(f"{dam['Dam Name']}: +{dam['Latest Dev from NHWL (m)']}m from NHWL")