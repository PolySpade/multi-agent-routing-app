"""
Preset scenario loaders for mock data.

Three scenarios matching the simulation modes:
- Light: Normal conditions, minimal flooding
- Medium: Moderate flooding, some alerts
- Heavy: Severe flooding, critical conditions
"""

import time
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from typing import Dict, Any

from .data_store import get_data_store


def _now_rfc2822() -> str:
    return format_datetime(datetime.now(timezone.utc))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts(offset_minutes: int = 0) -> int:
    """Unix timestamp with optional offset."""
    return int(time.time()) + (offset_minutes * 60)


def load_light_scenario():
    """Light scenario: Normal water levels, no rain, clear weather."""
    store = get_data_store()
    store.reset()

    # River stations - all normal
    stations = [
        {"station_name": "Sto Nino", "water_level_m": 12.5, "alert_level_m": 15.0, "alarm_level_m": 16.0, "critical_level_m": 17.0},
        {"station_name": "Nangka", "water_level_m": 10.2, "alert_level_m": 13.0, "alarm_level_m": 14.5, "critical_level_m": 15.5},
        {"station_name": "Tumana Bridge", "water_level_m": 11.0, "alert_level_m": 14.0, "alarm_level_m": 15.0, "critical_level_m": 16.0},
        {"station_name": "Montalban", "water_level_m": 9.8, "alert_level_m": 12.5, "alarm_level_m": 13.5, "critical_level_m": 14.5},
        {"station_name": "Rosario Bridge", "water_level_m": 11.5, "alert_level_m": 14.5, "alarm_level_m": 15.5, "critical_level_m": 16.5},
    ]
    for s in stations:
        store.update_river_station(s["station_name"], s)

    # Dams - normal levels
    dams = [
        {"dam_name": "ANGAT", "latest_rwl": 210.5, "nhwl": 212.0, "dev_nhwl": -1.5, "rule_curve": 209.0, "dev_rule_curve": 1.5,
         "previous_rwl": 210.4, "latest_time": "06:00", "latest_date": "Feb 08, 2026", "previous_time": "18:00", "previous_date": "Feb 07, 2026",
         "wl_dev_hr": 12, "wl_dev_amt": 0.1},
        {"dam_name": "IPO", "latest_rwl": 100.5, "nhwl": 101.0, "dev_nhwl": -0.5, "rule_curve": 99.5, "dev_rule_curve": 1.0,
         "previous_rwl": 100.4, "latest_time": "06:00", "latest_date": "Feb 08, 2026", "previous_time": "18:00", "previous_date": "Feb 07, 2026",
         "wl_dev_hr": 12, "wl_dev_amt": 0.1},
        {"dam_name": "LA MESA", "latest_rwl": 78.5, "nhwl": 80.15, "dev_nhwl": -1.65, "rule_curve": 77.0, "dev_rule_curve": 1.5,
         "previous_rwl": 78.4, "latest_time": "06:00", "latest_date": "Feb 08, 2026", "previous_time": "18:00", "previous_date": "Feb 07, 2026",
         "wl_dev_hr": 12, "wl_dev_amt": 0.1},
    ]
    for d in dams:
        store.update_dam(d["dam_name"], d)

    # Weather - clear
    store.update_weather({
        "current": {
            "coord": {"lon": 121.1029, "lat": 14.6507},
            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
            "main": {"temp": 31.0, "humidity": 65, "pressure": 1012},
            "wind": {"speed": 2.5},
            "rain": {},
            "dt": _ts(),
            "name": "Marikina",
        },
        "forecast": {
            "list": [
                {
                    "dt": _ts(i * 180),
                    "main": {"temp": 30.0 + (i % 3), "humidity": 60 + i, "pressure": 1012},
                    "weather": [{"main": "Clear"}],
                    "pop": 0.05,
                    "rain": {},
                } for i in range(40)
            ]
        }
    })

    # Social posts - 3 benign observation posts
    posts = [
        {"username": "marikina_watcher", "text": "Clear skies over Marikina River today. Water level looks normal. #Marikina",
         "timestamp": _now_iso(), "replies": "1", "retweets": "3", "likes": "12"},
        {"username": "weather_ph", "text": "Good morning Marikina! No rainfall expected today according to PAGASA.",
         "timestamp": _now_iso(), "replies": "0", "retweets": "5", "likes": "20"},
        {"username": "local_reporter", "text": "Traffic flowing smoothly along Marcos Highway. No flood reports.",
         "timestamp": _now_iso(), "replies": "2", "retweets": "1", "likes": "8"},
    ]
    for p in posts:
        store.add_social_post(p)


def load_medium_scenario():
    """Medium scenario: 2 stations at alert, moderate rain, some flood reports."""
    store = get_data_store()
    store.reset()

    # River stations - 2 at alert
    stations = [
        {"station_name": "Sto Nino", "water_level_m": 15.2, "alert_level_m": 15.0, "alarm_level_m": 16.0, "critical_level_m": 17.0},
        {"station_name": "Nangka", "water_level_m": 13.5, "alert_level_m": 13.0, "alarm_level_m": 14.5, "critical_level_m": 15.5},
        {"station_name": "Tumana Bridge", "water_level_m": 12.0, "alert_level_m": 14.0, "alarm_level_m": 15.0, "critical_level_m": 16.0},
        {"station_name": "Montalban", "water_level_m": 11.0, "alert_level_m": 12.5, "alarm_level_m": 13.5, "critical_level_m": 14.5},
        {"station_name": "Rosario Bridge", "water_level_m": 12.5, "alert_level_m": 14.5, "alarm_level_m": 15.5, "critical_level_m": 16.5},
    ]
    for s in stations:
        store.update_river_station(s["station_name"], s)

    # Dams - slightly elevated
    dams = [
        {"dam_name": "ANGAT", "latest_rwl": 212.3, "nhwl": 212.0, "dev_nhwl": 0.3, "rule_curve": 209.0, "dev_rule_curve": 3.3,
         "previous_rwl": 211.8, "latest_time": "06:00", "latest_date": "Feb 08, 2026", "previous_time": "18:00", "previous_date": "Feb 07, 2026",
         "wl_dev_hr": 12, "wl_dev_amt": 0.5},
        {"dam_name": "IPO", "latest_rwl": 101.2, "nhwl": 101.0, "dev_nhwl": 0.2, "rule_curve": 99.5, "dev_rule_curve": 1.7,
         "previous_rwl": 100.9, "latest_time": "06:00", "latest_date": "Feb 08, 2026", "previous_time": "18:00", "previous_date": "Feb 07, 2026",
         "wl_dev_hr": 12, "wl_dev_amt": 0.3},
        {"dam_name": "LA MESA", "latest_rwl": 79.8, "nhwl": 80.15, "dev_nhwl": -0.35, "rule_curve": 77.0, "dev_rule_curve": 2.8,
         "previous_rwl": 79.5, "latest_time": "06:00", "latest_date": "Feb 08, 2026", "previous_time": "18:00", "previous_date": "Feb 07, 2026",
         "wl_dev_hr": 12, "wl_dev_amt": 0.3},
    ]
    for d in dams:
        store.update_dam(d["dam_name"], d)

    # Weather - moderate rain (7.5 mm/hr)
    store.update_weather({
        "current": {
            "coord": {"lon": 121.1029, "lat": 14.6507},
            "weather": [{"id": 502, "main": "Rain", "description": "heavy intensity rain", "icon": "10d"}],
            "main": {"temp": 26.0, "humidity": 88, "pressure": 1005},
            "wind": {"speed": 5.0},
            "rain": {"1h": 7.5},
            "dt": _ts(),
            "name": "Marikina",
        },
        "forecast": {
            "list": [
                {
                    "dt": _ts(i * 180),
                    "main": {"temp": 25.0 + (i % 3), "humidity": 85 + (i % 10), "pressure": 1005},
                    "weather": [{"main": "Rain"}],
                    "pop": 0.7 + (i % 3) * 0.1,
                    "rain": {"3h": 15.0 + (i % 5) * 2},
                } for i in range(40)
            ]
        }
    })

    # 1 advisory
    store.add_advisory({
        "title": "PAGASA Yellow Rainfall Warning for Metro Manila",
        "text": "PAGASA has issued a yellow rainfall warning for Metro Manila including Marikina City. "
                "Moderate to heavy rainfall is expected in the next 3 hours. Water levels in the Marikina River "
                "are rising. Residents along low-lying areas are advised to monitor conditions.",
        "pub_date": _now_rfc2822(),
    })

    # 5 social posts (3 flood-related)
    posts = [
        {"username": "barangay_nangka", "text": "Water level sa Marikina River mataas na. Knee-deep flooding along Nangka area. Stay safe! #FloodAlert #Marikina",
         "timestamp": _now_iso(), "replies": "5", "retweets": "20", "likes": "45"},
        {"username": "marikina_resident", "text": "Flooding at Sto Nino area. Water is ankle-deep on the streets. Be careful if traveling. #baha #Marikina",
         "timestamp": _now_iso(), "replies": "3", "retweets": "15", "likes": "30"},
        {"username": "weather_update_ph", "text": "Heavy rain continues in Marikina area. PAGASA issued yellow warning.",
         "timestamp": _now_iso(), "replies": "1", "retweets": "8", "likes": "22"},
        {"username": "commuter_ph", "text": "Traffic is slow on Marcos Highway due to rain. Drive carefully everyone.",
         "timestamp": _now_iso(), "replies": "2", "retweets": "4", "likes": "10"},
        {"username": "food_blogger_ph", "text": "Rainy day perfect for bulalo! Any recommendations in Marikina?",
         "timestamp": _now_iso(), "replies": "10", "retweets": "2", "likes": "35"},
    ]
    for p in posts:
        store.add_social_post(p)


def load_heavy_scenario():
    """Heavy scenario: Critical flooding, torrential rain, multiple alerts."""
    store = get_data_store()
    store.reset()

    # River stations - 3 at alarm/critical
    stations = [
        {"station_name": "Sto Nino", "water_level_m": 17.5, "alert_level_m": 15.0, "alarm_level_m": 16.0, "critical_level_m": 17.0},
        {"station_name": "Nangka", "water_level_m": 15.8, "alert_level_m": 13.0, "alarm_level_m": 14.5, "critical_level_m": 15.5},
        {"station_name": "Tumana Bridge", "water_level_m": 15.5, "alert_level_m": 14.0, "alarm_level_m": 15.0, "critical_level_m": 16.0},
        {"station_name": "Montalban", "water_level_m": 13.8, "alert_level_m": 12.5, "alarm_level_m": 13.5, "critical_level_m": 14.5},
        {"station_name": "Rosario Bridge", "water_level_m": 15.0, "alert_level_m": 14.5, "alarm_level_m": 15.5, "critical_level_m": 16.5},
    ]
    for s in stations:
        store.update_river_station(s["station_name"], s)

    # Dams - elevated, Angat at critical
    dams = [
        {"dam_name": "ANGAT", "latest_rwl": 214.5, "nhwl": 212.0, "dev_nhwl": 2.5, "rule_curve": 209.0, "dev_rule_curve": 5.5,
         "previous_rwl": 213.0, "latest_time": "06:00", "latest_date": "Feb 08, 2026", "previous_time": "18:00", "previous_date": "Feb 07, 2026",
         "wl_dev_hr": 12, "wl_dev_amt": 1.5},
        {"dam_name": "IPO", "latest_rwl": 102.5, "nhwl": 101.0, "dev_nhwl": 1.5, "rule_curve": 99.5, "dev_rule_curve": 3.0,
         "previous_rwl": 101.8, "latest_time": "06:00", "latest_date": "Feb 08, 2026", "previous_time": "18:00", "previous_date": "Feb 07, 2026",
         "wl_dev_hr": 12, "wl_dev_amt": 0.7},
        {"dam_name": "LA MESA", "latest_rwl": 81.0, "nhwl": 80.15, "dev_nhwl": 0.85, "rule_curve": 77.0, "dev_rule_curve": 4.0,
         "previous_rwl": 80.2, "latest_time": "06:00", "latest_date": "Feb 08, 2026", "previous_time": "18:00", "previous_date": "Feb 07, 2026",
         "wl_dev_hr": 12, "wl_dev_amt": 0.8},
    ]
    for d in dams:
        store.update_dam(d["dam_name"], d)

    # Weather - torrential rain (35 mm/hr)
    store.update_weather({
        "current": {
            "coord": {"lon": 121.1029, "lat": 14.6507},
            "weather": [{"id": 503, "main": "Rain", "description": "very heavy rain", "icon": "10d"}],
            "main": {"temp": 24.0, "humidity": 95, "pressure": 998},
            "wind": {"speed": 12.0},
            "rain": {"1h": 35.0},
            "dt": _ts(),
            "name": "Marikina",
        },
        "forecast": {
            "list": [
                {
                    "dt": _ts(i * 180),
                    "main": {"temp": 23.0 + (i % 2), "humidity": 92 + (i % 8), "pressure": 998},
                    "weather": [{"main": "Rain"}],
                    "pop": 0.95,
                    "rain": {"3h": 80.0 + (i % 5) * 5},
                } for i in range(40)
            ]
        }
    })

    # 3 advisories
    store.add_advisory({
        "title": "PAGASA Red Rainfall Warning - Marikina City",
        "text": "PAGASA has raised a RED RAINFALL WARNING for Marikina City and surrounding areas. "
                "Torrential rainfall exceeding 30mm/hr has been recorded. The Marikina River has breached "
                "critical levels at Sto Nino station (17.5m). Immediate evacuation is advised for residents "
                "in low-lying barangays including Tumana, Nangka, and Malanday.",
    })
    store.add_advisory({
        "title": "Angat Dam Spilling Advisory",
        "text": "NIA reports that Angat Dam water level has reached 214.5m, which is 2.5m above the "
                "Normal High Water Level of 212.0m. Controlled spillway operations are underway. "
                "Downstream communities along the Angat-Ipo-La Mesa water system should prepare for "
                "increased water flow. Dam status: CRITICAL.",
    })
    store.add_advisory({
        "title": "Flood Bulletin - Marikina River System",
        "text": "As of 06:00 AM today, the Marikina River has reached critical levels. "
                "Sto Nino station: 17.5m (Critical), Nangka: 15.8m (Critical), "
                "Tumana Bridge: 15.5m (Alarm). Forced evacuation orders have been issued "
                "for Barangays Tumana, Nangka, and Malanday. All residents must proceed to "
                "nearest evacuation centers immediately.",
    })

    # 10 social posts (8 flood-related with depth keywords)
    posts = [
        {"username": "barangay_tumana", "text": "EMERGENCY! Waist-deep flooding in Tumana! Rescue operations ongoing. Please evacuate immediately! #BahaMarikina #FloodAlert",
         "timestamp": _now_iso(), "replies": "25", "retweets": "150", "likes": "200"},
        {"username": "marikina_rescue", "text": "Chest-deep na ang baha sa Nangka! RESCUE TEAM deployed. Call 161 for help. #Marikina #Rescue",
         "timestamp": _now_iso(), "replies": "30", "retweets": "200", "likes": "300"},
        {"username": "news_ph", "text": "BREAKING: Marikina River breaches critical level. Forced evacuation ordered for 3 barangays. Water level at 17.5m at Sto Nino.",
         "timestamp": _now_iso(), "replies": "50", "retweets": "500", "likes": "400"},
        {"username": "resident_malanday", "text": "Knee-deep flooding here in Malanday. Water keeps rising. We need help! #baha #Malanday",
         "timestamp": _now_iso(), "replies": "8", "retweets": "45", "likes": "60"},
        {"username": "mmda_traffic", "text": "Marcos Highway IMPASSABLE due to flooding. Waist-deep in some areas. Use alternate routes via Ortigas Extension.",
         "timestamp": _now_iso(), "replies": "15", "retweets": "100", "likes": "80"},
        {"username": "parang_resident", "text": "Water ankle-deep na here in Parang area. Still manageable but river level rising fast. #StaySafe",
         "timestamp": _now_iso(), "replies": "3", "retweets": "10", "likes": "25"},
        {"username": "volunteer_ph", "text": "Deployed at Marikina Sports Center evacuation site. Need more blankets and food. Waist-deep flooding in surrounding streets.",
         "timestamp": _now_iso(), "replies": "20", "retweets": "80", "likes": "150"},
        {"username": "concerned_citizen", "text": "Chest-deep baha along J.P. Rizal near Riverbanks. Cars stranded. Do NOT attempt to cross! #FloodWarning",
         "timestamp": _now_iso(), "replies": "12", "retweets": "120", "likes": "175"},
        {"username": "weather_enthusiast", "text": "Recording 35mm/hr rainfall in Marikina. This is torrential level. Stay indoors if possible.",
         "timestamp": _now_iso(), "replies": "5", "retweets": "30", "likes": "40"},
        {"username": "pet_rescue_ph", "text": "Anyone in San Roque area? Several pets stranded on rooftops. Water is thigh-deep. Need boat rescue.",
         "timestamp": _now_iso(), "replies": "15", "retweets": "60", "likes": "90"},
    ]
    for p in posts:
        store.add_social_post(p)


SCENARIO_LOADERS = {
    "light": load_light_scenario,
    "medium": load_medium_scenario,
    "heavy": load_heavy_scenario,
}


def load_scenario(name: str) -> Dict[str, Any]:
    """Load a named scenario. Returns status dict."""
    loader = SCENARIO_LOADERS.get(name.lower())
    if not loader:
        return {"status": "error", "message": f"Unknown scenario: {name}. Use light/medium/heavy."}
    loader()
    store = get_data_store()
    return {
        "status": "success",
        "scenario": name,
        "river_stations": len(store.river_stations),
        "dam_levels": len(store.dam_levels),
        "advisories": len(store.advisories),
        "social_posts": len(store.social_posts),
    }
