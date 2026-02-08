# GeoTIFF Toggle Feature Implementation Summary

## Date: 2025-01-12

## Overview

Successfully implemented enable/disable control for GeoTIFF flood simulation in the HazardAgent, allowing runtime toggling of spatial flood data integration in risk calculations.

---

## Changes Made

### 1. HazardAgent Modifications (`app/agents/hazard_agent.py`)

#### Added Constructor Parameter
```python
def __init__(
    self,
    agent_id: str,
    environment: "DynamicGraphEnvironment",
    enable_geotiff: bool = True  # NEW PARAMETER
) -> None:
```

**Backward compatible**: Default is `True`, existing code continues to work.

#### Added Instance Attributes
- `self.geotiff_enabled`: Boolean flag to track enable/disable state
- Conditional initialization of `self.geotiff_service` based on flag

#### Added Public Methods
- **`enable_geotiff()`**: Enable GeoTIFF flood simulation
  - Initializes service if not already available
  - Sets `geotiff_enabled = True`

- **`disable_geotiff()`**: Disable GeoTIFF flood simulation
  - Sets `geotiff_enabled = False`
  - Service remains initialized but not queried

- **`is_geotiff_enabled()`**: Check current status
  - Returns boolean enable/disable state

#### Modified Existing Methods
- **`get_edge_flood_depths()`**: Added early return if disabled
  ```python
  if not self.geotiff_enabled:
      logger.info("GeoTIFF integration disabled - skipping flood depth queries")
      return {}
  ```

---

### 2. API Endpoints (`app/main.py`)

Added 4 new admin endpoints for GeoTIFF control:

#### POST `/api/admin/geotiff/enable`
Enable GeoTIFF simulation

**Response**:
```json
{
  "status": "success",
  "message": "GeoTIFF flood simulation enabled",
  "geotiff_enabled": true,
  "return_period": "rr01",
  "time_step": 1
}
```

#### POST `/api/admin/geotiff/disable`
Disable GeoTIFF simulation

**Response**:
```json
{
  "status": "success",
  "message": "GeoTIFF flood simulation disabled",
  "geotiff_enabled": false,
  "note": "Risk calculation now uses only FloodAgent and ScoutAgent data"
}
```

#### GET `/api/admin/geotiff/status`
Get current configuration

**Response**:
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

#### POST `/api/admin/geotiff/set-scenario`
Change flood scenario

**Parameters**: `return_period` (rr01-rr04), `time_step` (1-18)

**Response**:
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

---

### 3. Documentation

Created comprehensive documentation:

#### **GEOTIFF_CONTROL_API.md** (Complete API Reference)
- All endpoint documentation with examples
- curl and Python usage examples
- Use case scenarios
- Risk calculation behavior
- Error handling

#### **GEOTIFF_TOGGLE_FEATURE_SUMMARY.md** (This Document)
- Implementation summary
- Test results
- File changes

#### **GEOTIFF_FUSION_BEHAVIOR.md** (Updated)
- Updated to reflect new toggle feature
- Explains default behavior

---

### 4. Test Script

Created **`scripts/test_geotiff_toggle.py`**:

**Tests**:
1. ✅ Default initialization (GeoTIFF enabled)
2. ✅ Initialize with GeoTIFF disabled
3. ✅ Runtime enable/disable
4. ✅ Query behavior when disabled
5. ✅ Scenario changes
6. ✅ Late enable (service initialization)

**Test Results**: ALL TESTS PASSED

```
======================================================================
ALL TESTS PASSED [OK]
======================================================================

Feature Summary:
  [OK] Default initialization: GeoTIFF enabled
  [OK] Optional initialization: GeoTIFF disabled
  [OK] Runtime enable/disable: Working
  [OK] Query behavior: Correct (empty when disabled)
  [OK] Scenario changes: Working
  [OK] Late enable: Service initialized correctly
```

---

## Technical Details

### Risk Calculation Behavior

#### With GeoTIFF Enabled (Default)
```python
# Risk from GeoTIFF spatial data (50% weight)
geotiff_risk = flood_depth_to_risk(depth) * 0.5

# Risk from FloodAgent environmental data (50% weight)
environmental_risk = flood_agent_risk * 0.5

# Total risk
total_risk = geotiff_risk + environmental_risk
```

**Example**: 0.8m flood depth + 0.6 environmental risk = 0.65 total risk

#### With GeoTIFF Disabled
```python
# No GeoTIFF contribution
geotiff_risk = 0

# Only FloodAgent environmental data (50% weight)
environmental_risk = flood_agent_risk * 0.5

# Total risk
total_risk = environmental_risk
```

**Example**: 0.6 environmental risk = 0.30 total risk

**Impact**: Disabling GeoTIFF significantly reduces risk scores in areas with high spatial flooding.

---

### Query Performance

**With GeoTIFF Enabled**:
- Queries all 72 TIFF files
- Returns edges with flood depth > 0.01m
- Example: 3,236 edges flooded (default rr01, step 1)

**With GeoTIFF Disabled**:
- Skips TIFF queries entirely
- Returns empty dict immediately
- ~0ms overhead

---

## Code Changes Summary

### Files Modified
- **app/agents/hazard_agent.py**
  - Lines 67-121: Updated `__init__()` with enable/disable logic
  - Lines 366-369: Added early return in `get_edge_flood_depths()`
  - Lines 440-492: Added `enable_geotiff()`, `disable_geotiff()`, `is_geotiff_enabled()`

- **app/main.py**
  - Lines 677-820: Added 4 new API endpoints for GeoTIFF control

### Files Created
- **docs/GEOTIFF_CONTROL_API.md** - Complete API documentation
- **docs/GEOTIFF_TOGGLE_FEATURE_SUMMARY.md** - This summary
- **scripts/test_geotiff_toggle.py** - Comprehensive test suite

### Backward Compatibility
✅ **100% Backward Compatible**
- Default parameter: `enable_geotiff=True`
- All existing code continues to work without modification
- No breaking changes to API or initialization

---

## Usage Examples

### Programmatic Usage

```python
from app.agents.hazard_agent import HazardAgent
from app.environment.graph_manager import DynamicGraphEnvironment

# Initialize with GeoTIFF enabled (default)
env = DynamicGraphEnvironment()
hazard_agent = HazardAgent("hazard_001", env)

# Disable GeoTIFF
hazard_agent.disable_geotiff()

# Check status
print(f"GeoTIFF enabled: {hazard_agent.is_geotiff_enabled()}")

# Enable GeoTIFF
hazard_agent.enable_geotiff()

# Change scenario
hazard_agent.set_flood_scenario("rr04", 18)
```

### API Usage

```bash
# Check status
curl http://localhost:8000/api/admin/geotiff/status

# Disable GeoTIFF
curl -X POST http://localhost:8000/api/admin/geotiff/disable

# Enable GeoTIFF
curl -X POST http://localhost:8000/api/admin/geotiff/enable

# Set worst-case scenario
curl -X POST "http://localhost:8000/api/admin/geotiff/set-scenario?return_period=rr04&time_step=18"
```

### Python API Client

```python
import requests

BASE_URL = "http://localhost:8000"

# Disable GeoTIFF for baseline test
requests.post(f"{BASE_URL}/api/admin/geotiff/disable")

# Get baseline route
baseline_route = requests.post(
    f"{BASE_URL}/api/route",
    json={"start": [14.6553, 121.0990], "destination": [14.6583, 121.1011]}
).json()

# Enable GeoTIFF and set severe flooding
requests.post(f"{BASE_URL}/api/admin/geotiff/enable")
requests.post(
    f"{BASE_URL}/api/admin/geotiff/set-scenario",
    params={"return_period": "rr04", "time_step": 18}
)

# Get flood-aware route
flood_aware_route = requests.post(
    f"{BASE_URL}/api/route",
    json={"start": [14.6553, 121.0990], "destination": [14.6583, 121.1011]}
).json()

# Compare
print(f"Baseline: {baseline_route['route_info']['distance']}m")
print(f"Flood-aware: {flood_aware_route['route_info']['distance']}m")
```

---

## Benefits

### 1. Testing Flexibility
- Compare baseline (no GeoTIFF) vs flood-aware routing
- Test algorithm under different flood scenarios
- Validate impact of spatial flood data

### 2. Performance Control
- Disable GeoTIFF to reduce query overhead when not needed
- Faster risk calculation in non-flood conditions

### 3. Configuration Flexibility
- Change scenarios dynamically without restart
- Test different return periods (rr01-rr04)
- Test different time steps (1-18 hours)

### 4. Production Control
- Toggle features based on data availability
- Fallback to environmental data only if GeoTIFF service fails
- Runtime configuration for different deployment environments

---

## Logging

### Initialization
```
INFO - hazard_agent_001 initialized with risk weights: {...},
       return_period: rr01, time_step: 1, geotiff_enabled: True
```

### Enable/Disable
```
INFO - hazard_agent_001 GeoTIFF flood simulation ENABLED
INFO - hazard_agent_001 GeoTIFF flood simulation DISABLED
```

### Query Behavior
```
INFO - GeoTIFF integration disabled - skipping flood depth queries
INFO - Querying flood depths for all edges (rp=rr04, ts=18)
INFO - Flood depth query complete: 5432/20124 edges flooded (>0.01m)
```

---

## Future Enhancements

### Potential Additions
1. **Persistence**: Save enable/disable state to config file
2. **WebSocket Broadcasting**: Notify clients when GeoTIFF toggled
3. **Scenario Presets**: Named scenarios ("severe_flooding", "normal", etc.)
4. **Auto-Toggle**: Automatically enable/disable based on conditions
5. **Weight Control**: Runtime adjustment of risk weights

---

## Testing Checklist

- [x] Default initialization (GeoTIFF enabled)
- [x] Initialize with GeoTIFF disabled
- [x] Runtime enable/disable
- [x] Query returns empty dict when disabled
- [x] Scenario changes work correctly
- [x] Late enable initializes service
- [x] API endpoints functional
- [x] Backward compatibility verified
- [x] Logging messages correct
- [x] Documentation complete

---

## Conclusion

Successfully implemented a comprehensive enable/disable feature for GeoTIFF flood simulation with:
- ✅ Clean API design
- ✅ 100% backward compatibility
- ✅ Comprehensive testing
- ✅ Complete documentation
- ✅ Flexible configuration
- ✅ Production-ready

The feature allows users to dynamically control GeoTIFF integration for testing, performance optimization, and flexible deployment scenarios.

---

**Implementation Date**: 2025-01-12
**Status**: ✅ Complete and Tested
**Test Results**: All tests passing
**Documentation**: Complete
