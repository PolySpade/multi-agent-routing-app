"""
Admin endpoints for the mock server.

Provides CRUD operations and scenario loading for interactive testing.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

from ..data_store import get_data_store
from ..scenarios import load_scenario

router = APIRouter()


# --- Request Models ---

class ScenarioRequest(BaseModel):
    scenario: str  # "light", "medium", "heavy"

class SocialPostRequest(BaseModel):
    username: str = "mock_user"
    text: str
    timestamp: Optional[str] = None
    image_path: Optional[str] = None
    replies: str = "0"
    retweets: str = "0"
    likes: str = "0"

class RiverUpdateRequest(BaseModel):
    station_name: str
    water_level_m: Optional[float] = None
    alert_level_m: Optional[float] = None
    alarm_level_m: Optional[float] = None
    critical_level_m: Optional[float] = None

class DamUpdateRequest(BaseModel):
    dam_name: str
    latest_rwl: Optional[float] = None
    nhwl: Optional[float] = None
    dev_nhwl: Optional[float] = None
    rule_curve: Optional[float] = None
    dev_rule_curve: Optional[float] = None

class WeatherUpdateRequest(BaseModel):
    temp: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    rain_1h: Optional[float] = None
    rain_3h_forecast: Optional[float] = None
    weather_main: str = "Rain"

class AdvisoryCreateRequest(BaseModel):
    title: str
    text: str
    pub_date: Optional[str] = None


# --- Endpoints ---

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """Simple admin dashboard HTML page."""
    store = get_data_store()
    html = f"""<!DOCTYPE html>
<html>
<head><title>Mock Server Admin</title>
<style>
body {{ font-family: sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
h1 {{ color: #333; }}
.stats {{ background: #f0f0f0; padding: 15px; border-radius: 8px; margin: 15px 0; }}
.section {{ margin: 20px 0; }}
form {{ background: #fff; border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin: 10px 0; }}
input, select, textarea {{ margin: 5px 0; padding: 8px; width: 100%; box-sizing: border-box; }}
button {{ background: #007bff; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 4px; }}
button:hover {{ background: #0056b3; }}
</style>
</head>
<body>
<h1>MAS-FRO Mock Server Admin</h1>

<div class="stats">
    <h3>Current Data</h3>
    <p>River Stations: {len(store.river_stations)}</p>
    <p>Dam Levels: {len(store.dam_levels)}</p>
    <p>Advisories: {len(store.advisories)}</p>
    <p>Social Posts: {len(store.social_posts)}</p>
    <p>Weather: {"Loaded" if store.current_weather else "Empty"}</p>
</div>

<div class="section">
    <h3>Load Scenario</h3>
    <form action="/admin/scenario/load" method="post" id="scenarioForm">
        <select name="scenario" id="scenarioSelect">
            <option value="light">Light (Normal)</option>
            <option value="medium">Medium (Alert)</option>
            <option value="heavy">Heavy (Critical)</option>
        </select>
        <button type="button" onclick="loadScenario()">Load Scenario</button>
    </form>
</div>

<div class="section">
    <h3>Add Social Post</h3>
    <form id="socialForm">
        <input type="text" id="postUsername" placeholder="Username" value="mock_user">
        <textarea id="postText" placeholder="Tweet text" rows="3"></textarea>
        <button type="button" onclick="addPost()">Add Post</button>
    </form>
</div>

<script>
async function loadScenario() {{
    const scenario = document.getElementById('scenarioSelect').value;
    const resp = await fetch('/admin/scenario/load', {{
        method: 'POST', headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{scenario}})
    }});
    const data = await resp.json();
    alert(JSON.stringify(data, null, 2));
    location.reload();
}}
async function addPost() {{
    const resp = await fetch('/admin/social/post', {{
        method: 'POST', headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
            username: document.getElementById('postUsername').value,
            text: document.getElementById('postText').value
        }})
    }});
    const data = await resp.json();
    alert('Post added: ' + data.tweet_id);
    location.reload();
}}
</script>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.post("/admin/scenario/load")
async def load_scenario_endpoint(req: ScenarioRequest):
    """Load a preset scenario (light/medium/heavy)."""
    return load_scenario(req.scenario)


@router.post("/admin/social/post")
async def create_social_post(req: SocialPostRequest):
    """Create a new social post."""
    store = get_data_store()
    return store.add_social_post(req.model_dump())


@router.post("/admin/river/update")
async def update_river_station(req: RiverUpdateRequest):
    """Update a river station's data."""
    store = get_data_store()
    data = {k: v for k, v in req.model_dump().items() if v is not None and k != "station_name"}
    store.update_river_station(req.station_name, data)
    return {"status": "success", "station": req.station_name}


@router.post("/admin/dam/update")
async def update_dam(req: DamUpdateRequest):
    """Update dam level data."""
    store = get_data_store()
    data = {k: v for k, v in req.model_dump().items() if v is not None and k != "dam_name"}
    store.update_dam(req.dam_name, data)
    return {"status": "success", "dam": req.dam_name}


@router.post("/admin/weather/update")
async def update_weather(req: WeatherUpdateRequest):
    """Update weather data."""
    import time
    store = get_data_store()
    weather_update = {"current": dict(store.get_current_weather())}

    if not weather_update["current"]:
        weather_update["current"] = {
            "coord": {"lon": 121.1029, "lat": 14.6507},
            "weather": [{"main": req.weather_main}],
            "main": {"temp": 30.0, "humidity": 70, "pressure": 1013},
            "rain": {},
            "dt": int(time.time()),
            "name": "Marikina",
        }

    if req.temp is not None:
        weather_update["current"].setdefault("main", {})["temp"] = req.temp
    if req.humidity is not None:
        weather_update["current"].setdefault("main", {})["humidity"] = req.humidity
    if req.pressure is not None:
        weather_update["current"].setdefault("main", {})["pressure"] = req.pressure
    if req.rain_1h is not None:
        weather_update["current"]["rain"] = {"1h": req.rain_1h}
    weather_update["current"]["weather"] = [{"main": req.weather_main}]

    store.update_weather(weather_update)
    return {"status": "success"}


@router.post("/admin/advisory/create")
async def create_advisory(req: AdvisoryCreateRequest):
    """Create a new advisory."""
    store = get_data_store()
    return store.add_advisory(req.model_dump())
