# Agent Data Visualization - Frontend Integration

## Overview

This document describes the complete implementation for displaying real-time data from backend agents (ScoutAgent, FloodAgent, EvacuationManagerAgent) in the frontend.

---

## ✅ What's Implemented

### Backend API Endpoints

Four new REST API endpoints have been added to `masfro-backend/app/main.py`:

#### 1. **GET `/api/agents/scout/reports`**
Get crowdsourced flood reports from ScoutAgent (social media data processed by NLP).

**Query Parameters:**
- `limit` (int): Maximum number of reports (1-200, default: 50)
- `hours` (int): Hours of history (1-168, default: 24)

**Response:**
```json
{
  "status": "success",
  "total_reports": 15,
  "time_range_hours": 24,
  "scout_agent_active": true,
  "reports": [
    {
      "location": "Nangka",
      "severity": 0.65,
      "coordinates": {
        "lat": 14.669151,
        "lon": 121.109186
      },
      "original_text": "Baha sa Nangka, hanggang tuhod na!",
      "timestamp": "2025-11-19T10:30:00",
      "is_flood_related": true
    }
  ]
}
```

#### 2. **GET `/api/agents/flood/current-status`**
Get current flood data from FloodAgent (PAGASA + OpenWeatherMap APIs).

**Response:**
```json
{
  "status": "success",
  "data_points": 8,
  "data_source": "PAGASA + OpenWeatherMap APIs",
  "last_update": "2025-11-19T10:25:00",
  "flood_data": [
    {
      "station": "Marikina River - Sto. Nino",
      "water_level": 14.2,
      "risk_level": "ALERT",
      "timestamp": "2025-11-19T10:25:00"
    }
  ]
}
```

#### 3. **GET `/api/agents/evacuation/centers`**
Get list of evacuation centers in Marikina City.

**Response:**
```json
{
  "status": "success",
  "total_centers": 12,
  "centers": [
    {
      "id": "evac_center_001",
      "name": "Nangka Elementary School",
      "location": "Brgy. Nangka, Marikina City",
      "coordinates": {
        "lat": 14.6728917,
        "lon": 121.109213
      },
      "capacity": 500,
      "facilities": ["medical", "food", "water"],
      "contact": "+63-2-1234-5678",
      "is_active": true
    }
  ]
}
```

#### 4. **GET `/api/agents/status`**
Get comprehensive status of all agents in the system.

**Response:**
```json
{
  "status": "success",
  "timestamp": "2025-11-19T10:30:00",
  "agents": {
    "scout_agent": {
      "active": false,
      "simulation_mode": null,
      "reports_cached": 15,
      "status": "inactive"
    },
    "flood_agent": {
      "active": true,
      "data_points": 8,
      "use_real_apis": true,
      "status": "active"
    },
    "hazard_agent": {
      "active": true,
      "geotiff_enabled": false,
      "current_scenario": {
        "return_period": "rr01",
        "time_step": 1
      },
      "total_cached_data": 23,
      "status": "active"
    },
    "routing_agent": {
      "active": true,
      "status": "active"
    },
    "evacuation_manager": {
      "active": true,
      "evacuation_centers": 12,
      "status": "active"
    },
    "system": {
      "graph_loaded": true,
      "total_nodes": 5243,
      "total_edges": 12456
    }
  }
}
```

---

## Frontend Components

### 1. **AgentDataPanel Component**
Location: `masfro-frontend/src/components/AgentDataPanel.js`

**Features:**
- ✅ Three tabs: Scout Reports, Flood Data, Evacuation Centers
- ✅ Real-time agent status indicators
- ✅ Auto-refresh every 30 seconds
- ✅ Manual refresh buttons
- ✅ Color-coded severity levels
- ✅ Responsive design with fixed positioning

**Usage in `page.js`:**
```javascript
import AgentDataPanel from '@/components/AgentDataPanel';

// In component
const [showAgentPanel, setShowAgentPanel] = useState(true);

// In JSX
{showAgentPanel && <AgentDataPanel />}
```

**Toggle Button:**
```javascript
<button onClick={() => setShowAgentPanel(!showAgentPanel)}>
  🤖 {showAgentPanel ? 'Hide' : 'Show'} Agents
</button>
```

---

## How It Works

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ScoutAgent                                                  │
│  ├─ Scrapes Twitter/X (or uses simulation mode)             │
│  ├─ NLP Processing (flood detection, location, severity)    │
│  └─ Forwards to HazardAgent ──┐                             │
│                                │                             │
│  FloodAgent                    │                             │
│  ├─ PAGASA API                 │                             │
│  ├─ OpenWeatherMap API         │                             │
│  └─ Forwards to HazardAgent ───┤                             │
│                                │                             │
│  HazardAgent                   │                             │
│  ├─ scout_data_cache ◄─────────┘                             │
│  ├─ flood_data_cache ◄─────────┘                             │
│  └─ Data fusion + risk calculation                           │
│                                                               │
│  EvacuationManagerAgent                                      │
│  └─ Manages evacuation centers                               │
│                                                               │
│  API Endpoints (main.py)                                     │
│  ├─ GET /api/agents/scout/reports                            │
│  ├─ GET /api/agents/flood/current-status                     │
│  ├─ GET /api/agents/evacuation/centers                       │
│  └─ GET /api/agents/status                                   │
│                                                               │
└───────────────────┬─────────────────────────────────────────┘
                    │ HTTP REST API
                    │
┌───────────────────▼─────────────────────────────────────────┐
│                      FRONTEND                                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  AgentDataPanel.js                                           │
│  ├─ Fetches data from API endpoints                          │
│  ├─ Auto-refresh every 30s                                   │
│  ├─ Displays in 3 tabs:                                      │
│  │   ├─ Scout Reports (crowdsourced)                         │
│  │   ├─ Flood Data (official)                                │
│  │   └─ Evacuation Centers                                   │
│  └─ Real-time status indicators                              │
│                                                               │
│  WebSocket (already existing)                                │
│  ├─ Real-time flood updates                                  │
│  └─ Critical alerts                                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing Instructions

### 1. **Start Backend**
```bash
cd masfro-backend
uv run uvicorn app.main:app --reload
```

### 2. **Test API Endpoints**

**Test Scout Reports:**
```bash
curl http://localhost:8000/api/agents/scout/reports
```

**Test Flood Status:**
```bash
curl http://localhost:8000/api/agents/flood/current-status
```

**Test Evacuation Centers:**
```bash
curl http://localhost:8000/api/agents/evacuation/centers
```

**Test All Agents Status:**
```bash
curl http://localhost:8000/api/agents/status
```

### 3. **Start Frontend**
```bash
cd masfro-frontend
npm run dev
```

### 4. **View in Browser**
1. Navigate to: `http://localhost:3000`
2. Look for the **"🤖 Show/Hide Agents"** button in the sidebar
3. The **Agent Data Panel** appears on the right side
4. Click tabs to switch between Scout, Flood, and Evacuation data

---

## Environment Variables

Make sure your frontend has the correct API URL:

**File:** `masfro-frontend/.env.local`
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## ScoutAgent Simulation Mode

Since ScoutAgent requires Twitter/X credentials, you can use **simulation mode** with synthetic data:

**Backend:** `masfro-backend/app/main.py` (around line 429)

**Replace:**
```python
scout_agent = None
```

**With:**
```python
scout_agent = ScoutAgent(
    "scout_agent_001",
    environment,
    hazard_agent=hazard_agent,
    simulation_mode=True,  # Use simulation instead of scraping
    simulation_scenario=1   # Scenario 1-3 (different flood intensities)
)
```

**Then trigger simulation:**
```bash
# Via API
curl -X POST http://localhost:8000/api/admin/collect-flood-data
```

**Or programmatically:**
```python
# In your code
scout_agent.scrape_and_forward()  # Will use simulation data
```

---

## Real-Time Updates

The system supports **two methods** for real-time updates:

### 1. **WebSocket (Already Implemented)**
- Real-time flood updates every 5 minutes
- Critical alerts (ALARM/CRITICAL water levels)
- Automatic broadcast to all connected clients

### 2. **Polling (New - AgentDataPanel)**
- Auto-refresh every 30 seconds
- Manual refresh buttons
- Fetches latest data from REST API

---

## Severity Color Coding

The AgentDataPanel uses color coding for flood severity:

| Severity | Range | Color | Label |
|----------|-------|-------|-------|
| Critical | ≥ 0.8 | 🔴 Red | Critical |
| Dangerous | 0.5 - 0.79 | 🟠 Orange | Dangerous |
| Minor | 0.3 - 0.49 | 🟡 Yellow | Minor |
| Low | < 0.3 | 🔵 Blue | Low |

**NLP Severity Mapping (v3.0):**
- `none`: 0.0
- `minor`: 0.3 (ankle-deep)
- `dangerous`: 0.65 (knee to waist)
- `critical`: 0.95 (chest to neck)

---

## Data Freshness

### Scout Reports
- **Source:** Social media (Twitter/X) via ScoutAgent
- **Update Frequency:** Depends on scraping schedule (manual trigger or scheduled)
- **Cache Duration:** 24 hours (configurable via `hours` parameter)
- **Expiry:** Reports older than 24 hours are filtered out

### Flood Data
- **Source:** PAGASA + OpenWeatherMap APIs via FloodAgent
- **Update Frequency:** Every 5 minutes (automated via scheduler)
- **Cache Duration:** Until next update
- **Real-time:** Also broadcasted via WebSocket

### Evacuation Centers
- **Source:** Environment configuration
- **Update Frequency:** Static (updated when centers are added/modified)
- **Real-time:** Status changes reflected immediately

---

## API Documentation

All endpoints are documented in **FastAPI Swagger UI**:

**URL:** `http://localhost:8000/docs`

**Tags:**
- **Agent Data** - New endpoints for agent data retrieval
- **Routing** - Route calculation and evacuation center lookup
- **Flood Data History** - Historical flood data from database
- **Simulation** - Simulation control (start/stop/reset)
- **Scheduler** - Flood data collection scheduler
- **Admin** - GeoTIFF and manual triggers

---

## Future Enhancements

### Possible Improvements:

1. **Map Integration:**
   - Display scout reports as markers on Mapbox
   - Color-code markers by severity
   - Click markers to see report details

2. **Filtering & Search:**
   - Filter reports by location/barangay
   - Search by keyword
   - Time range slider

3. **Statistics:**
   - Total reports by severity
   - Most affected barangays
   - Trend graphs (hourly/daily)

4. **Notifications:**
   - Browser notifications for critical reports
   - Sound alerts
   - Desktop notifications

5. **Export:**
   - Download reports as CSV/JSON
   - Generate PDF summary
   - Share specific reports

---

## Troubleshooting

### Issue: "No scout reports available"

**Causes:**
1. ScoutAgent is not initialized (set to `None`)
2. No tweets have been scraped yet
3. NLP filtered out all tweets as non-flood-related

**Solutions:**
1. Enable ScoutAgent with simulation mode (see above)
2. Manually trigger scraping: `POST /api/admin/collect-flood-data`
3. Check HazardAgent cache: `hazard_agent.scout_data_cache`

### Issue: "No flood data available"

**Causes:**
1. FloodAgent hasn't run yet
2. PAGASA/OpenWeatherMap API errors
3. Scheduler not started

**Solutions:**
1. Manually trigger: `POST /api/scheduler/trigger`
2. Check scheduler status: `GET /api/scheduler/status`
3. Check backend logs for API errors

### Issue: "No evacuation centers available"

**Cause:**
- Environment doesn't have evacuation centers configured

**Solution:**
- Check `environment.evacuation_centers` configuration
- Ensure evacuation centers are loaded during initialization

### Issue: "Agent Data Panel not showing"

**Causes:**
1. `showAgentPanel` state is `false`
2. Component import error
3. CSS z-index conflict

**Solutions:**
1. Click "🤖 Show Agents" button
2. Check browser console for errors
3. Inspect element to verify z-index (should be 40)

---

## Summary

### ✅ What You Can Now Do:

1. **View Scout Reports**
   - See crowdsourced flood reports from social media
   - Filter by time range (1-168 hours)
   - View location, severity, and original text

2. **Monitor Flood Status**
   - Official data from PAGASA + OpenWeatherMap
   - River levels and risk classifications
   - Auto-updated every 5 minutes

3. **Find Evacuation Centers**
   - Complete list with coordinates
   - Capacity and facility information
   - Contact details

4. **System Status Dashboard**
   - Real-time agent health monitoring
   - Data cache statistics
   - Graph and GeoTIFF status

### 📊 Technical Achievement:

- **4 new REST API endpoints** exposing agent data
- **1 new React component** for data visualization
- **Full integration** with existing WebSocket system
- **Backward compatible** - no breaking changes
- **Production-ready** - error handling, loading states, pagination

---

## Contact

For questions or issues:
- Check backend logs: `masfro-backend/logs/masfro.log`
- Test endpoints with Swagger: `http://localhost:8000/docs`
- Inspect browser console for frontend errors
