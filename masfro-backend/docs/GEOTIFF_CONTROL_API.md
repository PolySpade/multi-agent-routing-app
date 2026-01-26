# GeoTIFF Flood Simulation Control API

## Overview

The HazardAgent now supports **runtime enable/disable** of GeoTIFF flood simulation through API endpoints and programmatic methods.

This allows you to:
- Toggle GeoTIFF flood simulation on/off without restarting the application
- Compare baseline routing (no GeoTIFF) vs flood-aware routing (with GeoTIFF)
- Test different flood scenarios dynamically
- Control the weight of spatial flood data in risk calculations

---

## Feature Summary

### What Changed

**Before**: GeoTIFF integration was always active (no way to disable)

**Now**: GeoTIFF can be enabled/disabled at any time via:
- **API endpoints**: REST API for remote control
- **Programmatic methods**: Direct Python calls for testing

---

## API Endpoints

### Base URL
```
http://localhost:8000
```

---

### 1. Enable GeoTIFF Simulation

**Endpoint**: `POST /api/admin/geotiff/enable`

**Description**: Enable GeoTIFF flood simulation in risk calculations

**Request**:
```bash
POST http://localhost:8000/api/admin/geotiff/enable
```

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "GeoTIFF flood simulation enabled",
  "geotiff_enabled": true,
  "return_period": "rr01",
  "time_step": 1
}
```

**Example using curl**:
```bash
curl -X POST http://localhost:8000/api/admin/geotiff/enable
```

**Example using Python**:
```python
import requests

response = requests.post("http://localhost:8000/api/admin/geotiff/enable")
print(response.json())
```

---

### 2. Disable GeoTIFF Simulation

**Endpoint**: `POST /api/admin/geotiff/disable`

**Description**: Disable GeoTIFF flood simulation (use only FloodAgent + ScoutAgent)

**Request**:
```bash
POST http://localhost:8000/api/admin/geotiff/disable
```

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "GeoTIFF flood simulation disabled",
  "geotiff_enabled": false,
  "note": "Risk calculation now uses only FloodAgent and ScoutAgent data"
}
```

**Example using curl**:
```bash
curl -X POST http://localhost:8000/api/admin/geotiff/disable
```

**What Happens When Disabled**:
- `get_edge_flood_depths()` returns empty dict
- GeoTIFF contributes 0% to risk scores
- Only FloodAgent (PAGASA + OpenWeatherMap) contributes 50% environmental risk
- ScoutAgent contributes crowdsourced data (30% weight)

---

### 3. Get GeoTIFF Status

**Endpoint**: `GET /api/admin/geotiff/status`

**Description**: Get current GeoTIFF configuration and status

**Request**:
```bash
GET http://localhost:8000/api/admin/geotiff/status
```

**Response** (200 OK):
```json
{
  "status": "success",
  "geotiff_enabled": true,
  "geotiff_service_available": true,
  "current_scenario": {
    "return_period": "rr01",
    "time_step": 1,
    "description": "2-year flood"
  },
  "risk_weights": {
    "flood_depth": 0.5,
    "crowdsourced": 0.3,
    "historical": 0.2
  }
}
```

**Example using curl**:
```bash
curl http://localhost:8000/api/admin/geotiff/status
```

---

### 4. Set Flood Scenario

**Endpoint**: `POST /api/admin/geotiff/set-scenario`

**Description**: Change the GeoTIFF flood scenario (return period + time step)

**Query Parameters**:
- `return_period` (required): One of `rr01`, `rr02`, `rr03`, `rr04`
  - `rr01`: 2-year flood
  - `rr02`: 5-year flood
  - `rr03`: 10-year flood
  - `rr04`: 25-year flood
- `time_step` (required): Integer 1-18 (hours)

**Request**:
```bash
POST http://localhost:8000/api/admin/geotiff/set-scenario?return_period=rr04&time_step=18
```

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Flood scenario updated to rr04 step 18",
  "scenario": {
    "return_period": "rr04",
    "time_step": 18,
    "description": "25-year flood"
  },
  "update_triggered": true,
  "locations_updated": 8
}
```

**Example using curl**:
```bash
curl -X POST "http://localhost:8000/api/admin/geotiff/set-scenario?return_period=rr04&time_step=18"
```

**Example using Python**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/admin/geotiff/set-scenario",
    params={"return_period": "rr04", "time_step": 18}
)
print(response.json())
```

**Error Responses**:

Invalid return period (400 Bad Request):
```json
{
  "detail": "Invalid return_period 'rr05'. Must be one of ['rr01', 'rr02', 'rr03', 'rr04']"
}
```

Invalid time step (400 Bad Request):
```json
{
  "detail": "Invalid time_step 20. Must be between 1 and 18"
}
```

---

## Programmatic Methods

### Python API (Direct Access)

If you have direct access to the `hazard_agent` instance:

```python
from app.agents.hazard_agent import HazardAgent
from app.environment.graph_manager import DynamicGraphEnvironment

# Initialize HazardAgent
env = DynamicGraphEnvironment()
hazard_agent = HazardAgent("hazard_001", env, enable_geotiff=True)

# Enable GeoTIFF
hazard_agent.enable_geotiff()

# Disable GeoTIFF
hazard_agent.disable_geotiff()

# Check status
is_enabled = hazard_agent.is_geotiff_enabled()
print(f"GeoTIFF enabled: {is_enabled}")

# Set scenario
hazard_agent.set_flood_scenario("rr04", 18)

# Check configuration
print(f"Return period: {hazard_agent.return_period}")
print(f"Time step: {hazard_agent.time_step}")
```

---

## Initialization Options

### Enable GeoTIFF by Default (Backward Compatible)

```python
hazard_agent = HazardAgent("hazard_001", environment)
# GeoTIFF is ENABLED by default (enable_geotiff=True)
```

### Disable GeoTIFF at Initialization

```python
hazard_agent = HazardAgent("hazard_001", environment, enable_geotiff=False)
# GeoTIFF is DISABLED from the start
```

---

## Use Cases

### 1. Baseline Comparison Testing

**Scenario**: Compare routes with vs without GeoTIFF flood data

```python
import requests

# Test with GeoTIFF disabled (baseline)
requests.post("http://localhost:8000/api/admin/geotiff/disable")
baseline_route = requests.post(
    "http://localhost:8000/api/route",
    json={
        "start": [14.6553, 121.0990],
        "destination": [14.6583, 121.1011],
        "preference": "safest"
    }
).json()

# Test with GeoTIFF enabled (flood-aware)
requests.post("http://localhost:8000/api/admin/geotiff/enable")
requests.post(
    "http://localhost:8000/api/admin/geotiff/set-scenario",
    params={"return_period": "rr04", "time_step": 18}
)
flood_aware_route = requests.post(
    "http://localhost:8000/api/route",
    json={
        "start": [14.6553, 121.0990],
        "destination": [14.6583, 121.1011],
        "preference": "safest"
    }
).json()

# Compare
print(f"Baseline distance: {baseline_route['route_info']['distance']}m")
print(f"Flood-aware distance: {flood_aware_route['route_info']['distance']}m")
print(f"Detour factor: {flood_aware_route['route_info']['distance'] / baseline_route['route_info']['distance']:.2f}x")
```

---

### 2. Dynamic Scenario Testing

**Scenario**: Test routing under different flood severities

```python
import requests

scenarios = [
    ("rr01", 1, "2-year flood, hour 1"),
    ("rr02", 10, "5-year flood, hour 10"),
    ("rr03", 15, "10-year flood, hour 15"),
    ("rr04", 18, "25-year flood, hour 18 (worst case)")
]

for return_period, time_step, description in scenarios:
    # Set scenario
    requests.post(
        "http://localhost:8000/api/admin/geotiff/set-scenario",
        params={"return_period": return_period, "time_step": time_step}
    )

    # Calculate route
    route = requests.post(
        "http://localhost:8000/api/route",
        json={
            "start": [14.6553, 121.0990],
            "destination": [14.6583, 121.1011],
            "preference": "safest"
        }
    ).json()

    print(f"{description}:")
    print(f"  Distance: {route['route_info']['distance']}m")
    print(f"  Risk: {route['route_info']['risk_level']:.3f}")
    print()
```

---

### 3. Real-Time Simulation Control

**Scenario**: Frontend UI with enable/disable toggle

```javascript
// Frontend JavaScript example

// Toggle GeoTIFF simulation
async function toggleGeoTIFF(enable) {
  const endpoint = enable
    ? '/api/admin/geotiff/enable'
    : '/api/admin/geotiff/disable';

  const response = await fetch(endpoint, { method: 'POST' });
  const data = await response.json();

  console.log(`GeoTIFF ${enable ? 'enabled' : 'disabled'}`);

  // Update UI
  document.getElementById('geotiff-status').textContent =
    data.geotiff_enabled ? 'ON' : 'OFF';
}

// Set flood scenario
async function setFloodScenario(returnPeriod, timeStep) {
  const response = await fetch(
    `/api/admin/geotiff/set-scenario?return_period=${returnPeriod}&time_step=${timeStep}`,
    { method: 'POST' }
  );

  const data = await response.json();
  console.log(`Scenario updated: ${data.scenario.description}`);
}

// Usage
toggleGeoTIFF(true);  // Enable
setFloodScenario('rr04', 18);  // Worst case
```

---

## Risk Calculation Behavior

### With GeoTIFF Enabled (Default)

**Risk Formula**:
```
Total Risk = (GeoTIFF 50%) + (FloodAgent 50%)

Where:
- GeoTIFF: Spatial flood depth from TIFF files
- FloodAgent: Environmental conditions (PAGASA + OpenWeatherMap)
  - Crowdsourced: 30%
  - Historical: 20%
```

**Example**:
```python
# GeoTIFF flood depth at edge: 0.8m
geotiff_risk = 0.7 * 0.5 = 0.35  # 50% weight

# FloodAgent environmental risk: 0.6
environmental_risk = 0.6 * 0.5 = 0.30  # 50% weight

# Total risk
total_risk = 0.35 + 0.30 = 0.65  # High risk!
```

---

### With GeoTIFF Disabled

**Risk Formula**:
```
Total Risk = FloodAgent Environmental Risk (50%)

Where:
- GeoTIFF: 0% (disabled)
- FloodAgent: 50%
  - Crowdsourced: 30%
  - Historical: 20%
```

**Example**:
```python
# GeoTIFF disabled
geotiff_risk = 0  # 0% contribution

# FloodAgent environmental risk: 0.6
environmental_risk = 0.6 * 0.5 = 0.30  # 50% weight

# Total risk
total_risk = 0 + 0.30 = 0.30  # Moderate risk
```

**Impact**: Disabling GeoTIFF significantly reduces risk scores, especially in areas with high spatial flooding but low real-time environmental conditions.

---

## Logging

### Enable GeoTIFF
```
INFO - hazard_agent_001 GeoTIFF flood simulation ENABLED
```

### Disable GeoTIFF
```
INFO - hazard_agent_001 GeoTIFF flood simulation DISABLED
```

### Query Skipped (When Disabled)
```
INFO - GeoTIFF integration disabled - skipping flood depth queries
```

### Scenario Change
```
INFO - hazard_agent_001 flood scenario updated: return_period=rr04, time_step=18
```

---

## Testing Example

### Complete Test Workflow

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# 1. Check initial status
status = requests.get(f"{BASE_URL}/api/admin/geotiff/status").json()
print(f"Initial status: {status}")

# 2. Disable GeoTIFF
requests.post(f"{BASE_URL}/api/admin/geotiff/disable")
print("GeoTIFF disabled")

# 3. Get baseline route (no GeoTIFF)
baseline = requests.post(
    f"{BASE_URL}/api/route",
    json={
        "start": [14.6553, 121.0990],
        "destination": [14.6583, 121.1011],
        "preference": "safest"
    }
).json()
print(f"Baseline route: {baseline['route_info']['distance']}m, risk={baseline['route_info']['risk_level']}")

# 4. Enable GeoTIFF and set worst-case scenario
requests.post(f"{BASE_URL}/api/admin/geotiff/enable")
requests.post(
    f"{BASE_URL}/api/admin/geotiff/set-scenario",
    params={"return_period": "rr04", "time_step": 18}
)
print("GeoTIFF enabled with worst-case scenario (rr04, step 18)")

# 5. Wait for next scheduled update (or trigger manual)
time.sleep(2)
requests.post(f"{BASE_URL}/api/admin/collect-flood-data")

# 6. Get flood-aware route (with GeoTIFF)
flood_aware = requests.post(
    f"{BASE_URL}/api/route",
    json={
        "start": [14.6553, 121.0990],
        "destination": [14.6583, 121.1011],
        "preference": "safest"
    }
).json()
print(f"Flood-aware route: {flood_aware['route_info']['distance']}m, risk={flood_aware['route_info']['risk_level']}")

# 7. Compare
detour_factor = flood_aware['route_info']['distance'] / baseline['route_info']['distance']
print(f"\nComparison:")
print(f"  Distance increase: +{flood_aware['route_info']['distance'] - baseline['route_info']['distance']}m")
print(f"  Detour factor: {detour_factor:.2f}x")
print(f"  Risk increase: +{flood_aware['route_info']['risk_level'] - baseline['route_info']['risk_level']:.3f}")
```

---

## Configuration Summary

### Default Behavior (Backward Compatible)

**On Application Startup**:
```python
# app/main.py
hazard_agent = HazardAgent("hazard_agent_001", environment)
# GeoTIFF is ENABLED by default with:
#   - return_period = "rr01" (2-year flood)
#   - time_step = 1 (hour 1)
```

### Manual Configuration

**At Initialization**:
```python
# Disable from start
hazard_agent = HazardAgent("hazard_001", environment, enable_geotiff=False)
```

**At Runtime (via API)**:
```bash
# Disable
curl -X POST http://localhost:8000/api/admin/geotiff/disable

# Enable
curl -X POST http://localhost:8000/api/admin/geotiff/enable

# Change scenario
curl -X POST "http://localhost:8000/api/admin/geotiff/set-scenario?return_period=rr03&time_step=12"
```

---

## Error Handling

### GeoTIFF Service Not Available

**Scenario**: GeoTIFF files missing or service failed to initialize

**Behavior**:
- `enable_geotiff()` logs error but doesn't raise exception
- `geotiff_enabled` flag remains `False`
- API returns success but notes service unavailable

**Response**:
```json
{
  "status": "success",
  "geotiff_enabled": false,
  "geotiff_service_available": false
}
```

### Invalid Scenario Parameters

**Scenario**: Invalid return period or time step

**Response** (400 Bad Request):
```json
{
  "detail": "Invalid return_period 'rr05'. Must be one of ['rr01', 'rr02', 'rr03', 'rr04']"
}
```

---

## Best Practices

### 1. Always Check Status Before Testing

```python
status = requests.get(f"{BASE_URL}/api/admin/geotiff/status").json()
if not status['geotiff_service_available']:
    print("WARNING: GeoTIFF service not available!")
```

### 2. Trigger Manual Update After Scenario Change

```python
# Change scenario
requests.post(f"{BASE_URL}/api/admin/geotiff/set-scenario",
              params={"return_period": "rr04", "time_step": 18})

# Trigger immediate update (don't wait 5 minutes)
requests.post(f"{BASE_URL}/api/admin/collect-flood-data")
```

### 3. Use Descriptive Scenario Names in Logs

```python
scenarios = {
    ("rr01", 1): "Light flooding (2-year, 1hr)",
    ("rr04", 18): "Severe flooding (25-year, 18hr)"
}

for (rp, ts), description in scenarios.items():
    print(f"Testing: {description}")
    requests.post(f"{BASE_URL}/api/admin/geotiff/set-scenario",
                  params={"return_period": rp, "time_step": ts})
```

---

## Related Documentation

- **GEOTIFF_FUSION_BEHAVIOR.md** - How GeoTIFF integrates with FloodAgent data
- **FLOOD_AGENT_REAL_TIME_PROCESSING.md** - Real-time data collection workflow
- **HAZARD_AGENT_DATA_FLOW.md** - Complete HazardAgent data flow
- **BASELINE_COMPARISON_ANALYSIS.md** - Example comparison test results

---

## Summary

### What You Can Do Now

✅ **Enable/Disable GeoTIFF** at any time via API or code
✅ **Compare baseline vs flood-aware** routing dynamically
✅ **Test different scenarios** (rr01-rr04, steps 1-18) without restart
✅ **Control risk weights** by toggling GeoTIFF contribution
✅ **Check current status** programmatically

### Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/admin/geotiff/enable` | POST | Enable GeoTIFF simulation |
| `/api/admin/geotiff/disable` | POST | Disable GeoTIFF simulation |
| `/api/admin/geotiff/status` | GET | Get current configuration |
| `/api/admin/geotiff/set-scenario` | POST | Change flood scenario |

### Default Behavior

- ✅ GeoTIFF **enabled by default** (backward compatible)
- ✅ Default scenario: **rr01 (2-year flood), step 1**
- ✅ Can be disabled at initialization or runtime
- ✅ No restart required for any changes

---

**Document Created**: 2025-01-12
**Status**: ✓ Complete API documentation
**Feature**: GeoTIFF enable/disable control
