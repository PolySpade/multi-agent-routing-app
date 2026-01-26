# 🐛 Simulation Debugging Guide

## Issues Identified

### ⚠️ Issue 1: Stop Simulation Not Working
**Status**: Backend logic is CORRECT
**Problem**: Frontend state synchronization

### ⚠️ Issue 2: AgentDataPanel Not Showing Simulation Data
**Status**: Data flow is CORRECT
**Problem**: Timing/initialization or frontend polling

---

## 🔍 Step-by-Step Debugging

### Test 1: Verify Simulation Start/Stop Cycle

```bash
# Terminal 1: Start backend with verbose logging
cd masfro-backend
uv run uvicorn app.main:app --reload --log-level debug

# Terminal 2: Test endpoints
# Start simulation
curl -X POST "http://localhost:8000/api/simulation/start?mode=medium"

# Wait 5 seconds, then check status
sleep 5
curl "http://localhost:8000/api/simulation/status"

# Stop simulation
curl -X POST "http://localhost:8000/api/simulation/stop"

# Verify stopped
curl "http://localhost:8000/api/simulation/status"
```

**Expected Backend Logs**:
```
INFO: Simulation start request received - Mode: medium
INFO: Loaded scenario 'Medium Flood Scenario (from CSV)' with 24 events.
INFO: Simulation STARTED - Mode: MEDIUM
INFO: === TICK 1 START === Clock: 0.00s, Time step: 1/18
INFO: --- Phase 1: Data Collection ---
INFO: Processed 'flood_agent' event at clock 0.00s
INFO: --- Phase 2: Data Fusion & Graph Update ---
INFO: HazardAgent updated X edges (time_step=1)
...
INFO: Simulation stop request received
INFO: Simulation STOPPED (paused) - Total runtime: Xs, Ticks: Y
```

---

### Test 2: Verify Data Reaches HazardAgent Cache

```bash
# After starting simulation, query scout reports
curl "http://localhost:8000/api/agents/scout/reports?limit=50&hours=24"
```

**Expected Response**:
```json
{
  "status": "success",
  "total_reports": 15,
  "reports": [
    {
      "location": "SM Marikina",
      "coordinates": {"lat": 14.6550, "lon": 121.1080},
      "severity": 0.35,
      "text": "Heavy rain at SM Marikina! Parking lot starting to flood.",
      "timestamp": "2025-11-18T08:00:05Z"
    },
    ...
  ]
}
```

**If total_reports = 0**:
- Events not being processed
- Check simulation clock vs event time_offsets
- Verify scenario CSV loaded

---

### Test 3: Monitor WebSocket Broadcasts

Open browser DevTools Console:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/route-updates');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('WebSocket:', data.type, data);
};

// You should see:
// WebSocket: simulation_state {event: "started", ...}
// WebSocket: simulation_state {event: "tick", data: {tick: 1, ...}}
// WebSocket: simulation_state {event: "tick", data: {tick: 2, ...}}
// WebSocket: simulation_state {event: "stopped", ...}
```

---

## 🔧 Fixes to Apply

### Fix 1: Add Simulation State to AgentDataPanel

**Problem**: AgentDataPanel doesn't check if simulation is running
**Solution**: Add simulation status indicator

**File**: `masfro-frontend/src/components/AgentDataPanel.js`

Add state tracking:
```javascript
const [simulationState, setSimulationState] = useState(null);

// Fetch simulation status
const fetchSimulationStatus = async () => {
  try {
    const response = await fetch(`${API_BASE}/api/simulation/status`);
    const data = await response.json();
    setSimulationState(data);
  } catch (err) {
    logger.error('Failed to fetch simulation status', err);
  }
};

// Add to mount effect
useEffect(() => {
  fetchSimulationStatus();
  const interval = setInterval(fetchSimulationStatus, 5000); // Every 5s
  return () => clearInterval(interval);
}, []);
```

Add indicator in UI:
```javascript
{simulationState && simulationState.state === 'running' && (
  <div className="status-item">
    <div className="status-dot status-active"></div>
    Simulation: {simulationState.mode.toUpperCase()}
  </div>
)}
```

---

### Fix 2: Add Logging to Track Event Processing

**File**: `masfro-backend/app/services/simulation_manager.py`

Add detailed logging in `_run_collection_phase`:

```python
def _run_collection_phase(self) -> Dict[str, Any]:
    """Phase 1: Data collection from the scenario event queue."""
    phase_result = {
        "events_processed": 0,
        "flood_data_collected": 0,
        "scout_reports_collected": 0,
        "errors": []
    }

    # ADD THIS: Log current state
    logger.info(
        f"Collection phase - Clock: {self._simulation_clock:.2f}s, "
        f"Queue size: {len(self._event_queue)}, "
        f"Next event: {self._event_queue[0] if self._event_queue else 'None'}"
    )

    # Clear previous tick's data
    self.shared_data_bus["flood_data"] = {}
    self.shared_data_bus["scout_data"] = []
    self.shared_data_bus["graph_updated"] = False

    # Process events from the queue
    while self._event_queue and self._event_queue[0]["time_offset"] <= self._simulation_clock:
        event = self._event_queue.pop(0)
        phase_result["events_processed"] += 1
        agent = event.get("agent")
        payload = event.get("payload")

        # ADD THIS: Log each event processed
        logger.info(
            f"Processing event: agent={agent}, "
            f"time_offset={event.get('time_offset')}, "
            f"payload_keys={list(payload.keys()) if isinstance(payload, dict) else type(payload)}"
        )

        if agent == "flood_agent":
            self.shared_data_bus["flood_data"] = payload
            phase_result["flood_data_collected"] += 1
        elif agent == "scout_agent":
            # ADD THIS: Log scout data structure
            logger.debug(f"Scout report: {payload}")
            self.shared_data_bus["scout_data"].append(payload)
            phase_result["scout_reports_collected"] += 1
        else:
            error_msg = f"Unknown agent '{agent}' in scenario event."
            phase_result["errors"].append(error_msg)
            logger.warning(error_msg)

    # ADD THIS: Log phase summary
    logger.info(
        f"Collection phase complete - "
        f"Events: {phase_result['events_processed']}, "
        f"Flood data: {phase_result['flood_data_collected']}, "
        f"Scout reports: {phase_result['scout_reports_collected']}"
    )

    return phase_result
```

---

### Fix 3: Force Cache Inspection Endpoint (Debugging)

Add a debugging endpoint to directly inspect cache contents:

**File**: `masfro-backend/app/main.py`

```python
@app.get("/api/debug/hazard-cache", tags=["Debug"])
async def get_hazard_cache_debug():
    """
    Debug endpoint to inspect HazardAgent cache contents.

    Returns raw cache data for debugging simulation data flow.
    """
    if not hazard_agent:
        raise HTTPException(status_code=503, detail="HazardAgent not initialized")

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "flood_data_cache": hazard_agent.flood_data_cache,
        "scout_data_cache": hazard_agent.scout_data_cache,
        "cache_sizes": {
            "flood": len(hazard_agent.flood_data_cache),
            "scout": len(hazard_agent.scout_data_cache)
        },
        "simulation_manager_state": {
            "state": simulation_manager._state.value if simulation_manager else None,
            "tick_count": simulation_manager.tick_count if simulation_manager else 0,
            "time_step": simulation_manager.current_time_step if simulation_manager else 0,
            "simulation_clock": simulation_manager._simulation_clock if simulation_manager else 0
        }
    }
```

**Test it**:
```bash
# Start simulation
curl -X POST "http://localhost:8000/api/simulation/start?mode=medium"

# Wait 10 seconds
sleep 10

# Inspect cache
curl "http://localhost:8000/api/debug/hazard-cache" | jq
```

---

## 🎯 Quick Diagnostic Checklist

Run through these checks:

```bash
# 1. Backend running
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# 2. Start simulation
curl -X POST "http://localhost:8000/api/simulation/start?mode=medium"
# Expected: {"status":"success","state":"running"}

# 3. Check simulation running (wait 5s)
sleep 5
curl "http://localhost:8000/api/simulation/status"
# Expected: {"status":"success","state":"running","tick_count":5}

# 4. Check scout cache
curl "http://localhost:8000/api/agents/scout/reports"
# Expected: {"status":"success","total_reports":>0}

# 5. Stop simulation
curl -X POST "http://localhost:8000/api/simulation/stop"
# Expected: {"status":"success","state":"paused"}

# 6. Verify stopped
curl "http://localhost:8000/api/simulation/status"
# Expected: {"status":"success","state":"paused"}
```

---

## 🚨 Common Issues & Solutions

### Issue: "Simulation is not running" when calling stop
**Cause**: Simulation wasn't started or already stopped
**Fix**: Check `/api/simulation/status` before calling stop

### Issue: Scout reports array is empty
**Possible Causes**:
1. **Timing**: Events haven't reached their time_offset yet
   - Wait longer (events start at 5s, 10s, etc.)
   - Check logs for "Processed 'scout_agent' event"

2. **Scenario not loaded**:
   - Check logs for "Loaded scenario ... with X events"
   - Verify CSV file exists and is valid

3. **Cache cleared**:
   - Only happens on `/api/simulation/reset`
   - Check if reset was called accidentally

### Issue: Frontend not updating
**Cause**: Frontend not polling or WebSocket not connected
**Fix**:
1. Check WebSocket connection in DevTools Network tab
2. Add polling to AgentDataPanel for simulation status
3. Force refresh scout reports when simulation state changes

---

## 📝 Recommended Immediate Actions

1. **Add the debug endpoint** to inspect cache
2. **Add enhanced logging** to collection phase
3. **Test with curl** to isolate backend vs frontend issues
4. **Monitor backend logs** for event processing
5. **Check WebSocket messages** in browser DevTools

Once you identify where the data flow breaks, we can apply targeted fixes.
