# FloodDataScheduler Migration to MAS Architecture

**Status:** ✅ **COMPLETE**
**Date:** November 20, 2025

---

## Summary

Fixed `FloodDataScheduler` to use the new MAS architecture with MessageQueue-based communication after FloodAgent refactoring removed the `collect_and_forward_data()` method.

---

## Error Message

```
ERROR - [ERROR] Scheduled collection error: 'FloodAgent' object has no attribute 'collect_and_forward_data'
```

---

## Root Cause

During the MAS refactoring, `FloodAgent` method was renamed:
- **Old:** `collect_and_forward_data()` - collected data AND forwarded to HazardAgent directly
- **New:** `collect_flood_data()` - only collects data (no forwarding)
- **New:** `send_flood_data_via_message(data)` - sends data to HazardAgent via MessageQueue

The `FloodDataScheduler` was still calling the old method name in two places.

---

## Changes Made

### 1. Scheduled Collection Loop (Line 194-239)

**File:** `masfro-backend/app/services/flood_data_scheduler.py`

**Before:**
```python
# Call FloodAgent data collection
data = await asyncio.to_thread(
    self.flood_agent.collect_and_forward_data  # ❌ Method doesn't exist
)

# ... WebSocket broadcast ...

# Forward to HazardAgent (if hazard_agent is not None)
if self.hazard_agent:
    await asyncio.to_thread(
        self.hazard_agent.update_risk,
        flood_data=data,
        scout_data=[]
    )
```

**After:**
```python
# Call FloodAgent data collection
# NOTE: Using new MAS architecture - collect data then send via MessageQueue
data = await asyncio.to_thread(
    self.flood_agent.collect_flood_data  # ✅ New method name
)

# ... WebSocket broadcast ...

# Send data to HazardAgent via MessageQueue (MAS architecture)
try:
    await asyncio.to_thread(
        self.flood_agent.send_flood_data_via_message,
        data
    )
    logger.debug("Flood data sent to HazardAgent via MessageQueue")
except Exception as msg_error:
    logger.error(f"MessageQueue send error: {msg_error}")

# Forward to HazardAgent cache for frontend API endpoints (legacy, deprecated)
if self.hazard_agent:  # This is now None, so won't execute
    await asyncio.to_thread(
        self.hazard_agent.update_risk,
        flood_data=data,
        scout_data=[]
    )
```

---

### 2. Manual Collection Trigger (Line 367-399)

**File:** `masfro-backend/app/services/flood_data_scheduler.py`

**Before:**
```python
try:
    start_time = datetime.now()
    data = await asyncio.to_thread(
        self.flood_agent.collect_and_forward_data  # ❌ Method doesn't exist
    )

    # ... database save and WebSocket broadcast ...

    # Forward to HazardAgent
    if data and self.hazard_agent:
        await asyncio.to_thread(
            self.hazard_agent.update_risk,
            flood_data=data,
            scout_data=[]
        )
```

**After:**
```python
try:
    start_time = datetime.now()
    # NOTE: Using new MAS architecture - collect data then send via MessageQueue
    data = await asyncio.to_thread(
        self.flood_agent.collect_flood_data  # ✅ New method name
    )

    # ... database save and WebSocket broadcast ...

    # Send data to HazardAgent via MessageQueue (MAS architecture)
    if data:
        try:
            await asyncio.to_thread(
                self.flood_agent.send_flood_data_via_message,
                data
            )
            logger.debug("Manual collection: Flood data sent to HazardAgent via MessageQueue")
        except Exception as msg_error:
            logger.error(f"MessageQueue send error: {msg_error}")

    # Forward to HazardAgent cache for frontend API endpoints (legacy, deprecated)
    if data and self.hazard_agent:  # This is now None, so won't execute
        await asyncio.to_thread(
            self.hazard_agent.update_risk,
            flood_data=data,
            scout_data=[]
        )
```

---

## Verification

### Import Test
```bash
cd masfro-backend
uv run python -c "from app.main import app; print('Backend imports successfully!')"
```

**Result:**
```
✅ FloodDataScheduler initialized with interval=300s (5.0 minutes),
   WebSocket broadcasting=enabled, HazardAgent forwarding=disabled
✅ MAS-FRO system initialized successfully
✅ Backend imports successfully!
```

---

## Data Flow Diagram

### Old Architecture (Before MAS)

```
┌─────────────────────┐
│ FloodDataScheduler  │
└──────────┬──────────┘
           │
           │ collect_and_forward_data()
           ↓
┌──────────────────────┐
│    FloodAgent        │
│  (collects data +    │
│   forwards directly) │
└──────────┬───────────┘
           │
           │ Direct method call:
           │ hazard_agent.update_risk()
           ↓
┌──────────────────────┐
│    HazardAgent       │
└──────────────────────┘

Issues:
❌ Tight coupling
❌ Synchronous blocking
```

### New Architecture (After MAS)

```
┌─────────────────────┐
│ FloodDataScheduler  │
└──────────┬──────────┘
           │
           │ 1. collect_flood_data()
           ↓
┌──────────────────────┐
│    FloodAgent        │
└──────────┬───────────┘
           │
           │ 2. send_flood_data_via_message()
           ↓
┌──────────────────────┐
│    MessageQueue      │
└──────────┬───────────┘
           │
           │ 3. queue.put(ACLMessage)
           ↓
┌──────────────────────┐
│    HazardAgent       │
│  (polls queue in     │
│   step() method)     │
└──────────────────────┘

Benefits:
✅ Decoupled agents
✅ Asynchronous non-blocking
✅ FIPA-ACL protocol
✅ Scalable
```

---

## Scheduler Workflow

### Automatic Scheduled Collection (Every 5 Minutes)

1. **Timer triggers** → `_run_scheduled_loop()`
2. **Collect data** → `flood_agent.collect_flood_data()`
3. **Save to database** → `_save_to_database(data)`
4. **Broadcast WebSocket** → `ws_manager.broadcast_flood_update(data)`
5. **Send to HazardAgent** → `flood_agent.send_flood_data_via_message(data)` ✅ NEW
6. **Wait** → Sleep for 300 seconds (5 minutes)
7. **Repeat**

### Manual Collection (API Trigger)

API endpoint: `POST /api/flood-data/trigger-collection`

Same workflow as scheduled collection, but triggered on-demand instead of by timer.

---

## Expected Log Messages

### Successful Scheduled Collection

```
INFO - Scheduler triggering flood data collection...
INFO - [OK] Scheduled collection successful: 8 data points in 2.35s
DEBUG - WebSocket broadcast completed
DEBUG - Flood data sent to HazardAgent via MessageQueue  # ✅ NEW
INFO - [DB] Saved flood_collections record: collection_id=abc123...
```

### Successful Manual Collection

```
INFO - Manual collection triggered via API
INFO - Manual collection broadcast completed
DEBUG - Manual collection: Flood data sent to HazardAgent via MessageQueue  # ✅ NEW
```

### HazardAgent Receives Message

```
DEBUG - hazard_agent_001 performing step at 2025-11-20 11:40:00
INFO - hazard_agent_001 processed 1 messages from queue
INFO - hazard_agent_001 received flood data batch from flood_agent_001: 8 locations
DEBUG - Location Sto Nino: rainfall_1h=25.0mm/hr, rain_risk=0.60, depth_risk=0.00, combined=0.30
INFO - hazard_agent_001 updated 1234 edges with risk scores
```

---

## Testing

### 1. Start Backend Server

```bash
cd masfro-backend
uv run uvicorn app.main:app --reload
```

### 2. Wait for Scheduled Collection (5 Minutes)

The scheduler will automatically trigger every 5 minutes. Watch for:
- ✅ "Scheduler triggering flood data collection..."
- ✅ "Flood data sent to HazardAgent via MessageQueue"

### 3. Trigger Manual Collection

```bash
curl -X POST "http://localhost:8000/api/flood-data/trigger-collection"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Manual collection completed",
  "data_points": 8,
  "duration_seconds": 2.35,
  "timestamp": "2025-11-20T11:40:00.123456"
}
```

### 4. Start Simulation to Verify MAS Communication

```bash
curl -X POST "http://localhost:8000/api/simulation/start?mode=light"
```

Watch logs for message flow:
1. FloodAgent collects data
2. FloodAgent sends via MessageQueue
3. HazardAgent receives and processes message
4. Graph edges updated with risk scores

---

## Related Files Modified

### This Migration:
- ✅ `masfro-backend/app/services/flood_data_scheduler.py` (lines 194, 231-239, 367, 390-399)

### Previous MAS Migrations:
- ✅ `masfro-backend/app/agents/flood_agent.py` - Renamed method and added MessageQueue
- ✅ `masfro-backend/app/agents/hazard_agent.py` - Added MessageQueue and message handlers
- ✅ `masfro-backend/app/main.py` - Updated agent initialization

---

## Rollback Instructions (If Needed)

If you need to revert the FloodDataScheduler changes:

```python
# In flood_data_scheduler.py:

# 1. Revert method name (lines 194, 367)
data = await asyncio.to_thread(
    self.flood_agent.collect_and_forward_data  # Old method
)

# 2. Remove MessageQueue sending code (lines 231-239, 390-399)
# DELETE the try/except block with send_flood_data_via_message

# 3. Keep the hazard_agent forwarding (it will work if hazard_agent is not None)
```

**Note:** This requires reverting FloodAgent and main.py changes as well.

---

## Related Documentation

- **MAS Architecture:** `MAS_REFACTORING_COMPLETE.md`
- **main.py Migration:** `MAIN_PY_MAS_MIGRATION.md`
- **Risk Improvements:** `HAZARD_AGENT_RISK_IMPROVEMENTS.md`

---

**End of Document**
