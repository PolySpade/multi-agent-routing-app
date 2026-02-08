"""
Quick FloodAgent Test
=====================
Test the FloodAgent with real API integration.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "app"))

def test_river_scraper():
    """Test 1: PAGASA River Scraper"""
    print("\n" + "="*70)
    print("TEST 1: PAGASA River Scraper Service")
    print("="*70)

    try:
        from app.services.river_scraper_service import RiverScraperService

        scraper = RiverScraperService()
        stations = scraper.get_river_levels()

        if stations:
            print(f"[PASS] Fetched {len(stations)} river stations\n")

            # Show Marikina stations
            marikina = ["Sto Nino", "Nangka", "Tumana Bridge", "Montalban", "Rosario Bridge"]
            print("Key Marikina River Stations:")
            for station in stations:
                name = station.get("station_name")
                if name in marikina:
                    level = station.get("water_level_m") or "No data"
                    alert = station.get("alert_level_m") or "N/A"
                    critical = station.get("critical_level_m") or "N/A"
                    print(f"  {name}: Current={level}m, Alert={alert}m, Critical={critical}m")

            return True
        else:
            print("[FAIL] No stations returned")
            return False

    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def test_weather_service():
    """Test 2: OpenWeatherMap Service"""
    print("\n" + "="*70)
    print("TEST 2: OpenWeatherMap Service")
    print("="*70)

    try:
        from app.services.weather_service import OpenWeatherMapService

        weather = OpenWeatherMapService()
        data = weather.get_forecast(14.6507, 121.1029)  # Marikina City Hall

        if data:
            current = data.get("current", {})
            rain = current.get("rain", {}).get("1h", 0)

            print(f"[PASS] Weather data fetched\n")
            print(f"Current Conditions:")
            print(f"  Temperature: {current.get('temp')}°C")
            print(f"  Humidity: {current.get('humidity')}%")
            print(f"  Rainfall: {rain} mm/hr")

            return True
        else:
            print("[FAIL] No weather data returned")
            return False

    except ValueError as e:
        print(f"[FAIL] {e}")
        print("  Check .env file has: OPENWEATHERMAP_API_KEY=your_key")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def test_flood_agent():
    """Test 3: FloodAgent with Real APIs"""
    print("\n" + "="*70)
    print("TEST 3: FloodAgent with Real APIs")
    print("="*70)

    try:
        # Create minimal mock environment
        class MockEnvironment:
            def __init__(self):
                self.graph = None

        class MockHazardAgent:
            def __init__(self):
                self.flood_data_cache = {}
                self.agent_id = "mock_hazard"

            def process_flood_data(self, data):
                location = data.get("location", "unknown")
                self.flood_data_cache[location] = data

        from app.agents.flood_agent import FloodAgent

        print("Initializing FloodAgent...")
        env = MockEnvironment()
        hazard = MockHazardAgent()

        flood_agent = FloodAgent(
            "test_flood_001",
            env,
            hazard_agent=hazard,
            use_simulated=False,
            use_real_apis=True
        )

        print(f"  River Scraper: {'Active' if flood_agent.river_scraper else 'Inactive'}")
        print(f"  Weather Service: {'Active' if flood_agent.weather_service else 'Inactive'}")

        # Collect data
        print("\nCollecting flood data...")
        data = flood_agent.collect_and_forward_data()

        if data:
            print(f"[PASS] Collected {len(data)} data points\n")

            print("Data Summary:")
            for location, info in data.items():
                print(f"\n  Location: {location}")
                print(f"    Source: {info.get('source', 'unknown')}")

                # River data
                if 'water_level_m' in info:
                    print(f"    Water Level: {info.get('water_level_m')} m")
                    print(f"    Status: {info.get('status')}")
                    print(f"    Risk Score: {info.get('risk_score')}")

                # Weather data
                if 'current_rainfall_mm' in info:
                    print(f"    Current Rainfall: {info.get('current_rainfall_mm')} mm/hr")
                    print(f"    24h Forecast: {info.get('rainfall_24h_mm')} mm")
                    print(f"    Intensity: {info.get('intensity')}")
                    print(f"    Temperature: {info.get('temperature_c')}°C")

            # Check HazardAgent
            print(f"\nHazardAgent Cache:")
            print(f"  Locations cached: {len(hazard.flood_data_cache)}")

            return True
        else:
            print("[FAIL] No data collected")
            return False

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("FLOODAGENT REAL API INTEGRATION TEST")
    print("="*70)

    results = []
    results.append(("PAGASA River Scraper", test_river_scraper()))
    results.append(("OpenWeatherMap", test_weather_service()))
    results.append(("FloodAgent Integration", test_flood_agent()))

    # Summary
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n*** ALL TESTS PASSED! FloodAgent is working with real APIs! ***")
    else:
        print("\n*** Some tests failed. Check errors above. ***")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
