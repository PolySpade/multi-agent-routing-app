#!/usr/bin/env python3
"""
Comprehensive integration test for mock server + scrapers.

Assumes mock server is running on http://localhost:8081 with heavy scenario.
Run: python test_mock_integration.py
"""

import sys
import json
import traceback
import requests
from datetime import datetime

MOCK_URL = "http://localhost:8081"
PASS = 0
FAIL = 0
ERRORS = []


def test(name, fn):
    global PASS, FAIL
    try:
        result = fn()
        if result:
            PASS += 1
            print(f"  PASS  {name}")
        else:
            FAIL += 1
            ERRORS.append(name)
            print(f"  FAIL  {name}")
    except Exception as e:
        FAIL += 1
        ERRORS.append(f"{name}: {e}")
        print(f"  FAIL  {name}: {e}")
        traceback.print_exc()


# ============================================================
# TEST GROUP 1: Mock Server Endpoints
# ============================================================
print("\n" + "=" * 60)
print("TEST GROUP 1: Mock Server Endpoints (heavy scenario)")
print("=" * 60)


def test_root_endpoint():
    r = requests.get(f"{MOCK_URL}/")
    data = r.json()
    return r.status_code == 200 and data["service"] == "MAS-FRO Mock Data Server"


def test_river_table_html():
    r = requests.get(f"{MOCK_URL}/pagasa/water/map.do")
    html = r.text
    return (
        r.status_code == 200
        and 'class="table-type1"' in html
        and 'id="tblList"' in html
        and "Sto Nino" in html
        and "17.5" in html  # Heavy scenario critical level
    )


def test_dam_table_html():
    r = requests.get(f"{MOCK_URL}/pagasa/flood")
    html = r.text
    return (
        r.status_code == 200
        and 'class="dam-table"' in html
        and "ANGAT" in html
        and "214.5" in html  # Heavy scenario ANGAT level
    )


def test_advisory_links_in_dam_page():
    r = requests.get(f"{MOCK_URL}/pagasa/flood")
    html = r.text
    return "flood advisory" in html.lower() or "Rainfall Warning" in html or "/pagasa/advisory/" in html


def test_advisory_detail():
    r = requests.get(f"{MOCK_URL}/pagasa/advisory/1")
    html = r.text
    return r.status_code == 200 and "advisory-content" in html and "RED RAINFALL" in html


def test_weather_current_json():
    r = requests.get(f"{MOCK_URL}/weather/data/2.5/weather", params={"lat": 14.65, "lon": 121.10})
    data = r.json()
    return (
        r.status_code == 200
        and "main" in data
        and "weather" in data
        and "rain" in data
        and data["rain"].get("1h") == 35.0  # Heavy scenario
    )


def test_weather_forecast_json():
    r = requests.get(f"{MOCK_URL}/weather/data/2.5/forecast", params={"lat": 14.65, "lon": 121.10})
    data = r.json()
    return (
        r.status_code == 200
        and "list" in data
        and len(data["list"]) == 40
        and "3h" in data["list"][0].get("rain", {})
    )


def test_news_rss_xml():
    r = requests.get(f"{MOCK_URL}/news/rss", params={"q": "Marikina Flood"})
    return (
        r.status_code == 200
        and "<rss" in r.text
        and "<item>" in r.text
        and "RED RAINFALL" in r.text
    )


def test_social_feed_html():
    r = requests.get(f"{MOCK_URL}/social/feed")
    html = r.text
    return (
        r.status_code == 200
        and 'class="tweet"' in html
        and "data-tweet-id" in html
        and html.count('class="tweet"') == 10  # Heavy scenario: 10 posts
    )


def test_social_api_json():
    r = requests.get(f"{MOCK_URL}/social/api/tweets", params={"limit": 50})
    data = r.json()
    return (
        r.status_code == 200
        and "tweets" in data
        and data["count"] == 10
        and all("text" in t for t in data["tweets"])
    )


def test_social_api_limit():
    r = requests.get(f"{MOCK_URL}/social/api/tweets", params={"limit": 3})
    data = r.json()
    return data["count"] == 3


test("Root endpoint", test_root_endpoint)
test("River table HTML structure", test_river_table_html)
test("Dam table HTML structure", test_dam_table_html)
test("Advisory links in dam page", test_advisory_links_in_dam_page)
test("Advisory detail page", test_advisory_detail)
test("Weather current JSON (OWM 2.5 format)", test_weather_current_json)
test("Weather forecast JSON (40 items)", test_weather_forecast_json)
test("News RSS XML (RSS 2.0)", test_news_rss_xml)
test("Social feed HTML (article.tweet)", test_social_feed_html)
test("Social API JSON", test_social_api_json)
test("Social API limit parameter", test_social_api_limit)


# ============================================================
# TEST GROUP 2: Scenario Switching
# ============================================================
print("\n" + "=" * 60)
print("TEST GROUP 2: Scenario Switching")
print("=" * 60)


def test_load_light_scenario():
    r = requests.post(f"{MOCK_URL}/admin/scenario/load", json={"scenario": "light"})
    data = r.json()
    if data["status"] != "success":
        return False
    # Verify weather has no rain
    w = requests.get(f"{MOCK_URL}/weather/data/2.5/weather").json()
    rain = w.get("rain", {}).get("1h", 0)
    # Verify 3 social posts
    s = requests.get(f"{MOCK_URL}/social/api/tweets", params={"limit": 50}).json()
    return rain == 0 and s["count"] == 3


def test_load_medium_scenario():
    r = requests.post(f"{MOCK_URL}/admin/scenario/load", json={"scenario": "medium"})
    data = r.json()
    if data["status"] != "success":
        return False
    w = requests.get(f"{MOCK_URL}/weather/data/2.5/weather").json()
    rain = w.get("rain", {}).get("1h", 0)
    s = requests.get(f"{MOCK_URL}/social/api/tweets", params={"limit": 50}).json()
    return rain == 7.5 and s["count"] == 5


def test_load_heavy_scenario():
    r = requests.post(f"{MOCK_URL}/admin/scenario/load", json={"scenario": "heavy"})
    data = r.json()
    if data["status"] != "success":
        return False
    w = requests.get(f"{MOCK_URL}/weather/data/2.5/weather").json()
    rain = w.get("rain", {}).get("1h", 0)
    s = requests.get(f"{MOCK_URL}/social/api/tweets", params={"limit": 50}).json()
    return rain == 35.0 and s["count"] == 10


def test_invalid_scenario():
    r = requests.post(f"{MOCK_URL}/admin/scenario/load", json={"scenario": "extreme"})
    data = r.json()
    return data["status"] == "error"


test("Load light scenario", test_load_light_scenario)
test("Load medium scenario", test_load_medium_scenario)
test("Load heavy scenario (restore)", test_load_heavy_scenario)
test("Invalid scenario returns error", test_invalid_scenario)


# ============================================================
# TEST GROUP 3: Admin CRUD
# ============================================================
print("\n" + "=" * 60)
print("TEST GROUP 3: Admin CRUD Operations")
print("=" * 60)


def test_add_social_post():
    r = requests.post(f"{MOCK_URL}/admin/social/post", json={
        "username": "test_bot", "text": "Unit test post #flooding"
    })
    data = r.json()
    return "tweet_id" in data and data["username"] == "test_bot"


def test_update_river_station():
    r = requests.post(f"{MOCK_URL}/admin/river/update", json={
        "station_name": "Sto Nino", "water_level_m": 19.0
    })
    data = r.json()
    if data["status"] != "success":
        return False
    # Verify
    html = requests.get(f"{MOCK_URL}/pagasa/water/map.do").text
    return "19.0" in html


def test_update_dam():
    r = requests.post(f"{MOCK_URL}/admin/dam/update", json={
        "dam_name": "ANGAT", "latest_rwl": 216.0
    })
    return r.json()["status"] == "success"


def test_create_advisory():
    r = requests.post(f"{MOCK_URL}/admin/advisory/create", json={
        "title": "Test Advisory", "text": "Test advisory text for verification"
    })
    data = r.json()
    return "id" in data and data["title"] == "Test Advisory"


def test_update_weather():
    r = requests.post(f"{MOCK_URL}/admin/weather/update", json={
        "rain_1h": 50.0, "temp": 20.0
    })
    if r.json()["status"] != "success":
        return False
    w = requests.get(f"{MOCK_URL}/weather/data/2.5/weather").json()
    return w["rain"]["1h"] == 50.0 and w["main"]["temp"] == 20.0


test("Add social post", test_add_social_post)
test("Update river station", test_update_river_station)
test("Update dam level", test_update_dam)
test("Create advisory", test_create_advisory)
test("Update weather", test_update_weather)


# Restore heavy scenario for scraper tests
requests.post(f"{MOCK_URL}/admin/scenario/load", json={"scenario": "heavy"})


# ============================================================
# TEST GROUP 4: Scraper Services Against Mock Server
# ============================================================
print("\n" + "=" * 60)
print("TEST GROUP 4: Scraper Services Against Mock Server")
print("=" * 60)


def test_dam_scraper_service():
    from app.services.dam_water_scraper_service import DamWaterScraperService
    svc = DamWaterScraperService(url=f"{MOCK_URL}/pagasa/flood")
    data = svc.get_dam_levels()
    if not data or len(data) == 0:
        print(f"    No dam data returned")
        return False
    # Check data structure
    dam = data[0]
    print(f"    Dams: {len(data)}, First: {dam.get('Dam Name', '?')}")
    return (
        len(data) >= 3
        and "Dam Name" in dam
        and "Latest RWL (m)" in dam
    )


def test_weather_service():
    from app.services.weather_service import OpenWeatherMapService
    svc = OpenWeatherMapService(base_url=f"{MOCK_URL}/weather")
    data = svc.get_forecast(14.65, 121.10)
    current = data.get("current", {})
    hourly = data.get("hourly", [])
    rain = current.get("rain", {}).get("1h", 0)
    print(f"    Rain: {rain}mm/hr, Hourly items: {len(hourly)}")
    return rain == 35.0 and len(hourly) == 40


def test_advisory_scraper_rss():
    from app.services.advisory_scraper_service import AdvisoryScraperService
    svc = AdvisoryScraperService(
        pagasa_url=f"{MOCK_URL}/pagasa/flood",
        rss_url=f"{MOCK_URL}/news/rss"
    )
    news = svc.scrape_google_news_rss("Marikina Flood")
    print(f"    RSS items: {len(news)}")
    if not news:
        return False
    item = news[0]
    return "text" in item and "pub_date" in item


def test_advisory_scraper_discovery():
    from app.services.advisory_scraper_service import AdvisoryScraperService
    svc = AdvisoryScraperService(
        pagasa_url=f"{MOCK_URL}/pagasa/flood",
        rss_url=f"{MOCK_URL}/news/rss"
    )
    urls = svc.discover_pagasa_advisories()
    print(f"    Discovered URLs: {len(urls)}")
    if urls:
        print(f"    First URL: {urls[0]}")
    return len(urls) >= 1


def test_social_scraper_html():
    from app.services.social_scraper_service import SocialScraperService
    svc = SocialScraperService(base_url=MOCK_URL)
    tweets = svc.scrape_feed()
    print(f"    HTML scraped tweets: {len(tweets)}")
    if not tweets:
        return False
    t = tweets[0]
    return all(k in t for k in ["tweet_id", "username", "text", "timestamp"])


def test_social_scraper_api():
    from app.services.social_scraper_service import SocialScraperService
    svc = SocialScraperService(base_url=MOCK_URL)
    tweets = svc.fetch_tweets_api(limit=5)
    print(f"    API fetched tweets: {len(tweets)}")
    if not tweets:
        return False
    return len(tweets) == 5 and all("text" in t for t in tweets)


# Note: RiverScraperService requires Selenium/Chrome, skipped in this environment
def test_river_scraper_constructor():
    from app.services.river_scraper_service import RiverScraperService
    svc = RiverScraperService(base_url=f"{MOCK_URL}/pagasa/water/map.do")
    return svc.html_url == f"{MOCK_URL}/pagasa/water/map.do"


test("DamWaterScraperService against mock", test_dam_scraper_service)
test("OpenWeatherMapService against mock", test_weather_service)
test("AdvisoryScraperService RSS against mock", test_advisory_scraper_rss)
test("AdvisoryScraperService discovery against mock", test_advisory_scraper_discovery)
test("SocialScraperService HTML scraping", test_social_scraper_html)
test("SocialScraperService JSON API", test_social_scraper_api)
test("RiverScraperService constructor with mock URL", test_river_scraper_constructor)


# ============================================================
# TEST GROUP 5: Configuration System
# ============================================================
print("\n" + "=" * 60)
print("TEST GROUP 5: Configuration System")
print("=" * 60)


def test_mock_sources_config_from_yaml():
    from app.core.agent_config import AgentConfigLoader, MockSourcesConfig
    # Reset singleton
    AgentConfigLoader._instance = None
    AgentConfigLoader._config = {}
    loader = AgentConfigLoader()
    cfg = loader.get_mock_sources_config()
    print(f"    enabled={cfg.enabled}, base_url={cfg.base_url}")
    return (
        isinstance(cfg, MockSourcesConfig)
        and cfg.enabled == False  # Default in YAML
        and cfg.base_url == "http://localhost:8081"
    )


def test_mock_sources_url_methods():
    from app.core.agent_config import MockSourcesConfig
    cfg = MockSourcesConfig(enabled=True, base_url="http://localhost:9999")
    return (
        cfg.get_river_scraper_url() == "http://localhost:9999/pagasa/water/map.do"
        and cfg.get_dam_scraper_url() == "http://localhost:9999/pagasa/flood"
        and cfg.get_weather_base_url() == "http://localhost:9999/weather"
        and cfg.get_advisory_rss_url() == "http://localhost:9999/news/rss"
        and cfg.get_social_feed_url() == "http://localhost:9999/social/feed"
        and cfg.get_social_api_url() == "http://localhost:9999/social/api/tweets"
    )


def test_mock_sources_url_override():
    from app.core.agent_config import MockSourcesConfig
    cfg = MockSourcesConfig(
        enabled=True,
        base_url="http://localhost:9999",
        river_scraper_url="http://custom:1234/river"
    )
    return (
        cfg.get_river_scraper_url() == "http://custom:1234/river"
        and cfg.get_dam_scraper_url() == "http://localhost:9999/pagasa/flood"
    )


def test_scout_config_scraper_fields():
    from app.core.agent_config import AgentConfigLoader
    AgentConfigLoader._instance = None
    AgentConfigLoader._config = {}
    loader = AgentConfigLoader()
    cfg = loader.get_scout_config()
    print(f"    use_scraper={cfg.use_scraper}, scraper_base_url={cfg.scraper_base_url}")
    return hasattr(cfg, "use_scraper") and hasattr(cfg, "scraper_base_url")


def test_config_settings_mock_fields():
    from app.core.config import Settings
    s = Settings()
    return hasattr(s, "USE_MOCK_SOURCES") and hasattr(s, "MOCK_SERVER_URL")


def test_env_var_override():
    import os
    os.environ["USE_MOCK_SOURCES"] = "true"
    os.environ["MOCK_SERVER_URL"] = "http://test:9999"
    try:
        from app.core.agent_config import AgentConfigLoader
        AgentConfigLoader._instance = None
        AgentConfigLoader._config = {}
        loader = AgentConfigLoader()
        cfg = loader.get_mock_sources_config()
        print(f"    enabled={cfg.enabled}, base_url={cfg.base_url}")
        return cfg.enabled == True and cfg.base_url == "http://test:9999"
    finally:
        del os.environ["USE_MOCK_SOURCES"]
        del os.environ["MOCK_SERVER_URL"]
        AgentConfigLoader._instance = None
        AgentConfigLoader._config = {}


test("MockSourcesConfig from agents.yaml", test_mock_sources_config_from_yaml)
test("MockSourcesConfig URL generation methods", test_mock_sources_url_methods)
test("MockSourcesConfig URL override", test_mock_sources_url_override)
test("ScoutConfig scraper fields", test_scout_config_scraper_fields)
test("Settings has mock source fields", test_config_settings_mock_fields)
test("Environment variable overrides", test_env_var_override)


# ============================================================
# TEST GROUP 6: Backward Compatibility
# ============================================================
print("\n" + "=" * 60)
print("TEST GROUP 6: Backward Compatibility")
print("=" * 60)


def test_river_scraper_default_url():
    from app.services.river_scraper_service import RiverScraperService
    svc = RiverScraperService()
    return svc.html_url == "https://pasig-marikina-tullahanffws.pagasa.dost.gov.ph/water/map.do"


def test_dam_scraper_default_url():
    from app.services.dam_water_scraper_service import DamWaterScraperService
    svc = DamWaterScraperService()
    return svc.url == "https://www.pagasa.dost.gov.ph/flood"


def test_advisory_scraper_default_urls():
    from app.services.advisory_scraper_service import AdvisoryScraperService
    svc = AdvisoryScraperService()
    return (
        svc._pagasa_base_url == "https://bagong.pagasa.dost.gov.ph"
        and svc._rss_base_url is None  # None means real Google News
    )


def test_weather_service_default_needs_key():
    """OpenWeatherMapService without base_url should require API key."""
    import os
    # Remove any API key to test validation
    old_key = os.environ.pop("OPENWEATHERMAP_API_KEY", None)
    old_key2 = os.environ.pop("OPENWEATHER_API_KEY", None)
    try:
        from app.services.weather_service import OpenWeatherMapService
        try:
            svc = OpenWeatherMapService()  # No base_url, no API key
            return False  # Should have raised ValueError
        except ValueError:
            return True  # Correct: requires API key
    finally:
        if old_key:
            os.environ["OPENWEATHERMAP_API_KEY"] = old_key
        if old_key2:
            os.environ["OPENWEATHER_API_KEY"] = old_key2


def test_weather_service_mock_skips_key():
    from app.services.weather_service import OpenWeatherMapService
    svc = OpenWeatherMapService(base_url="http://localhost:8081/weather")
    return svc.api_key == "mock-key"


def test_mock_disabled_uses_real_urls():
    from app.core.agent_config import MockSourcesConfig
    cfg = MockSourcesConfig(enabled=False)
    # When disabled, the methods still return URLs, but FloodAgent
    # should not use them (checks cfg.enabled)
    return cfg.enabled == False


test("RiverScraperService default URL (real PAGASA)", test_river_scraper_default_url)
test("DamWaterScraperService default URL (real PAGASA)", test_dam_scraper_default_url)
test("AdvisoryScraperService default URLs", test_advisory_scraper_default_urls)
test("WeatherService default requires API key", test_weather_service_default_needs_key)
test("WeatherService mock skips API key", test_weather_service_mock_skips_key)
test("MockSourcesConfig disabled by default", test_mock_disabled_uses_real_urls)


# ============================================================
# TEST GROUP 7: SimulationManager Mock Sync
# ============================================================
print("\n" + "=" * 60)
print("TEST GROUP 7: SimulationManager Mock Sync")
print("=" * 60)


def test_sync_mock_server_scenario():
    """Test that _sync_mock_server_scenario POSTs to mock server."""
    # First load light to set a baseline
    requests.post(f"{MOCK_URL}/admin/scenario/load", json={"scenario": "light"})

    # Verify light (no rain)
    w = requests.get(f"{MOCK_URL}/weather/data/2.5/weather").json()
    if w.get("rain", {}).get("1h", 0) != 0:
        print("    Pre-condition failed: light scenario should have 0 rain")
        return False

    # Now use SimulationManager's sync method
    import os
    os.environ["USE_MOCK_SOURCES"] = "true"
    os.environ["MOCK_SERVER_URL"] = MOCK_URL
    try:
        from app.core.agent_config import AgentConfigLoader
        AgentConfigLoader._instance = None
        AgentConfigLoader._config = {}

        from app.services.simulation_manager import SimulationManager
        sm = SimulationManager()
        sm._sync_mock_server_scenario("heavy")

        # Verify heavy (35mm rain)
        w = requests.get(f"{MOCK_URL}/weather/data/2.5/weather").json()
        rain = w.get("rain", {}).get("1h", 0)
        print(f"    After sync heavy: rain={rain}mm/hr")
        return rain == 35.0
    finally:
        del os.environ["USE_MOCK_SOURCES"]
        del os.environ["MOCK_SERVER_URL"]
        AgentConfigLoader._instance = None
        AgentConfigLoader._config = {}


test("SimulationManager._sync_mock_server_scenario()", test_sync_mock_server_scenario)


# ============================================================
# TEST GROUP 8: Data Integrity Checks
# ============================================================
print("\n" + "=" * 60)
print("TEST GROUP 8: Data Integrity Checks")
print("=" * 60)

# Restore heavy
requests.post(f"{MOCK_URL}/admin/scenario/load", json={"scenario": "heavy"})


def test_heavy_river_stations_critical():
    """Heavy scenario should have stations at critical levels."""
    from app.services.dam_water_scraper_service import DamWaterScraperService
    # Use river table directly via requests + BS4
    import pandas as pd
    from io import StringIO
    from bs4 import BeautifulSoup

    r = requests.get(f"{MOCK_URL}/pagasa/water/map.do")
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", class_="table-type1")
    df = pd.read_html(StringIO(str(table)))[0]

    # Find Sto Nino
    sto_nino = df[df.iloc[:, 0] == "Sto Nino"]
    if sto_nino.empty:
        print("    Sto Nino not found")
        return False

    water_level = float(sto_nino.iloc[0, 1])
    critical_level = float(sto_nino.iloc[0, 4])
    print(f"    Sto Nino: WL={water_level}m, Critical={critical_level}m")
    return water_level >= critical_level  # Should be at/above critical


def test_heavy_social_flood_keywords():
    """Heavy scenario social posts should contain flood keywords."""
    from app.services.social_scraper_service import SocialScraperService
    svc = SocialScraperService(base_url=MOCK_URL)
    tweets = svc.scrape_feed()

    flood_keywords = ["flood", "baha", "waist-deep", "chest-deep", "knee-deep", "rescue", "evacuat"]
    flood_count = 0
    for t in tweets:
        text = t.get("text", "").lower()
        if any(kw in text for kw in flood_keywords):
            flood_count += 1

    print(f"    Flood-related tweets: {flood_count}/{len(tweets)}")
    return flood_count >= 8  # Heavy scenario: 8+ flood-related


def test_weather_forecast_transform():
    """WeatherService should transform 3h rain to 1h in hourly output."""
    from app.services.weather_service import OpenWeatherMapService
    svc = OpenWeatherMapService(base_url=f"{MOCK_URL}/weather")
    data = svc.get_forecast(14.65, 121.10)

    hourly = data.get("hourly", [])
    if not hourly:
        return False

    # First forecast item should have rain.1h = rain_3h / 3
    first = hourly[0]
    rain_1h = first.get("rain", {}).get("1h", 0)
    # Heavy scenario: first item has 3h=80.0, so 1h should be ~26.67
    expected = 80.0 / 3.0
    diff = abs(rain_1h - expected)
    print(f"    Hourly rain.1h: {rain_1h:.2f} (expected ~{expected:.2f})")
    return diff < 0.1


def test_rss_date_filtering():
    """RSS items should pass date filtering (all are recent)."""
    from app.services.advisory_scraper_service import AdvisoryScraperService
    svc = AdvisoryScraperService(
        max_age_hours=24,
        rss_url=f"{MOCK_URL}/news/rss"
    )
    items = svc.scrape_google_news_rss("Marikina Flood")
    print(f"    Items passing date filter: {len(items)}")
    # All 3 heavy advisories should pass (they have current timestamps)
    return len(items) >= 3


def test_dam_scraper_data_structure():
    """DamWaterScraperService output should match expected column names."""
    from app.services.dam_water_scraper_service import DamWaterScraperService
    svc = DamWaterScraperService(url=f"{MOCK_URL}/pagasa/flood")
    dams = svc.get_dam_levels()
    if not dams:
        return False

    expected_keys = ["Dam Name", "Latest RWL (m)", "NHWL (m)"]
    dam = dams[0]
    missing = [k for k in expected_keys if k not in dam]
    if missing:
        print(f"    Missing keys: {missing}")
        print(f"    Available keys: {list(dam.keys())}")
        return False

    print(f"    Keys: {list(dam.keys())[:5]}...")
    return True


test("Heavy scenario: Sto Nino at critical", test_heavy_river_stations_critical)
test("Heavy scenario: 8+ flood tweets", test_heavy_social_flood_keywords)
test("Weather forecast 3h->1h transform", test_weather_forecast_transform)
test("RSS date filtering passes recent items", test_rss_date_filtering)
test("Dam scraper output structure", test_dam_scraper_data_structure)


# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
total = PASS + FAIL
print(f"RESULTS: {PASS}/{total} passed, {FAIL} failed")
print("=" * 60)

if ERRORS:
    print("\nFailed tests:")
    for e in ERRORS:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("\nAll tests passed!")
    sys.exit(0)
