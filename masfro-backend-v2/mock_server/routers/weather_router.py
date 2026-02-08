"""
OpenWeatherMap-compatible mock endpoints.

Serves JSON in the exact same format as the real OpenWeatherMap 2.5 API
so that OpenWeatherMapService can consume it with zero logic changes.
"""

from fastapi import APIRouter, Query

from ..data_store import get_data_store

router = APIRouter()


@router.get("/weather/data/2.5/weather")
async def current_weather(
    lat: float = Query(14.6507),
    lon: float = Query(121.1029),
    appid: str = Query("mock-key"),
    units: str = Query("metric"),
):
    """
    Mock OpenWeatherMap /data/2.5/weather endpoint.
    Returns current weather in the exact OWM 2.5 JSON format.
    Used by: OpenWeatherMapService.get_forecast() (first API call)
    """
    store = get_data_store()
    weather = store.get_current_weather()

    if not weather:
        # Return minimal valid response
        return {
            "coord": {"lon": lon, "lat": lat},
            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
            "main": {"temp": 30.0, "humidity": 70, "pressure": 1013},
            "wind": {"speed": 3.0},
            "rain": {},
            "dt": 0,
            "name": "Marikina",
        }

    return weather


@router.get("/weather/data/2.5/forecast")
async def forecast(
    lat: float = Query(14.6507),
    lon: float = Query(121.1029),
    appid: str = Query("mock-key"),
    units: str = Query("metric"),
):
    """
    Mock OpenWeatherMap /data/2.5/forecast endpoint.
    Returns 5-day/3-hour forecast in exact OWM 2.5 JSON format.
    Used by: OpenWeatherMapService.get_forecast() (second API call)
    """
    store = get_data_store()
    fc = store.get_forecast()

    if not fc:
        return {"list": [], "cnt": 0}

    return fc
