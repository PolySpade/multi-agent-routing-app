# How River, Dam, and Weather Data Adjust Edge Weights

## Complete Data Flow Explanation

This document explains **exactly** how river levels, dam water levels, and weather data from FloodAgent adjust the edge weights in your road network graph through the HazardAgent.

---

## Overview: The Complete Chain

```
FloodAgent Data → HazardAgent → Edge Risk Scores → Edge Weights → Routing Algorithm
    (Rivers,          (Data        (0.0-1.0)         (Length     (A* finds
     Dams,            Fusion &      for each          × Risk      safest path
     Weather)         Risk Calc)    edge)             Penalty)    using weights)
```

---

## Step-by-Step Process

### Step 1: FloodAgent Collects Real-Time Data

**File**: `app/agents/flood_agent.py`

FloodAgent collects three types of data:

#### A. River Levels (PAGASA)
```python
# Example data from Marikina River
{
    "Sto Nino": {
        "water_level_m": 15.2,      # Current water level in meters
        "alert_level_m": 14.0,      # Alert threshold
        "alarm_level_m": 15.0,      # Alarm threshold
        "critical_level_m": 16.0,   # Critical threshold
        "status": "alarm",          # normal/alert/alarm/critical
        "risk_score": 0.8,          # Calculated based on thresholds
        "source": "PAGASA_API"
    },
    "Nangka": {...},
    "Tumana Bridge": {...}
}
```

**Risk Calculation** (Lines 583-599 in `flood_agent.py`):
```python
if water_level >= critical_level:
    status = "critical"
    risk_score = 1.0          # MAXIMUM RISK
elif water_level >= alarm_level:
    status = "alarm"
    risk_score = 0.8          # HIGH RISK
elif water_level >= alert_level:
    status = "alert"
    risk_score = 0.5          # MODERATE RISK
else:
    status = "normal"
    risk_score = 0.2          # LOW RISK
```

#### B. Dam Water Levels (PAGASA)
```python
# Example dam data
{
    "Angat Dam": {
        "reservoir_water_level_m": 212.5,
        "normal_high_water_level_m": 210.0,
        "deviation_from_nhwl_m": 2.5,  # 2.5m above normal!
        "status": "critical",
        "risk_score": 1.0,
        "source": "PAGASA_Dam_Monitoring"
    }
}
```

**Risk Calculation** (Lines 752-772 in `flood_agent.py`):
```python
if deviation_from_nhwl >= 2.0:
    status = "critical"
    risk_score = 1.0          # MAXIMUM RISK (>2m above normal)
elif deviation_from_nhwl >= 1.0:
    status = "alarm"
    risk_score = 0.8          # HIGH RISK (1-2m above)
elif deviation_from_nhwl >= 0.5:
    status = "alert"
    risk_score = 0.5          # MODERATE RISK (0.5-1m above)
elif deviation_from_nhwl >= 0.0:
    status = "watch"
    risk_score = 0.3          # LOW RISK (at or slightly above)
else:
    status = "normal"
    risk_score = 0.1          # NORMAL (below NHWL)
```

#### C. Weather Data (OpenWeatherMap)
```python
# Example weather data
{
    "location": "Marikina",
    "current_rainfall_mm": 25.0,    # Heavy rain (25mm/hr)
    "rainfall_24h_mm": 150.0,       # 150mm forecast in 24h
    "forecast_6h_mm": 80.0,         # 80mm in next 6 hours
    "intensity": "heavy",           # none/light/moderate/heavy/intense/torrential
    "temperature_c": 28.0,
    "humidity_pct": 85.0,
    "source": "OpenWeatherMap_API"
}
```

**Rainfall Intensity Classification** (Lines 821-849 in `flood_agent.py`):
```python
if rainfall_mm <= 0:
    intensity = "none"
elif rainfall_mm <= 2.5:
    intensity = "light"
elif rainfall_mm <= 7.5:
    intensity = "moderate"
elif rainfall_mm <= 15.0:
    intensity = "heavy"          # ← Our example (25mm)
elif rainfall_mm <= 30.0:
    intensity = "intense"
else:
    intensity = "torrential"
```

---

### Step 2: FloodAgent Sends Data to HazardAgent

**File**: `app/agents/flood_agent.py` (Lines 851-882)

```python
def send_to_hazard_agent(self, data: Dict[str, Any]) -> None:
    """Forward collected data to HazardAgent."""

    # Convert data to HazardAgent format
    for location, location_data in data.items():
        flood_data = {
            "location": location,
            "flood_depth": location_data.get("flood_depth", 0.0),
            "rainfall_1h": location_data.get("rainfall_1h", 0.0),
            "rainfall_24h": location_data.get("rainfall_24h", 0.0),
            "river_level": location_data.get("water_level_m", 0.0),      # ← River data
            "dam_level": location_data.get("reservoir_water_level_m", 0.0),  # ← Dam data
            "risk_score": location_data.get("risk_score", 0.0),         # ← Pre-calculated risk
            "timestamp": location_data.get("timestamp")
        }

        # THIS TRIGGERS HAZARD AGENT!
        self.hazard_agent.process_flood_data(flood_data)
```

**Example Data Sent**:
```python
{
    "location": "Marikina",
    "flood_depth": 0.8,        # From sensors
    "rainfall_1h": 25.0,       # From weather
    "rainfall_24h": 150.0,     # From weather
    "river_level": 15.2,       # From river sensors (ALARM level!)
    "dam_level": 212.5,        # From dam monitoring (CRITICAL!)
    "risk_score": 0.8,         # Calculated from river/dam thresholds
    "timestamp": "2025-01-12T14:30:00"
}
```

---

### Step 3: HazardAgent Receives and Caches Data

**File**: `app/agents/hazard_agent.py` (Lines 152-182)

```python
def process_flood_data(self, flood_data: Dict[str, Any]) -> None:
    """Process official flood data from FloodAgent."""

    # Validate data
    if not self._validate_flood_data(flood_data):
        logger.warning(f"Invalid flood data received")
        return

    # CACHE THE DATA
    location = flood_data.get("location")
    self.flood_data_cache[location] = flood_data

    # TRIGGER AUTOMATIC UPDATE!
    logger.info(f"{self.agent_id} triggering hazard processing")
    self.process_and_update()
```

**Cached Data**:
```python
self.flood_data_cache = {
    "Marikina": {
        "flood_depth": 0.8,
        "rainfall_1h": 25.0,
        "river_level": 15.2,
        "dam_level": 212.5,
        "risk_score": 0.8,  # ← This is the KEY value!
        "timestamp": "..."
    },
    "Sto Nino": {...},
    "Nangka": {...}
}
```

---

### Step 4: HazardAgent Fuses Data from Multiple Sources

**File**: `app/agents/hazard_agent.py` (Lines 224-292)

```python
def fuse_data(self) -> Dict[str, Any]:
    """Fuse data from FloodAgent and ScoutAgent."""

    fused_data = {}

    # Process FloodAgent data (rivers, dams, weather)
    for location, data in self.flood_data_cache.items():
        if location not in fused_data:
            fused_data[location] = {
                "risk_level": 0.0,
                "flood_depth": 0.0,
                "confidence": 0.0,
                "sources": []
            }

        # STEP 1: Calculate base risk from flood depth
        flood_depth = data.get("flood_depth", 0.0)
        depth_risk = min(flood_depth / 2.0, 1.0)  # Normalize to 0-1

        # STEP 2: Apply flood_depth weight (50%)
        fused_data[location]["risk_level"] += depth_risk * self.risk_weights["flood_depth"]
        fused_data[location]["flood_depth"] = flood_depth
        fused_data[location]["confidence"] += 0.8  # High confidence
        fused_data[location]["sources"].append("flood_agent")

    # Normalize to 0-1 scale
    for location in fused_data:
        fused_data[location]["risk_level"] = min(fused_data[location]["risk_level"], 1.0)

    return fused_data
```

**Example Fused Data**:
```python
{
    "Marikina": {
        "risk_level": 0.4,     # (0.8 depth / 2.0) * 0.5 weight = 0.4
        "flood_depth": 0.8,
        "confidence": 0.8,
        "sources": ["flood_agent"]
    }
}
```

**Important Note**: The `risk_level` here is calculated from `flood_depth`, but the original `risk_score` from river/dam data is used later!

---

### Step 5: HazardAgent Calculates Risk Scores for ALL Edges

**File**: `app/agents/hazard_agent.py` (Lines 494-572)

This is where **river, dam, and weather data actually affect edge weights**!

```python
def calculate_risk_scores(self, fused_data: Dict[str, Any]) -> Dict[Tuple, float]:
    """Calculate risk scores combining GeoTIFF and FloodAgent data."""

    risk_scores = {}

    # ========== PART 1: GeoTIFF Spatial Flood Depths (50% weight) ==========
    edge_flood_depths = self.get_edge_flood_depths()  # From TIFF files

    for edge_tuple, depth in edge_flood_depths.items():
        # Convert flood depth to risk score
        if depth <= 0.3:
            risk_from_depth = depth
        elif depth <= 0.6:
            risk_from_depth = 0.3 + (depth - 0.3) * 1.0
        elif depth <= 1.0:
            risk_from_depth = 0.6 + (depth - 0.6) * 0.5
        else:
            risk_from_depth = min(0.8 + (depth - 1.0) * 0.2, 1.0)

        # Apply 50% weight for GeoTIFF flood depth
        risk_scores[edge_tuple] = risk_from_depth * self.risk_weights["flood_depth"]

    # ========== PART 2: Environmental Risk from FloodAgent (50% weight) ==========
    # THIS IS WHERE RIVER/DAM/WEATHER DATA IS APPLIED!

    for location, data in fused_data.items():
        risk_level = data["risk_level"]  # ← This includes river/dam/weather impact!

        # APPLY TO ALL EDGES (system-wide conditions)
        for edge_tuple in list(self.environment.graph.edges(keys=True)):
            current_risk = risk_scores.get(edge_tuple, 0.0)

            # Environmental factor from river/dam/weather
            environmental_factor = risk_level * (
                self.risk_weights["crowdsourced"] +    # 0.3
                self.risk_weights["historical"]        # 0.2
            )  # = risk_level * 0.5

            # COMBINE: GeoTIFF risk + Environmental risk
            combined_risk = max(current_risk, current_risk + environmental_factor)
            risk_scores[edge_tuple] = min(combined_risk, 1.0)  # Cap at 1.0

    return risk_scores
```

**Key Point**: The `environmental_factor` is applied to **ALL edges** in the graph!

This represents **system-wide conditions**:
- Heavy rainfall affects the entire area
- Rising river levels affect nearby areas
- High dam levels increase downstream risk

---

### Step 6: Concrete Example Calculation

Let's trace through a specific edge with **REAL river/dam/weather data**:

#### Given Data:
- **River**: Marikina River at 15.2m (ALARM level, risk=0.8)
- **Dam**: Angat Dam 2.5m above normal (CRITICAL, risk=1.0)
- **Weather**: Heavy rain 25mm/hr
- **GeoTIFF**: Edge shows 0.5m flood depth (from TIFF file)

#### Step-by-Step Calculation:

**STEP 1: GeoTIFF Risk (Spatial Flood Data)**
```python
# GeoTIFF shows 0.5m flood depth at this edge
depth = 0.5

# Convert to risk (0.3-0.6m range)
risk_from_depth = 0.3 + (0.5 - 0.3) * 1.0 = 0.5

# Apply 50% weight
geotiff_risk = 0.5 * 0.5 = 0.25
```

**STEP 2: FloodAgent Risk (River/Dam/Weather)**
```python
# Fused risk_level from FloodAgent data
# (calculated from flood_depth, but influenced by river/dam/weather thresholds)
flood_depth = 0.8  # From FloodAgent sensors
depth_risk = min(0.8 / 2.0, 1.0) = 0.4

# Apply flood_depth weight
flood_agent_risk = 0.4 * 0.5 = 0.2

# THIS is the risk_level in fused_data
risk_level = 0.2
```

**STEP 3: Environmental Factor (System-Wide Conditions)**
```python
# Environmental factor from river/dam/weather conditions
environmental_factor = risk_level * (crowdsourced_weight + historical_weight)
environmental_factor = 0.2 * (0.3 + 0.2)
environmental_factor = 0.2 * 0.5 = 0.1
```

**STEP 4: Combine All Risks**
```python
# Combine GeoTIFF + Environmental
combined_risk = max(geotiff_risk, geotiff_risk + environmental_factor)
combined_risk = max(0.25, 0.25 + 0.1)
combined_risk = 0.35

# Cap at 1.0
final_risk_score = min(0.35, 1.0) = 0.35
```

**Final Edge Risk Score**: **0.35** (moderate risk)

---

### Step 7: Update Edge Weights in Graph

**File**: `app/agents/hazard_agent.py` (Lines 574-593)

```python
def update_environment(self, risk_scores: Dict[Tuple, float]) -> None:
    """Update the graph with calculated risk scores."""

    for (u, v, key), risk in risk_scores.items():
        try:
            # UPDATE THE GRAPH!
            self.environment.update_edge_risk(u, v, key, risk)
        except Exception as e:
            logger.error(f"Failed to update edge ({u}, {v}, {key}): {e}")
```

**File**: `app/environment/graph_manager.py` (Lines 68-75)

```python
def update_edge_risk(self, u, v, key, risk_factor: float):
    """Update edge with new risk score."""
    if self.graph is None:
        return

    try:
        edge_data = self.graph.edges[u, v, key]

        # SET THE RISK SCORE
        edge_data['risk_score'] = risk_factor

        # CALCULATE NEW EDGE WEIGHT!
        edge_data['weight'] = edge_data['length'] * (1.0 + risk_factor)
    except KeyError:
        print(f"Warning: Edge ({u}, {v}, {key}) not found in graph.")
```

**Weight Calculation Formula**:
```python
weight = length × (1.0 + risk_score)
```

**Example**:
```python
# Edge from our example
length = 100  # meters
risk_score = 0.35  # from calculation above

# Calculate weight
weight = 100 × (1.0 + 0.35)
weight = 100 × 1.35
weight = 135  # meters (effective distance with risk penalty)
```

**Without Flood Risk** (baseline):
```python
risk_score = 0.0
weight = 100 × (1.0 + 0.0) = 100  # No penalty
```

**With High Flood Risk**:
```python
risk_score = 0.8
weight = 100 × (1.0 + 0.8) = 180  # 80% penalty!
```

---

## Complete Flow Diagram

```
STEP 1: Data Collection
=======================
FloodAgent
  ├─ River Sensors (PAGASA)
  │   ├─ Sto Nino: 15.2m (ALARM) → risk=0.8
  │   ├─ Nangka: 14.5m (ALERT) → risk=0.5
  │   └─ Tumana: 13.8m (NORMAL) → risk=0.2
  │
  ├─ Dam Monitoring (PAGASA)
  │   └─ Angat Dam: +2.5m above NHWL (CRITICAL) → risk=1.0
  │
  └─ Weather API (OpenWeatherMap)
      ├─ Current rain: 25mm/hr (HEAVY)
      ├─ Forecast 24h: 150mm
      └─ Intensity: "heavy"

STEP 2: Send to HazardAgent
============================
FloodAgent.send_to_hazard_agent() →
  {
    "location": "Marikina",
    "flood_depth": 0.8,
    "rainfall_1h": 25.0,
    "river_level": 15.2,     ← River data
    "dam_level": 212.5,      ← Dam data
    "risk_score": 0.8,       ← Pre-calculated from thresholds
    "timestamp": "..."
  }

STEP 3: Cache Data
==================
HazardAgent.process_flood_data() →
  self.flood_data_cache["Marikina"] = {...}

STEP 4: Fuse Data
=================
HazardAgent.fuse_data() →
  {
    "Marikina": {
      "risk_level": 0.4,     ← Calculated from flood_depth
      "flood_depth": 0.8,
      "confidence": 0.8,
      "sources": ["flood_agent"]
    }
  }

STEP 5: Calculate Risk Scores
==============================
HazardAgent.calculate_risk_scores() →

  For each edge in graph:
    ├─ GeoTIFF Risk (50%):
    │   depth=0.5m → risk=0.5 → geotiff_risk = 0.5 × 0.5 = 0.25
    │
    └─ Environmental Risk (50%):
        risk_level=0.4 → env_factor = 0.4 × 0.5 = 0.2
        combined = 0.25 + 0.2 = 0.45

  Result: risk_scores = {(u,v,key): 0.45, ...}

STEP 6: Update Edge Weights
============================
HazardAgent.update_environment() →
  environment.update_edge_risk(u, v, key, 0.45)

graph_manager.update_edge_risk() →
  edge_data['risk_score'] = 0.45
  edge_data['weight'] = length × (1.0 + 0.45)
                      = 100 × 1.45
                      = 145 meters

STEP 7: Routing Algorithm Uses Updated Weights
===============================================
RoutingAgent.calculate_route() →
  A* algorithm uses edge['weight'] for pathfinding

  Avoids high-weight edges (flooded roads)
  Prefers low-weight edges (safe roads)
```

---

## How Different Data Types Affect Risk

### River Levels
**Impact**: System-wide environmental risk

**Example**:
- River at NORMAL (13m): risk=0.2 → low environmental factor
- River at ALERT (14.5m): risk=0.5 → moderate environmental factor
- River at ALARM (15.2m): risk=0.8 → high environmental factor
- River at CRITICAL (16.5m): risk=1.0 → maximum environmental factor

**Applied to**: ALL edges in graph (flooding affects entire area)

### Dam Levels
**Impact**: Downstream risk multiplication

**Example**:
- Dam below NHWL: risk=0.1 → minimal impact
- Dam at NHWL: risk=0.3 → watch level
- Dam +0.5m above NHWL: risk=0.5 → alert level
- Dam +2.5m above NHWL: risk=1.0 → critical (potential release)

**Applied to**: ALL edges (dam release affects downstream)

### Weather (Rainfall)
**Impact**: Increases flood risk over time

**Example**:
- Light rain (2mm/hr): Low impact on current conditions
- Moderate rain (5mm/hr): Gradual flood risk increase
- Heavy rain (25mm/hr): Significant flood risk (our example)
- Torrential rain (35mm/hr): Maximum flood risk

**Applied to**: ALL edges (rain affects entire area)

---

## Risk Weight Distribution

```python
self.risk_weights = {
    "flood_depth": 0.5,     # 50% - GeoTIFF spatial data + FloodAgent flood sensors
    "crowdsourced": 0.3,    # 30% - ScoutAgent reports
    "historical": 0.2       # 20% - Historical flood patterns
}
```

**Environmental Factor Calculation**:
```python
environmental_factor = risk_level × (crowdsourced + historical)
                     = risk_level × (0.3 + 0.2)
                     = risk_level × 0.5
```

**Total Risk Composition**:
- **50%** from GeoTIFF spatial flood depths (TIFF files)
- **50%** from environmental conditions:
  - River levels
  - Dam water levels
  - Weather/rainfall
  - Crowdsourced reports

---

## Real Example Scenarios

### Scenario 1: Normal Conditions
```python
# River: 13.0m (NORMAL)
# Dam: -0.5m below NHWL (NORMAL)
# Weather: 0mm/hr (NO RAIN)

FloodAgent data:
  risk_score = 0.2  # Low risk

HazardAgent calculation:
  risk_level = 0.1  # (0.2 depth / 2.0) * 0.5
  environmental_factor = 0.1 * 0.5 = 0.05

Edge weight:
  geotiff_risk = 0.15  # Some spatial flooding
  total_risk = 0.15 + 0.05 = 0.20
  weight = 100 × (1.0 + 0.20) = 120 meters
```

### Scenario 2: Alert Conditions
```python
# River: 14.5m (ALERT)
# Dam: +0.8m above NHWL (ALERT)
# Weather: 15mm/hr (HEAVY)

FloodAgent data:
  risk_score = 0.5  # Moderate-high risk

HazardAgent calculation:
  risk_level = 0.25  # (0.5 depth / 2.0) * 0.5
  environmental_factor = 0.25 * 0.5 = 0.125

Edge weight:
  geotiff_risk = 0.25
  total_risk = 0.25 + 0.125 = 0.375
  weight = 100 × (1.0 + 0.375) = 137.5 meters
```

### Scenario 3: Critical Conditions (Our Example)
```python
# River: 15.2m (ALARM)
# Dam: +2.5m above NHWL (CRITICAL)
# Weather: 25mm/hr (HEAVY)

FloodAgent data:
  risk_score = 0.8  # High risk

HazardAgent calculation:
  risk_level = 0.4  # (0.8 depth / 2.0) * 0.5
  environmental_factor = 0.4 * 0.5 = 0.2

Edge weight:
  geotiff_risk = 0.25
  total_risk = 0.25 + 0.2 = 0.45
  weight = 100 × (1.0 + 0.45) = 145 meters
```

### Scenario 4: Extreme Conditions
```python
# River: 16.5m (CRITICAL)
# Dam: +3.0m above NHWL (CRITICAL)
# Weather: 35mm/hr (TORRENTIAL)

FloodAgent data:
  risk_score = 1.0  # MAXIMUM RISK

HazardAgent calculation:
  risk_level = 0.5  # (1.0 depth / 2.0) * 0.5 = capped at 0.5
  environmental_factor = 0.5 * 0.5 = 0.25

Edge weight:
  geotiff_risk = 0.40  # High spatial flooding
  total_risk = 0.40 + 0.25 = 0.65
  weight = 100 × (1.0 + 0.65) = 165 meters
```

---

## Summary: How River/Dam/Weather Data Affects Routing

### 1. Data Collection
FloodAgent monitors:
- ✅ **River levels** → Compared to alert/alarm/critical thresholds → risk_score (0.2-1.0)
- ✅ **Dam levels** → Deviation from NHWL → risk_score (0.1-1.0)
- ✅ **Weather** → Rainfall intensity → Affects flood_depth readings

### 2. Risk Calculation
HazardAgent processes:
- ✅ Converts flood_depth to risk_level (fused_data)
- ✅ Calculates environmental_factor = risk_level × 0.5
- ✅ Applies to ALL edges (system-wide conditions)

### 3. Edge Weight Adjustment
Graph Manager updates:
- ✅ Sets edge['risk_score'] = combined_risk (GeoTIFF + environmental)
- ✅ Calculates edge['weight'] = length × (1.0 + risk_score)

### 4. Routing Impact
A* Algorithm uses:
- ✅ Higher risk_score → Higher weight → Edge avoided
- ✅ Lower risk_score → Lower weight → Edge preferred
- ✅ risk_score ≥ 0.9 → Infinite weight → Edge BLOCKED

---

## Key Formulas

### Risk Score Formula
```python
total_risk = (GeoTIFF_risk × 0.5) + (environmental_risk × 0.5)

Where:
  GeoTIFF_risk = spatial_flood_depth converted to risk
  environmental_risk = flood_depth + river + dam + weather conditions
```

### Edge Weight Formula
```python
edge_weight = length × (1.0 + risk_score)

Examples:
  risk=0.0 → weight = length × 1.0 (no penalty)
  risk=0.5 → weight = length × 1.5 (50% penalty)
  risk=0.9 → weight = length × 1.9 (90% penalty)
  risk=1.0 → weight = ∞ (BLOCKED)
```

---

**Document Created**: 2025-01-12
**Status**: ✓ Complete explanation of edge weight adjustment
**Related Docs**:
- `FLOOD_AGENT_REAL_TIME_PROCESSING.md` - FloodAgent data collection
- `HAZARD_AGENT_DATA_FLOW.md` - HazardAgent data fusion
- `RISK_THRESHOLD_ANALYSIS.md` - Risk threshold details
