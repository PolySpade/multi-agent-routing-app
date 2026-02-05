# MAS-FRO Backend Implementation Documentation

> **Multi-Agent System for Flood Route Optimization (MAS-FRO)**
>
> Comprehensive implementation reference for the backend microservice architecture.
>
> **Version:** 1.0.0
> **Last Updated:** February 2026
> **Framework:** FastAPI 0.118.0+
> **Python Version:** 3.10+

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Multi-Agent System](#3-multi-agent-system)
4. [Environment & Graph Management](#4-environment--graph-management)
5. [External Service Integrations](#5-external-service-integrations)
6. [API Endpoints Reference](#6-api-endpoints-reference)
7. [Simulation System](#7-simulation-system)
8. [Core Utilities](#8-core-utilities)
9. [Data Models & Schemas](#9-data-models--schemas)
10. [Key Algorithms](#10-key-algorithms)
11. [Configuration Reference](#11-configuration-reference)
12. [Development Guide](#12-development-guide)
13. [Qwen 3 LLM Integration](#13-qwen-3-llm-integration)

---

## 1. Executive Summary

### Project Overview

MAS-FRO is a multi-agent system designed for flood-aware route optimization in Marikina City, Philippines. The system combines:

- **Official data sources** (PAGASA river levels, dam monitoring, OpenWeatherMap)
- **Crowdsourced reports** (Twitter/X data processed through NLP)
- **GeoTIFF flood maps** (4 return periods × 18 time steps)

### Key Features

- Real-time flood risk assessment using multi-source data fusion
- Risk-aware A* pathfinding with "Virtual Meters" approach
- Tick-based simulation with event-driven architecture
- WebSocket real-time updates for critical alerts
- Automated 5-minute data collection scheduler

### Technology Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Graph Library | NetworkX + OSMnx |
| Database | PostgreSQL (SQLAlchemy ORM) |
| Web Scraping | Selenium, BeautifulSoup |
| NLP Processing | Custom ML models |
| Geospatial | Rasterio, GeoTIFF |
| Real-time | WebSockets |

---

## 2. Architecture Overview

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI APPLICATION                             │
│                                  (main.py)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐    │
│  │   REST API  │   │  WebSocket  │   │  Scheduler  │   │  Simulation │    │
│  │  Endpoints  │   │   Manager   │   │  (5-min)    │   │   Manager   │    │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘    │
│         │                 │                 │                 │            │
├─────────┴─────────────────┴─────────────────┴─────────────────┴────────────┤
│                                                                             │
│                          MESSAGE QUEUE (ACL Protocol)                       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │  FloodAgent   │  │  ScoutAgent   │  │ EvacManager   │                   │
│  │  (Official    │  │  (Crowdsource │  │ (User Routes  │                   │
│  │   Data)       │  │   + NLP)      │  │  + Feedback)  │                   │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘                   │
│          │                  │                  │                            │
│          └─────────┬────────┴──────────────────┘                            │
│                    ▼                                                        │
│            ┌───────────────┐                                                │
│            │  HazardAgent  │ ◄── Central Data Fusion Hub                    │
│            │  (Risk Calc   │                                                │
│            │   + Graph     │                                                │
│            │   Update)     │                                                │
│            └───────┬───────┘                                                │
│                    │                                                        │
│          ┌─────────┴──────────┐                                             │
│          ▼                    ▼                                             │
│  ┌───────────────┐    ┌───────────────┐                                     │
│  │RoutingAgent   │    │ DynamicGraph  │                                     │
│  │(A* Pathfind)  │◄───│ Environment   │                                     │
│  └───────────────┘    └───────────────┘                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │   PAGASA    │ │OpenWeather  │ │  GeoTIFF    │
            │   (River/   │ │    Map      │ │   Flood     │
            │    Dam)     │ │   (API)     │ │    Maps     │
            └─────────────┘ └─────────────┘ └─────────────┘
```

### Data Flow Pattern

```
1. DATA COLLECTION PHASE
   FloodAgent ──┐
                ├──► MessageQueue ──► HazardAgent
   ScoutAgent ──┘

2. FUSION PHASE
   HazardAgent:
   ├── Receive ACL messages
   ├── Validate & fuse data
   ├── Calculate risk scores (Kreibich formula)
   └── Update DynamicGraphEnvironment

3. ROUTING PHASE
   EvacuationManager ──► RoutingAgent ──► Risk-Aware A* ──► Path Result

4. UPDATE PHASE
   HazardAgent ──► Graph Edge Updates ──► WebSocket Broadcast
```

### Component Relationships

| Component | Depends On | Provides To |
|-----------|-----------|-------------|
| FloodAgent | RiverScraperService, WeatherService, DamScraperService | HazardAgent |
| ScoutAgent | NLPProcessor, LocationGeocoder | HazardAgent |
| HazardAgent | MessageQueue, GeoTIFFService, RiskCalculator | DynamicGraphEnvironment |
| RoutingAgent | DynamicGraphEnvironment | EvacuationManagerAgent |
| SimulationManager | All Agents | API Endpoints |

---

## 3. Multi-Agent System

### Agent Hierarchy

```
BaseAgent (Abstract)
├── FloodAgent          - Official data collection
├── ScoutAgent          - Crowdsourced data + NLP
├── HazardAgent         - Central fusion hub
├── RoutingAgent        - A* pathfinding
└── EvacuationManagerAgent - User interface coordinator
```

### 3.1 BaseAgent

**Location:** `app/agents/base_agent.py`

Base class providing common interface for all agents.

```python
class BaseAgent:
    def __init__(self, agent_id: str, environment: "DynamicGraphEnvironment"):
        self.agent_id = agent_id
        self.environment = environment
        self.logger = get_logger(f"app.agents.{agent_id}")

    def step(self) -> None:
        """Must be implemented by subclasses."""
        raise NotImplementedError
```

### 3.2 FloodAgent

**Location:** `app/agents/flood_agent.py`

Collects official environmental data from authoritative sources.

#### Initialization Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_id` | str | - | Unique identifier |
| `environment` | DynamicGraphEnvironment | - | Graph reference |
| `message_queue` | MessageQueue | None | MAS communication |
| `use_simulated` | bool | False | Use simulated data |
| `use_real_apis` | bool | True | Enable real API services |
| `hazard_agent_id` | str | "hazard_agent_001" | Target for messages |

#### Data Sources

1. **PAGASA River Levels** (`RiverScraperService`)
   - Marikina River stations: Sto Nino, Nangka, Tumana Bridge, Montalban, Rosario Bridge
   - Water level, alert/alarm/critical thresholds

2. **OpenWeatherMap** (`OpenWeatherMapService`)
   - Current rainfall (mm/hr)
   - 24-hour forecast
   - Temperature, humidity, pressure

3. **PAGASA Dam Levels** (`DamWaterScraperService`)
   - Reservoir water level (RWL)
   - Normal high water level (NHWL)
   - Rule curve deviation

#### Key Methods

```python
def collect_flood_data(self) -> Dict[str, Any]:
    """Collect from all sources with fallback to simulated."""

def fetch_real_river_levels(self) -> Dict[str, Any]:
    """Fetch REAL river levels from PAGASA API."""

def fetch_real_weather_data(self, lat=14.6507, lon=121.1029) -> Dict[str, Any]:
    """Fetch REAL weather from OpenWeatherMap."""

def send_flood_data_via_message(self, data: Dict[str, Any]) -> None:
    """Send to HazardAgent via MessageQueue using ACL INFORM."""
```

#### Risk Score Calculation (River Levels)

```python
if water_level >= critical_level:
    status, risk_score = "critical", 1.0
elif water_level >= alarm_level:
    status, risk_score = "alarm", 0.8
elif water_level >= alert_level:
    status, risk_score = "alert", 0.5
else:
    status, risk_score = "normal", 0.2
```

#### Rainfall Intensity Classification (PAGASA)

| Intensity | Range (mm/hr) |
|-----------|---------------|
| None | 0 |
| Light | 0.1 - 2.5 |
| Moderate | 2.6 - 7.5 |
| Heavy | 7.6 - 15.0 |
| Intense | 15.1 - 30.0 |
| Torrential | > 30.0 |

### 3.3 ScoutAgent

**Location:** `app/agents/scout_agent.py`

Collects crowdsourced flood reports with NLP processing.

#### Initialization Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_id` | str | - | Unique identifier |
| `environment` | DynamicGraphEnvironment | - | Graph reference |
| `message_queue` | MessageQueue | None | MAS communication |
| `hazard_agent_id` | str | "hazard_agent_001" | Target for messages |
| `simulation_scenario` | int | 1 | Scenario 1-3 |
| `use_ml_in_simulation` | bool | True | Process through ML models |

#### Components

- **NLPProcessor**: Extracts flood information from tweet text
- **LocationGeocoder**: Converts location mentions to coordinates

#### Processing Pipeline

```
Raw Tweet ──► NLP Extract ──► Geocode ──► Validate ──► ACL Message ──► HazardAgent
```

#### Key Methods

```python
def step(self) -> list:
    """Collect and process simulation batch."""

def _process_and_forward_tweets(self, tweets: list) -> None:
    """Process with NLP, geocode, and forward to HazardAgent."""

def _load_simulation_data(self) -> bool:
    """Load synthetic tweets from JSON file."""
```

#### Validation Checks

```python
# Coordinate validation
if not (-90 <= lat <= 90 and -180 <= lon <= 180):
    continue  # Skip invalid coordinates

# Severity validation
if not 0 <= severity <= 1:
    severity = max(0, min(1, float(severity)))
```

### 3.4 HazardAgent

**Location:** `app/agents/hazard_agent.py`

Central data fusion hub and risk calculator.

#### Initialization Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_id` | str | - | Unique identifier |
| `environment` | DynamicGraphEnvironment | - | Graph reference |
| `message_queue` | MessageQueue | None | MAS communication |
| `enable_geotiff` | bool | False | Enable GeoTIFF flood simulation |

#### Data Caches

```python
self.flood_data_cache: Dict[str, Any] = {}  # Official data
self.scout_data_cache: deque = deque(maxlen=1000)  # Crowdsourced (LRU)
self.scout_cache_keys: set = set()  # O(1) deduplication
```

#### Risk Weights

```python
self.risk_weights = {
    "flood_depth": 0.5,    # Official flood depth
    "crowdsourced": 0.3,   # Crowdsourced reports
    "historical": 0.2      # Historical data
}
```

#### Time-Based Risk Decay

```python
# Fast decay: Rain-based flooding (drains quickly)
scout_decay_rate_fast = 0.10  # 10% per minute

# Slow decay: River/dam flooding (slow recession)
scout_decay_rate_slow = 0.03  # 3% per minute

# TTL values
scout_report_ttl_minutes = 45
flood_data_ttl_minutes = 90
```

#### Spatial Index

Grid-based spatial index for O(1) edge lookups:

```python
spatial_index_grid_size = 0.001  # ~111m per grid cell
# Key: (grid_lat, grid_lon) -> List[(u, v, key, mid_lat, mid_lon)]
```

#### Key Methods

```python
def step(self) -> Dict[str, Any]:
    """Process messages and update graph."""

def process_messages(self) -> Dict[str, int]:
    """Process all pending ACL messages."""

def update_risk(self, flood_data, scout_data, time_step) -> Dict[str, Any]:
    """Main risk update method for simulation."""

def _process_scout_reports_with_coordinates(self, reports: List[Dict]) -> Dict[str, int]:
    """Spatial risk processing using grid index."""
```

#### GeoTIFF Scenario Control

```python
def set_flood_scenario(self, return_period: str, time_step: int):
    """
    Set flood scenario.

    return_period: rr01 (2-year), rr02 (5-year), rr03 (10-year), rr04 (25-year)
    time_step: 1-18 (hours of flood progression)
    """
```

### 3.5 RoutingAgent

**Location:** `app/agents/routing_agent.py`

Risk-aware A* pathfinding with Virtual Meters approach.

#### Virtual Meters Approach

**Problem:** Traditional weighted A* with risk uses `f(n) = g(n) + h(n)` where risk weights (0-1) are negligible compared to distance (50-500m), causing A* to ignore risk.

**Solution:** Convert risk to "virtual meters":

```python
edge_cost = distance_meters + (risk_penalty * risk_score)
```

#### Routing Modes

| Mode | Risk Penalty | Effect |
|------|-------------|--------|
| **Safest** | 100,000 | Take ANY detour to avoid flooded roads |
| **Balanced** | 2,000 | Prefer safer routes, accept minor risk |
| **Fastest** | 0 | Pure shortest path (still blocks risk >= 0.9) |

#### Key Methods

```python
def calculate_route(
    self,
    start: Tuple[float, float],
    end: Tuple[float, float],
    preferences: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Returns:
    {
        "status": "success" | "impassable" | "no_safe_route",
        "path": List[(lat, lon)],
        "distance": float,
        "estimated_time": float,
        "risk_level": float,
        "max_risk": float,
        "warnings": List[RouteWarning]
    }
    """

def find_nearest_evacuation_center(
    self,
    location: Tuple[float, float],
    max_centers: int = 5
) -> Optional[Dict[str, Any]]:
    """Find nearest evacuation center with route."""
```

#### Warning Severity Levels

```python
class WarningSeverity(Enum):
    INFO = "info"         # FYI - informational
    CAUTION = "caution"   # Be aware - minor concerns
    WARNING = "warning"   # Dangerous - significant risk
    CRITICAL = "critical" # Life-threatening - do not proceed
```

### 3.6 EvacuationManagerAgent

**Location:** `app/agents/evacuation_manager_agent.py`

User interface coordinator for route requests and feedback.

#### Key Methods

```python
def handle_route_request(
    self,
    start: Tuple[float, float],
    end: Tuple[float, float],
    preferences: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Handle route request, coordinate with RoutingAgent."""

def collect_user_feedback(
    self,
    route_id: str,
    feedback_type: str,  # "clear", "blocked", "flooded", "traffic"
    location: Optional[Tuple[float, float]] = None,
    data: Optional[Dict[str, Any]] = None
) -> bool:
    """Collect and forward user feedback."""
```

### Agent Communication via Message Queue

#### Message Queue

**Location:** `app/communication/message_queue.py`

Thread-safe centralized message routing:

```python
class MessageQueue:
    def register_agent(self, agent_id: str) -> None
    def send_message(self, message: ACLMessage) -> bool
    def receive_message(self, agent_id: str, timeout: float) -> Optional[ACLMessage]
    def broadcast_message(self, message: ACLMessage) -> int
```

#### ACL Protocol (FIPA-ACL)

**Location:** `app/communication/acl_protocol.py`

```python
class Performative(str, Enum):
    REQUEST = "REQUEST"   # Request action
    INFORM = "INFORM"     # Provide information
    QUERY = "QUERY"       # Query for information
    CONFIRM = "CONFIRM"   # Confirm truth
    REFUSE = "REFUSE"     # Refuse action
    AGREE = "AGREE"       # Agree to action
    FAILURE = "FAILURE"   # Notification of failure

@dataclass
class ACLMessage:
    performative: Performative
    sender: str
    receiver: str
    content: Dict[str, Any]
    language: str = "json"
    ontology: str = "routing"
    conversation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
```

#### Message Types

| info_type | Sender | Receiver | Content |
|-----------|--------|----------|---------|
| `flood_data_batch` | FloodAgent | HazardAgent | `{location: data}` |
| `scout_report_batch` | ScoutAgent | HazardAgent | `{reports: [], has_coordinates: bool}` |
| `user_feedback` | EvacManager | HazardAgent | `{scout_report_batch: [data]}` |

---

## 4. Environment & Graph Management

### DynamicGraphEnvironment

**Location:** `app/environment/graph_manager.py`

Thread-safe road network graph management.

#### Initialization

```python
def __init__(self):
    self.filepath = "data/marikina_graph.graphml"
    self.graph = None
    self._lock = Lock()

    # State persistence
    self.state_file = data_dir / "graph_state.pkl"

    # Load or recover graph
    if self.state_file.exists():
        self._recover_state()
    else:
        self._load_graph_from_file()
```

#### Graph Structure

- **Type:** NetworkX MultiDiGraph
- **Nodes:** ~40,000+ (road intersections)
- **Edges:** ~100,000+ (road segments)

**Node Attributes:**
```python
{
    'x': float,  # Longitude
    'y': float   # Latitude
}
```

**Edge Attributes:**
```python
{
    'length': float,      # Meters
    'risk_score': float,  # 0.0-1.0
    'weight': float       # length * (1 + risk_score)
}
```

#### Key Methods

```python
def update_edge_risk(self, u, v, key, risk_factor: float):
    """Thread-safe single edge update."""

def batch_update_edge_risks(self, risk_updates: dict):
    """Efficient batch update with lock."""

def _save_snapshot(self):
    """Persist risk scores to disk (atomic write)."""

def _recover_state(self):
    """Recover from last session."""
```

### RiskCalculator

**Location:** `app/environment/risk_calculator.py`

Calculates risk scores using Kreibich formula.

#### Kreibich Formula (2009)

Energy head for damage prediction:

```
E = h + v²/(2g)

where:
  h = flood depth (meters)
  v = flow velocity (m/s)
  g = gravitational acceleration (9.81 m/s²)
```

#### Risk Thresholds

| Energy (E) | Risk | Description |
|------------|------|-------------|
| < 0.3m | 0.0-0.4 | Low risk (vehicles can pass) |
| 0.3-0.6m | 0.4-0.7 | Moderate risk |
| > 0.6m | 0.7-1.0 | High risk (dangerous) |

#### Passability Thresholds by Vehicle

| Vehicle | Static Depth | Flowing Depth | Max Velocity |
|---------|--------------|---------------|--------------|
| Car | 0.3m | 0.4m | 0.5 m/s |
| SUV | 0.5m | 0.6m | 0.5 m/s |
| Truck | 0.6m | 0.7m | 0.6 m/s |

---

## 5. External Service Integrations

### 5.1 PAGASA River Scraper

**Location:** `app/services/river_scraper_service.py`

Scrapes PAGASA Flood Forecasting website for river levels.

**Target Stations:**
- Sto Nino
- Nangka
- Tumana Bridge
- Montalban
- Rosario Bridge

**Data Fields:**
- `water_level_m`: Current water level
- `alert_level_m`, `alarm_level_m`, `critical_level_m`: Thresholds

### 5.2 PAGASA Dam Scraper

**Location:** `app/services/dam_water_scraper_service.py`

Scrapes PAGASA for dam water levels.

**Data Fields:**
- `reservoir_water_level_m`: Current RWL
- `normal_high_water_level_m`: NHWL threshold
- `deviation_from_nhwl_m`: RWL - NHWL

**Risk Status:**
```python
if deviation >= 2.0m: status = "critical", risk = 1.0
elif deviation >= 1.0m: status = "alarm", risk = 0.8
elif deviation >= 0.5m: status = "alert", risk = 0.5
elif deviation >= 0.0m: status = "watch", risk = 0.3
else: status = "normal", risk = 0.1
```

### 5.3 OpenWeatherMap Service

**Location:** `app/services/weather_service.py`

Fetches weather data from OpenWeatherMap API.

**Requires:** `OPENWEATHERMAP_API_KEY` environment variable

**Data Fields:**
- `current_rainfall_mm`: mm/hr
- `rainfall_24h_mm`: Accumulated forecast
- `temperature_c`, `humidity_pct`, `pressure_hpa`

### 5.4 GeoTIFF Service

**Location:** `app/services/geotiff_service.py`

Manages flood depth maps from GeoTIFF files.

**Directory Structure:**
```
app/data/geotiff_data/
├── rr01/             # 2-year return period
│   ├── rr01_step_01.tif
│   ├── rr01_step_02.tif
│   └── ... (steps 01-18)
├── rr02/             # 5-year return period
├── rr03/             # 10-year return period
└── rr04/             # 25-year return period
```

**Return Period Mapping:**
| Code | Return Period | Description |
|------|---------------|-------------|
| rr01 | 2-year | Light flooding |
| rr02 | 5-year | Moderate flooding |
| rr03 | 10-year | Heavy flooding |
| rr04 | 25-year | Severe flooding |

**Key Methods:**
```python
def load_flood_map(self, return_period: str, time_step: int) -> Tuple[np.ndarray, dict]
def get_flood_depth_at_point(self, lon: float, lat: float, return_period: str, time_step: int) -> Optional[float]
def get_available_maps(self) -> List[dict]
```

### 5.5 Evacuation Center Service

**Location:** `app/services/evacuation_service.py`

Manages evacuation center data and occupancy.

**Data Source:** `app/data/evacuation_centers.csv`

**Key Methods:**
```python
def get_all_centers(self) -> List[dict]
def get_center_by_name(self, name: str) -> Optional[dict]
def add_evacuees(self, name: str, count: int) -> dict
def reset_all_occupancy(self) -> None
```

### 5.6 Flood Data Scheduler

**Location:** `app/services/flood_data_scheduler.py`

Background scheduler for automated data collection.

**Configuration:**
- Interval: 300 seconds (5 minutes)
- Auto-start on application startup

**Key Methods:**
```python
async def start(self) -> None
async def stop(self) -> None
async def trigger_manual_collection(self) -> dict
def get_status(self) -> dict
```

---

## 6. API Endpoints Reference

### General Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/api/health` | System health status |
| GET | `/api/statistics` | System statistics |

### Routing Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/route` | Calculate optimal flood-safe route |
| POST | `/api/evacuation-center` | Find nearest evacuation center |
| POST | `/api/feedback` | Submit user feedback |

**POST /api/route Request:**
```json
{
  "start_location": [14.6507, 121.1029],
  "end_location": [14.6545, 121.1089],
  "preferences": {
    "avoid_floods": true,
    "fastest": false
  }
}
```

**POST /api/route Response:**
```json
{
  "route_id": "uuid",
  "status": "success",
  "path": [[14.6507, 121.1029], ...],
  "distance": 2500.0,
  "estimated_time": 8.5,
  "risk_level": 0.35,
  "warnings": [...]
}
```

### Simulation Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/simulation/start?mode=light` | API Key | Start simulation |
| POST | `/api/simulation/stop` | API Key | Stop simulation |
| POST | `/api/simulation/reset` | API Key | Reset simulation |
| GET | `/api/simulation/status` | - | Get status |

### Admin Endpoints (API Key Required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/admin/collect-flood-data` | Manual flood data collection |
| POST | `/api/admin/geotiff/enable` | Enable GeoTIFF simulation |
| POST | `/api/admin/geotiff/disable` | Disable GeoTIFF simulation |
| GET | `/api/admin/geotiff/status` | Get GeoTIFF status |
| POST | `/api/admin/geotiff/set-scenario` | Set flood scenario |

### Scheduler Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/scheduler/status` | Scheduler health |
| GET | `/api/scheduler/stats` | Detailed statistics |
| POST | `/api/scheduler/trigger` | Manual collection |

### Flood Data History Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/flood-data/latest` | Latest collection |
| GET | `/api/flood-data/history` | Paginated history |
| GET | `/api/flood-data/river/{station}/history` | Station history |
| GET | `/api/flood-data/critical-alerts` | Critical alerts |
| GET | `/api/flood-data/statistics` | Database statistics |

### Agent Data Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/agents/status` | All agents status |
| GET | `/api/agents/scout/reports` | Crowdsourced reports |
| POST | `/api/agents/scout/collect` | Trigger scout collection |
| GET | `/api/agents/flood/current-status` | FloodAgent status |
| GET | `/api/agents/evacuation/centers` | Evacuation centers |

### GeoTIFF Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/geotiff/available-maps` | List available maps |
| GET | `/api/geotiff/flood-map` | Get map metadata |
| GET | `/api/geotiff/flood-depth` | Get depth at point |
| GET | `/data/timed_floodmaps/{period}/{file}` | Serve TIFF file |

### WebSocket Endpoint

**URL:** `ws://host/ws/route-updates`

**Message Types:**

```json
// Connection established
{"type": "connection", "status": "connected", "message": "..."}

// System status
{"type": "system_status", "graph_status": "loaded", "agents": {...}}

// Flood data update
{"type": "flood_update", "data": {...}, "timestamp": "..."}

// Critical alert
{"type": "critical_alert", "severity": "critical", "station": "...", "water_level": 15.2}

// Simulation state
{"type": "simulation_state", "event": "started|stopped|tick", "data": {...}}

// Risk update
{"type": "risk_update", "data": {"edges_updated": 500, "average_risk": 0.45}}
```

### Debug Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/debug/hazard-cache` | Inspect HazardAgent cache |
| GET | `/api/debug/simulation-events` | Event queue status |
| GET | `/api/debug/graph-risk-scores` | Graph risk statistics |

---

## 7. Simulation System

### SimulationManager

**Location:** `app/services/simulation_manager.py`

Tick-based simulation orchestrator.

#### States

```python
class SimulationState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
```

#### Modes (Return Periods)

```python
class SimulationMode(str, Enum):
    LIGHT = "light"    # rr01 (2-year)
    MEDIUM = "medium"  # rr02 (5-year)
    HEAVY = "heavy"    # rr04 (25-year)
```

### Tick Execution Phases

```
=== TICK {n} START ===

Phase 1: DATA COLLECTION
├── Process events from event queue
├── Populate shared_data_bus["flood_data"]
└── Populate shared_data_bus["scout_data"]

Phase 2: DATA FUSION & GRAPH UPDATE
├── HazardAgent receives data
├── Calculate risk scores
└── Update graph edges

Phase 3: ROUTING
└── Process pending route requests

Phase 4: EVACUATION CENTER UPDATE
└── Simulate evacuee flow

Phase 5: TIME ADVANCEMENT
└── Increment time step (1-18)

=== TICK {n} COMPLETE ===
```

### Shared Data Bus

```python
shared_data_bus = {
    "flood_data": {},      # Dict from FloodAgent
    "scout_data": [],      # List from ScoutAgent
    "graph_updated": False,
    "pending_routes": []
}
```

### Scenario Files

**Location:** `app/data/simulation_scenarios/`

```
light_scenario.csv
medium_scenario.csv
heavy_scenario.csv
```

**CSV Format:**
```csv
time_offset,agent,payload
0,flood_agent,{"location": "Nangka", "water_level_m": 12.5}
5,scout_agent,{"text": "Baha sa Marikina!", "location": "Tumana"}
```

### Evacuation Rate Calculation

```python
# Mode multiplier
mode_multiplier = {
    LIGHT: 1.0,
    MEDIUM: 2.0,
    HEAVY: 3.5
}

# Time progression
time_multiplier = 1.0 + (current_time_step / 18.0) * 1.5

# Final rate
evacuation_rate = base_rate * mode_multiplier * time_multiplier
```

---

## 8. Core Utilities

### Configuration

**Location:** `app/core/config.py`

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    API_KEY: str
    OPENWEATHERMAP_API_KEY: str
    DATABASE_URL: str

    class Config:
        env_file = ".env"
```

### Agent Configuration (YAML)

**Location:** `app/core/agent_config.py`

```yaml
# config/agents.yaml
hazard:
  risk_radius_m: 500
  enable_spatial_filtering: true
  decay_function: "gaussian"
  grid_size_degrees: 0.001
```

### Authentication

**Location:** `app/core/auth.py`

```python
def verify_api_key(api_key: str = Header(...)):
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=401)
```

### Logging

**Location:** `app/core/logging_config.py`

```python
def setup_logging():
    """Configure structured logging to logs/masfro.log"""
```

### Pagination

**Location:** `app/core/pagination.py`

```python
def paginate(items: list, page: int, page_size: int) -> PaginatedResult:
    """Generic pagination utility."""
```

### WebSocket Connection Manager

**Location:** `app/main.py` (ConnectionManager class)

```python
class ConnectionManager:
    async def connect(self, websocket: WebSocket)
    def disconnect(self, websocket: WebSocket)
    async def broadcast(self, message: dict)
    async def broadcast_flood_update(self, flood_data: Dict)
    async def broadcast_critical_alert(self, station, level, risk, message)
```

---

## 9. Data Models & Schemas

### Pydantic Request/Response Models

**Location:** `app/main.py`

```python
class RouteRequest(BaseModel):
    start_location: Tuple[float, float]
    end_location: Tuple[float, float]
    preferences: Optional[Dict[str, Any]] = None

class RouteResponse(BaseModel):
    route_id: str
    status: str
    path: List[Tuple[float, float]]
    distance: Optional[float] = None
    estimated_time: Optional[float] = None
    risk_level: Optional[float] = None
    warnings: List[str] = []
    message: Optional[str] = None

class FeedbackRequest(BaseModel):
    route_id: str
    feedback_type: str  # "clear", "blocked", "flooded", "traffic"
    location: Optional[Tuple[float, float]] = None
    severity: Optional[float] = None
    description: Optional[str] = None
```

### Database Models

**Location:** `app/database/models.py`

```python
class FloodDataCollection(Base):
    id: UUID
    collected_at: datetime
    data_source: str
    success: bool
    duration_seconds: float
    river_stations_count: int
    weather_data_available: bool

class RiverLevelRecord(Base):
    station_name: str
    water_level: float
    risk_level: str
    alert_level: float
    alarm_level: float
    critical_level: float

class WeatherDataRecord(Base):
    rainfall_1h: float
    rainfall_24h_forecast: float
    intensity: str
    temperature: float
    humidity: float
```

### ACL Message Content Formats

**FloodAgent → HazardAgent:**
```python
{
    "info_type": "flood_data_batch",
    "data": {
        "Sto Nino": {
            "water_level_m": 12.5,
            "alert_level_m": 12.0,
            "alarm_level_m": 14.0,
            "critical_level_m": 15.0,
            "status": "alert",
            "risk_score": 0.5,
            "timestamp": "2026-02-02T10:30:00",
            "source": "PAGASA_API"
        }
    }
}
```

**ScoutAgent → HazardAgent:**
```python
{
    "info_type": "scout_report_batch",
    "data": {
        "reports": [
            {
                "location": "Tumana",
                "coordinates": {"lat": 14.6507, "lon": 121.1029},
                "severity": 0.7,
                "report_type": "flood",
                "confidence": 0.85,
                "timestamp": "2026-02-02T10:30:00",
                "source": "twitter",
                "text": "Baha sa Tumana! Hanggang tuhod na ang tubig."
            }
        ],
        "has_coordinates": true,
        "report_count": 1
    }
}
```

---

## 10. Key Algorithms

### Risk-Aware A* Pathfinding

**Location:** `app/algorithms/risk_aware_astar.py`

#### Haversine Distance (Heuristic)

```python
def haversine_distance(coord1, coord2) -> float:
    """
    Great circle distance between two points.

    Formula:
    a = sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlon/2)
    c = 2·asin(√a)
    d = R·c  (R = 6371000m)
    """
```

#### A* Weight Function

```python
def weight_function(u, v, edge_data):
    # For MultiDiGraph: find lowest-risk parallel edge
    best_risk = 1.0
    best_length = 1.0

    for key, data in graph[u][v].items():
        if data['risk_score'] < best_risk:
            best_risk = data['risk_score']
            best_length = data['length']

    # Block impassable roads
    if best_risk >= 0.9:
        return float('inf')

    # Combined cost: distance + risk penalty
    return best_length * distance_weight + best_length * best_risk * risk_weight
```

### Weighted Data Fusion

```python
# HazardAgent fusion weights
composite_risk = (
    flood_depth_risk * 0.50 +      # Official flood depth
    crowdsourced_risk * 0.30 +     # Scout reports
    historical_risk * 0.20          # Historical data
)
```

### Time-Based Risk Decay

```python
def apply_time_decay(base_value, age_minutes, decay_rate):
    """
    Exponential decay: value × e^(-rate × age)
    """
    return base_value * math.exp(-decay_rate * age_minutes)
```

### Spatial Risk Processing

```python
# Grid-based spatial index for O(1) edge lookups
def _get_grid_cell(self, lat: float, lon: float) -> Tuple[int, int]:
    grid_lat = int(lat / self.spatial_index_grid_size)
    grid_lon = int(lon / self.spatial_index_grid_size)
    return (grid_lat, grid_lon)

# Gaussian distance decay for risk spreading
def _gaussian_decay(distance_m, radius_m):
    sigma = radius_m / 3
    return math.exp(-(distance_m ** 2) / (2 * sigma ** 2))
```

---

## 11. Configuration Reference

### Environment Variables

```bash
# .env file
API_KEY=your-secure-api-key
OPENWEATHERMAP_API_KEY=your-owm-key
DATABASE_URL=postgresql://user:pass@localhost:5432/masfro
ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.com
```

### YAML Configuration

**Location:** `config/agents.yaml`

```yaml
hazard:
  # Spatial risk processing
  risk_radius_m: 500          # Max distance for risk spreading
  enable_spatial_filtering: true
  decay_function: "gaussian"  # gaussian, linear, exponential
  grid_size_degrees: 0.001    # ~111m grid cells

  # Time decay
  scout_decay_rate_fast: 0.10  # 10%/min (rain flooding)
  scout_decay_rate_slow: 0.03  # 3%/min (river flooding)
  flood_decay_rate: 0.05       # 5%/min (official data)

  # TTL
  scout_report_ttl_minutes: 45
  flood_data_ttl_minutes: 90

routing:
  risk_penalty_safest: 100000
  risk_penalty_balanced: 2000
  risk_penalty_fastest: 0
  max_risk_threshold: 0.9

scheduler:
  interval_seconds: 300  # 5 minutes
```

### Configurable Parameters per Agent

| Agent | Parameter | Default | Description |
|-------|-----------|---------|-------------|
| FloodAgent | `data_update_interval` | 300s | Data fetch interval |
| ScoutAgent | `simulation_batch_size` | 10 | Tweets per step |
| HazardAgent | `environmental_risk_radius_m` | 500m | Risk spreading radius |
| HazardAgent | `MAX_SCOUT_CACHE_SIZE` | 1000 | LRU cache limit |
| RoutingAgent | `risk_penalty` | 2000 | Virtual meters/risk |
| EvacManager | `max_history_size` | 1000 | Route history limit |

---

## 12. Development Guide

### Directory Structure

```
masfro-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── flood_agent.py
│   │   ├── scout_agent.py
│   │   ├── hazard_agent.py
│   │   ├── routing_agent.py
│   │   └── evacuation_manager_agent.py
│   ├── algorithms/
│   │   ├── risk_aware_astar.py
│   │   └── path_optimizer.py
│   ├── api/
│   │   ├── graph_routes.py
│   │   └── evacuation_routes.py
│   ├── communication/
│   │   ├── acl_protocol.py
│   │   └── message_queue.py
│   ├── core/
│   │   ├── config.py
│   │   ├── auth.py
│   │   ├── logging_config.py
│   │   ├── agent_config.py
│   │   ├── pagination.py
│   │   └── validation.py
│   ├── data/
│   │   ├── evacuation_centers.csv
│   │   ├── geotiff_data/
│   │   ├── synthetic/
│   │   └── simulation_scenarios/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── repository.py
│   ├── environment/
│   │   ├── graph_manager.py
│   │   └── risk_calculator.py
│   ├── ml_models/
│   │   ├── nlp_processor.py
│   │   └── location_geocoder.py
│   └── services/
│       ├── river_scraper_service.py
│       ├── dam_water_scraper_service.py
│       ├── weather_service.py
│       ├── geotiff_service.py
│       ├── evacuation_service.py
│       ├── flood_data_scheduler.py
│       └── simulation_manager.py
├── config/
│   └── agents.yaml
├── data/
│   └── marikina_graph.graphml
├── logs/
├── tests/
├── scripts/
│   └── generate_scout_synthetic_data.py
├── .env
├── pyproject.toml
└── requirements.txt
```

### Setup Instructions

```bash
# 1. Install uv package manager
pip install uv -g

# 2. Create virtual environment and install dependencies
uv sync

# 3. Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Initialize database
python -c "from app.database import init_db; init_db()"

# 6. Download map data (if not present)
python scripts/download_map.py

# 7. Run development server
uvicorn app.main:app --reload
```

### Testing Guidelines

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_routing_agent.py

# Run with verbose output
pytest -v
```

### Key Testing Areas

1. **Agent Unit Tests**
   - Message processing
   - Risk calculation accuracy
   - Cache management

2. **Integration Tests**
   - Agent communication flow
   - API endpoint responses
   - Database operations

3. **Performance Tests**
   - A* pathfinding with 40k+ nodes
   - Batch graph updates
   - WebSocket broadcast latency

---

## Appendix: Quick Reference Cards

### Risk Score Interpretation

| Score | Category | Description | Action |
|-------|----------|-------------|--------|
| 0.0-0.2 | Safe | No flooding | Normal travel |
| 0.2-0.4 | Low | Minor water | Proceed with caution |
| 0.4-0.6 | Moderate | Significant water | Use alternative route |
| 0.6-0.8 | High | Dangerous | Avoid if possible |
| 0.8-1.0 | Critical | Impassable | Do not attempt |

### GeoTIFF Scenario Matrix

| Mode | Return Period | Time Steps | Description |
|------|--------------|------------|-------------|
| Light | rr01 (2-year) | 1-18 | Minor flooding |
| Medium | rr02 (5-year) | 1-18 | Moderate flooding |
| Heavy | rr04 (25-year) | 1-18 | Severe flooding |

### Agent Message Flow Summary

```
FloodAgent ──INFORM[flood_data_batch]──► HazardAgent
ScoutAgent ──INFORM[scout_report_batch]──► HazardAgent
EvacManager ──INFORM[user_feedback]──► HazardAgent
HazardAgent ──────► Graph Update ──────► WebSocket Broadcast
```

---

## 13. Qwen 3 LLM Integration

> **Upgrade Path:** Integrating Qwen 3 (Text) and Qwen 3-VL (Vision) models to enhance semantic understanding and enable multimodal flood detection.

### 13.1 Architecture Update: LLM Service Sidecar

The architecture is modular (FastAPI + Microservices pattern), making it easy to "plug in" Qwen 3 and Qwen 3-VL as intelligent processing services without rewriting core logic.

**Key Principle:** We do not embed LLM code directly into every agent. Instead, we create a **centralized LLMService** that any agent can call.

#### Updated Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI APPLICATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                   │
│  │  FloodAgent   │  │  ScoutAgent   │  │ EvacManager   │                   │
│  │  + Qwen 3     │  │  + Qwen 3     │  │               │                   │
│  │  (Text Parse) │  │  + Qwen 3-VL  │  │               │                   │
│  └───────┬───────┘  └───────┬───────┘  └───────────────┘                   │
│          │                  │                                               │
│          └────────┬─────────┘                                               │
│                   ▼                                                         │
│           ┌───────────────┐                                                 │
│           │  LLM Service  │◄──────── Ollama API (localhost:11434)          │
│           │  (Centralized)│                                                 │
│           └───────────────┘                                                 │
│                   │                                                         │
│          ┌────────┴────────┐                                                │
│          ▼                 ▼                                                │
│    ┌───────────┐    ┌───────────┐                                           │
│    │  Qwen 3   │    │ Qwen 3-VL │                                           │
│    │  (Text)   │    │ (Vision)  │                                           │
│    └───────────┘    └───────────┘                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 13.2 LLM Service Implementation

**Location:** `app/services/llm_service.py`

```python
# app/services/llm_service.py
import ollama
import json
from typing import Dict, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """
    Centralized LLM service for Qwen 3 text and vision models.

    Wraps the Ollama API for structured flood data extraction.
    """

    def __init__(self):
        self.text_model = settings.LLM_TEXT_MODEL  # "qwen3"
        self.vision_model = settings.LLM_VISION_MODEL  # "qwen3-vl"
        self.base_url = settings.OLLAMA_BASE_URL
        logger.info(f"LLMService initialized: text={self.text_model}, vision={self.vision_model}")

    def analyze_text_report(self, text: str) -> Dict:
        """
        Uses Qwen 3 to extract structured data from unstructured flood reports.

        Args:
            text: Raw flood report text (tweet, advisory, etc.)

        Returns:
            Dict with extracted fields:
            {
                "location": str,      # Landmark or street name
                "severity": float,    # 0.0 to 1.0
                "is_flood_related": bool,
                "description": str    # Summary
            }
        """
        prompt = f"""
        Analyze this flood report and extract JSON:
        {{
            "location": "string (landmark or street in Marikina)",
            "severity": float (0.0 to 1.0, where 1.0 is life-threatening),
            "is_flood_related": boolean,
            "description": "brief summary"
        }}

        Report: "{text}"

        Return ONLY valid JSON, no explanation.
        """

        try:
            response = ollama.chat(
                model=self.text_model,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return self._clean_json(response['message']['content'])
        except Exception as e:
            logger.error(f"LLM text analysis failed: {e}")
            return {}

    def analyze_flood_image(self, image_path: str) -> Dict:
        """
        Uses Qwen 3-VL to estimate flood depth from an image.

        Args:
            image_path: Path to flood image file

        Returns:
            Dict with visual analysis:
            {
                "estimated_depth_m": float,
                "risk_score": float,
                "vehicles_passable": List[str],
                "visual_indicators": str
            }
        """
        prompt = """
        Analyze this flood image. Estimate flood depth in meters and risk level.

        Return JSON:
        {
            "estimated_depth_m": float (water depth estimate),
            "risk_score": float (0.0 to 1.0),
            "vehicles_passable": ["car", "suv", "truck"] (list which can pass),
            "visual_indicators": "what you see that indicates flood severity"
        }

        Return ONLY valid JSON.
        """

        try:
            response = ollama.chat(
                model=self.vision_model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_path]
                }]
            )
            return self._clean_json(response['message']['content'])
        except Exception as e:
            logger.error(f"LLM vision analysis failed: {e}")
            return {}

    def _clean_json(self, content: str) -> Dict:
        """
        Helper to strip markdown code blocks if Qwen adds them.

        Args:
            content: Raw LLM response

        Returns:
            Parsed JSON dict or empty dict on failure
        """
        # Remove markdown code blocks
        content = content.replace("```json", "").replace("```", "").strip()

        # Try to find JSON in the response
        try:
            # Find first { and last }
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed: {e}, content: {content[:100]}")

        return {}


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
```

### 13.3 ScoutAgent Upgrade (The "Eyes")

**Location:** `app/agents/scout_agent.py`

The ScoutAgent is upgraded to use LLMService for both text nuance understanding and image analysis. This replaces keyword-based NLP with semantic understanding.

#### Key Changes

```python
# app/agents/scout_agent.py

from app.services.llm_service import get_llm_service

class ScoutAgent(BaseAgent):
    def __init__(self, agent_id, environment, message_queue, ...):
        super().__init__(agent_id, environment)

        # Initialize LLM Service for Qwen integration
        try:
            self.llm_service = get_llm_service()
            self.use_llm = True
            self.logger.info(f"{self.agent_id} LLM Service initialized (Qwen 3 + Qwen 3-VL)")
        except Exception as e:
            self.llm_service = None
            self.use_llm = False
            self.logger.warning(f"{self.agent_id} LLM Service unavailable: {e}")

    def _process_and_forward_tweets(self, tweets: list) -> None:
        """
        Process tweets using Qwen 3 (text) and Qwen 3-VL (vision).

        Processing Pipeline:
        1. Visual Analysis (if image present) - Qwen 3-VL
        2. Text Analysis - Qwen 3
        3. Fusion - Combine visual and text signals
        4. Forward to HazardAgent
        """
        processed_reports = []

        for tweet in tweets:
            report_data = {
                'visual_evidence': False,
                'confidence': 0.5  # Default confidence
            }

            # ========== 1. VISUAL ANALYSIS (Qwen 3-VL) ==========
            if tweet.get('image_path') and self.llm_service:
                visual_analysis = self.llm_service.analyze_flood_image(
                    tweet['image_path']
                )

                if visual_analysis:
                    report_data.update({
                        'estimated_depth_m': visual_analysis.get('estimated_depth_m'),
                        'risk_score': visual_analysis.get('risk_score', 0),
                        'vehicles_passable': visual_analysis.get('vehicles_passable', []),
                        'visual_evidence': True
                    })

                    # Visual evidence with high risk = high confidence
                    if visual_analysis.get('risk_score', 0) > 0.5:
                        report_data['confidence'] = 0.9
                        self.logger.info(
                            f"[Qwen-VL] High-risk visual detected: "
                            f"depth={visual_analysis.get('estimated_depth_m')}m, "
                            f"risk={visual_analysis.get('risk_score')}"
                        )

            # ========== 2. TEXT ANALYSIS (Qwen 3) ==========
            text_analysis = {}
            if self.llm_service:
                text_analysis = self.llm_service.analyze_text_report(tweet['text'])
            elif self.nlp_processor:
                # Fallback to original NLP if LLM unavailable
                text_analysis = self.nlp_processor.extract_flood_info(tweet['text'])

            # ========== 3. FUSION LOGIC ==========
            # Take maximum risk from visual and text analysis
            visual_risk = report_data.get('risk_score', 0)
            text_risk = text_analysis.get('severity', 0)
            final_risk = max(visual_risk, text_risk)

            # Skip non-flood reports
            if not text_analysis.get('is_flood_related', False) and not report_data.get('visual_evidence'):
                continue

            # Build final payload
            payload = {
                "location": text_analysis.get('location') or tweet.get('location'),
                "severity": final_risk,
                "risk_score": final_risk,
                "report_type": "flood" if final_risk > 0.3 else "observation",
                "confidence": report_data.get('confidence', 0.5),
                "visual_evidence": report_data.get('visual_evidence', False),
                "estimated_depth_m": report_data.get('estimated_depth_m'),
                "vehicles_passable": report_data.get('vehicles_passable'),
                "timestamp": tweet.get('timestamp'),
                "source": "scout_agent_qwen_enhanced",
                "text": tweet['text']
            }

            # Geocode if we have location but no coordinates
            if payload['location'] and self.geocoder:
                coords = self.geocoder.geocode_location(payload['location'])
                if coords:
                    payload['coordinates'] = coords

            processed_reports.append(payload)

            self.logger.info(
                f"[Qwen] Processed: location={payload['location']}, "
                f"risk={final_risk:.2f}, visual={payload['visual_evidence']}"
            )

        # ========== 4. FORWARD TO HAZARD AGENT ==========
        if processed_reports:
            message = ACLMessage(
                performative=Performative.INFORM,
                sender=self.agent_id,
                receiver=self.hazard_agent_id,
                content={
                    "info_type": "scout_report_batch",
                    "data": {
                        "reports": processed_reports,
                        "has_coordinates": any(r.get('coordinates') for r in processed_reports),
                        "has_visual_evidence": any(r.get('visual_evidence') for r in processed_reports),
                        "report_count": len(processed_reports)
                    }
                }
            )
            self.message_queue.send_message(message)

            self.logger.info(
                f"{self.agent_id} forwarded {len(processed_reports)} Qwen-enhanced reports "
                f"({sum(1 for r in processed_reports if r.get('visual_evidence'))} with visual evidence)"
            )
```

### 13.4 FloodAgent Upgrade (The "Reader")

**Location:** `app/agents/flood_agent.py`

Sometimes PAGASA releases text advisories (Facebook posts, PDF bulletins) before the API updates. Qwen 3 can read and parse these unstructured advisories.

#### Key Additions

```python
# app/agents/flood_agent.py

from app.services.llm_service import get_llm_service

class FloodAgent(BaseAgent):
    def __init__(self, agent_id, environment, ...):
        super().__init__(agent_id, environment)

        # Initialize LLM Service for text advisory parsing
        try:
            self.llm_service = get_llm_service()
            self.logger.info(f"{self.agent_id} LLM Service initialized for advisory parsing")
        except Exception as e:
            self.llm_service = None
            self.logger.warning(f"{self.agent_id} LLM Service unavailable: {e}")

    def parse_text_advisory(self, advisory_text: str) -> Dict[str, Any]:
        """
        Parse raw text advisories using Qwen 3.

        Use this when scraping:
        - PAGASA Facebook page updates
        - PDF bulletins (converted to text)
        - News articles about flooding

        Args:
            advisory_text: Raw advisory text

        Returns:
            Parsed flood data in standard format
        """
        if not self.llm_service:
            self.logger.warning("LLM Service unavailable for advisory parsing")
            return {}

        self.logger.info(f"{self.agent_id} parsing text advisory via Qwen 3")

        # Use Qwen 3 to extract structured data
        analysis = self.llm_service.analyze_text_report(advisory_text)

        if not analysis.get('is_flood_related'):
            self.logger.debug("Advisory not flood-related, skipping")
            return {}

        # Convert LLM output to standard FloodAgent data format
        location = analysis.get('location', 'Unknown')
        severity = analysis.get('severity', 0.5)

        # Map severity to status
        if severity >= 0.8:
            status = "critical"
        elif severity >= 0.6:
            status = "alarm"
        elif severity >= 0.4:
            status = "alert"
        else:
            status = "watch"

        data = {
            location: {
                "water_level_m": -1.0,  # Unknown exact number from text
                "status": status,
                "risk_score": severity,
                "source": "PAGASA_TEXT_ADVISORY",
                "description": analysis.get('description', ''),
                "timestamp": datetime.now(),
                "parsed_by": "qwen3"
            }
        }

        self.logger.info(
            f"[Qwen 3] Parsed advisory: location={location}, "
            f"status={status}, severity={severity:.2f}"
        )

        # Forward to HazardAgent
        self.send_flood_data_via_message(data)

        return data

    def collect_and_parse_advisories(self, advisory_urls: List[str]) -> Dict[str, Any]:
        """
        Collect and parse multiple text advisories.

        Args:
            advisory_urls: List of URLs to advisory pages

        Returns:
            Combined parsed data
        """
        all_data = {}

        for url in advisory_urls:
            try:
                # Fetch advisory text (implementation depends on source)
                advisory_text = self._fetch_advisory_text(url)
                if advisory_text:
                    parsed = self.parse_text_advisory(advisory_text)
                    all_data.update(parsed)
            except Exception as e:
                self.logger.error(f"Failed to parse advisory from {url}: {e}")

        return all_data
```

### 13.5 HazardAgent Upgrade (The "Judge")

**Location:** `app/agents/hazard_agent.py`

This is where the **Agentic Workflow** happens. When FloodAgent (official sensors) says SAFE, but ScoutAgent (Qwen-VL visual evidence) says DANGER, HazardAgent must decide. Visual evidence with high confidence overrides sensor lag.

#### Key Additions

```python
# app/agents/hazard_agent.py

class HazardAgent(BaseAgent):

    def update_risk(self, flood_data, scout_data, time_step) -> Dict[str, Any]:
        """
        Main risk update method with Visual Confirmation Override.

        Priority Logic:
        1. Visual evidence (Qwen 3-VL) with high confidence = IMMEDIATE UPDATE
        2. Official sensor data = STANDARD UPDATE
        3. Text-only scout reports = WEIGHTED UPDATE
        """

        edges_updated = 0
        visual_overrides = 0

        # ... existing GeoTIFF and flood data processing ...

        # ========== VISUAL CONFIRMATION OVERRIDE ==========
        # If a scout report has visual evidence (analyzed by Qwen-VL)
        # and high confidence, it overrides official sensor lag.

        for report in scout_data:
            if report.get('visual_evidence') and report.get('risk_score', 0) > 0.8:
                # HIGH PRIORITY: Visual evidence shows danger
                location = report.get('location')
                coordinates = report.get('coordinates')

                if coordinates:
                    # Direct coordinate-based update
                    lat, lon = coordinates.get('lat'), coordinates.get('lon')
                    affected_edges = self._get_edges_in_radius(lat, lon, radius_m=300)

                    for u, v, key in affected_edges:
                        # FORCE UPDATE - Mark as high risk or impassable
                        risk_score = min(report['risk_score'] + 0.1, 1.0)
                        self.environment.update_edge_risk(u, v, key, risk_score)
                        edges_updated += 1

                    visual_overrides += 1
                    self.logger.warning(
                        f"VISUAL OVERRIDE: {location} - Risk={report['risk_score']:.2f}, "
                        f"Depth={report.get('estimated_depth_m', 'unknown')}m, "
                        f"Affected edges: {len(affected_edges)}"
                    )

                elif location:
                    # Geocode and update
                    edge = self._map_location_to_edge(location)
                    if edge:
                        u, v, key = edge
                        self.environment.update_edge_risk(u, v, key, 1.0)  # Mark impassable
                        edges_updated += 1
                        visual_overrides += 1
                        self.logger.warning(
                            f"VISUAL OVERRIDE: Blocked road at {location}"
                        )

        # ... rest of fusion logic (text-only reports with lower priority) ...

        return {
            "edges_updated": edges_updated,
            "visual_overrides": visual_overrides,
            "time_step": time_step,
            "risk_trend": self._calculate_risk_trend()
        }

    def _process_scout_with_visual_priority(self, reports: List[Dict]) -> Dict[str, int]:
        """
        Process scout reports with visual evidence given higher priority.

        Visual Evidence Priority:
        - visual_evidence=True, risk>0.8: Immediate graph update (override sensors)
        - visual_evidence=True, risk<0.8: High-weight fusion
        - visual_evidence=False: Standard weighted fusion
        """
        results = {"processed": 0, "visual_overrides": 0, "text_updates": 0}

        # Sort by visual evidence and risk (highest priority first)
        sorted_reports = sorted(
            reports,
            key=lambda r: (r.get('visual_evidence', False), r.get('risk_score', 0)),
            reverse=True
        )

        for report in sorted_reports:
            has_visual = report.get('visual_evidence', False)
            risk_score = report.get('risk_score', 0)

            if has_visual and risk_score > 0.8:
                # VISUAL OVERRIDE - Trust the image
                weight = 1.0  # Full weight
                results["visual_overrides"] += 1
            elif has_visual:
                # Visual but lower risk - still prioritize
                weight = 0.8
            else:
                # Text only - standard weight
                weight = self.risk_weights.get("crowdsourced", 0.3)
                results["text_updates"] += 1

            # Apply weighted update
            # ... edge update logic with weight ...

            results["processed"] += 1

        return results
```

### 13.6 Configuration Updates

**Location:** `app/core/config.py`

Add settings for the local Ollama instance and model configuration.

```python
# app/core/config.py

class Settings(BaseSettings):
    # ... existing settings ...

    # === Qwen 3 LLM Configuration ===
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_TEXT_MODEL: str = "qwen3"
    LLM_VISION_MODEL: str = "qwen3-vl"
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_ENABLED: bool = True

    class Config:
        env_file = ".env"
```

**Environment Variables:**

```bash
# .env additions for Qwen 3
OLLAMA_BASE_URL=http://localhost:11434
LLM_TEXT_MODEL=qwen3
LLM_VISION_MODEL=qwen3-vl
LLM_ENABLED=true
```

### 13.7 Setup Instructions

#### Prerequisites

1. **Install Ollama:**
   ```bash
   # macOS/Linux
   curl -fsSL https://ollama.ai/install.sh | sh

   # Windows: Download from https://ollama.ai/download
   ```

2. **Pull Qwen 3 Models:**
   ```bash
   # Text model
   ollama pull qwen3

   # Vision model (requires GPU for best performance)
   ollama pull qwen3-vl
   ```

3. **Verify Installation:**
   ```bash
   # Test text model
   ollama run qwen3 "Hello, what is flood depth?"

   # Test vision model
   ollama run qwen3-vl "Describe this image" --image /path/to/test.jpg
   ```

#### Integration Testing

```python
# Test LLM Service
from app.services.llm_service import get_llm_service

llm = get_llm_service()

# Test text analysis
result = llm.analyze_text_report("Baha sa Tumana! Hanggang tuhod na ang tubig!")
print(result)
# Expected: {"location": "Tumana", "severity": 0.6, "is_flood_related": true, ...}

# Test image analysis
result = llm.analyze_flood_image("/path/to/flood_image.jpg")
print(result)
# Expected: {"estimated_depth_m": 0.5, "risk_score": 0.7, "vehicles_passable": ["suv", "truck"], ...}
```

### 13.8 Impact Summary

| Aspect | Before (NLP) | After (Qwen 3) |
|--------|--------------|----------------|
| **Text Understanding** | Keyword matching | Semantic understanding |
| **Image Analysis** | Not supported | Flood depth estimation from photos |
| **Advisory Parsing** | Manual or regex | Natural language understanding |
| **Confidence** | Fixed weights | Context-aware confidence |
| **Sensor Lag** | Dependent on API | Can read text advisories early |
| **Resilience** | API-dependent | Multimodal fallback |

### 13.9 Thesis Innovation Points

1. **Semantic Understanding:** Move from keyword matching to true language understanding with Qwen 3.

2. **Multimodality:** Process images as data points - a major upgrade for flood monitoring systems.

3. **Resilience:** If API sensors fail, agents can "read" text advisories and "see" photos to keep the graph updated.

4. **Agentic Workflow:** HazardAgent makes intelligent decisions when official sensors conflict with visual evidence.

5. **Local Processing:** Ollama runs locally, ensuring data privacy and low latency for real-time decisions.

---

*This documentation was generated for MAS-FRO Backend v1.0.0*
