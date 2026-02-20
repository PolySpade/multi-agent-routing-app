"""
Preset scenario loaders for mock data.

Scenario data is defined in scenarios.json (same directory).
Edit that file to change water levels, weather, advisories, or social posts.

Three scenarios:
- light:  Normal conditions, minimal flooding
- medium: Moderate flooding, some alerts
- heavy:  Severe flooding, critical conditions
"""

import copy
import json
import time
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Dict, Any

from .data_store import get_data_store

_SCENARIOS_FILE = Path(__file__).parent / "scenarios.json"

FORECAST_COUNT = 40  # Number of 3-hour forecast slots to generate


def _now_rfc2822() -> str:
    return format_datetime(datetime.now(timezone.utc))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_forecast(template_entries: list, count: int = FORECAST_COUNT) -> list:
    """
    Generate `count` forecast entries by cycling through the template entries.
    Each entry gets a `dt` timestamp spaced 3 hours apart starting from now.
    """
    now = int(time.time())
    result = []
    for i in range(count):
        entry = copy.deepcopy(template_entries[i % len(template_entries)])
        entry["dt"] = now + i * 3 * 3600
        result.append(entry)
    return result


def load_scenario(name: str) -> Dict[str, Any]:
    """Load a named scenario from scenarios.json. Returns a status dict."""
    try:
        with open(_SCENARIOS_FILE, encoding="utf-8") as f:
            scenarios = json.load(f)
    except FileNotFoundError:
        return {"status": "error", "message": f"scenarios.json not found at {_SCENARIOS_FILE}"}
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Invalid JSON in scenarios.json: {e}"}

    data = scenarios.get(name.lower())
    if not data:
        available = ", ".join(scenarios.keys())
        return {"status": "error", "message": f"Unknown scenario '{name}'. Available: {available}"}

    store = get_data_store()
    store.reset()

    # River stations
    for s in data.get("river_stations", []):
        store.update_river_station(s["station_name"], s)

    # Dam levels
    for d in data.get("dam_levels", []):
        store.update_dam(d["dam_name"], d)

    # Weather — inject current timestamp into the current conditions block
    current = copy.deepcopy(data["weather_current"])
    current["dt"] = int(time.time())
    store.update_weather({
        "current": current,
        "forecast": {"list": _build_forecast(data.get("weather_forecast", [current]))},
    })

    # Advisories — inject pub_date as current time
    for adv in data.get("advisories", []):
        store.add_advisory({**adv, "pub_date": _now_rfc2822()})

    # Social posts — inject timestamp as current time
    for post in data.get("social_posts", []):
        store.add_social_post({**post, "timestamp": _now_iso()})

    return {
        "status": "success",
        "scenario": name,
        "river_stations": len(store.river_stations),
        "dam_levels": len(store.dam_levels),
        "advisories": len(store.advisories),
        "social_posts": len(store.social_posts),
    }
