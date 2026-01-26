"""
Quick Test for Real API Services
=================================

Tests only the API services without loading the full agent system.

Usage:
    cd masfro-backend
    python test_services_only.py
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))


def test_river_scraper():
    """Test PAGASA River Scraper."""
    print("\n" + "="*70)
    print("TEST 1: PAGASA River Scraper Service")
    print("="*70)

    try:
        from app.services.river_scraper_service import RiverScraperService

        scraper = RiverScraperService()
        stations = scraper.get_river_levels()

        if stations:
            print(f"✅ SUCCESS: Fetched {len(stations)} river stations\n")

            # Filter Marikina stations
            marikina_stations = [
                "Sto Nino", "Nangka", "Tumana Bridge", "Montalban", "Rosario Bridge"
            ]

            print("Key Marikina River Stations:")
            print("-" * 70)
            for station in stations:
                name = station.get("station_name")
                if name in marikina_stations:
                    level = station.get("water_level_m") or "No data"
                    alert = station.get("alert_level_m") or "N/A"
                    alarm = station.get("alarm_level_m") or "N/A"
                    critical = station.get("critical_level_m") or "N/A"

                    print(f"📍 {name}")
                    print(f"   Current Level: {level} m")
                    print(f"   Alert: {alert} m | Alarm: {alarm} m | Critical: {critical} m")
                    print()

            return True
        else:
            print("❌ FAILED: No stations returned")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_weather_service():
    """Test OpenWeatherMap Service."""
    print("\n" + "="*70)
    print("TEST 2: OpenWeatherMap Service")
    print("="*70)

    try:
        from app.services.weather_service import OpenWeatherMapService

        weather = OpenWeatherMapService()
        # Marikina City Hall coordinates
        data = weather.get_forecast(14.6507, 121.1029)

        if data:
            current = data.get("current", {})
            hourly = data.get("hourly", [])

            print(f"✅ SUCCESS: Fetched weather data\n")

            print("Current Conditions (Marikina City):")
            print("-" * 70)
            print(f"🌡️  Temperature: {current.get('temp', 'N/A')}°C")
            print(f"💧 Humidity: {current.get('humidity', 'N/A')}%")
            print(f"🌬️  Pressure: {current.get('pressure', 'N/A')} hPa")

            rain = current.get("rain", {}).get("1h", 0)
            print(f"🌧️  Rainfall (1hr): {rain} mm")

            if rain > 0:
                if rain <= 2.5:
                    intensity = "Light"
                elif rain <= 7.5:
                    intensity = "Moderate"
                elif rain <= 15.0:
                    intensity = "Heavy"
                elif rain <= 30.0:
                    intensity = "Intense"
                else:
                    intensity = "Torrential"
                print(f"   Intensity: {intensity}")

            # Show 6-hour forecast
            if hourly:
                print(f"\n6-Hour Rainfall Forecast:")
                print("-" * 70)
                total_rain = 0
                for i, hour in enumerate(hourly[:6]):
                    from datetime import datetime
                    hour_rain = hour.get("rain", {}).get("1h", 0)
                    total_rain += hour_rain
                    time_str = datetime.fromtimestamp(hour.get("dt")).strftime("%I:%M %p")
                    print(f"  {time_str}: {hour_rain:.1f} mm")
                print(f"  Total 6hr: {total_rain:.1f} mm")

            return True
        else:
            print("❌ FAILED: No weather data returned")
            return False

    except ValueError as e:
        print(f"⚠️ WARNING: {e}")
        print("\n🔑 Action Required:")
        print("   1. Sign up at: https://openweathermap.org/api")
        print("   2. Get free API key (1,000 calls/day)")
        print("   3. Create .env file in masfro-backend/")
        print("   4. Add: OPENWEATHERMAP_API_KEY=your_key_here")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run service tests."""
    print("\n" + "="*70)
    print("REAL API SERVICES TEST")
    print("="*70)
    print("\nTesting direct API integrations:")
    print("  1. PAGASA River Levels (no key needed)")
    print("  2. OpenWeatherMap Weather/Rainfall (needs API key)")
    print("="*70)

    results = []

    # Test services
    results.append(("PAGASA River Scraper", test_river_scraper()))
    results.append(("OpenWeatherMap", test_weather_service()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All API services are working!")
        print("\nNext Steps:")
        print("  1. Make sure your .env file has: OPENWEATHERMAP_API_KEY=your_key")
        print("  2. Run: uvicorn app.main:app --reload")
        print("  3. Test endpoint: curl http://localhost:8000/api/admin/collect-flood-data")
    elif passed > 0:
        print("\n⚠️ Some services working. Check errors above for failed tests.")
    else:
        print("\n❌ No services working. Check your environment setup.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
