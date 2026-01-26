# Data Collection Documentation

**Project:** MAS-FRO (Multi-Agent System for Flood Route Optimization)
**Last Updated:** November 5, 2025
**Version:** 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Sources](#data-sources)
4. [Data Collection Process](#data-collection-process)
5. [Data Formats](#data-formats)
6. [Configuration](#configuration)
7. [Usage Examples](#usage-examples)
8. [Integration with Agents](#integration-with-agents)
9. [Troubleshooting](#troubleshooting)
10. [Future Enhancements](#future-enhancements)

---

## Overview

The MAS-FRO data collection system gathers flood-related information from multiple sources to enable real-time flood risk assessment and safe route planning. The system is designed to be modular, extensible, and resilient to data source failures.

### Key Features

- **Multi-source data collection**: PAGASA, NOAH, MMDA, and simulated data
- **Modular architecture**: Enable/disable sources independently
- **Unified interface**: Standardized data format across all sources
- **Graceful degradation**: System continues operating if sources are unavailable
- **Real-time updates**: Designed for periodic data polling
- **Extensible design**: Easy to add new data sources

### Data Collection Goals

1. **Rainfall monitoring**: Track current and historical rainfall measurements
2. **River level monitoring**: Monitor Marikina River water levels
3. **Flood depth tracking**: Real-time flood depth at key locations
4. **Hazard assessment**: Integrate flood hazard maps and predictions
5. **Crowdsourced reports**: Incorporate citizen-reported flood conditions

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   External Data Sources                      │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   PAGASA     │    NOAH      │    MMDA      │   Simulated    │
│  (Weather)   │  (Hazards)   │  (Reports)   │   (Testing)    │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬─────────┘
       │              │              │              │
       └──────────────┼──────────────┼──────────────┘
                      ▼
       ┌──────────────────────────────────────────┐
       │         DataCollector                     │
       │  (app/services/data_sources.py)          │
       │                                           │
       │  • collect_flood_data()                  │
       │  • get_summary()                         │
       │  • Source management                     │
       └──────────────────┬───────────────────────┘
                          ▼
       ┌──────────────────────────────────────────┐
       │          FloodAgent                       │
       │  (app/agents/flood_agent.py)             │
       │                                           │
       │  • collect_and_forward_data()            │
       │  • _process_collected_data()             │
       │  • fetch_rainfall_data()                 │
       │  • fetch_river_levels()                  │
       │  • fetch_flood_depths()                  │
       └──────────────────┬───────────────────────┘
                          ▼
       ┌──────────────────────────────────────────┐
       │         HazardAgent                       │
       │  (app/agents/hazard_agent.py)            │
       │                                           │
       │  • process_flood_data()                  │
       │  • assess_risk()                         │
       │  • update_graph_risks()                  │
       └──────────────────┬───────────────────────┘
                          ▼
       ┌──────────────────────────────────────────┐
       │    DynamicGraphEnvironment               │
       │  (app/environment/graph_manager.py)      │
       │                                           │
       │  • update_edge_risk()                    │
       │  • Road network with risk scores         │
       └──────────────────────────────────────────┘
```

### Component Responsibilities

**DataCollector** (`app/services/data_sources.py`)
- Manages all data source connections
- Coordinates data collection from multiple sources
- Standardizes data formats
- Handles source failures gracefully

**FloodAgent** (`app/agents/flood_agent.py`)
- Initiates data collection on schedule
- Processes raw data into actionable information
- Forwards data to HazardAgent
- Maintains data caches

**HazardAgent** (`app/agents/hazard_agent.py`)
- Receives flood data from FloodAgent
- Assesses flood risk levels
- Updates road network with risk scores
- Triggers alerts for high-risk conditions

---

## Data Sources

### 1. PAGASA (Philippine Atmospheric, Geophysical and Astronomical Services Administration)

**Purpose:** Official weather and rainfall data

**Status:** ⏳ Awaiting API access

**Data Provided:**
- Rainfall measurements (mm/hour)
- Weather station data
- Weather forecasts
- Rain gauge readings

**Implementation:**
```python
class PAGASADataSource:
    def __init__(self):
        self.panahon_url = "https://www.panahon.gov.ph"
        self.session = requests.Session()

    def get_rainfall_data(self, station: str = "Marikina") -> Optional[Dict[str, Any]]:
        """
        Get rainfall data for specified station.

        Returns:
            {
                "station": "Marikina",
                "timestamp": "2025-11-05T12:00:00",
                "rainfall_mm": 15.5,
                "source": "PAGASA",
                "available": True/False
            }
        """
```

**API Access:**
- **Required:** Formal request to PAGASA
- **Contact:** cadpagasa@gmail.com
- **Process:** Submit project details and data usage plan
- **Timeline:** 2-4 weeks for approval

**How to Enable:**
```python
collector = DataCollector(enable_pagasa=True)
```

---

### 2. NOAH (Nationwide Operational Assessment of Hazards)

**Purpose:** Flood hazard maps and historical data

**Status:** ⏳ Awaiting data access

**Data Provided:**
- Flood hazard level maps
- Historical flood events
- River basin data
- Terrain elevation

**Implementation:**
```python
class NOAHDataSource:
    def __init__(self):
        self.noah_url = "https://noah.up.edu.ph"

    def get_flood_hazard_data(self, location: str = "Marikina") -> Optional[Dict[str, Any]]:
        """
        Get flood hazard map data for location.

        Returns:
            {
                "location": "Marikina",
                "timestamp": "2025-11-05T12:00:00",
                "hazard_level": "moderate" | "high" | "extreme",
                "source": "NOAH",
                "available": True/False
            }
        """
```

**Background:**
- Project NOAH real-time sensors discontinued in 2017
- UP NOAH Center maintains historical flood hazard maps
- Alternative: Crowdsourced data via UP NOAH website

**API Access:**
- **Required:** Contact UP NOAH Center
- **Contact:** UP NOAH Center for current data access methods
- **Timeline:** Variable

**How to Enable:**
```python
collector = DataCollector(enable_noah=True)
```

---

### 3. MMDA (Metropolitan Manila Development Authority)

**Purpose:** Real-time flood reports and traffic advisories

**Status:** ⏳ Awaiting Twitter API setup

**Data Provided:**
- Real-time flood depths
- Road closures
- Traffic advisories
- Emergency alerts

**Implementation:**
```python
class MMDADataSource:
    def __init__(self):
        self.twitter_handle = "@MMDA"

    def get_flood_reports(self, area: str = "Marikina") -> Optional[List[Dict[str, Any]]]:
        """
        Get flood reports for specified area.

        Returns:
            [
                {
                    "area": "Marikina",
                    "timestamp": "2025-11-05T12:00:00",
                    "flood_level": 0.5,  # meters
                    "status": "passable" | "impassable",
                    "source": "MMDA"
                }
            ]
        """
```

**Data Sources:**
- **Primary:** Twitter updates via @MMDA
- **Secondary:** MMDA website scraping
- **Update Frequency:** Real-time (as events occur)

**API Access:**
- **Required:** Twitter Developer account
- **Process:** Apply at https://developer.twitter.com
- **Cost:** Free tier available
- **Timeline:** 1-2 weeks for approval

**How to Enable:**
```python
collector = DataCollector(enable_mmda=True)
```

---

### 4. SimulatedDataSource (Testing & Development)

**Purpose:** Realistic test data for development

**Status:** ✅ Fully operational

**Data Provided:**
- Simulated rainfall (light, moderate, heavy, extreme)
- Simulated flood depths based on rainfall
- Risk level calculations
- Realistic timestamps

**Implementation:**
```python
class SimulatedDataSource:
    def get_simulated_rainfall(
        self,
        location: str = "Marikina",
        intensity: str = "moderate"
    ) -> Dict[str, Any]:
        """
        Generate simulated rainfall data.

        Args:
            location: Location name
            intensity: "light" | "moderate" | "heavy" | "extreme"

        Returns:
            {
                "location": "Marikina",
                "timestamp": "2025-11-05T12:00:00",
                "rainfall_mm": 15.5,
                "intensity": "moderate",
                "source": "simulated"
            }
        """
```

**Rainfall Intensity Mapping:**
- **Light:** 1-5 mm/hr
- **Moderate:** 5-15 mm/hr
- **Heavy:** 15-30 mm/hr
- **Extreme:** 30-50 mm/hr

**Flood Depth Calculation:**
```python
# Simple correlation model
flood_depth_cm = max(0, (rainfall_mm - 10) * 2)

# Risk levels
if flood_depth_cm > 50: risk = "extreme"
elif flood_depth_cm > 30: risk = "high"
elif flood_depth_cm > 15: risk = "moderate"
else: risk = "low"
```

**How to Enable:**
```python
collector = DataCollector(use_simulated=True)  # Default
```

---

## Data Collection Process

### Step 1: Initialization

When FloodAgent is created, it initializes the DataCollector with desired sources:

```python
# In FloodAgent.__init__()
self.data_collector = DataCollector(
    use_simulated=True,   # Enable simulated data
    enable_pagasa=False,  # Enable when API ready
    enable_noah=False,    # Enable when API ready
    enable_mmda=False     # Enable when API ready
)
```

### Step 2: Scheduled Collection

FloodAgent checks if it's time to update data:

```python
def step(self):
    """Called periodically by the multi-agent system."""
    if self._should_update():
        self.collect_and_forward_data()

def _should_update(self) -> bool:
    """Check if update interval has elapsed."""
    if self.last_update is None:
        return True
    elapsed = (datetime.now() - self.last_update).total_seconds()
    return elapsed >= self.data_update_interval  # Default: 300s (5 min)
```

### Step 3: Data Collection

FloodAgent triggers data collection from all sources:

```python
def collect_and_forward_data(self) -> Dict[str, Any]:
    """Collect data from all enabled sources."""

    # Use DataCollector to gather data
    collected_data = self.data_collector.collect_flood_data(
        location="Marikina",
        coordinates=(14.6507, 121.1029)  # Marikina City Hall
    )

    # Process raw data
    combined_data = self._process_collected_data(collected_data)

    # Forward to HazardAgent
    self.send_to_hazard_agent(combined_data)

    return combined_data
```

### Step 4: Data Processing

Raw data from multiple sources is standardized:

```python
def _process_collected_data(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process collected data into standardized format.

    Input (from DataCollector):
        {
            "location": "Marikina",
            "coordinates": (14.6507, 121.1029),
            "timestamp": "2025-11-05T12:00:00",
            "sources": {
                "simulated": {
                    "rainfall": {...},
                    "flood_depth": {...}
                },
                "pagasa": {...},
                "noah": {...},
                "mmda": {...}
            }
        }

    Output (for HazardAgent):
        {
            "Marikina": {
                "rainfall_1h": 15.5,
                "rainfall_24h": 372.0,
                "flood_depth": 0.25,
                "risk_level": "moderate",
                "timestamp": "2025-11-05T12:00:00"
            }
        }
    """
```

### Step 5: Data Forwarding

Processed data is sent to HazardAgent:

```python
def send_to_hazard_agent(self, data: Dict[str, Any]) -> None:
    """Forward collected data to HazardAgent."""

    if not self.hazard_agent:
        logger.warning("No HazardAgent reference, data not forwarded")
        return

    for location, location_data in data.items():
        flood_data = {
            "location": location,
            "flood_depth": location_data.get("flood_depth", 0.0),
            "rainfall_1h": location_data.get("rainfall_1h", 0.0),
            "rainfall_24h": location_data.get("rainfall_24h", 0.0),
            "timestamp": location_data.get("timestamp")
        }
        self.hazard_agent.process_flood_data(flood_data)
```

### Step 6: Risk Assessment

HazardAgent processes the data and updates the road network:

```python
# In HazardAgent.process_flood_data()
def process_flood_data(self, flood_data: Dict[str, Any]) -> None:
    """
    Process incoming flood data and update risk scores.

    Args:
        flood_data: {
            "location": "Marikina",
            "flood_depth": 0.25,
            "rainfall_1h": 15.5,
            "rainfall_24h": 372.0
        }
    """
    # Calculate risk score
    risk_score = self.assess_risk(flood_data)

    # Update graph edges near this location
    self.environment.update_edge_risk(
        location=flood_data["location"],
        risk_score=risk_score
    )
```

---

## Data Formats

### DataCollector Output Format

```python
{
    "location": "Marikina",
    "coordinates": (14.6507, 121.1029),
    "timestamp": "2025-11-05T12:00:00",
    "sources": {
        "simulated": {
            "rainfall": {
                "location": "Marikina",
                "timestamp": "2025-11-05T12:00:00",
                "rainfall_mm": 15.5,
                "intensity": "moderate",
                "source": "simulated",
                "message": "Simulated moderate rainfall: 15.5mm/hr"
            },
            "flood_depth": {
                "coordinates": (14.6507, 121.1029),
                "timestamp": "2025-11-05T12:00:00",
                "flood_depth_cm": 25.0,
                "risk_level": "moderate",
                "source": "simulated",
                "based_on_rainfall": 15.5
            }
        },
        "pagasa": {
            "station": "Marikina",
            "timestamp": "2025-11-05T12:00:00",
            "rainfall_mm": null,
            "source": "PAGASA",
            "available": false,
            "message": "API access requires formal request to PAGASA"
        },
        "noah": {
            "location": "Marikina",
            "timestamp": "2025-11-05T12:00:00",
            "hazard_level": null,
            "source": "NOAH",
            "available": false,
            "message": "Real-time sensor network no longer fully operational"
        },
        "mmda": [
            {
                "area": "Marikina",
                "timestamp": "2025-11-05T12:00:00",
                "flood_level": null,
                "status": "No real-time data",
                "source": "MMDA",
                "message": "Real-time updates available via @MMDA Twitter"
            }
        ]
    }
}
```

### FloodAgent Processed Format

```python
{
    "Marikina": {
        "rainfall_1h": 15.5,        # mm in last hour
        "rainfall_24h": 372.0,       # mm in last 24 hours
        "flood_depth": 0.25,         # meters
        "risk_level": "moderate",    # low | moderate | high | extreme
        "timestamp": "2025-11-05T12:00:00"
    },
    "Marikina River_monitoring": {
        "water_level": 1.2,          # meters above normal
        "status": "alert",           # normal | alert | critical
        "timestamp": "2025-11-05T12:00:00"
    }
}
```

### HazardAgent Input Format

```python
{
    "location": "Marikina",
    "flood_depth": 0.25,             # meters
    "rainfall_1h": 15.5,             # mm/hour
    "rainfall_24h": 372.0,           # mm/day
    "timestamp": "2025-11-05T12:00:00"
}
```

---

## Configuration

### DataCollector Configuration

```python
from app.services.data_sources import DataCollector

# Option 1: Simulated data only (default)
collector = DataCollector(
    use_simulated=True,
    enable_pagasa=False,
    enable_noah=False,
    enable_mmda=False
)

# Option 2: Real data sources only
collector = DataCollector(
    use_simulated=False,
    enable_pagasa=True,   # Requires API credentials
    enable_noah=True,     # Requires data access
    enable_mmda=True      # Requires Twitter API
)

# Option 3: Hybrid (simulated + selective real sources)
collector = DataCollector(
    use_simulated=True,
    enable_pagasa=True,   # Use if available
    enable_noah=False,
    enable_mmda=False
)
```

### FloodAgent Configuration

```python
from app.agents.flood_agent import FloodAgent

# Basic configuration
flood_agent = FloodAgent(
    agent_id="flood_001",
    environment=env,
    hazard_agent=hazard_agent,
    use_simulated=True  # Use simulated data
)

# Advanced configuration (modify after initialization)
flood_agent.data_update_interval = 300  # Update every 5 minutes (default)
flood_agent.pagasa_api_url = "https://custom-api.pagasa.gov.ph"
flood_agent.river_sensor_url = "https://custom-noah.dost.gov.ph"
```

### Update Frequency

```python
# In FloodAgent.__init__()
self.data_update_interval = 300  # 5 minutes (default)

# Modify for different update frequencies
flood_agent.data_update_interval = 60   # 1 minute (high frequency)
flood_agent.data_update_interval = 600  # 10 minutes (low frequency)
```

---

## Usage Examples

### Example 1: Basic Data Collection

```python
from app.services.data_sources import DataCollector

# Initialize collector
collector = DataCollector(use_simulated=True)

# Collect data for Marikina
data = collector.collect_flood_data(
    location="Marikina City",
    coordinates=(14.6507, 121.1029)
)

# Get summary
summary = collector.get_summary(data)
print(f"Location: {summary['location']}")
print(f"Rainfall: {summary['rainfall_mm']} mm/hr")
print(f"Flood depth: {summary['flood_depth_cm']} cm")
print(f"Risk level: {summary['risk_level']}")
```

**Output:**
```
Location: Marikina City
Rainfall: 15.5 mm/hr
Flood depth: 25.0 cm
Risk level: moderate
```

### Example 2: FloodAgent Integration

```python
from app.agents.flood_agent import FloodAgent
from app.agents.hazard_agent import HazardAgent
from app.environment.graph_manager import DynamicGraphEnvironment

# Setup environment and agents
env = DynamicGraphEnvironment()
hazard_agent = HazardAgent("hazard_001", env)
flood_agent = FloodAgent(
    "flood_001",
    env,
    hazard_agent=hazard_agent,
    use_simulated=True
)

# Collect and forward data
data = flood_agent.collect_and_forward_data()

print(f"Collected data for {len(data)} locations")
for location, info in data.items():
    print(f"{location}: {info}")
```

**Output:**
```
Collected data for 1 locations
Marikina: {
    'rainfall_1h': 15.5,
    'rainfall_24h': 372.0,
    'flood_depth': 0.25,
    'risk_level': 'moderate',
    'timestamp': '2025-11-05T12:00:00'
}
```

### Example 3: Manual Data Fetching

```python
from app.agents.flood_agent import FloodAgent
from app.environment.graph_manager import DynamicGraphEnvironment

env = DynamicGraphEnvironment()
flood_agent = FloodAgent("flood_test", env, use_simulated=True)

# Fetch specific data types
rainfall = flood_agent.fetch_rainfall_data()
river_levels = flood_agent.fetch_river_levels()
flood_depths = flood_agent.fetch_flood_depths()

print(f"Rainfall data: {len(rainfall)} locations")
print(f"River levels: {len(river_levels)} rivers")
print(f"Flood depths: {len(flood_depths)} locations")
```

### Example 4: Custom Rainfall Intensity

```python
from app.services.data_sources import SimulatedDataSource

simulated = SimulatedDataSource()

# Light rainfall
light_rain = simulated.get_simulated_rainfall(
    location="Marikina",
    intensity="light"
)
print(f"Light rain: {light_rain['rainfall_mm']} mm/hr")

# Extreme rainfall
extreme_rain = simulated.get_simulated_rainfall(
    location="Marikina",
    intensity="extreme"
)
print(f"Extreme rain: {extreme_rain['rainfall_mm']} mm/hr")

# Calculate flood depth
flood = simulated.get_simulated_flood_depth(
    coordinates=(14.6507, 121.1029),
    rainfall_mm=extreme_rain['rainfall_mm']
)
print(f"Flood depth: {flood['flood_depth_cm']} cm")
print(f"Risk level: {flood['risk_level']}")
```

**Output:**
```
Light rain: 3.2 mm/hr
Extreme rain: 42.5 mm/hr
Flood depth: 65.0 cm
Risk level: extreme
```

### Example 5: Multi-Source Data Collection

```python
from app.services.data_sources import DataCollector

# Initialize with all sources enabled
collector = DataCollector(
    use_simulated=True,
    enable_pagasa=True,  # If API credentials available
    enable_noah=True,
    enable_mmda=True
)

# Collect data
data = collector.collect_flood_data("Marikina", (14.6507, 121.1029))

# Check which sources returned data
available_sources = list(data['sources'].keys())
print(f"Data collected from: {', '.join(available_sources)}")

# Process each source
for source_name, source_data in data['sources'].items():
    if source_name == "simulated":
        print(f"Simulated rainfall: {source_data['rainfall']['rainfall_mm']} mm/hr")
    elif source_name == "pagasa":
        if source_data.get('available'):
            print(f"PAGASA rainfall: {source_data['rainfall_mm']} mm")
    # ... handle other sources
```

---

## Integration with Agents

### FloodAgent → HazardAgent Flow

```python
# Step 1: FloodAgent collects data
flood_agent = FloodAgent("flood_001", env, hazard_agent, use_simulated=True)
data = flood_agent.collect_and_forward_data()

# Step 2: Data is processed internally
# _process_collected_data() standardizes the format

# Step 3: Data is forwarded to HazardAgent
# send_to_hazard_agent() sends each location's data

# Step 4: HazardAgent receives and processes
# hazard_agent.process_flood_data() is called for each location

# Step 5: HazardAgent updates the graph
# environment.update_edge_risk() applies risk scores to roads
```

### Complete Multi-Agent System

```python
from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.flood_agent import FloodAgent
from app.agents.hazard_agent import HazardAgent
from app.agents.routing_agent import RoutingAgent

# Initialize environment
env = DynamicGraphEnvironment()

# Create agents in dependency order
hazard_agent = HazardAgent("hazard_001", env)
flood_agent = FloodAgent(
    "flood_001",
    env,
    hazard_agent=hazard_agent,
    use_simulated=True
)
routing_agent = RoutingAgent("routing_001", env)

# Simulate one data collection cycle
print("Step 1: FloodAgent collects data")
data = flood_agent.collect_and_forward_data()

print("Step 2: HazardAgent processes data (automatic)")
# Data was forwarded in step 1

print("Step 3: Calculate route with updated risks")
route = routing_agent.calculate_route(
    start=(14.6507, 121.1029),  # Marikina City Hall
    end=(14.6324, 121.1084)     # SM City Marikina
)

print(f"Route calculated:")
print(f"  Distance: {route['distance']:.1f}m")
print(f"  Risk level: {route['risk_level']:.2f}")
print(f"  Warnings: {route['warnings']}")
```

---

## Troubleshooting

### Issue: No data being collected

**Symptoms:**
- `collect_flood_data()` returns empty sources
- Logs show "No data collected"

**Solutions:**
1. Check if any sources are enabled:
```python
collector = DataCollector(use_simulated=True)  # At least one source
```

2. Verify API credentials if using real sources:
```python
# Check PAGASA API credentials
# Check Twitter API keys for MMDA
```

3. Check network connectivity for external APIs

---

### Issue: FloodAgent not updating

**Symptoms:**
- `last_update` timestamp not changing
- No new data being forwarded to HazardAgent

**Solutions:**
1. Check update interval:
```python
flood_agent.data_update_interval = 60  # Reduce to 1 minute for testing
```

2. Force immediate update:
```python
flood_agent.collect_and_forward_data()  # Manual trigger
```

3. Check if FloodAgent.step() is being called:
```python
# In main loop or scheduler
flood_agent.step()
```

---

### Issue: HazardAgent not receiving data

**Symptoms:**
- FloodAgent collecting data but HazardAgent not processing
- Warning: "No HazardAgent reference"

**Solutions:**
1. Verify agent linkage:
```python
flood_agent.set_hazard_agent(hazard_agent)
# Or pass in constructor
flood_agent = FloodAgent("flood_001", env, hazard_agent=hazard_agent)
```

2. Check logs for errors in `send_to_hazard_agent()`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

### Issue: Simulated data not realistic

**Symptoms:**
- Rainfall values always the same
- Flood depths don't correlate with rainfall

**Solutions:**
1. Verify randomization is working:
```python
import random
# Check if random is seeded
# Simulated data uses random.uniform()
```

2. Adjust intensity for variety:
```python
simulated = SimulatedDataSource()
data1 = simulated.get_simulated_rainfall(intensity="light")
data2 = simulated.get_simulated_rainfall(intensity="extreme")
```

---

### Issue: API connection failures

**Symptoms:**
- Timeout errors when collecting data
- "Connection refused" or "403 Forbidden"

**Solutions:**
1. Check API credentials and authentication
2. Verify API endpoint URLs are correct
3. Check rate limiting:
```python
# Add rate limiting
import time
time.sleep(1)  # 1 second between requests
```

4. Implement retry logic:
```python
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)
```

---

## Future Enhancements

### Phase 4: Real API Integration

**PAGASA Integration**
1. Submit formal API access request
2. Implement authentication
3. Add rate limiting (likely 1 req/min)
4. Cache responses (TTL: 5 minutes)

```python
# Future implementation
class PAGASADataSource:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.pagasa.dost.gov.ph"

    def get_rainfall_data(self, station: str) -> Dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(
            f"{self.base_url}/rainfall/{station}",
            headers=headers
        )
        return response.json()
```

**NOAH Integration**
1. Contact UP NOAH Center for partnership
2. Access historical flood hazard maps
3. Implement GeoJSON parsing
4. Cache hazard maps locally

**MMDA Integration**
1. Create Twitter Developer account
2. Set up Twitter API v2 credentials
3. Implement tweet scraping
4. Add NLP for Filipino text processing

### Additional Data Sources

**Weather Radar**
- Integrate PAGASA weather radar data
- Real-time precipitation maps
- Rainfall intensity forecasts

**IoT Sensors**
- Deploy water level sensors
- Marikina River monitoring stations
- Community-based flood sensors

**Crowdsourced Data**
- Mobile app for citizen reports
- Photo/video flood evidence
- Real-time passability updates

### Machine Learning Enhancements

**Flood Prediction Model**
```python
from app.ml_models.flood_predictor import FloodPredictor

predictor = FloodPredictor()
predictor.load_model("trained_flood_model.pkl")

# Predict flood depth from rainfall
prediction = predictor.predict(
    rainfall_1h=15.5,
    rainfall_24h=372.0,
    elevation=50.0,
    distance_to_river=500.0
)
```

**Anomaly Detection**
- Detect unusual sensor readings
- Flag suspicious crowdsourced reports
- Validate data cross-references

### Performance Optimizations

**Caching Strategy**
```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=100)
def cached_flood_data(location: str, timestamp_minute: str):
    """Cache data for 1 minute."""
    return collector.collect_flood_data(location)

# Use with current minute
data = cached_flood_data("Marikina", datetime.now().strftime("%Y-%m-%d %H:%M"))
```

**Async Data Collection**
```python
import asyncio

async def collect_all_sources():
    """Collect from all sources concurrently."""
    tasks = [
        fetch_pagasa_data(),
        fetch_noah_data(),
        fetch_mmda_data()
    ]
    results = await asyncio.gather(*tasks)
    return combine_results(results)
```

---

## Best Practices

### 1. Error Handling

Always handle data source failures gracefully:

```python
try:
    data = collector.collect_flood_data("Marikina")
except Exception as e:
    logger.error(f"Data collection failed: {e}")
    # Use cached data or default values
    data = get_cached_data() or get_default_data()
```

### 2. Data Validation

Validate collected data before processing:

```python
def validate_flood_data(data: Dict) -> bool:
    """Validate flood data structure and values."""
    if "location" not in data:
        return False
    if "sources" not in data:
        return False
    # Check for valid numeric ranges
    if rainfall := data.get("rainfall_mm"):
        if not (0 <= rainfall <= 500):  # Unrealistic if > 500mm/hr
            return False
    return True
```

### 3. Logging

Use appropriate log levels:

```python
logger.info("Starting data collection")      # Normal operations
logger.debug(f"Raw data: {raw_data}")        # Detailed debugging
logger.warning("API rate limit approached")  # Potential issues
logger.error(f"Failed to fetch data: {e}")   # Errors
```

### 4. Configuration Management

Use environment variables for sensitive data:

```python
import os
from dotenv import load_dotenv

load_dotenv()

PAGASA_API_KEY = os.getenv("PAGASA_API_KEY")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
```

### 5. Testing

Test data collection with mocked responses:

```python
from unittest.mock import patch, MagicMock

def test_data_collection():
    with patch('requests.get') as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"rainfall_mm": 15.5}
        )

        collector = DataCollector(enable_pagasa=True)
        data = collector.collect_flood_data("Marikina")

        assert data['sources']['pagasa']['rainfall_mm'] == 15.5
```

---

## Summary

The MAS-FRO data collection system provides:

✅ **Modular architecture** - Enable/disable sources independently
✅ **Multiple data sources** - PAGASA, NOAH, MMDA, Simulated
✅ **Unified interface** - Standardized data format
✅ **Graceful degradation** - Works even if sources fail
✅ **Real-time updates** - Periodic polling (configurable)
✅ **Easy integration** - Simple API for agents
✅ **Extensible design** - Add new sources easily

**Current Status:**
- ✅ Framework complete
- ✅ Simulated data fully functional
- ⏳ Real API integration pending credentials

**Next Steps:**
1. Obtain API credentials for PAGASA, NOAH, MMDA
2. Enable real data sources
3. Implement caching and rate limiting
4. Add machine learning predictions

---

**For More Information:**
- **Phase 3 Completion:** `PHASE_3_COMPLETION.md`
- **Phase 3 Summary:** `PHASE_3_SUMMARY.md`
- **Implementation Details:** `app/services/data_sources.py`
- **Agent Integration:** `app/agents/flood_agent.py`

**Last Updated:** November 5, 2025
**Version:** 1.0
