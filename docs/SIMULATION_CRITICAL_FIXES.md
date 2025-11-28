# 🚨 Critical Simulation Fixes Applied

## Issues Fixed

### ✅ Issue 1: "Object of type coroutine is not JSON serializable"
**Root Cause**: Async methods `stop()` and `reset()` were called without `await` keyword

**Files Modified**:
- `masfro-backend/app/main.py`

**Changes**:
```python
# Line 943 - BEFORE:
result = sim_manager.stop()

# Line 943 - AFTER:
result = await sim_manager.stop()

# Line 996 - BEFORE:
result = sim_manager.reset()

# Line 996 - AFTER:
result = await sim_manager.reset()
```

**Impact**: Stop and Reset endpoints now work correctly without JSON serialization errors.

---

## ⚠️ Issue 2: AgentDataPanel Shows No Data

This requires diagnosis. Follow the testing procedure below.

---

## 🧪 Testing Procedure

### Step 1: Restart Backend with Latest Fixes

```bash
cd masfro-backend
# Kill existing backend process
taskkill /F /IM python.exe 2>nul
taskkill /F /IM uvicorn.exe 2>nul

# Start with verbose logging
uv run uvicorn app.main:app --reload --log-level debug
```

**Wait for**: `Application startup complete.`

---

### Step 2: Test Stop Simulation Fix

Open a new terminal:

```bash
# Start simulation
curl -X POST "http://localhost:8000/api/simulation/start?mode=medium"
# Expected: {"status":"success","state":"running",...}

# Wait 5 seconds
timeout /T 5 /NOBREAK

# Stop simulation (this was failing before)
curl -X POST "http://localhost:8000/api/simulation/stop"
# Expected: {"status":"success","message":"Simulation stopped (paused)",...}
# NOT: {"detail":"Error stopping simulation: Object of type coroutine is not JSON serializable"}
```

✅ **If you see the success response, the stop fix is working!**

---

### Step 3: Diagnose "No Data in AgentDataPanel"

#### 3.1 Check Simulation is Actually Running

```bash
curl "http://localhost:8000/api/simulation/status" | jq
```

**Expected**:
```json
{
  "status": "success",
  "state": "running",  # ← Should be "running"
  "mode": "medium",
  "tick_count": 10,    # ← Should be increasing
  "time_step": 5       # ← Should be 1-18
}
```

❌ **If state is "stopped" or "paused"**: Simulation didn't start properly.

---

#### 3.2 Check HazardAgent Cache

```bash
curl "http://localhost:8000/api/debug/hazard-cache" | jq
```

**Expected**:
```json
{
  "status": "success",
  "cache_sizes": {
    "flood": 3,    # ← Should be > 0
    "scout": 12    # ← Should be > 0 after 10+ seconds
  },
  "simulation_manager_state": {
    "state": "running",
    "tick_count": 15,
    "simulation_clock": 15.5  # ← Should be advancing
  }
}
```

❌ **If scout is 0**: Events aren't being processed. Check backend logs.

---

#### 3.3 Check Scout Reports Endpoint

```bash
curl "http://localhost:8000/api/agents/scout/reports?limit=50&hours=24" | jq
```

**Expected**:
```json
{
  "status": "success",
  "total_reports": 12,  # ← Should be > 0
  "reports": [
    {
      "location": "SM Marikina",
      "coordinates": {"lat": 14.655, "lon": 121.108},
      "severity": 0.35,
      "text": "Heavy rain at SM Marikina! ...",
      "timestamp": "2025-11-19T08:00:05Z"
    }
  ]
}
```

❌ **If total_reports is 0**: Data is not reaching the cache. Proceed to Step 3.4.

---

#### 3.4 Check Backend Logs

Look for these log messages in the backend terminal:

✅ **Good signs**:
```
INFO: Simulation start request received - Mode: medium
INFO: Loaded scenario 'Medium Flood Scenario (from CSV)' with 24 events.
INFO: Simulation STARTED - Mode: MEDIUM
INFO: === TICK 1 START === Clock: 0.00s, Time step: 1/18
INFO: Collection phase START - Clock: 0.00s, Queue size: 24, Next event: agent=flood_agent, time=0s
INFO: Processing event #1: agent=flood_agent, time_offset=0s
INFO: ✓ Flood data collected: 3 data points
INFO: Collection phase COMPLETE - Events processed: 1
```

After 5+ seconds:
```
INFO: Collection phase START - Clock: 5.23s, Queue size: 20, Next event: agent=scout_agent, time=5s
INFO: Processing event #X: agent=scout_agent, time_offset=5s
INFO: ✓ Scout report collected: location='SM Marikina', severity=0.35
```

❌ **Bad signs**:
- No "Processing event" messages → Events not being processed
- No "Scout report collected" messages → Scout events not reaching cache
- Any Python exceptions or errors

---

#### 3.5 Check Event Queue

```bash
curl "http://localhost:8000/api/debug/simulation-events" | jq
```

**Expected**:
```json
{
  "status": "success",
  "simulation_clock": 15.5,
  "total_events_remaining": 18,
  "upcoming_events": [
    {
      "time_offset": 20,
      "agent": "scout_agent",
      "payload": {...}
    }
  ]
}
```

❌ **If total_events_remaining is 0**: All events were processed. Either:
- Simulation ran too long and all events completed
- Event queue was empty from start (CSV not loaded properly)

---

### Step 4: Test Frontend AgentDataPanel

1. **Open Browser**: Navigate to `http://localhost:3000`
2. **Open DevTools Console** (F12)
3. **Start Simulation** via frontend button
4. **Watch Console Logs**:

✅ **Expected**:
```
[AgentDataPanel][INFO] Simulation state changed: stopped → running
[AgentDataPanel][INFO] Auto-refresh ENABLED
[AgentDataPanel][DEBUG] Auto-refresh: fetching latest data
[AgentDataPanel][INFO] Fetching scout reports
[AgentDataPanel][INFO] Successfully loaded 12 scout reports
```

❌ **Bad signs**:
```
[AgentDataPanel][ERROR] Failed to fetch simulation status
[AgentDataPanel][ERROR] Unable to load scout reports
[AgentDataPanel][ERROR] Backend server not responding
```

5. **Check AgentDataPanel Header**:
   - Should show "Sim: MEDIUM" with pulsing green dot
   - Scout agent status should be active (green)

6. **Check Scout Reports Tab**:
   - Should show report cards appearing after 5-10 seconds
   - Each card should have location, severity, text

---

## 🐛 Common Issues & Solutions

### Issue: Backend logs show "Simulation is not running" when stopping
**Cause**: Simulation already stopped or never started
**Solution**: Check status before stopping:
```bash
curl "http://localhost:8000/api/simulation/status"
```

---

### Issue: No scout reports after 30 seconds
**Cause**: Events not reaching their time_offset or cache not being queried correctly
**Check**:
1. Simulation clock advancing? → `curl localhost:8000/api/debug/hazard-cache | jq '.simulation_manager_state.simulation_clock'`
2. Event queue has scout events? → `curl localhost:8000/api/debug/simulation-events | jq '.upcoming_events[] | select(.agent=="scout_agent")'`
3. Backend logs show "Scout report collected"? → Check terminal

**Solutions**:
- If clock not advancing: Simulation stuck. Check backend for errors.
- If no scout events in queue: CSV file not loaded. Check `medium_scenario.csv` exists.
- If logs show collection but cache empty: Issue in HazardAgent. Check `hazard_agent.update_risk()` method.

---

### Issue: Frontend shows "Backend server not responding"
**Cause**: CORS issue or backend not running
**Solution**:
1. Check backend running: `curl http://localhost:8000/health`
2. Check CORS headers: Open DevTools → Network tab → Look for CORS errors
3. Restart backend with CORS fix if needed

---

### Issue: Auto-refresh not working in frontend
**Cause**: Simulation state not detected as "running"
**Check**:
1. Console shows "Auto-refresh ENABLED"?
2. Simulation indicator shows pulsing dot?
3. `/api/simulation/status` returns `state: "running"`?

**Solution**: Ensure simulation polling is working. Check DevTools Network tab for status polling requests every 3 seconds.

---

## 📊 Expected Timeline

From simulation start:

| Time | Expected Behavior |
|------|------------------|
| **0s** | Simulation starts, flood event processed |
| **5s** | First scout report (SM Marikina) collected |
| **10s** | Second scout report (Nangka) collected |
| **20s** | Third scout report (J.P. Rizal) collected |
| **30s** | More flood data collected |
| **35s** | Fourth scout report (Concepcion Uno) collected |

**Total**: ~15-20 scout reports over 18 time steps (5 minutes real time at 1 tick/sec)

---

## 🔧 Emergency Reset

If everything is broken:

```bash
# 1. Stop backend (Ctrl+C or):
taskkill /F /IM python.exe

# 2. Reset simulation state
curl -X POST "http://localhost:8000/api/simulation/reset"

# 3. Restart backend
cd masfro-backend
uv run uvicorn app.main:app --reload --log-level debug

# 4. Start fresh simulation
curl -X POST "http://localhost:8000/api/simulation/start?mode=medium"

# 5. Check cache after 10 seconds
timeout /T 10 /NOBREAK
curl "http://localhost:8000/api/debug/hazard-cache" | jq '.cache_sizes'
```

---

## 📝 Next Steps

1. **Test the stop fix** (Step 2 above) ✅
2. **Diagnose data issue** (Steps 3.1 → 3.5) 🔍
3. **Report findings**:
   - What does `/api/debug/hazard-cache` show?
   - What do backend logs show during simulation?
   - What do frontend console logs show?
   - Screenshots of AgentDataPanel if possible

With this information, we can pinpoint the exact cause of the "no data" issue.

---

## ✅ Summary

**Fixed**:
- ✅ Stop simulation coroutine error
- ✅ Reset simulation coroutine error

**To Diagnose**:
- ⚠️ AgentDataPanel showing no data (follow testing procedure above)

The fixes are deployed. Please follow the testing procedure and report back with the diagnostic results.
