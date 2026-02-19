"""
Admin endpoints for the mock server.

Provides CRUD operations and scenario loading for interactive testing.
Serves a full-featured dashboard for managing all mock data.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

from ..data_store import get_data_store
from ..scenarios import load_scenario

UPLOADS_DIR = Path(__file__).parent.parent / "uploads"

router = APIRouter()


# --- Request Models ---

class ScenarioRequest(BaseModel):
    scenario: str  # "light", "medium", "heavy"

class SocialPostRequest(BaseModel):
    username: str = "mock_user"
    text: str
    timestamp: Optional[str] = None
    image_path: Optional[str] = None

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
    weather_description: Optional[str] = None
    wind_speed: Optional[float] = None

class AdvisoryCreateRequest(BaseModel):
    title: str
    text: str
    pub_date: Optional[str] = None


# --- Dashboard ---

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """Full-featured admin dashboard."""
    store = get_data_store()

    # Build river station rows
    river_rows = ""
    for s in store.get_river_stations():
        wl = s.get("water_level_m", 0)
        al = s.get("alert_level_m", 0)
        am = s.get("alarm_level_m", 0)
        cl = s.get("critical_level_m", 0)
        # Determine status
        if wl >= cl:
            badge = '<span class="badge badge-critical">CRITICAL</span>'
        elif wl >= am:
            badge = '<span class="badge badge-alarm">ALARM</span>'
        elif wl >= al:
            badge = '<span class="badge badge-alert">ALERT</span>'
        else:
            badge = '<span class="badge badge-normal">Normal</span>'
        river_rows += f"""<tr>
            <td class="font-medium">{s.get('station_name','')}</td>
            <td>{wl}</td><td>{al}</td><td>{am}</td><td>{cl}</td>
            <td>{badge}</td>
        </tr>"""

    # Build dam rows
    dam_rows = ""
    for d in store.get_dam_levels():
        rwl = d.get("latest_rwl", 0)
        nhwl = d.get("nhwl", 0)
        dev = d.get("dev_nhwl", 0)
        dev_class = "text-danger" if dev > 0 else "text-success"
        dam_rows += f"""<tr>
            <td class="font-medium">{d.get('dam_name','')}</td>
            <td>{rwl}</td><td>{nhwl}</td>
            <td class="{dev_class}">{dev:+.2f}</td>
            <td>{d.get('rule_curve','')}</td>
            <td>{d.get('dev_rule_curve','')}</td>
        </tr>"""

    # Build advisory rows
    advisory_rows = ""
    for a in store.get_advisories():
        advisory_rows += f"""<tr>
            <td>#{a.get('id','')}</td>
            <td class="font-medium">{a.get('title','')}</td>
            <td class="text-muted" style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{a.get('text','')[:100]}...</td>
            <td class="text-muted">{a.get('pub_date','')[:20]}</td>
        </tr>"""

    # Build social post rows
    post_rows = ""
    for p in store.get_social_posts():
        img_cell = ""
        if p.get("image_path"):
            img_cell = f'<img src="{p["image_path"]}" style="max-height:32px;border-radius:4px" alt="img">'
        post_rows += f"""<tr>
            <td class="font-medium">@{p.get('username','')}</td>
            <td style="max-width:350px">{p.get('text','')[:120]}</td>
            <td>{img_cell}</td>
            <td class="text-muted">{p.get('timestamp','')[:19]}</td>
        </tr>"""

    # Evacuation stats placeholder (fetched client-side from main backend)
    evac_stat_count = "..."

    # Weather summary
    w = store.get_current_weather()
    if w:
        w_main = w.get("weather", [{}])[0].get("main", "N/A")
        w_desc = w.get("weather", [{}])[0].get("description", "")
        w_temp = w.get("main", {}).get("temp", "N/A")
        w_humidity = w.get("main", {}).get("humidity", "N/A")
        w_pressure = w.get("main", {}).get("pressure", "N/A")
        w_wind = w.get("wind", {}).get("speed", "N/A")
        w_rain = w.get("rain", {}).get("1h", 0)
    else:
        w_main = w_desc = "N/A"
        w_temp = w_humidity = w_pressure = w_wind = w_rain = "N/A"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MAS-FRO Mock Server</title>
<style>
:root {{
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #232733;
    --border: #2d3140;
    --text: #e4e6ed;
    --text-muted: #8b8fa3;
    --primary: #6366f1;
    --primary-hover: #818cf8;
    --success: #22c55e;
    --warning: #f59e0b;
    --danger: #ef4444;
    --info: #3b82f6;
    --radius: 8px;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; }}

/* Layout */
.container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
.header {{ display: flex; align-items: center; justify-content: space-between; padding: 20px 0; border-bottom: 1px solid var(--border); margin-bottom: 24px; }}
.header h1 {{ font-size: 1.5rem; font-weight: 700; }}
.header h1 span {{ color: var(--primary); }}

/* Stats bar */
.stats-bar {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }}
.stat-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; }}
.stat-card .label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 4px; }}
.stat-card .value {{ font-size: 1.5rem; font-weight: 700; }}

/* Scenario selector */
.scenario-bar {{ display: flex; align-items: center; gap: 12px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; margin-bottom: 24px; }}
.scenario-bar label {{ font-weight: 600; white-space: nowrap; }}
.scenario-btns {{ display: flex; gap: 8px; }}
.scenario-btn {{ padding: 8px 20px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface2); color: var(--text); cursor: pointer; font-size: 0.875rem; font-weight: 500; transition: all 0.15s; }}
.scenario-btn:hover {{ border-color: var(--primary); color: var(--primary); }}
.scenario-btn.active {{ background: var(--primary); border-color: var(--primary); color: #fff; }}

/* Tabs */
.tabs {{ display: flex; gap: 4px; border-bottom: 1px solid var(--border); margin-bottom: 20px; overflow-x: auto; }}
.tab {{ padding: 10px 20px; border: none; background: none; color: var(--text-muted); cursor: pointer; font-size: 0.875rem; font-weight: 500; border-bottom: 2px solid transparent; transition: all 0.15s; white-space: nowrap; }}
.tab:hover {{ color: var(--text); }}
.tab.active {{ color: var(--primary); border-bottom-color: var(--primary); }}
.tab-panel {{ display: none; }}
.tab-panel.active {{ display: block; }}

/* Cards */
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 20px; overflow: hidden; }}
.card-header {{ padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }}
.card-header h3 {{ font-size: 0.95rem; font-weight: 600; }}
.card-body {{ padding: 20px; }}

/* Tables */
table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
th {{ text-align: left; padding: 10px 12px; color: var(--text-muted); font-weight: 500; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border); }}
td {{ padding: 10px 12px; border-bottom: 1px solid var(--border); }}
tr:last-child td {{ border-bottom: none; }}
tr:hover td {{ background: var(--surface2); }}

/* Forms */
.form-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
.form-group {{ display: flex; flex-direction: column; gap: 4px; }}
.form-group label {{ font-size: 0.75rem; font-weight: 500; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.03em; }}
.form-group input, .form-group textarea, .form-group select {{
    padding: 8px 12px; background: var(--surface2); border: 1px solid var(--border); border-radius: 6px;
    color: var(--text); font-size: 0.875rem; font-family: inherit; transition: border-color 0.15s;
}}
.form-group input:focus, .form-group textarea:focus {{ outline: none; border-color: var(--primary); }}
.form-group textarea {{ resize: vertical; min-height: 60px; }}
.form-row {{ grid-column: 1 / -1; }}

/* Buttons */
.btn {{ padding: 8px 20px; border-radius: 6px; border: none; font-size: 0.875rem; font-weight: 500; cursor: pointer; transition: all 0.15s; }}
.btn-primary {{ background: var(--primary); color: #fff; }}
.btn-primary:hover {{ background: var(--primary-hover); }}
.btn-success {{ background: var(--success); color: #fff; }}
.btn-success:hover {{ opacity: 0.9; }}
.btn-sm {{ padding: 6px 14px; font-size: 0.8rem; }}
.form-actions {{ display: flex; gap: 8px; margin-top: 12px; }}

/* Badges */
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }}
.badge-normal {{ background: rgba(34,197,94,0.15); color: var(--success); }}
.badge-alert {{ background: rgba(245,158,11,0.15); color: var(--warning); }}
.badge-alarm {{ background: rgba(239,68,68,0.15); color: var(--danger); }}
.badge-critical {{ background: rgba(239,68,68,0.3); color: #ff6b6b; animation: pulse 1.5s infinite; }}
@keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.6; }} }}

/* Weather card */
.weather-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 16px; }}
.weather-item {{ text-align: center; }}
.weather-item .wi-value {{ font-size: 1.25rem; font-weight: 700; }}
.weather-item .wi-label {{ font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; }}

/* Toast */
.toast {{ position: fixed; bottom: 24px; right: 24px; background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 12px 20px; font-size: 0.875rem; box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    transform: translateY(100px); opacity: 0; transition: all 0.3s; z-index: 1000; }}
.toast.show {{ transform: translateY(0); opacity: 1; }}
.toast.success {{ border-left: 3px solid var(--success); }}
.toast.error {{ border-left: 3px solid var(--danger); }}

.font-medium {{ font-weight: 500; }}
.text-muted {{ color: var(--text-muted); }}
.text-danger {{ color: var(--danger); }}
.text-success {{ color: var(--success); }}
.text-warning {{ color: var(--warning); }}
.empty-state {{ text-align: center; padding: 40px; color: var(--text-muted); }}
</style>
</head>
<body>
<div class="container">
    <!-- Header -->
    <div class="header">
        <h1><span>MAS-FRO</span> Mock Data Server</h1>
        <span class="text-muted" style="font-size:0.8rem">localhost:8081</span>
    </div>

    <!-- Stats Bar -->
    <div class="stats-bar">
        <div class="stat-card">
            <div class="label">River Stations</div>
            <div class="value" id="statRiver">{len(store.river_stations)}</div>
        </div>
        <div class="stat-card">
            <div class="label">Dams</div>
            <div class="value" id="statDam">{len(store.dam_levels)}</div>
        </div>
        <div class="stat-card">
            <div class="label">Advisories</div>
            <div class="value" id="statAdvisory">{len(store.advisories)}</div>
        </div>
        <div class="stat-card">
            <div class="label">Social Posts</div>
            <div class="value" id="statSocial">{len(store.social_posts)}</div>
        </div>
        <div class="stat-card">
            <div class="label">Evac Centers</div>
            <div class="value" id="statEvac">{evac_stat_count}</div>
        </div>
        <div class="stat-card">
            <div class="label">Weather</div>
            <div class="value" style="font-size:1rem">{w_main}</div>
        </div>
    </div>

    <!-- Scenario Bar -->
    <div class="scenario-bar">
        <label>Load Scenario:</label>
        <div class="scenario-btns">
            <button class="scenario-btn" onclick="loadScenario('light')">Light</button>
            <button class="scenario-btn" onclick="loadScenario('medium')">Medium</button>
            <button class="scenario-btn" onclick="loadScenario('heavy')">Heavy</button>
        </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
        <button class="tab active" onclick="switchTab('river')">River Stations</button>
        <button class="tab" onclick="switchTab('dam')">Dam Levels</button>
        <button class="tab" onclick="switchTab('weather')">Weather</button>
        <button class="tab" onclick="switchTab('advisory')">Advisories</button>
        <button class="tab" onclick="switchTab('social')">Social Posts</button>
        <button class="tab" onclick="switchTab('evacuation')">Evacuation</button>
    </div>

    <!-- River Stations Tab -->
    <div class="tab-panel active" id="panel-river">
        <div class="card">
            <div class="card-header">
                <h3>River Monitoring Stations</h3>
            </div>
            <div class="card-body" style="padding:0">
                <table>
                    <thead><tr><th>Station</th><th>Water Level (m)</th><th>Alert (m)</th><th>Alarm (m)</th><th>Critical (m)</th><th>Status</th></tr></thead>
                    <tbody id="riverTableBody">{river_rows if river_rows else '<tr><td colspan="6" class="empty-state">No stations loaded</td></tr>'}</tbody>
                </table>
            </div>
        </div>
        <div class="card">
            <div class="card-header"><h3>Add / Update River Station</h3></div>
            <div class="card-body">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Station Name</label>
                        <input type="text" id="riverName" placeholder="e.g. Sto Nino">
                    </div>
                    <div class="form-group">
                        <label>Water Level (m)</label>
                        <input type="number" step="0.1" id="riverWL" placeholder="e.g. 15.2">
                    </div>
                    <div class="form-group">
                        <label>Alert Level (m)</label>
                        <input type="number" step="0.1" id="riverAL" placeholder="e.g. 15.0">
                    </div>
                    <div class="form-group">
                        <label>Alarm Level (m)</label>
                        <input type="number" step="0.1" id="riverAM" placeholder="e.g. 16.0">
                    </div>
                    <div class="form-group">
                        <label>Critical Level (m)</label>
                        <input type="number" step="0.1" id="riverCL" placeholder="e.g. 17.0">
                    </div>
                </div>
                <div class="form-actions">
                    <button class="btn btn-primary" onclick="submitRiver()">Save Station</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Dam Levels Tab -->
    <div class="tab-panel" id="panel-dam">
        <div class="card">
            <div class="card-header"><h3>Dam Water Levels</h3></div>
            <div class="card-body" style="padding:0">
                <table>
                    <thead><tr><th>Dam</th><th>RWL (m)</th><th>NHWL (m)</th><th>Dev NHWL</th><th>Rule Curve (m)</th><th>Dev RC</th></tr></thead>
                    <tbody id="damTableBody">{dam_rows if dam_rows else '<tr><td colspan="6" class="empty-state">No dams loaded</td></tr>'}</tbody>
                </table>
            </div>
        </div>
        <div class="card">
            <div class="card-header"><h3>Add / Update Dam</h3></div>
            <div class="card-body">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Dam Name</label>
                        <input type="text" id="damName" placeholder="e.g. ANGAT">
                    </div>
                    <div class="form-group">
                        <label>Reservoir Water Level (m)</label>
                        <input type="number" step="0.1" id="damRWL" placeholder="e.g. 212.3">
                    </div>
                    <div class="form-group">
                        <label>NHWL (m)</label>
                        <input type="number" step="0.1" id="damNHWL" placeholder="e.g. 212.0">
                    </div>
                    <div class="form-group">
                        <label>Dev from NHWL (m)</label>
                        <input type="number" step="0.01" id="damDevNHWL" placeholder="e.g. 0.3">
                    </div>
                    <div class="form-group">
                        <label>Rule Curve (m)</label>
                        <input type="number" step="0.1" id="damRC" placeholder="e.g. 209.0">
                    </div>
                    <div class="form-group">
                        <label>Dev from Rule Curve (m)</label>
                        <input type="number" step="0.01" id="damDevRC" placeholder="e.g. 3.3">
                    </div>
                </div>
                <div class="form-actions">
                    <button class="btn btn-primary" onclick="submitDam()">Save Dam</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Weather Tab -->
    <div class="tab-panel" id="panel-weather">
        <div class="card">
            <div class="card-header"><h3>Current Weather</h3></div>
            <div class="card-body">
                <div class="weather-grid">
                    <div class="weather-item">
                        <div class="wi-value">{w_temp}C</div>
                        <div class="wi-label">Temperature</div>
                    </div>
                    <div class="weather-item">
                        <div class="wi-value">{w_humidity}%</div>
                        <div class="wi-label">Humidity</div>
                    </div>
                    <div class="weather-item">
                        <div class="wi-value">{w_pressure}</div>
                        <div class="wi-label">Pressure (hPa)</div>
                    </div>
                    <div class="weather-item">
                        <div class="wi-value">{w_wind}</div>
                        <div class="wi-label">Wind (m/s)</div>
                    </div>
                    <div class="weather-item">
                        <div class="wi-value">{w_rain}</div>
                        <div class="wi-label">Rain 1h (mm)</div>
                    </div>
                    <div class="weather-item">
                        <div class="wi-value">{w_desc}</div>
                        <div class="wi-label">Condition</div>
                    </div>
                </div>
            </div>
        </div>
        <div class="card">
            <div class="card-header"><h3>Update Weather</h3></div>
            <div class="card-body">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Condition</label>
                        <select id="wxMain">
                            <option value="Clear">Clear</option>
                            <option value="Clouds">Clouds</option>
                            <option value="Rain">Rain</option>
                            <option value="Thunderstorm">Thunderstorm</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Description</label>
                        <input type="text" id="wxDesc" placeholder="e.g. heavy intensity rain">
                    </div>
                    <div class="form-group">
                        <label>Temperature (C)</label>
                        <input type="number" step="0.1" id="wxTemp" placeholder="e.g. 26.0">
                    </div>
                    <div class="form-group">
                        <label>Humidity (%)</label>
                        <input type="number" id="wxHumidity" placeholder="e.g. 88">
                    </div>
                    <div class="form-group">
                        <label>Pressure (hPa)</label>
                        <input type="number" id="wxPressure" placeholder="e.g. 1005">
                    </div>
                    <div class="form-group">
                        <label>Wind Speed (m/s)</label>
                        <input type="number" step="0.1" id="wxWind" placeholder="e.g. 5.0">
                    </div>
                    <div class="form-group">
                        <label>Rain 1h (mm)</label>
                        <input type="number" step="0.1" id="wxRain1h" placeholder="e.g. 7.5">
                    </div>
                    <div class="form-group">
                        <label>Rain 3h Forecast (mm)</label>
                        <input type="number" step="0.1" id="wxRain3h" placeholder="e.g. 15.0">
                    </div>
                </div>
                <div class="form-actions">
                    <button class="btn btn-primary" onclick="submitWeather()">Update Weather</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Advisories Tab -->
    <div class="tab-panel" id="panel-advisory">
        <div class="card">
            <div class="card-header"><h3>Active Advisories</h3></div>
            <div class="card-body" style="padding:0">
                <table>
                    <thead><tr><th>ID</th><th>Title</th><th>Text</th><th>Published</th></tr></thead>
                    <tbody id="advisoryTableBody">{advisory_rows if advisory_rows else '<tr><td colspan="4" class="empty-state">No advisories loaded</td></tr>'}</tbody>
                </table>
            </div>
        </div>
        <div class="card">
            <div class="card-header"><h3>Create Advisory</h3></div>
            <div class="card-body">
                <div class="form-grid">
                    <div class="form-group form-row">
                        <label>Title</label>
                        <input type="text" id="advTitle" placeholder="e.g. PAGASA Red Rainfall Warning - Marikina City">
                    </div>
                    <div class="form-group form-row">
                        <label>Advisory Text</label>
                        <textarea id="advText" rows="4" placeholder="Full advisory text..."></textarea>
                    </div>
                </div>
                <div class="form-actions">
                    <button class="btn btn-primary" onclick="submitAdvisory()">Create Advisory</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Evacuation Tab -->
    <div class="tab-panel" id="panel-evacuation">
        <div class="card">
            <div class="card-header">
                <h3>Evacuation Centers <span class="text-muted" style="font-size:0.75rem;margin-left:8px" id="evacSourceLabel">(from main backend :8000)</span></h3>
                <div style="display:flex;gap:8px">
                    <button class="btn btn-sm btn-primary" onclick="loadEvacCenters()">Refresh</button>
                    <button class="btn btn-sm" style="background:var(--danger);color:#fff" onclick="resetAllOccupancy()">Reset All Occupancy</button>
                </div>
            </div>
            <div class="card-body">
                <div id="evacStats" style="display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap"></div>
                <div style="max-height:400px;overflow-y:auto">
                    <table>
                        <thead><tr><th>Name</th><th>Barangay</th><th>Status</th><th>Capacity</th><th>Occupancy</th><th>Available</th><th>Actions</th></tr></thead>
                        <tbody id="evacTableBody"><tr><td colspan="7" class="empty-state">Click Refresh to load from backend</td></tr></tbody>
                    </table>
                </div>
            </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
            <!-- Distress Call Form -->
            <div class="card">
                <div class="card-header"><h3>Send Distress Call</h3></div>
                <div class="card-body">
                    <p class="text-muted" style="font-size:0.8rem;margin-bottom:12px">Triggers a coordinated_evacuation mission via the Orchestrator agent</p>
                    <div class="form-grid" style="grid-template-columns:1fr 1fr">
                        <div class="form-group">
                            <label>Latitude</label>
                            <input type="number" step="0.0001" id="distressLat" placeholder="14.6507" value="14.6507">
                        </div>
                        <div class="form-group">
                            <label>Longitude</label>
                            <input type="number" step="0.0001" id="distressLon" placeholder="121.1029" value="121.1029">
                        </div>
                        <div class="form-group">
                            <label>Urgency</label>
                            <select id="distressUrgency">
                                <option value="critical">Critical</option>
                                <option value="high" selected>High</option>
                                <option value="medium">Medium</option>
                                <option value="low">Low</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Evacuees</label>
                            <input type="number" id="distressEvacuees" value="5" min="1">
                        </div>
                        <div class="form-group form-row">
                            <label>Message</label>
                            <textarea id="distressMsg" rows="2" placeholder="Water rising fast, need evacuation!">Water rising fast in our area, need immediate evacuation assistance!</textarea>
                        </div>
                    </div>
                    <div class="form-actions">
                        <button class="btn btn-primary" onclick="sendDistressCall()" id="distressBtn">Send Distress Call</button>
                    </div>
                </div>
            </div>

            <!-- Update Occupancy Form -->
            <div class="card">
                <div class="card-header"><h3>Update Center Occupancy</h3></div>
                <div class="card-body">
                    <p class="text-muted" style="font-size:0.8rem;margin-bottom:12px">Manually set or add evacuees to a center</p>
                    <div class="form-grid" style="grid-template-columns:1fr 1fr">
                        <div class="form-group form-row">
                            <label>Center Name</label>
                            <select id="occupancyCenter" style="width:100%">
                                <option value="">-- Load centers first --</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Set Occupancy To</label>
                            <input type="number" id="occupancyValue" placeholder="e.g. 50" min="0">
                        </div>
                        <div class="form-group">
                            <label>Or Add Evacuees (+)</label>
                            <input type="number" id="addEvacueesCount" placeholder="e.g. 10" min="1">
                        </div>
                    </div>
                    <div class="form-actions">
                        <button class="btn btn-primary" onclick="setOccupancy()">Set Occupancy</button>
                        <button class="btn btn-success" onclick="addEvacuees()">Add Evacuees</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Mission Tracker -->
        <div class="card">
            <div class="card-header">
                <h3>Orchestrator Missions</h3>
                <button class="btn btn-sm btn-primary" onclick="loadMissions()">Refresh</button>
            </div>
            <div class="card-body" style="padding:0">
                <table>
                    <thead><tr><th>Mission ID</th><th>Type</th><th>State</th><th>Created</th><th>Actions</th></tr></thead>
                    <tbody id="missionTableBody"><tr><td colspan="5" class="empty-state">Click Refresh to load missions</td></tr></tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Social Posts Tab -->
    <div class="tab-panel" id="panel-social">
        <div class="card">
            <div class="card-header"><h3>Social Media Feed</h3></div>
            <div class="card-body" style="padding:0">
                <table>
                    <thead><tr><th>User</th><th>Text</th><th>Image</th><th>Timestamp</th></tr></thead>
                    <tbody id="socialTableBody">{post_rows if post_rows else '<tr><td colspan="4" class="empty-state">No posts loaded</td></tr>'}</tbody>
                </table>
            </div>
        </div>
        <div class="card">
            <div class="card-header"><h3>Create Social Post</h3></div>
            <div class="card-body">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Username</label>
                        <input type="text" id="postUser" placeholder="@marikina_resident" value="mock_user">
                    </div>
                    <div class="form-group">
                        <label>Image (optional)</label>
                        <input type="file" id="postImage" accept="image/*" style="padding:6px">
                    </div>
                    <div class="form-group form-row">
                        <label>Tweet Text</label>
                        <textarea id="postText" rows="3" placeholder="e.g. Waist-deep flooding sa Tumana! #BahaMarikina"></textarea>
                    </div>
                </div>
                <div class="form-actions">
                    <button class="btn btn-primary" onclick="submitPost()">Create Post</button>
                </div>
            </div>
        </div>
    </div>

</div><!-- container -->

<!-- Toast -->
<div class="toast" id="toast"></div>

<script>
// --- Tab switching ---
function switchTab(name) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.getElementById('panel-' + name).classList.add('active');
    // Find the matching tab button
    document.querySelectorAll('.tab').forEach(t => {{
        if (t.textContent.toLowerCase().includes(name.replace('advisory','advisor').replace('social','social'))) t.classList.add('active');
    }});
    event.target.classList.add('active');
}}

// --- Toast ---
function showToast(msg, type) {{
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast show ' + (type || 'success');
    setTimeout(() => t.className = 'toast', 3000);
}}

// --- API helpers ---
async function api(url, body) {{
    try {{
        const resp = await fetch(url, {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(body)
        }});
        const data = await resp.json();
        if (data.status === 'error') throw new Error(data.message);
        return data;
    }} catch(e) {{
        showToast('Error: ' + e.message, 'error');
        throw e;
    }}
}}

// --- Scenario ---
async function loadScenario(name) {{
    const data = await api('/admin/scenario/load', {{scenario: name}});
    showToast('Loaded ' + name + ' scenario (' + data.river_stations + ' stations, ' + data.social_posts + ' posts)');
    document.querySelectorAll('.scenario-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    setTimeout(() => location.reload(), 800);
}}

// --- River ---
async function submitRiver() {{
    const name = document.getElementById('riverName').value.trim();
    if (!name) {{ showToast('Station name is required', 'error'); return; }}
    const body = {{ station_name: name }};
    const wl = document.getElementById('riverWL').value;
    const al = document.getElementById('riverAL').value;
    const am = document.getElementById('riverAM').value;
    const cl = document.getElementById('riverCL').value;
    if (wl) body.water_level_m = parseFloat(wl);
    if (al) body.alert_level_m = parseFloat(al);
    if (am) body.alarm_level_m = parseFloat(am);
    if (cl) body.critical_level_m = parseFloat(cl);
    await api('/admin/river/update', body);
    showToast('Station "' + name + '" saved');
    setTimeout(() => location.reload(), 800);
}}

// --- Dam ---
async function submitDam() {{
    const name = document.getElementById('damName').value.trim();
    if (!name) {{ showToast('Dam name is required', 'error'); return; }}
    const body = {{ dam_name: name }};
    const fields = [['damRWL','latest_rwl'],['damNHWL','nhwl'],['damDevNHWL','dev_nhwl'],['damRC','rule_curve'],['damDevRC','dev_rule_curve']];
    fields.forEach(([id, key]) => {{
        const v = document.getElementById(id).value;
        if (v) body[key] = parseFloat(v);
    }});
    await api('/admin/dam/update', body);
    showToast('Dam "' + name + '" saved');
    setTimeout(() => location.reload(), 800);
}}

// --- Weather ---
async function submitWeather() {{
    const body = {{ weather_main: document.getElementById('wxMain').value }};
    const desc = document.getElementById('wxDesc').value.trim();
    if (desc) body.weather_description = desc;
    const fields = [['wxTemp','temp'],['wxHumidity','humidity'],['wxPressure','pressure'],['wxWind','wind_speed'],['wxRain1h','rain_1h'],['wxRain3h','rain_3h_forecast']];
    fields.forEach(([id, key]) => {{
        const v = document.getElementById(id).value;
        if (v) body[key] = parseFloat(v);
    }});
    await api('/admin/weather/update', body);
    showToast('Weather updated');
    setTimeout(() => location.reload(), 800);
}}

// --- Advisory ---
async function submitAdvisory() {{
    const title = document.getElementById('advTitle').value.trim();
    const text = document.getElementById('advText').value.trim();
    if (!title || !text) {{ showToast('Title and text are required', 'error'); return; }}
    await api('/admin/advisory/create', {{ title, text }});
    showToast('Advisory created');
    setTimeout(() => location.reload(), 800);
}}

// --- Social Post ---
async function submitPost() {{
    const text = document.getElementById('postText').value.trim();
    if (!text) {{ showToast('Tweet text is required', 'error'); return; }}
    const fileInput = document.getElementById('postImage');
    const formData = new FormData();
    formData.append('username', document.getElementById('postUser').value.trim() || 'mock_user');
    formData.append('text', text);
    if (fileInput.files.length > 0) {{
        formData.append('image', fileInput.files[0]);
    }}
    try {{
        const resp = await fetch('/admin/social/post-with-image', {{
            method: 'POST',
            body: formData
        }});
        const data = await resp.json();
        if (data.status === 'error') throw new Error(data.message);
        showToast('Post created');
        setTimeout(() => location.reload(), 800);
    }} catch(e) {{
        showToast('Error: ' + e.message, 'error');
    }}
}}

// --- Evacuation (talks to main backend on :8000) ---
const BACKEND = 'http://localhost:8000';

async function backendApi(path, options) {{
    const resp = await fetch(BACKEND + path, options);
    if (!resp.ok) {{
        const err = await resp.json().catch(() => ({{detail: resp.statusText}}));
        throw new Error(err.detail || resp.statusText);
    }}
    return resp.json();
}}

async function loadEvacCenters() {{
    try {{
        const data = await backendApi('/api/agents/evacuation/centers');
        const centers = data.centers || [];
        const stats = data.statistics || {{}};

        // Update stat card
        document.getElementById('statEvac').textContent = centers.length;

        // Stats row
        document.getElementById('evacStats').innerHTML = `
            <div class="stat-card" style="padding:10px;min-width:100px"><div class="label">Total</div><div class="value" style="font-size:1.1rem">${{stats.total_centers || centers.length}}</div></div>
            <div class="stat-card" style="padding:10px;min-width:100px"><div class="label">Capacity</div><div class="value" style="font-size:1.1rem">${{stats.total_capacity || 0}}</div></div>
            <div class="stat-card" style="padding:10px;min-width:100px"><div class="label">Occupancy</div><div class="value" style="font-size:1.1rem">${{stats.total_occupancy || 0}}</div></div>
            <div class="stat-card" style="padding:10px;min-width:100px"><div class="label">Available Slots</div><div class="value" style="font-size:1.1rem">${{stats.total_available_slots || 0}}</div></div>
        `;

        // Table
        if (centers.length === 0) {{
            document.getElementById('evacTableBody').innerHTML = '<tr><td colspan="7" class="empty-state">No evacuation centers found</td></tr>';
            return;
        }}

        const rows = centers.map(c => {{
            const statusBadge = c.status === 'OFFICIAL'
                ? '<span class="badge badge-normal">OFFICIAL</span>'
                : '<span class="badge" style="background:rgba(99,102,241,0.15);color:var(--info)">POTENTIAL</span>';
            const occ = c.current_occupancy || 0;
            const cap = c.capacity || 0;
            const avail = Math.max(0, cap - occ);
            const occClass = cap > 0 && occ >= cap ? 'text-danger' : occ > cap * 0.8 ? 'text-warning' : '';
            return `<tr>
                <td class="font-medium">${{c.name}}</td>
                <td>${{c.barangay || '-'}}</td>
                <td>${{statusBadge}}</td>
                <td>${{cap}}</td>
                <td class="${{occClass}}">${{occ}}</td>
                <td>${{avail}}</td>
                <td><button class="btn btn-sm btn-primary" onclick="quickAddEvac('${{c.name.replace(/'/g, "\\\\'")}}')">+5</button></td>
            </tr>`;
        }}).join('');
        document.getElementById('evacTableBody').innerHTML = rows;

        // Populate center dropdown
        const sel = document.getElementById('occupancyCenter');
        sel.innerHTML = '<option value="">-- Select Center --</option>' +
            centers.map(c => `<option value="${{c.name}}">${{c.name}} (${{c.barangay || 'N/A'}})</option>`).join('');

        showToast('Loaded ' + centers.length + ' evacuation centers');
    }} catch(e) {{
        showToast('Backend error: ' + e.message, 'error');
    }}
}}

async function quickAddEvac(name) {{
    try {{
        await backendApi('/api/agents/evacuation/centers/add-evacuees', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{ center_name: name, count: 5 }})
        }});
        showToast('Added 5 evacuees to ' + name);
        loadEvacCenters();
    }} catch(e) {{
        showToast('Error: ' + e.message, 'error');
    }}
}}

async function setOccupancy() {{
    const name = document.getElementById('occupancyCenter').value;
    const val = document.getElementById('occupancyValue').value;
    if (!name) {{ showToast('Select a center first', 'error'); return; }}
    if (val === '') {{ showToast('Enter an occupancy value', 'error'); return; }}
    try {{
        await backendApi('/api/agents/evacuation/centers/occupancy', {{
            method: 'PUT',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{ center_name: name, occupancy: parseInt(val) }})
        }});
        showToast('Occupancy set for ' + name);
        loadEvacCenters();
    }} catch(e) {{
        showToast('Error: ' + e.message, 'error');
    }}
}}

async function addEvacuees() {{
    const name = document.getElementById('occupancyCenter').value;
    const count = document.getElementById('addEvacueesCount').value;
    if (!name) {{ showToast('Select a center first', 'error'); return; }}
    if (!count || parseInt(count) < 1) {{ showToast('Enter a valid count', 'error'); return; }}
    try {{
        await backendApi('/api/agents/evacuation/centers/add-evacuees', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{ center_name: name, count: parseInt(count) }})
        }});
        showToast('Added ' + count + ' evacuees to ' + name);
        loadEvacCenters();
    }} catch(e) {{
        showToast('Error: ' + e.message, 'error');
    }}
}}

async function resetAllOccupancy() {{
    if (!confirm('Reset ALL center occupancy to 0?')) return;
    try {{
        await backendApi('/api/agents/evacuation/centers/reset', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}}
        }});
        showToast('All occupancy reset');
        loadEvacCenters();
    }} catch(e) {{
        showToast('Error: ' + e.message, 'error');
    }}
}}

async function sendDistressCall() {{
    const lat = parseFloat(document.getElementById('distressLat').value);
    const lon = parseFloat(document.getElementById('distressLon').value);
    const urgency = document.getElementById('distressUrgency').value;
    const evacuees = parseInt(document.getElementById('distressEvacuees').value) || 5;
    const msg = document.getElementById('distressMsg').value.trim();
    if (!lat || !lon) {{ showToast('Latitude and longitude are required', 'error'); return; }}

    const btn = document.getElementById('distressBtn');
    btn.disabled = true;
    btn.textContent = 'Sending...';
    try {{
        const result = await backendApi('/api/orchestrator/mission', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                mission_type: 'coordinated_evacuation',
                params: {{
                    user_location: [lat, lon],
                    urgency: urgency,
                    evacuees: evacuees,
                    message: msg || 'Emergency distress call from mock server'
                }}
            }})
        }});
        showToast('Distress call sent! Mission: ' + (result.mission_id || 'created'));
        setTimeout(loadMissions, 1500);
    }} catch(e) {{
        showToast('Error: ' + e.message, 'error');
    }} finally {{
        btn.disabled = false;
        btn.textContent = 'Send Distress Call';
    }}
}}

async function loadMissions() {{
    try {{
        const data = await backendApi('/api/orchestrator/missions');
        const all = [...(data.active || []), ...(data.completed || [])];
        if (all.length === 0) {{
            document.getElementById('missionTableBody').innerHTML = '<tr><td colspan="5" class="empty-state">No missions</td></tr>';
            return;
        }}
        const rows = all.map(m => {{
            const state = m.state || 'unknown';
            let badgeClass = 'badge-normal';
            if (state.toLowerCase().includes('completed')) badgeClass = 'badge-normal';
            else if (state.toLowerCase().includes('fail') || state.toLowerCase().includes('timeout')) badgeClass = 'badge-critical';
            else badgeClass = 'badge-alert';
            const created = m.created_at ? new Date(m.created_at).toLocaleTimeString() : '-';
            return `<tr>
                <td class="font-medium" style="font-size:0.75rem">${{m.mission_id || '-'}}</td>
                <td>${{m.mission_type || '-'}}</td>
                <td><span class="badge ${{badgeClass}}">${{state}}</span></td>
                <td class="text-muted">${{created}}</td>
                <td><button class="btn btn-sm" style="background:var(--surface2)" onclick="viewMission('${{m.mission_id}}')">View</button></td>
            </tr>`;
        }}).join('');
        document.getElementById('missionTableBody').innerHTML = rows;
    }} catch(e) {{
        showToast('Backend error: ' + e.message, 'error');
    }}
}}

async function viewMission(id) {{
    try {{
        const data = await backendApi('/api/orchestrator/mission/' + id);
        alert(JSON.stringify(data, null, 2));
    }} catch(e) {{
        showToast('Error: ' + e.message, 'error');
    }}
}}
</script>
</body>
</html>"""
    return HTMLResponse(content=html)


# --- API Endpoints ---

@router.post("/admin/scenario/load")
async def load_scenario_endpoint(req: ScenarioRequest):
    """Load a preset scenario (light/medium/heavy)."""
    return load_scenario(req.scenario)


@router.post("/admin/social/post")
async def create_social_post(req: SocialPostRequest):
    """Create a new social post."""
    store = get_data_store()
    return store.add_social_post(req.model_dump())


@router.post("/admin/social/post-with-image")
async def create_social_post_with_image(
    username: str = Form("mock_user"),
    text: str = Form(...),
    image: Optional[UploadFile] = File(None),
):
    """Create a social post with an optional image file upload."""
    image_path = None
    if image and image.filename:
        ext = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        save_path = UPLOADS_DIR / filename
        content = await image.read()
        save_path.write_bytes(content)
        image_path = f"/uploads/{filename}"

    store = get_data_store()
    return store.add_social_post({
        "username": username,
        "text": text,
        "image_path": image_path,
    })


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
            "weather": [{"main": req.weather_main, "description": req.weather_description or req.weather_main.lower()}],
            "main": {"temp": 30.0, "humidity": 70, "pressure": 1013},
            "wind": {"speed": 3.0},
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
    if req.wind_speed is not None:
        weather_update["current"].setdefault("wind", {})["speed"] = req.wind_speed
    if req.rain_1h is not None:
        weather_update["current"]["rain"] = {"1h": req.rain_1h}
    weather_update["current"]["weather"] = [{
        "main": req.weather_main,
        "description": req.weather_description or req.weather_main.lower(),
    }]

    store.update_weather(weather_update)
    return {"status": "success"}


@router.post("/admin/advisory/create")
async def create_advisory(req: AdvisoryCreateRequest):
    """Create a new advisory."""
    store = get_data_store()
    return store.add_advisory(req.model_dump())
