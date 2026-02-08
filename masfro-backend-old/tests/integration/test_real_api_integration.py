"""
Test Script for Real API Integration
======================================

This script tests the FloodAgent integration with real APIs:
1. PAGASA River Scraper Service
2. OpenWeatherMap Service

Run this script to verify the integration is working correctly.

Usage:
    cd masfro-backend
    python test_real_api_integration.py
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.hazard_agent import HazardAgent
from app.agents.flood_agent import FloodAgent
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_river_scraper_standalone():
    """Test RiverScraperService standalone."""
    print("\n" + "="*70)
    print("TEST 1: River Scraper Service (Standalone)")
    print("="*70)

    try:
        from app.services.river_scraper_service import RiverScraperService

        scraper = RiverScraperService()
        stations = scraper.get_river_levels()

        if stations:
            print(f"✅ SUCCESS: Fetched {len(stations)} river stations")
            print("\nKey Marikina Stations:")
            marikina_stations = [
                "Sto Nino", "Nangka", "Tumana Bridge", "Montalban", "Rosario Bridge"
            ]
            for station in stations:
                if station.get("station_name") in marikina_stations:
                    print(f"  - {station.get('station_name')}: "
                          f"Level={station.get('water_level_m')} "
                          f"Alert={station.get('alert_level_m')}")
            return True
        else:
            print("❌ FAILED: No stations returned")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_weather_service_standalone():
    """Test OpenWeatherMapService standalone."""
    print("\n" + "="*70)
    print("TEST 2: OpenWeatherMap Service (Standalone)")
    print("="*70)

    try:
        from app.services.weather_service import OpenWeatherMapService

        weather = OpenWeatherMapService()
        data = weather.get_forecast(14.6507, 121.1029)

        if data:
            current = data.get("current", {})
            print(f"✅ SUCCESS: Fetched weather data")
            print(f"\nCurrent Conditions:")
            print(f"  Temperature: {current.get('temp')}°C")
            print(f"  Humidity: {current.get('humidity')}%")
            print(f"  Pressure: {current.get('pressure')} hPa")
            rain = current.get("rain", {}).get("1h", 0)
            print(f"  Rainfall: {rain} mm/hr")
            return True
        else:
            print("❌ FAILED: No weather data returned")
            return False

    except ValueError as e:
        print(f"⚠️ WARNING: {e}")
        print("   Make sure OPENWEATHERMAP_API_KEY is set in .env file")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_flood_agent_integration():
    """Test FloodAgent with real APIs."""
    print("\n" + "="*70)
    print("TEST 3: FloodAgent Integration with Real APIs")
    print("="*70)

    try:
        # Initialize environment and agents
        print("Initializing environment and agents...")
        env = DynamicGraphEnvironment()
        hazard_agent = HazardAgent("hazard_test_001", env)
        flood_agent = FloodAgent(
            "flood_test_001",
            env,
            hazard_agent=hazard_agent,
            use_simulated=False,
            use_real_apis=True
        )

        # Check if services initialized
        print(f"\nAPI Services Status:")
        print(f"  River Scraper: {'✅ Active' if flood_agent.river_scraper else '❌ Inactive'}")
        print(f"  Weather Service: {'✅ Active' if flood_agent.weather_service else '❌ Inactive'}")

        # Collect data
        print("\nCollecting flood data from all sources...")
        data = flood_agent.collect_and_forward_data()

        if data:
            print(f"\n✅ SUCCESS: Collected {len(data)} data points")
            print("\nData Breakdown:")
            for location, location_data in data.items():
                print(f"\n📍 {location}:")
                for key, value in location_data.items():
                    if key != "forecast_hourly":  # Skip detailed forecast
                        print(f"    {key}: {value}")

            # Check HazardAgent received data
            print(f"\nHazardAgent Cache Status:")
            print(f"  Flood data cache: {len(hazard_agent.flood_data_cache)} locations")
            print(f"  Scout data cache: {len(hazard_agent.scout_data_cache)} reports")

            return True
        else:
            print("❌ FAILED: No data collected")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoint():
    """Test the API endpoint for flood data collection."""
    print("\n" + "="*70)
    print("TEST 4: API Endpoint Test")
    print("="*70)

    try:
        import requests

        print("Testing /api/admin/collect-flood-data endpoint...")
        print("(Make sure the FastAPI server is running: uvicorn app.main:app --reload)")

        response = requests.post(
            "http://localhost:8000/api/admin/collect-flood-data",
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ SUCCESS: API endpoint working")
            print(f"Response:")
            print(f"  Status: {result.get('status')}")
            print(f"  Locations updated: {result.get('locations_updated')}")
            print(f"  Data summary: {result.get('data_summary')}")
            return True
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("⚠️ SKIPPED: FastAPI server not running")
        print("   Start server: uvicorn app.main:app --reload")
        return None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("REAL API INTEGRATION TEST SUITE")
    print("="*70)
    print("\nThis script tests the FloodAgent integration with:")
    print("  1. PAGASA River Scraper Service")
    print("  2. OpenWeatherMap API Service")
    print("\nMake sure your .env file contains:")
    print("  OPENWEATHERMAP_API_KEY=your_key_here")
    print("="*70)

    results = []

    # Run tests
    results.append(("River Scraper", test_river_scraper_standalone()))
    results.append(("Weather Service", test_weather_service_standalone()))
    results.append(("FloodAgent Integration", test_flood_agent_integration()))
    results.append(("API Endpoint", test_api_endpoint()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)

    for test_name, result in results:
        status = "✅ PASS" if result is True else ("❌ FAIL" if result is False else "⚠️ SKIP")
        print(f"{status}: {test_name}")

    print(f"\nResults: {passed} passed, {failed} failed, {skipped} skipped")

    if failed == 0 and passed > 0:
        print("\n🎉 All tests passed! Real API integration is working!")
    elif failed > 0:
        print("\n⚠️ Some tests failed. Check error messages above.")
    else:
        print("\n⚠️ No tests completed successfully.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
