# FloodAgent Analysis & Next Steps

**Analysis Date:** November 5, 2025
**Current Status:** ~60% Complete (Core framework done, real data integration pending)

---

## 📊 Current Implementation Status

### ✅ What's Already Implemented

#### 1. **Core Architecture (100%)**
- ✅ BaseAgent inheritance with proper structure
- ✅ Agent initialization with configurable parameters
- ✅ HazardAgent reference for data forwarding
- ✅ Logging system integrated

**File:** `masfro-backend/app/agents/flood_agent.py` (555 lines)

#### 2. **Data Collection Framework (90%)**
- ✅ DataCollector service integration (`app/services/data_sources.py`)
- ✅ Simulated data source working (for testing)
- ✅ Multi-source data collection architecture
- ✅ Data processing and formatting pipeline
- ✅ Three main collection methods:
  - `fetch_rainfall_data()` - PAGASA rain gauge data
  - `fetch_river_levels()` - River water level monitoring
  - `fetch_flood_depths()` - Flood depth measurements

#### 3. **Data Processing (100%)**
- ✅ `collect_and_forward_data()` - Main collection orchestrator
- ✅ `_process_collected_data()` - Data normalization
- ✅ `send_to_hazard_agent()` - Agent communication
- ✅ `_combine_data()` - Multi-source data fusion
- ✅ Update interval management (`_should_update()`)

#### 4. **Data Caches (100%)**
- ✅ `rainfall_data` - Rainfall measurements cache
- ✅ `river_levels` - River level data cache
- ✅ `flood_depth_data` - Flood depth cache
- ✅ Timestamp tracking with `last_update`

#### 5. **Available Data Assets**
- ✅ **18 time-step flood maps** (GeoTIFF format)
  - `app/data/timed_floodmaps/rr01/` (2-year return period)
  - `app/data/timed_floodmaps/rr02/` (5-year return period)
  - `app/data/timed_floodmaps/rr03/` (10-year return period)
  - `app/data/timed_floodmaps/rr04/` (25-year return period)
  - Each: ~1MB TIFF files (512x512 pixels)
- ✅ `marikina_graph.graphml` - Road network (8.4MB)
- ✅ `evacuation_centers.csv` - Evacuation center locations

---

## ❌ What's Missing / Needs Implementation

### 🔴 Critical (Must-Have for Production)

#### 1. **Real Data Source Integration (Priority: HIGH)**

**Problem:** Currently using placeholder/simulated data only

**What's Needed:**
```python
# PAGASA Integration
class PAGASADataSource:
    def get_rainfall_data(self):
        # TODO: Implement actual API calls
        # Contact: cadpagasa@gmail.com for API access
        # Alternative: Web scraping from panahon.gov.ph
        pass
```

**Action Items:**
- [ ] Apply for PAGASA API access
- [ ] Implement web scraping fallback for PAGASA weather data
- [ ] Add authentication/API key management
- [ ] Test with real-time data
- [ ] Handle rate limiting

**Estimated Time:** 8-12 hours
**Difficulty:** Medium

---

#### 2. **GeoTIFF Flood Map Integration (Priority: HIGH)**

**Problem:** 18 TIFF flood maps exist but aren't being parsed/used by FloodAgent

**What's Needed:**
```python
# New methods to add to FloodAgent

def load_flood_maps(self) -> Dict[str, Any]:
    """
    Load and parse GeoTIFF flood maps for all return periods.

    Returns:
        Dict with flood depth grids for each return period and time step
    """
    from osgeo import gdal
    import numpy as np

    flood_maps = {}
    for return_period in ['rr01', 'rr02', 'rr03', 'rr04']:
        flood_maps[return_period] = {}
        for time_step in range(1, 19):
            tiff_path = f"app/data/timed_floodmaps/{return_period}/{return_period}-{time_step}.tif"
            dataset = gdal.Open(tiff_path)
            flood_maps[return_period][time_step] = {
                'data': dataset.ReadAsArray(),
                'geotransform': dataset.GetGeoTransform(),
                'projection': dataset.GetProjection()
            }
    return flood_maps

def get_flood_depth_at_coordinate(
    self,
    lat: float,
    lng: float,
    return_period: str = 'rr01',
    time_step: int = 1
) -> float:
    """
    Get flood depth at specific coordinates from TIFF map.

    Args:
        lat: Latitude
        lng: Longitude
        return_period: 'rr01', 'rr02', 'rr03', or 'rr04'
        time_step: 1-18

    Returns:
        Flood depth in meters
    """
    # Convert lat/lng to pixel coordinates using geotransform
    # Sample TIFF data at that pixel
    # Return interpolated flood depth
    pass

def interpolate_current_flood_state(
    self,
    current_rainfall: float
) -> Dict[str, float]:
    """
    Interpolate between TIFF maps based on current rainfall intensity.

    Args:
        current_rainfall: Current rainfall in mm/hr

    Returns:
        Dict mapping locations to estimated flood depths
    """
    # Use rainfall-runoff model to select appropriate return period
    # Interpolate between time steps
    # Return flood depth estimates for entire city
    pass
```

**Required Dependencies:**
```bash
uv add gdal rasterio
```

**Action Items:**
- [ ] Install GDAL/rasterio for TIFF parsing
- [ ] Implement `load_flood_maps()` to read all 72 TIFFs (18 × 4 return periods)
- [ ] Create coordinate-to-pixel transformation
- [ ] Implement bilinear interpolation for sub-pixel accuracy
- [ ] Add TIFF metadata caching (geotransform, bounds)
- [ ] Create rainfall-to-return-period mapping function
- [ ] Integrate with existing `fetch_flood_depths()` method

**Estimated Time:** 12-16 hours
**Difficulty:** High (GIS expertise required)

---

#### 3. **Automated Data Collection Scheduler (Priority: MEDIUM)**

**Problem:** `step()` method exists but no automatic scheduling

**What's Needed:**
```python
# In main.py or new scheduler module

import schedule
import threading

def start_flood_agent_scheduler():
    """Start background thread for periodic data collection."""

    def run_flood_collection():
        logger.info("Running scheduled flood data collection")
        flood_agent.collect_and_forward_data()

    # Schedule every 5 minutes
    schedule.every(5).minutes.do(run_flood_collection)

    def scheduler_thread():
        while True:
            schedule.run_pending()
            time.sleep(60)

    thread = threading.Thread(target=scheduler_thread, daemon=True)
    thread.start()
    logger.info("Flood data collection scheduler started")

# In main.py startup
@app.on_event("startup")
async def startup_event():
    start_flood_agent_scheduler()
```

**Action Items:**
- [ ] Implement background scheduler using `schedule` library
- [ ] Add configurable collection intervals
- [ ] Implement graceful shutdown
- [ ] Add health check endpoint for scheduler status
- [ ] Log collection statistics

**Estimated Time:** 4-6 hours
**Difficulty:** Low

---

### 🟡 Important (Should-Have)

#### 4. **WebSocket Broadcasting for Real-Time Updates (Priority: MEDIUM)**

**Problem:** FloodAgent collects data but doesn't broadcast to connected clients

**What's Needed:**
```python
# Add to FloodAgent

def broadcast_flood_update(self, data: Dict[str, Any]) -> None:
    """
    Broadcast flood update to all connected WebSocket clients.

    Args:
        data: Flood data update to broadcast
    """
    if not hasattr(self.environment, 'ws_manager'):
        return

    # Format update for frontend
    update = {
        'type': 'flood_update',
        'timestamp': datetime.now().isoformat(),
        'locations': [],
        'summary': {
            'total_locations': len(data),
            'max_depth': 0.0,
            'avg_rainfall': 0.0
        }
    }

    for location, location_data in data.items():
        update['locations'].append({
            'name': location,
            'flood_depth': location_data.get('flood_depth', 0.0),
            'rainfall': location_data.get('rainfall_1h', 0.0),
            'risk_level': self._calculate_location_risk(location_data)
        })

    # Broadcast via WebSocket manager
    asyncio.create_task(
        self.environment.ws_manager.broadcast(update)
    )
```

**Action Items:**
- [ ] Add WebSocket manager reference to FloodAgent
- [ ] Implement `broadcast_flood_update()` method
- [ ] Create frontend handler for flood updates
- [ ] Add real-time flood visualization layer updates
- [ ] Implement connection status indicators

**Estimated Time:** 6-8 hours
**Difficulty:** Medium

---

#### 5. **Historical Flood Data Integration (Priority: MEDIUM)**

**Problem:** No historical flood pattern analysis

**What's Needed:**
```python
class HistoricalFloodDatabase:
    """Store and query historical flood events."""

    def __init__(self, db_path: str = "app/data/flood_history.db"):
        self.db_path = db_path
        self.conn = self._init_database()

    def _init_database(self):
        """Create SQLite database for flood history."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flood_events (
                event_id INTEGER PRIMARY KEY,
                location TEXT,
                timestamp DATETIME,
                flood_depth REAL,
                rainfall_1h REAL,
                rainfall_24h REAL,
                source TEXT
            )
        ''')
        conn.commit()
        return conn

    def store_flood_event(self, event: Dict[str, Any]):
        """Store flood event in database."""
        pass

    def get_historical_avg(self, location: str, days: int = 30) -> float:
        """Get historical average flood depth for location."""
        pass
```

**Action Items:**
- [ ] Create SQLite database schema
- [ ] Implement flood event storage
- [ ] Add historical query methods
- [ ] Integrate with risk calculation (HazardAgent)
- [ ] Create data visualization endpoints

**Estimated Time:** 8-10 hours
**Difficulty:** Medium

---

#### 6. **Enhanced Data Validation & Anomaly Detection (Priority: MEDIUM)**

**Current Validation:** Basic field checks only

**What's Needed:**
```python
def validate_flood_data_advanced(self, data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Advanced validation with anomaly detection.

    Returns:
        (is_valid, error_message)
    """
    # 1. Range checks
    flood_depth = data.get('flood_depth', 0.0)
    if flood_depth < 0 or flood_depth > 10:  # Max 10m
        return False, f"Invalid flood depth: {flood_depth}m"

    # 2. Temporal consistency
    if self.last_update:
        time_diff = (datetime.now() - self.last_update).total_seconds()
        last_depth = self.flood_depth_data.get(data['location'], {}).get('flood_depth', 0.0)

        # Detect sudden spikes (>1m change in <5 minutes = suspicious)
        if time_diff < 300 and abs(flood_depth - last_depth) > 1.0:
            return False, "Suspicious flood depth spike detected"

    # 3. Cross-source correlation
    rainfall = data.get('rainfall_1h', 0.0)
    if flood_depth > 1.0 and rainfall < 5.0:
        # High flood depth but low rainfall = suspicious
        return False, "Flood depth inconsistent with rainfall"

    return True, "OK"
```

**Action Items:**
- [ ] Implement range validation
- [ ] Add temporal consistency checks
- [ ] Create cross-source correlation validation
- [ ] Implement outlier detection (statistical methods)
- [ ] Add data quality scoring
- [ ] Create alert system for anomalies

**Estimated Time:** 6-8 hours
**Difficulty:** Medium

---

### 🟢 Nice-to-Have (Future Enhancements)

#### 7. **ML-Based Flood Prediction (Priority: LOW)**

**What's Needed:**
- Train Random Forest model on historical data
- Predict flood depths 1-6 hours ahead
- Integrate with HazardAgent for proactive routing

**Estimated Time:** 20-30 hours
**Difficulty:** High

---

#### 8. **Multi-City Support (Priority: LOW)**

**What's Needed:**
- Generalize to support other Philippine cities
- Dynamic TIFF loading based on city selection
- City-specific configuration files

**Estimated Time:** 12-16 hours
**Difficulty:** Medium

---

#### 9. **Database Persistence (Priority: LOW)**

**What's Needed:**
```python
# Store collected data in PostgreSQL/MongoDB
class FloodDataRepository:
    def save_flood_reading(self, reading: Dict[str, Any]):
        """Save to database for historical analysis."""
        pass
```

**Estimated Time:** 8-10 hours
**Difficulty:** Low

---

#### 10. **Comprehensive Unit Tests (Priority: MEDIUM)**

**Current Status:** HazardAgent has 27 tests (100% pass rate), but FloodAgent has 0 tests

**What's Needed:**
```python
# tests/test_flood_agent.py

def test_flood_agent_initialization():
    """Test FloodAgent initializes correctly."""
    env = DynamicGraphEnvironment()
    agent = FloodAgent("flood_001", env)
    assert agent.agent_id == "flood_001"
    assert agent.data_update_interval == 300

def test_fetch_rainfall_data():
    """Test rainfall data fetching."""
    agent = FloodAgent("flood_001", env, use_simulated=True)
    data = agent.fetch_rainfall_data()
    assert "Marikina" in data
    assert data["Marikina"]["rainfall_1h"] >= 0

def test_data_forwarding_to_hazard_agent():
    """Test data is properly forwarded to HazardAgent."""
    hazard_agent = HazardAgent("hazard_001", env)
    flood_agent = FloodAgent("flood_001", env, hazard_agent=hazard_agent)

    data = flood_agent.collect_and_forward_data()
    assert len(hazard_agent.flood_data_cache) > 0
```

**Action Items:**
- [ ] Create `tests/test_flood_agent.py`
- [ ] Test initialization
- [ ] Test data collection methods
- [ ] Test data processing pipeline
- [ ] Test HazardAgent integration
- [ ] Test error handling
- [ ] Test update interval logic
- [ ] Achieve 80%+ code coverage

**Estimated Time:** 10-12 hours
**Difficulty:** Medium

---

## 🎯 Recommended Implementation Roadmap

### Phase 1: Core Data Integration (2-3 weeks)
**Priority:** Critical
**Goal:** Get real flood data flowing through the system

1. ✅ **Week 1: GeoTIFF Integration**
   - Install GDAL/rasterio
   - Implement TIFF loading and parsing
   - Create coordinate-to-flood-depth mapping
   - Test with all 72 TIFF files

2. ✅ **Week 2: Real Data Sources**
   - Apply for PAGASA API access
   - Implement web scraping fallback
   - Test with live rainfall data
   - Add error handling and retry logic

3. ✅ **Week 3: Automated Collection**
   - Implement scheduler
   - Add WebSocket broadcasting
   - Create frontend real-time updates
   - End-to-end testing

**Deliverable:** FloodAgent collecting and broadcasting real flood data every 5 minutes

---

### Phase 2: Data Quality & Reliability (1-2 weeks)
**Priority:** Important
**Goal:** Ensure data accuracy and system reliability

4. ✅ **Week 4: Validation & Testing**
   - Advanced data validation
   - Anomaly detection
   - Comprehensive unit tests (80% coverage)
   - Integration tests with HazardAgent

5. ✅ **Week 5: Historical Data**
   - Database setup
   - Historical data storage
   - Query interfaces
   - Data visualization

**Deliverable:** Robust, tested FloodAgent with historical tracking

---

### Phase 3: Advanced Features (2-3 weeks)
**Priority:** Nice-to-Have
**Goal:** Enhanced capabilities for better predictions

6. ✅ **Week 6-7: ML Prediction**
   - Collect training data
   - Train Random Forest model
   - Integrate predictions into system
   - Validate accuracy

7. ✅ **Week 8: Multi-City Support**
   - Generalize city configuration
   - Dynamic TIFF loading
   - Testing with other cities

**Deliverable:** Production-ready FloodAgent with predictive capabilities

---

## 📝 Quick Start Guide

### To Continue Development:

1. **Start with GeoTIFF Integration:**
   ```bash
   cd masfro-backend
   uv add gdal rasterio numpy
   ```

2. **Create new module:**
   ```bash
   touch app/services/tiff_processor.py
   ```

3. **Implement TIFF loader:**
   ```python
   # See detailed implementation in section #2 above
   ```

4. **Update FloodAgent:**
   ```python
   # Add TIFF integration to existing methods
   ```

5. **Test:**
   ```bash
   uv run pytest tests/test_flood_agent.py -v
   ```

---

## 📊 Progress Metrics

| Component | Status | Completion |
|-----------|--------|------------|
| Core Architecture | ✅ Complete | 100% |
| Simulated Data | ✅ Complete | 100% |
| Data Processing | ✅ Complete | 100% |
| Real Data Integration | ❌ Pending | 0% |
| GeoTIFF Integration | ❌ Pending | 0% |
| Automated Scheduling | ❌ Pending | 0% |
| WebSocket Broadcasting | ❌ Pending | 0% |
| Data Validation | 🟡 Basic | 40% |
| Historical Tracking | ❌ Not Started | 0% |
| Unit Tests | ❌ Not Started | 0% |
| **OVERALL** | 🟡 In Progress | **~35%** |

---

## 🔗 Related Files to Review

1. `app/agents/hazard_agent.py` - Data receiver (100% complete with tests)
2. `app/agents/scout_agent.py` - Crowdsourced data collector
3. `app/services/data_sources.py` - Data collection framework
4. `app/environment/graph_manager.py` - Graph environment
5. `app/main.py` - API endpoints using FloodAgent
6. `PHASE_2.5_COMPLETION.md` - Recent frontend flood visualization work

---

## 💡 Key Insights

1. **FloodAgent is architecturally sound** - The framework is well-designed and follows clean architecture principles

2. **Main gap is real data** - You have the plumbing but need to connect to actual water sources (PAGASA, NOAH, MMDA)

3. **TIFF assets are gold** - 72 high-quality flood maps sitting unused. Priority #1 should be integrating these

4. **Testing gap** - HazardAgent has 27 tests, FloodAgent has 0. This needs attention before production

5. **Scheduler needed** - FloodAgent has `step()` but nothing is calling it automatically

6. **WebSocket integration ready** - Infrastructure exists in main.py, just needs FloodAgent hook-up

---

## 🚀 Next Immediate Actions (This Week)

1. [ ] **Install GDAL:** `uv add gdal rasterio`
2. [ ] **Create TIFF processor:** Implement `load_flood_maps()` method
3. [ ] **Test TIFF loading:** Verify all 72 files load correctly
4. [ ] **Integrate with FloodAgent:** Update `fetch_flood_depths()` to use TIFFs
5. [ ] **Write 5 unit tests:** Basic coverage for core methods
6. [ ] **Setup scheduler:** Implement automated 5-minute data collection
7. [ ] **Test end-to-end:** Verify data flows from FloodAgent → HazardAgent → RoutingAgent

**Estimated Time:** 20-25 hours of focused development

---

**Next Document to Read:** `TIFF_INTEGRATION_GUIDE.md` (to be created with step-by-step GDAL tutorial)
