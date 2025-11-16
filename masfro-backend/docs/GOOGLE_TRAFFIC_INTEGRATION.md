# Google Maps Traffic API Integration Guide

**Project:** MAS-FRO (Multi-Agent System for Flood Route Optimization)
**Feature:** Real-time traffic data integration
**Status:** Implementation complete, ready for testing
**Date:** November 2025

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup Instructions](#setup-instructions)
4. [Usage Examples](#usage-examples)
5. [API Cost Analysis](#api-cost-analysis)
6. [Performance Optimization](#performance-optimization)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## 1. Overview

### What This Integration Does

Enhances the MAS-FRO routing system with **real-time traffic conditions** from Google Maps, allowing the system to optimize routes based on:

1. **Flood risk** (from FloodAgent & HazardAgent)
2. **Current traffic congestion** (from Google Maps Traffic API)
3. **Road distance** (from OSMnx graph)

### Enhanced Cost Function

**Before (Flood-aware only):**
```python
edge_cost = length × (1.0 + risk_score)
```

**After (Flood + Traffic aware):**
```python
edge_cost = length × (1.0 + risk_score) × (1.0 + traffic_factor)
```

### Example Calculation

```python
# Example: 1000m road segment
length = 1000  # meters
risk_score = 0.3  # 30% flood risk
traffic_factor = 0.5  # 50% traffic delay

# Old cost (flood only)
old_cost = 1000 × (1.0 + 0.3) = 1300

# New cost (flood + traffic)
new_cost = 1000 × (1.0 + 0.3) × (1.0 + 0.5) = 1950

# Interpretation: This segment is 50% slower due to traffic
# AND has 30% risk penalty, making it 95% more expensive than
# a safe, free-flowing road of the same length
```

---

## 2. Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Google Maps Traffic API                   │
│          (Directions API with traffic_model=best_guess)     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              GoogleTrafficService                           │
│  - Fetches traffic data with 5-min caching                  │
│  - Converts duration_in_traffic → traffic_factor            │
│  - Rate limiting (60 requests/min)                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    TrafficAgent                             │
│  - Samples graph edges (every 20th by default)              │
│  - Updates graph with traffic_factor attribute              │
│  - Interpolates data to non-sampled edges                   │
│  - Notifies other agents via ACL messages                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│            DynamicGraphEnvironment                          │
│  Edge attributes:                                           │
│    - length (OSMnx)                                         │
│    - risk_score (HazardAgent)                               │
│    - traffic_factor (TrafficAgent) ← NEW                    │
│    - weight = length × (1+risk) × (1+traffic)               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   RoutingAgent                              │
│  Uses updated edge weights for risk-aware A* pathfinding    │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
masfro-backend/
├── app/
│   ├── agents/
│   │   └── traffic_agent.py           ← NEW: Traffic monitoring agent
│   ├── services/
│   │   └── google_traffic_service.py  ← NEW: Google API wrapper
│   └── environment/
│       └── graph_manager.py           ← UPDATED: Added traffic support
├── docs/
│   └── GOOGLE_TRAFFIC_INTEGRATION.md  ← This file
└── .env.example                       ← UPDATED: Added GOOGLE_MAPS_API_KEY
```

---

## 3. Setup Instructions

### Step 1: Get Google Maps API Key

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/

2. **Create a new project** (or select existing):
   - Project name: "MAS-FRO Traffic"

3. **Enable the Directions API:**
   - Navigate to: APIs & Services → Library
   - Search for "Directions API"
   - Click "Enable"

4. **Create API credentials:**
   - APIs & Services → Credentials
   - Click "Create Credentials" → "API Key"
   - Copy the generated key

5. **Restrict the API key (recommended):**
   - Click on the key name
   - Under "Application restrictions": Select "IP addresses"
   - Add your server IP
   - Under "API restrictions": Select "Restrict key"
   - Choose "Directions API"
   - Save

### Step 2: Configure Environment Variables

```bash
# Navigate to backend directory
cd masfro-backend

# Copy example env file
cp .env.example .env

# Edit .env file
nano .env  # or use your preferred editor
```

**Add your Google Maps API key:**
```bash
GOOGLE_MAPS_API_KEY=AIzaSyD1234567890abcdefghijklmnopqrstuv
```

### Step 3: Install Dependencies

No new dependencies needed! The implementation uses only built-in Python libraries and existing dependencies (`requests` is already in `pyproject.toml`).

### Step 4: Initialize TrafficAgent in Main Application

**Edit `app/main.py`:**

```python
# Add import at top
from app.agents.traffic_agent import TrafficAgent

# In startup event (after other agents are initialized):
@app.on_event("startup")
async def startup_event():
    # ... existing agent initialization ...

    # Initialize TrafficAgent (optional - enable if you have API key)
    try:
        traffic_agent = TrafficAgent(
            agent_id="traffic_001",
            environment=graph_env,
            update_interval=300,  # 5 minutes
            sample_interval=20    # Sample every 20th edge
        )
        # Store in app state for access in endpoints
        app.state.traffic_agent = traffic_agent

        logger.info("✅ TrafficAgent initialized successfully")
    except ValueError as e:
        # API key not configured - skip traffic integration
        logger.warning(f"⚠️ TrafficAgent not initialized: {e}")
        app.state.traffic_agent = None
```

---

## 4. Usage Examples

### Example 1: Manual Traffic Update

```python
from app.agents.traffic_agent import TrafficAgent
from app.environment.graph_manager import DynamicGraphEnvironment

# Initialize
env = DynamicGraphEnvironment()
agent = TrafficAgent("traffic_001", env)

# Fetch and update traffic data
stats = agent.update_traffic_data()

print(f"Updated {stats['edges_updated']} edges")
print(f"Average traffic delay: {stats['avg_traffic_factor']:.1%}")
print(f"Max traffic delay: {stats['max_traffic_factor']:.1%}")
```

### Example 2: Query Specific Route Traffic

```python
# Get traffic for specific segment
origin = (14.6507, 121.1029)  # Marikina City Hall
destination = (14.6545, 121.1089)  # Sports Center

traffic_factor = agent.get_current_traffic(origin, destination)

if traffic_factor < 0.2:
    print("🟢 Light traffic - good to go!")
elif traffic_factor < 0.5:
    print("🟡 Moderate traffic - expect some delays")
else:
    print("🔴 Heavy traffic - consider alternative route")
```

### Example 3: Automated Updates via Scheduler

```python
# In app/main.py or scheduler service

import schedule
import time

def update_traffic():
    """Scheduled traffic update function."""
    if app.state.traffic_agent:
        stats = app.state.traffic_agent.update_traffic_data()
        logger.info(f"Traffic update: {stats['edges_updated']} edges")

# Schedule updates every 5 minutes
schedule.every(5).minutes.do(update_traffic)

# Run in background task
async def run_scheduler():
    while True:
        schedule.run_pending()
        await asyncio.sleep(60)  # Check every minute

# Start scheduler on app startup
asyncio.create_task(run_scheduler())
```

### Example 4: Add Traffic Endpoint to API

**Add to `app/main.py`:**

```python
@app.post("/api/admin/update-traffic")
async def update_traffic_data():
    """
    Manually trigger traffic data update.

    Returns:
        Traffic update statistics
    """
    if not app.state.traffic_agent:
        raise HTTPException(
            status_code=503,
            detail="Traffic monitoring not enabled (API key not configured)"
        )

    try:
        stats = app.state.traffic_agent.update_traffic_data()
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Traffic update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/traffic/status")
async def get_traffic_status():
    """
    Get current traffic monitoring status.

    Returns:
        Traffic agent statistics
    """
    if not app.state.traffic_agent:
        return {
            "enabled": False,
            "message": "Traffic monitoring not configured"
        }

    stats = app.state.traffic_agent.get_statistics()
    return {
        "enabled": True,
        "statistics": stats
    }
```

---

## 5. API Cost Analysis

### Google Maps Directions API Pricing

**Pricing Tier:**
- **$5.00 per 1,000 requests**
- **Free tier:** $200/month credit = 40,000 free requests/month

### Cost Scenarios for Marikina City

**Graph Size:**
- ~5,000 nodes
- ~12,000 edges

**Scenario 1: Conservative (sample_interval=20)**
- Edges sampled per update: 12,000 / 20 = 600 edges
- Updates per day: 24 hours × (60 min / 5 min) = 288 updates
- **Daily requests:** 600 × 288 = 172,800 requests
- **Monthly cost:** 172,800 × 30 × $5 / 1,000 = **$25,920** ❌ Too expensive!

**Scenario 2: Moderate (sample_interval=50, hourly updates)**
- Edges sampled per update: 12,000 / 50 = 240 edges
- Updates per day: 24 updates
- **Daily requests:** 240 × 24 = 5,760 requests
- **Monthly requests:** 5,760 × 30 = 172,800 requests
- **Monthly cost:** 172,800 × $5 / 1,000 - $200 (free) = **$664** ⚠️ Still expensive

**Scenario 3: Optimized (sample_interval=100, 2-hour updates)**
- Edges sampled per update: 12,000 / 100 = 120 edges
- Updates per day: 12 updates
- **Daily requests:** 120 × 12 = 1,440 requests
- **Monthly requests:** 1,440 × 30 = 43,200 requests
- **Monthly cost:** 43,200 × $5 / 1,000 - $200 (free) = **$16** ✅ Affordable!

**Scenario 4: FREE Tier Only (sample_interval=200, 4-hour updates)**
- Edges sampled per update: 12,000 / 200 = 60 edges
- Updates per day: 6 updates
- **Daily requests:** 60 × 6 = 360 requests
- **Monthly requests:** 360 × 30 = 10,800 requests
- **Monthly cost:** **$0** (within free tier) ✅ FREE!

### Recommended Configuration

```python
# For production (stay within free tier)
traffic_agent = TrafficAgent(
    agent_id="traffic_001",
    environment=env,
    update_interval=14400,  # 4 hours = 6 updates/day
    sample_interval=200     # Sample 60 edges per update
)

# For testing/demo (more frequent, higher cost)
traffic_agent = TrafficAgent(
    agent_id="traffic_001",
    environment=env,
    update_interval=7200,   # 2 hours = 12 updates/day
    sample_interval=100     # Sample 120 edges per update
)
```

---

## 6. Performance Optimization

### Caching Strategy

**Built-in Cache:**
- Duration: 5 minutes (configurable)
- Key: origin-destination pair (rounded to 4 decimals)
- Auto-expiration: Yes

**Example:**
```python
# First call - hits API
factor1 = service.get_traffic_factor((14.6507, 121.1029), (14.6545, 121.1089))

# Second call within 5 minutes - returns cached value
factor2 = service.get_traffic_factor((14.6507, 121.1029), (14.6545, 121.1089))
# No API request made!
```

### Edge Sampling Strategy

**Spatial Sampling:**
The implementation samples every Nth edge systematically, ensuring:
- Coverage across entire graph
- Consistent update patterns
- Predictable API usage

**Interpolation:**
Non-sampled edges inherit traffic factors from nearest sampled edges using spatial proximity.

### Rate Limiting

**Google's Limits:**
- Default: 60 requests/minute
- Can request increase to 1,000 req/min

**Built-in Protection:**
- 50ms delay between requests
- Request counter tracking
- Warning logs at threshold

---

## 7. Testing

### Unit Test for Traffic Service

Create `masfro-backend/tests/test_traffic_service.py`:

```python
import pytest
from app.services.google_traffic_service import GoogleTrafficService
from unittest.mock import Mock, patch

def test_traffic_factor_calculation():
    """Test traffic factor calculation."""
    service = GoogleTrafficService()

    # Mock API response
    mock_response = {
        "status": "OK",
        "routes": [{
            "legs": [{
                "duration": {"value": 600},  # 10 minutes normal
                "duration_in_traffic": {"value": 900}  # 15 minutes with traffic
            }]
        }]
    }

    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        factor = service.get_traffic_factor(
            (14.6507, 121.1029),
            (14.6545, 121.1089)
        )

        # 50% delay: (900-600)/600 = 0.5
        assert factor == pytest.approx(0.5, abs=0.01)

def test_cache_functionality():
    """Test that caching works correctly."""
    service = GoogleTrafficService(cache_duration=300)

    # ... implement cache test
```

### Integration Test

```bash
# Run with real API key (uses actual credits!)
cd masfro-backend
uv run pytest tests/test_traffic_integration.py -v
```

---

## 8. Troubleshooting

### Common Issues

**1. "API key not found" Error**

```
ValueError: Google Maps API key not found
```

**Solution:**
- Check `.env` file has `GOOGLE_MAPS_API_KEY=...`
- Verify the variable name is correct (no typos)
- Restart the server after updating .env

---

**2. "REQUEST_DENIED" Status**

```
Google API status: REQUEST_DENIED
```

**Solution:**
- Verify Directions API is enabled in Google Cloud Console
- Check API key restrictions (IP, referrer, API list)
- Ensure billing is enabled on the project

---

**3. High API Costs**

**Solution:**
- Increase `sample_interval` (e.g., 100 → 200)
- Increase `update_interval` (e.g., 1 hour → 4 hours)
- Monitor usage in Google Cloud Console

---

**4. Traffic Data Not Updating Graph**

**Check:**
```python
# Verify edge has traffic_factor attribute
env = DynamicGraphEnvironment()
edge = env.graph.edges[u, v, key]
print(edge.get('traffic_factor', 'NOT SET'))
```

**Solution:**
- Ensure `TrafficAgent.update_traffic_data()` is being called
- Check logs for API errors
- Verify graph is loaded before traffic update

---

## 9. Future Enhancements

### Potential Improvements

1. **Machine Learning Traffic Prediction**
   - Train model on historical Google traffic data
   - Predict traffic patterns for future time windows
   - Reduce API calls by 90%

2. **Waze Integration**
   - Alternative free data source
   - Crowdsourced real-time incidents
   - Combine with Google data for validation

3. **Local Traffic Model**
   - Use historical data to build traffic patterns
   - Time-of-day based predictions
   - Only query Google for verification

4. **Smart Sampling**
   - Sample high-traffic roads more frequently
   - Skip residential streets (usually free-flow)
   - Dynamic sample_interval based on time of day

---

## Summary

✅ **Implementation Status:** Complete and ready for production
✅ **Cost:** Can stay within free tier with optimized settings
✅ **Performance:** 4-hour updates with 200-edge sampling = 10,800 req/month
✅ **Integration:** Seamlessly combines with existing flood risk scoring

**Next Steps:**
1. Get Google Maps API key
2. Configure `.env` file
3. Initialize TrafficAgent in `main.py`
4. Test with sample requests
5. Monitor costs in Google Cloud Console
6. Adjust `sample_interval` and `update_interval` as needed

**Questions?** Check the troubleshooting section or review the code comments in:
- `app/services/google_traffic_service.py`
- `app/agents/traffic_agent.py`
