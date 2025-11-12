# HazardAgent Data Flow Analysis

## Quick Answer

**YES**, the HazardAgent **DOES update graph edges** based on data from FloodAgent (and ScoutAgent).

The update happens automatically through this workflow:
1. **FloodAgent** sends flood data to HazardAgent → `process_flood_data()`
2. **HazardAgent** fuses data from multiple sources → `fuse_data()`
3. **HazardAgent** calculates risk scores (GeoTIFF + FloodAgent data) → `calculate_risk_scores()`
4. **HazardAgent** updates graph edges → `update_environment()`

---

## Complete Data Flow

### Step-by-Step Process

```
FloodAgent → HazardAgent → Graph Environment
    |             |              |
    |      1. process_flood_data |
    |      2. fuse_data          |
    |      3. calculate_risk     |
    |      4. update_environment |
    |                            |
    |                    Graph edges updated!
```

### Detailed Workflow

#### 1. FloodAgent Sends Data

**File**: `app/agents/hazard_agent.py`
**Method**: `process_flood_data()` (Lines 152-182)

When FloodAgent collects official flood measurements (PAGASA, OpenWeatherMap), it sends data to HazardAgent:

```python
def process_flood_data(self, flood_data: Dict[str, Any]) -> None:
    """
    Process official flood data from FloodAgent.

    Expected format:
    {
        "location": str,
        "flood_depth": float,  # meters
        "rainfall": float,     # mm
        "river_level": float,  # meters
        "timestamp": datetime
    }
    """
    # Validate data
    if not self._validate_flood_data(flood_data):
        logger.warning(f"Invalid flood data received")
        return

    # Update cache
    location = flood_data.get("location")
    self.flood_data_cache[location] = flood_data

    # Trigger automatic update!
    self.process_and_update()  # ← THIS TRIGGERS THE ENTIRE WORKFLOW
```

**Key Point**: As soon as FloodAgent data is received, `process_and_update()` is automatically called!

---

#### 2. Data Fusion

**Method**: `fuse_data()` (Lines 213-231)

Combines data from multiple sources:

```python
def fuse_data(self) -> Dict[str, Any]:
    """
    Fuse data from multiple sources:
    - FloodAgent (official measurements)
    - ScoutAgent (crowdsourced reports)

    Returns:
    {
        "location_name": {
            "risk_level": float,  # 0-1 scale
            "flood_depth": float,
            "confidence": float,
            "sources": ["flood_agent", "scout_agent"]
        }
    }
    """
```

**What it does**:
- Takes FloodAgent data from cache (`self.flood_data_cache`)
- Takes ScoutAgent data from cache (`self.scout_data_cache`)
- Combines using weighted averaging based on reliability

---

#### 3. Risk Score Calculation

**Method**: `calculate_risk_scores()` (Lines 424-502)

This is the **CRITICAL** method that combines GeoTIFF flood depths with FloodAgent data:

```python
def calculate_risk_scores(self, fused_data: Dict[str, Any]) -> Dict[Tuple, float]:
    """
    Calculate risk scores combining:
    1. GeoTIFF flood depth data (spatial extents)
    2. Fused data from FloodAgent and ScoutAgent (river levels, weather)

    Returns:
        {(u, v, key): risk_score, ...}
    """
    risk_scores = {}

    # STEP 1: Query GeoTIFF flood depths for all edges
    edge_flood_depths = self.get_edge_flood_depths()

    # STEP 2: Convert flood depths to base risk scores
    for edge_tuple, depth in edge_flood_depths.items():
        if depth <= 0.3:
            risk_from_depth = depth
        elif depth <= 0.6:
            risk_from_depth = 0.3 + (depth - 0.3) * 1.0
        elif depth <= 1.0:
            risk_from_depth = 0.6 + (depth - 0.6) * 0.5
        else:
            risk_from_depth = min(0.8 + (depth - 1.0) * 0.2, 1.0)

        # Apply flood depth weight (50%)
        risk_scores[edge_tuple] = risk_from_depth * 0.5

    # STEP 3: Add FloodAgent environmental risk (weather, river levels)
    for location, data in fused_data.items():
        risk_level = data["risk_level"]  # ← FROM FLOODAGENT!

        # Apply to ALL edges (system-wide conditions)
        for edge_tuple in graph.edges(keys=True):
            current_risk = risk_scores.get(edge_tuple, 0.0)

            # FloodAgent contributes 50% (crowdsourced 30% + historical 20%)
            environmental_factor = risk_level * 0.5

            # Combine risks
            combined_risk = max(current_risk, current_risk + environmental_factor)
            risk_scores[edge_tuple] = min(combined_risk, 1.0)

    return risk_scores
```

**Risk Composition**:
- **50%**: GeoTIFF flood depths (spatial flooding)
- **30%**: Crowdsourced data (ScoutAgent)
- **20%**: Historical flood data
- **FloodAgent**: Contributes to environmental factor affecting all edges

---

#### 4. Graph Update

**Method**: `update_environment()` (Lines 504-523)

Finally, the calculated risk scores are written to the graph edges:

```python
def update_environment(self, risk_scores: Dict[Tuple, float]) -> None:
    """
    Update the Dynamic Graph Environment with calculated risk scores.
    """
    for (u, v, key), risk in risk_scores.items():
        try:
            # THIS UPDATES THE GRAPH!
            self.environment.update_edge_risk(u, v, key, risk)
        except Exception as e:
            logger.error(f"Failed to update edge ({u}, {v}, {key}): {e}")

    logger.info(f"Updated {len(risk_scores)} edges in the environment")
```

This calls `DynamicGraphEnvironment.update_edge_risk()` which sets the `risk_score` attribute on each edge.

---

## Automatic Trigger Chain

When FloodAgent sends data, this happens **automatically**:

```python
# In HazardAgent.process_flood_data() (Line 182)
self.process_and_update()

# Which calls (Lines 128-144):
def process_and_update(self) -> Dict[str, Any]:
    fused_data = self.fuse_data()              # Combine all sources
    risk_scores = self.calculate_risk_scores(fused_data)  # Calculate risks
    self.update_environment(risk_scores)        # Update graph!

    return {
        "locations_processed": len(fused_data),
        "edges_updated": len(risk_scores),
        "timestamp": datetime.now()
    }
```

**Result**: Graph edges are automatically updated every time FloodAgent sends new data!

---

## How FloodAgent Data Affects Risk Scores

### FloodAgent Contribution

FloodAgent data affects risk scores through the **environmental factor**:

**Code** (Lines 470-486):
```python
# Get risk_level from fused FloodAgent data
risk_level = fused_data[location]["risk_level"]

# Calculate environmental factor (50% weight)
environmental_factor = risk_level * (
    self.risk_weights["crowdsourced"] +    # 0.3
    self.risk_weights["historical"]        # 0.2
)  # = risk_level * 0.5

# Add to existing GeoTIFF-based risk
combined_risk = current_risk + environmental_factor
```

### Example Calculation

**Scenario**: Heavy rain + rising river levels

**FloodAgent sends**:
```python
{
    "location": "Marikina",
    "rainfall": 150,        # mm (heavy rain)
    "river_level": 15.5,    # meters (critical)
    "flood_depth": 1.2,     # meters (official measurement)
    "timestamp": now
}
```

**After fusion**, risk_level might be **0.8** (high environmental risk)

**For an edge with GeoTIFF depth 0.5m**:
```python
# Base risk from GeoTIFF
depth = 0.5m
risk_from_depth = 0.3 + (0.5 - 0.3) * 1.0 = 0.5
base_risk = 0.5 * 0.5 (weight) = 0.25

# Environmental risk from FloodAgent
environmental_factor = 0.8 * 0.5 = 0.4

# Combined risk
final_risk = 0.25 + 0.4 = 0.65  # HIGH RISK!
```

**Impact**: FloodAgent data elevated risk from 0.25 → 0.65 due to severe weather conditions!

---

## Risk Weight Distribution

The HazardAgent uses these weights for risk calculation:

```python
self.risk_weights = {
    "flood_depth": 0.5,    # 50% - GeoTIFF spatial data
    "crowdsourced": 0.3,   # 30% - ScoutAgent reports
    "historical": 0.2      # 20% - Historical patterns
}
```

**FloodAgent's Influence**:
- **Direct**: Provides river_level and rainfall to fused_data
- **Indirect**: Affects environmental_factor calculation (30% + 20% = 50% of total)
- **System-wide**: FloodAgent data impacts ALL edges globally (weather affects entire area)

---

## When Graph Updates Occur

### Trigger Points

1. **When FloodAgent sends data**:
   ```python
   hazard_agent.process_flood_data(flood_data)
   # → Automatically triggers process_and_update()
   # → Graph updated immediately
   ```

2. **When ScoutAgent sends reports**:
   ```python
   hazard_agent.process_scout_data(scout_reports)
   # → Data cached but doesn't auto-trigger update
   # → Update happens when FloodAgent sends next data
   ```

3. **Manual trigger**:
   ```python
   hazard_agent.process_and_update()
   # → Can be called manually to force update
   ```

4. **Scheduled updates** (from FloodDataScheduler):
   ```python
   # Every 5 minutes
   flood_data = flood_agent.collect_official_data()
   hazard_agent.process_flood_data(flood_data)
   # → Graph updated every 5 minutes!
   ```

---

## Data Validation

Before updating, HazardAgent validates FloodAgent data:

**Method**: `_validate_flood_data()` (Lines 525-544)

```python
def _validate_flood_data(self, flood_data: Dict[str, Any]) -> bool:
    # Required fields
    required_fields = ["location", "flood_depth", "timestamp"]
    for field in required_fields:
        if field not in flood_data:
            return False  # REJECT!

    # Validate ranges
    if not 0 <= flood_data.get("flood_depth", -1) <= 10:
        return False  # REJECT! (unrealistic depth)

    return True  # ACCEPT
```

**Invalid data is rejected** and graph is NOT updated.

---

## Summary: Complete Answer

### Question: Does HazardAgent update edges based on FloodAgent data?

**Answer: YES, absolutely!**

### The Process:

1. ✓ **FloodAgent collects** official flood data (PAGASA, OpenWeatherMap)
2. ✓ **FloodAgent sends** data to HazardAgent via `process_flood_data()`
3. ✓ **HazardAgent validates** the data
4. ✓ **HazardAgent fuses** FloodAgent + ScoutAgent data
5. ✓ **HazardAgent calculates** risk scores (GeoTIFF 50% + Environmental 50%)
6. ✓ **HazardAgent updates** ALL graph edges with new risk scores
7. ✓ **RoutingAgent** uses updated risk scores for pathfinding

### FloodAgent's Impact:

**Direct contributions**:
- River level measurements
- Rainfall data
- Official flood depth readings
- Timestamp for data freshness

**Indirect contributions**:
- Environmental risk factor (affects all edges)
- System-wide condition modifier
- Combines with GeoTIFF spatial data

**Weight**: FloodAgent data contributes to 50% of environmental risk factor (via crowdsourced 30% + historical 20% weights)

### Update Frequency:

- **Automatic**: Every time FloodAgent sends new data
- **Scheduled**: Every 5 minutes (via FloodDataScheduler)
- **Manual**: Can be triggered via API endpoint

### Code References:

| Method | File | Lines | Purpose |
|--------|------|-------|---------|
| `process_flood_data()` | hazard_agent.py | 152-182 | Receive FloodAgent data |
| `fuse_data()` | hazard_agent.py | 213-231 | Combine all sources |
| `calculate_risk_scores()` | hazard_agent.py | 424-502 | Calculate edge risks |
| `update_environment()` | hazard_agent.py | 504-523 | Update graph edges |
| `process_and_update()` | hazard_agent.py | 128-144 | Orchestrate workflow |

---

**Conclusion**: The HazardAgent acts as a **central data fusion hub** that automatically processes FloodAgent data and updates the graph environment. This ensures routing decisions always reflect the latest flood conditions from official sources!

---

**Document Created**: 2025-01-12
**Status**: ✓ Complete analysis of HazardAgent data flow
**Related Docs**:
- `GEOTIFF_INTEGRATION_SUMMARY.md` - GeoTIFF data usage
- `RISK_THRESHOLD_ANALYSIS.md` - How risk scores affect routing
- `GEOTIFF_AUTO_LOADING_ANALYSIS.md` - When data loads to graph
