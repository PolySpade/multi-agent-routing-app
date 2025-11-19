# ✅ Simulation Fixes Applied

## 📋 Summary

I've analyzed your simulation issues and applied diagnostic enhancements to help identify the root causes.

---

## 🔍 Issues Reported

1. **Stop simulation doesn't work** - Frontend command doesn't stop the backend simulation
2. **AgentDataPanel shows no logs during simulation** - No scout reports appearing in frontend

---

## 🎯 Root Cause Analysis

### Issue 1: Stop Simulation
**Status**: ✅ **Backend logic is CORRECT**

The `stop_simulation()` endpoint (main.py:925) properly:
- Cancels the async tick loop task
- Sets state to `PAUSED`
- Returns success response
- Broadcasts WebSocket message

**Most likely cause**: Frontend state synchronization issue:
- Frontend may not be polling `/api/simulation/status` after stop request
- WebSocket listener may not be updating UI on "stopped" event
- UI may not reflect the paused state visually

**Recommendation**: Check frontend simulation controls and add status polling.

---

### Issue 2: No Data in AgentDataPanel
**Status**: ⚠️ **Requires testing to identify exact issue**

The data flow is theoretically correct:
1. ✅ CSV scenario files contain scout_agent events (verified medium_scenario.csv has 15+ scout events)
2. ✅ `_run_collection_phase()` processes events and adds to `shared_data_bus["scout_data"]`
3. ✅ `_run_fusion_phase()` calls `hazard_agent.update_risk(scout_data=...)`
4. ✅ `update_risk()` does `self.scout_data_cache.extend(scout_data)`
5. ✅ `/api/agents/scout/reports` returns `hazard_agent.scout_data_cache`

**Possible causes**:
- Events not reaching their time_offset (simulation clock too slow)
- Events being processed but cache query happens before data arrives
- Frontend polling AgentDataPanel endpoints before simulation generates data
- Cache being cleared unexpectedly

---

## 🔧 Fixes Applied

### 1. ✅ Debug Endpoints Added

**File**: `masfro-backend/app/main.py`

Added two new debug endpoints:

#### `/api/debug/hazard-cache`
Inspects HazardAgent cache contents directly:
```bash
curl "http://localhost:8000/api/debug/hazard-cache" | jq
```

Returns:
```json
{
  "status": "success",
  "flood_data_cache": {...},
  "scout_data_cache": [...],
  "cache_sizes": {
    "flood": 3,
    "scout": 15
  },
  "simulation_manager_state": {
    "state": "running",
    "tick_count": 45,
    "time_step": 3,
    "simulation_clock": 45.2,
    "event_queue_size": 12
  }
}
```

#### `/api/debug/simulation-events`
Inspects event queue and upcoming events:
```bash
curl "http://localhost:8000/api/debug/simulation-events" | jq
```

Returns:
```json
{
  "status": "success",
  "simulation_clock": 45.2,
  "total_events_remaining": 12,
  "upcoming_events": [
    {
      "time_offset": 60,
      "agent": "flood_agent",
      "payload": {...}
    },
    ...
  ],
  "simulation_state": {
    "state": "running",
    "is_running": true,
    "is_paused": false
  }
}
```

---

### 2. ✅ Enhanced Logging Added

**File**: `masfro-backend/app/services/simulation_manager.py`

Enhanced `_run_collection_phase()` method with detailed logging:

**Before**:
```
INFO: --- Phase 1: Data Collection ---
```

**After**:
```
INFO: Collection phase START - Clock: 5.23s, Queue size: 20, Next event: agent=scout_agent, time=5s
INFO: Processing event #1: agent=scout_agent, time_offset=5s
INFO: ✓ Scout report collected: location='SM Marikina', severity=0.35
INFO: Processing event #2: agent=scout_agent, time_offset=10s
INFO: ✓ Scout report collected: location='Nangka', severity=0.38
INFO: Collection phase COMPLETE - Events processed: 2 (scout_agent@5s[SM Marikina], scout_agent@10s[Nangka]), Flood data: 0, Scout reports: 2, Remaining in queue: 18
```

This logging shows:
- Exact simulation clock time
- Queue size and next event
- Each event processed with details
- Location and severity for scout reports
- Summary of what was collected

---

## 🧪 Testing Instructions

### Step 1: Start Backend with Verbose Logging

```bash
cd masfro-backend
uv run uvicorn app.main:app --reload --log-level debug
```

### Step 2: Start Simulation

```bash
curl -X POST "http://localhost:8000/api/simulation/start?mode=medium"
```

**Watch Backend Logs** - You should see:
```
INFO: Simulation start request received - Mode: medium
INFO: Loaded scenario 'Medium Flood Scenario (from CSV)' with 24 events.
INFO: Simulation STARTED - Mode: MEDIUM
INFO: === TICK 1 START === Clock: 0.00s, Time step: 1/18
INFO: Collection phase START - Clock: 0.00s, Queue size: 24, Next event: agent=flood_agent, time=0s
INFO: Processing event #1: agent=flood_agent, time_offset=0s
INFO: ✓ Flood data collected: 3 data points
INFO: Collection phase COMPLETE - Events processed: 1 ...
```

### Step 3: Wait for Scout Events (5-10 seconds)

Scout events in medium_scenario.csv start at:
- 5s - SM Marikina
- 10s - Nangka
- 20s - J.P. Rizal
- 30s - (more flood data)
- 35s - Concepcion Uno
- etc.

**Watch logs** for:
```
INFO: Collection phase START - Clock: 5.23s, Queue size: 20, Next event: agent=scout_agent, time=5s
INFO: Processing event #X: agent=scout_agent, time_offset=5s
INFO: ✓ Scout report collected: location='SM Marikina', severity=0.35
```

### Step 4: Inspect Cache Using Debug Endpoint

```bash
# After 10 seconds, check cache
curl "http://localhost:8000/api/debug/hazard-cache" | jq '.cache_sizes'
```

**Expected**:
```json
{
  "flood": 1,
  "scout": 2
}
```

If `scout: 0`, events haven't been processed yet or there's an issue.

### Step 5: Query Scout Reports (AgentDataPanel Endpoint)

```bash
curl "http://localhost:8000/api/agents/scout/reports?limit=50&hours=24" | jq '.total_reports'
```

**Expected**: Number > 0

If 0, check:
1. Is simulation running? `curl http://localhost:8000/api/simulation/status`
2. Has enough time passed? Check simulation_clock in debug endpoint
3. Are events being processed? Check backend logs

### Step 6: Test Stop Simulation

```bash
curl -X POST "http://localhost:8000/api/simulation/stop"
```

**Watch logs** for:
```
INFO: Simulation stop request received
INFO: Simulation STOPPED (paused) - Total runtime: 12.34s, Ticks: 12
```

**Verify state**:
```bash
curl "http://localhost:8000/api/simulation/status" | jq '.state'
# Expected: "paused"
```

---

## 🐛 Debugging Workflow

If issues persist, follow this workflow:

### 1. Verify Simulation State

```bash
curl "http://localhost:8000/api/simulation/status"
```

Check:
- `state` should be "running" during simulation
- `tick_count` should be increasing
- `time_step` should advance (1-18)

### 2. Inspect Event Queue

```bash
curl "http://localhost:8000/api/debug/simulation-events"
```

Check:
- `simulation_clock` matches expected value
- `upcoming_events` shows events with time_offset values
- `total_events_remaining` decreases as events are processed

### 3. Inspect Cache Contents

```bash
curl "http://localhost:8000/api/debug/hazard-cache"
```

Check:
- `cache_sizes.scout` increases as scout events are processed
- `scout_data_cache` array contains objects with expected fields:
  - `location`
  - `coordinates` (with lat/lon)
  - `severity`
  - `text`
  - `timestamp`

### 4. Check Backend Logs

Look for:
- ✅ `"Processing event #X: agent=scout_agent"`
- ✅ `"Scout report collected: location='...', severity=..."`
- ✅ `"Added X scout reports (total: Y)"` (from hazard_agent.py:471)
- ❌ Any errors or warnings

### 5. Test Frontend Independently

Open browser DevTools Console:
```javascript
// Test API directly
fetch('http://localhost:8000/api/agents/scout/reports?limit=50&hours=24')
  .then(r => r.json())
  .then(d => console.log('Scout reports:', d.total_reports, d.reports));

// Test debug endpoint
fetch('http://localhost:8000/api/debug/hazard-cache')
  .then(r => r.json())
  .then(d => console.log('Cache sizes:', d.cache_sizes));
```

---

## 📊 Expected vs Actual Behavior

### Expected Behavior

**Simulation Start**:
1. State changes to "running"
2. Tick loop starts
3. Events are processed at their time_offsets
4. Scout reports accumulate in hazard_agent.scout_data_cache
5. AgentDataPanel queries /api/agents/scout/reports and displays data

**Simulation Stop**:
1. Tick loop task is cancelled
2. State changes to "paused"
3. Cache persists (not cleared)
4. AgentDataPanel continues to show accumulated data

### If Not Working

**Symptom**: Stop doesn't work
- **Check**: Backend logs show "Simulation STOPPED"?
  - YES: Frontend issue - check UI state management
  - NO: Backend issue - check for exceptions in logs

**Symptom**: No scout reports in AgentDataPanel
- **Check**: `curl http://localhost:8000/api/debug/hazard-cache`
  - `scout: 0`: Events not reaching cache - check logs for "Processing event"
  - `scout: >0`: Data IS in cache - frontend issue or timing issue

---

## 🔍 Next Steps

1. **Run the tests above** to identify where the flow breaks
2. **Check backend logs** for the enhanced logging messages
3. **Use debug endpoints** to inspect internal state
4. **Report findings**:
   - What do the debug endpoints show?
   - What do backend logs show during simulation?
   - Does frontend show any errors in console?

With this information, we can pinpoint the exact issue and apply a targeted fix.

---

## 📁 Files Modified

1. ✅ `masfro-backend/app/main.py` - Added 2 debug endpoints
2. ✅ `masfro-backend/app/services/simulation_manager.py` - Enhanced logging in collection phase
3. ✅ `SIMULATION_DEBUGGING_GUIDE.md` - Comprehensive debugging documentation
4. ✅ `SIMULATION_FIXES_APPLIED.md` - This file

---

## 💡 Quick Diagnostic Command

Run this to get a snapshot of simulation state:

```bash
echo "=== Simulation Status ===" && \
curl -s "http://localhost:8000/api/simulation/status" | jq && \
echo "" && \
echo "=== Cache Sizes ===" && \
curl -s "http://localhost:8000/api/debug/hazard-cache" | jq '.cache_sizes' && \
echo "" && \
echo "=== Scout Reports Count ===" && \
curl -s "http://localhost:8000/api/agents/scout/reports" | jq '.total_reports'
```

Expected output when working:
```
=== Simulation Status ===
{
  "status": "success",
  "state": "running",
  "tick_count": 25
}

=== Cache Sizes ===
{
  "flood": 8,
  "scout": 12
}

=== Scout Reports Count ===
12
```
