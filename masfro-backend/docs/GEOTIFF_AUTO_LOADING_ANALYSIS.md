# GeoTIFF Auto-Loading Analysis

## Executive Summary

**Answer: NO** - Your backend does NOT automatically load GeoTIFF files to the graph on startup or during routing requests.

GeoTIFF flood data is **loaded on-demand** only when explicitly triggered through specific agent methods or API endpoints.

---

## Current Loading Behavior

### 1. Initialization Phase (Startup)

**File**: `app/main.py` (Lines 386-425)

```python
# Initialize agents
hazard_agent = HazardAgent("hazard_agent_001", environment)
```

**What Happens**:
- ✅ HazardAgent is initialized
- ✅ GeoTIFFService is initialized and ready
- ✅ Default flood scenario is set: `return_period="rr01"`, `time_step=1`
- ❌ **NO GeoTIFF data is loaded**
- ❌ **NO graph edges are updated with flood risk**

**Result**: Graph starts with **all edges at risk_score=0.0** (safe).

---

### 2. Runtime Loading Workflow

GeoTIFF data is loaded **on-demand** through this workflow:

#### Flow Chart

```
User Request / API Call
        ↓
FloodAgent.collect_and_forward_data()
        ↓
HazardAgent.process_flood_data()
        ↓
HazardAgent.process_and_update()
        ↓
HazardAgent.calculate_risk_scores()
        ↓
HazardAgent.get_edge_flood_depths()  ← GeoTIFF LOADED HERE
        ↓
Graph edges updated with risk scores
```

#### Trigger Points

GeoTIFF data is ONLY loaded when one of these is called:

**1. Manual Flood Data Collection** (`main.py:649-675`)
```python
POST /api/admin/collect-flood-data
```
- Triggers: `flood_agent.collect_and_forward_data()`
- Calls: `hazard_agent.process_flood_data()`
- Result: GeoTIFF queried, graph updated

**2. Automated Scheduler** (`main.py:418-423`)
```python
flood_scheduler = FloodDataScheduler(
    flood_agent,
    interval_seconds=300,  # Every 5 minutes
    ws_manager=ws_manager
)
```
- Runs every 5 minutes automatically
- Calls `flood_agent.collect_and_forward_data()`
- Result: GeoTIFF queried, graph updated periodically

**3. Direct HazardAgent Method Call** (For testing/scripts)
```python
hazard_agent.set_flood_scenario(return_period="rr02", time_step=10)
fused_data = {"system_wide": {"risk_level": 0.0, "source": "test"}}
risk_scores = hazard_agent.calculate_risk_scores(fused_data)
hazard_agent.update_environment(risk_scores)
```
- Manually sets flood scenario
- Directly calculates risk scores
- Updates graph

---

### 3. Routing Requests

**File**: `app/main.py` (Lines 499-557)

```python
@app.post("/api/route")
async def get_route(request: RouteRequest):
    route_result = routing_agent.calculate_route(
        start=request.start_location,
        end=request.end_location,
        preferences=request.preferences
    )
```

**What Happens**:
- ✅ Uses **current graph state** (whatever risk scores are already loaded)
- ❌ **Does NOT trigger GeoTIFF loading**
- ❌ **Does NOT update flood risk**

**Result**: Route calculation uses the most recent risk scores (could be outdated or all zeros if never loaded).

---

## Detailed Code Analysis

### HazardAgent Initialization

**File**: `app/agents/hazard_agent.py` (Lines 67-110)

```python
def __init__(self, agent_id: str, environment: "DynamicGraphEnvironment"):
    super().__init__(agent_id, environment)

    # Initialize caches (empty)
    self.flood_data_cache: Dict[str, Any] = {}
    self.scout_data_cache: List[Dict[str, Any]] = []

    # Risk calculation weights
    self.risk_weights = {
        "flood_depth": 0.5,
        "crowdsourced": 0.3,
        "historical": 0.2
    }

    # Initialize GeoTIFF service (but don't load data)
    self.geotiff_service = get_geotiff_service()

    # Default flood scenario (NOT loaded to graph yet)
    self.return_period = "rr01"  # 2-year flood
    self.time_step = 1           # Hour 1
```

**Key Point**: GeoTIFFService is initialized, but **no data is queried or loaded to the graph**.

---

### GeoTIFF Query Mechanism

**File**: `app/agents/hazard_agent.py` (Lines 339-382)

```python
def get_edge_flood_depths(self, return_period: Optional[str] = None,
                          time_step: Optional[int] = None) -> Dict[Tuple, float]:
    """Query flood depths for all edges in the graph."""

    edge_depths = {}
    rp = return_period or self.return_period
    ts = time_step or self.time_step

    # Loop through ALL edges and query GeoTIFF
    for u, v, key in self.environment.graph.edges(keys=True):
        depth = self.get_flood_depth_at_edge(u, v, rp, ts)

        if depth is not None and depth > 0.01:  # 1cm threshold
            edge_depths[(u, v, key)] = depth

    return edge_depths
```

**What This Does**:
1. Iterates through **all 20,124 edges** in the graph
2. For each edge, queries GeoTIFF service for flood depth
3. Returns only flooded edges (depth > 1cm)

**Performance**: ~2-3 seconds to query all edges (per your test results).

---

### Risk Score Calculation

**File**: `app/agents/hazard_agent.py` (Lines 424-502)

```python
def calculate_risk_scores(self, fused_data: Dict[str, Any]) -> Dict[Tuple, float]:
    """Calculate risk scores based on GeoTIFF flood depths."""

    # THIS is where GeoTIFF is queried
    edge_flood_depths = self.get_edge_flood_depths()

    # Convert depths to risk scores
    for edge_tuple, depth in edge_flood_depths.items():
        if depth <= 0.3:
            risk_from_depth = depth
        elif depth <= 0.6:
            risk_from_depth = 0.3 + (depth - 0.3) * 1.0
        elif depth <= 1.0:
            risk_from_depth = 0.6 + (depth - 0.6) * 0.5
        else:
            risk_from_depth = min(0.8 + (depth - 1.0) * 0.2, 1.0)

        risk_scores[edge_tuple] = risk_from_depth * self.risk_weights["flood_depth"]

    return risk_scores
```

**Risk Mapping**:
- 0.0-0.3m depth → 0.0-0.3 risk (low)
- 0.3-0.6m depth → 0.3-0.6 risk (moderate)
- 0.6-1.0m depth → 0.6-0.8 risk (high)
- >1.0m depth → 0.8-1.0 risk (extreme)

---

### Graph Update

**File**: `app/agents/hazard_agent.py` (Lines 504-523)

```python
def update_environment(self, risk_scores: Dict[Tuple, float]) -> None:
    """Update graph edges with calculated risk scores."""

    for (u, v, key), risk in risk_scores.items():
        self.environment.update_edge_risk(u, v, key, risk)

    logger.info(f"Updated {len(risk_scores)} edges in the environment")
```

**File**: `app/environment/graph_manager.py`

```python
def update_edge_risk(self, u, v, key, risk_score: float):
    """Update edge with risk score and recalculate weight."""

    edge_data = self.graph[u][v][key]
    edge_data['risk_score'] = risk_score

    # Recalculate weight: weight = length * (1.0 + risk_score)
    length = edge_data.get('length', 1.0)
    edge_data['weight'] = length * (1.0 + risk_score)
```

**Effect**:
- Updates `risk_score` attribute
- Recalculates `weight` using formula: `weight = length × (1 + risk)`
- Routing algorithm uses these updated weights

---

## Current Gaps

### ❌ Gap 1: No Automatic Loading on Startup

**Problem**:
- Backend starts with all edges at risk=0.0
- First routing request uses empty risk data
- Users get inaccurate routes until first flood data collection

**Impact**:
- Cold start problem: First 5 minutes have no flood risk
- Route calculations may be dangerous if real flooding exists

---

### ❌ Gap 2: No Pre-Loading Before Routing

**Problem**:
- `/api/route` endpoint doesn't check if flood data is loaded
- Doesn't trigger GeoTIFF loading
- Uses stale data if scheduler hasn't run recently

**Impact**:
- Routes calculated with outdated flood conditions
- No guarantee of current flood risk awareness

---

### ❌ Gap 3: Dependency on Scheduler

**Problem**:
- GeoTIFF loading only happens via 5-minute scheduler
- If scheduler fails, no updates occur
- No fallback mechanism

**Impact**:
- System relies entirely on scheduler health
- No manual trigger except admin endpoint

---

## Comparison: What's NOT Happening

### ❌ NOT Implemented: Auto-Load on Startup

What it would look like:
```python
@app.on_event("startup")
async def startup_event():
    # ... existing code ...

    # THIS DOES NOT EXIST
    logger.info("Pre-loading GeoTIFF flood data...")
    hazard_agent.set_flood_scenario("rr02", 10)
    fused_data = {"system_wide": {"risk_level": 0.0, "source": "startup"}}
    risk_scores = hazard_agent.calculate_risk_scores(fused_data)
    hazard_agent.update_environment(risk_scores)
    logger.info(f"Pre-loaded flood data for {len(risk_scores)} edges")
```

**Status**: ❌ Not implemented

---

### ❌ NOT Implemented: Auto-Load Before Routing

What it would look like:
```python
@app.post("/api/route")
async def get_route(request: RouteRequest):
    # THIS DOES NOT EXIST
    if not graph_has_recent_flood_data():
        logger.info("Loading fresh flood data before routing...")
        trigger_flood_data_update()

    # Then calculate route...
    route_result = routing_agent.calculate_route(...)
```

**Status**: ❌ Not implemented

---

### ❌ NOT Implemented: Cached GeoTIFF Pre-Loading

What it would look like:
```python
# Pre-load all 72 TIFF files into memory on startup
# Cache flood depth data for fast queries
# No need to open TIFF files during runtime

# THIS DOES NOT EXIST
geotiff_cache = {}
for rp in ["rr01", "rr02", "rr03", "rr04"]:
    for ts in range(1, 19):
        data, metadata = geotiff_service.load_flood_map(rp, ts)
        geotiff_cache[(rp, ts)] = data
```

**Status**: ❌ Not implemented

---

## Recommendations

### Option 1: Auto-Load Default Scenario on Startup ⭐ RECOMMENDED

**Implementation**:
```python
@app.on_event("startup")
async def startup_event():
    # ... existing startup code ...

    # Pre-load default flood scenario
    logger.info("Pre-loading default flood scenario (RR02, T10)...")
    try:
        hazard_agent.set_flood_scenario("rr02", 10)
        fused_data = {"system_wide": {"risk_level": 0.0, "source": "startup"}}
        risk_scores = hazard_agent.calculate_risk_scores(fused_data)
        hazard_agent.update_environment(risk_scores)
        logger.info(f"✓ Pre-loaded flood data for {len(risk_scores)} edges")
    except Exception as e:
        logger.error(f"Failed to pre-load flood data: {e}")
```

**Benefits**:
- Graph ready with flood risk on first request
- Eliminates cold start problem
- ~5-7 seconds additional startup time

**Drawbacks**:
- Slightly slower startup
- Uses specific scenario (may not be current conditions)

---

### Option 2: Smart Loading Before Routing

**Implementation**:
```python
@app.post("/api/route")
async def get_route(request: RouteRequest):
    # Check if flood data is recent
    last_update = hazard_agent.get_last_update_time()
    if not last_update or (datetime.now() - last_update) > timedelta(minutes=10):
        logger.info("Triggering flood data refresh before routing...")
        await trigger_flood_data_collection()

    # Then calculate route
    route_result = routing_agent.calculate_route(...)
```

**Benefits**:
- Always uses fresh flood data
- No cold start issue
- Automatic refresh if data is stale

**Drawbacks**:
- Adds 5-7 seconds latency to first request
- May slow down user experience

---

### Option 3: Background Pre-Loading with Cache

**Implementation**:
```python
class GeoTIFFCache:
    """Pre-load and cache all TIFF files in memory."""

    def __init__(self):
        self.cache = {}
        self.load_all_tiffs()

    def load_all_tiffs(self):
        """Load all 72 TIFF files into memory."""
        for rp in ["rr01", "rr02", "rr03", "rr04"]:
            for ts in range(1, 19):
                data, meta = geotiff_service.load_flood_map(rp, ts)
                self.cache[(rp, ts)] = data

    def get_depth(self, rp, ts, lon, lat):
        """Query depth from cached data (instant)."""
        data = self.cache.get((rp, ts))
        # ... query from cached array ...
```

**Benefits**:
- Instant GeoTIFF queries (no file I/O)
- All scenarios available immediately
- Fastest runtime performance

**Drawbacks**:
- High memory usage (~500MB-1GB)
- Longer startup time (~2-3 minutes)
- Requires significant RAM

---

### Option 4: Keep Current Behavior (Scheduler Only)

**Current Implementation**: ✅ Already working

**Benefits**:
- Fast startup
- Low memory usage
- Automatic updates every 5 minutes

**Drawbacks**:
- Cold start problem (first 5 minutes)
- Routes may use stale data
- Depends on scheduler reliability

---

## Current API Endpoints for GeoTIFF

### Available Endpoints

**1. Get Available Maps**
```
GET /api/geotiff/available-maps
```
Returns list of 72 TIFF files available.

**2. Get Flood Map Metadata**
```
GET /api/geotiff/flood-map?return_period=rr02&time_step=10
```
Returns metadata, but NOT the actual flood data on the graph.

**3. Query Specific Point**
```
GET /api/geotiff/flood-depth?lon=121.10&lat=14.65&return_period=rr02&time_step=10
```
Returns flood depth at a specific coordinate.

**4. Trigger Manual Collection** ⭐ THIS loads GeoTIFF to graph
```
POST /api/admin/collect-flood-data
```
Manually triggers FloodAgent → HazardAgent → GeoTIFF query → Graph update.

**5. Serve TIFF File**
```
GET /data/timed_floodmaps/rr02/rr02-10.tif
```
Serves raw TIFF file for frontend visualization.

---

## Testing Current Behavior

### Test 1: Verify Cold Start (No Auto-Load)

```bash
# 1. Start backend
uvicorn app.main:app --reload

# 2. Immediately call routing (before scheduler runs)
curl -X POST http://localhost:8000/api/route \
  -H "Content-Type: application/json" \
  -d '{
    "start_location": [14.65, 121.10],
    "end_location": [14.64, 121.11]
  }'

# Expected: Route calculated with risk_score=0.0 on all edges
```

**Result**: Confirms GeoTIFF NOT auto-loaded.

---

### Test 2: Verify Manual Trigger Works

```bash
# Trigger flood data collection
curl -X POST http://localhost:8000/api/admin/collect-flood-data

# Wait for completion (~5-7 seconds)

# Check graph statistics
curl http://localhost:8000/api/statistics
```

**Expected**: Shows updated risk scores on graph edges.

---

### Test 3: Verify Scheduler Updates

```bash
# Wait 5+ minutes after startup
# Scheduler should run automatically

# Check if data was updated
curl http://localhost:8000/api/flood-data/latest
```

**Expected**: Shows recent flood data collection timestamp.

---

## Conclusion

### Summary

**Your backend does NOT automatically load GeoTIFF files to the graph.**

**Current Behavior**:
- ✅ GeoTIFFService initialized on startup (ready to use)
- ❌ No GeoTIFF data loaded to graph on startup
- ❌ Routing requests don't trigger GeoTIFF loading
- ✅ Scheduler loads data every 5 minutes (automatic)
- ✅ Manual trigger via `/api/admin/collect-flood-data` works

**Workflow**:
1. Backend starts → Graph has risk_score=0.0 on all edges
2. Scheduler runs (5 min) → GeoTIFF queried, graph updated
3. Routing request → Uses current graph state (from last scheduler run)
4. Scheduler runs again (5 min) → GeoTIFF re-queried, graph updated

**When GeoTIFF IS Loaded**:
- Every 5 minutes via automatic scheduler
- On demand via `/api/admin/collect-flood-data`
- During test scripts (manual `calculate_risk_scores()` calls)

**When GeoTIFF is NOT Loaded**:
- Application startup
- Routing requests
- Health checks
- Statistics queries

---

## Recommendation

**For production use, implement Option 1 (Auto-Load on Startup)** to ensure the graph always has current flood risk data from the first request.

**Alternative**: Keep current scheduler-based approach but add a "warmup" endpoint that frontend calls on initial page load to trigger first data collection.

---

**Document Created**: 2025-01-12
**Analysis Status**: Complete
**Files Analyzed**:
- `app/main.py` (Lines 1-1329)
- `app/agents/hazard_agent.py` (Lines 1-573)
- `app/environment/graph_manager.py`
- `app/services/geotiff_service.py`

