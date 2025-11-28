# main.py Migration to MAS Architecture

**Status:** ✅ **COMPLETE**
**Date:** November 20, 2025

---

## Summary

Updated `main.py` to use the new MAS (Multi-Agent System) architecture with MessageQueue-based communication for FloodAgent and HazardAgent.

---

## Changes Made

### 1. HazardAgent Initialization (Line 415-420)

**Before:**
```python
hazard_agent = HazardAgent("hazard_agent_001", environment, enable_geotiff=True)
```

**After:**
```python
hazard_agent = HazardAgent(
    "hazard_agent_001",
    environment,
    message_queue=message_queue,  # MAS communication
    enable_geotiff=True
)
```

**Reason:** HazardAgent now requires MessageQueue for receiving messages from FloodAgent and other agents.

---

### 2. FloodAgent Initialization (Line 423-430)

**Before:**
```python
flood_agent = FloodAgent(
    "flood_agent_001",
    environment,
    hazard_agent=hazard_agent,  # ❌ Direct reference (tight coupling)
    use_simulated=False,
    use_real_apis=True
)
```

**After:**
```python
flood_agent = FloodAgent(
    "flood_agent_001",
    environment,
    message_queue=message_queue,  # ✅ MAS communication
    use_simulated=False,
    use_real_apis=True,
    hazard_agent_id="hazard_agent_001"  # Target agent for messages
)
```

**Changes:**
- ❌ Removed `hazard_agent=hazard_agent` (tight coupling)
- ✅ Added `message_queue=message_queue` (MAS communication)
- ✅ Added `hazard_agent_id="hazard_agent_001"` (message routing)

**Reason:** FloodAgent now sends data to HazardAgent via MessageQueue using FIPA-ACL protocol instead of direct method calls.

---

### 3. Removed Direct Linking (Line 441 - DELETED)

**Before:**
```python
# Link agents (create agent network)
flood_agent.set_hazard_agent(hazard_agent)  # ❌ DELETED
evacuation_manager.set_hazard_agent(hazard_agent)
evacuation_manager.set_routing_agent(routing_agent)
```

**After:**
```python
# NOTE: FloodAgent and HazardAgent now communicate via MessageQueue (MAS architecture)
# Old direct linking methods (set_hazard_agent) removed for these agents
# ScoutAgent and EvacuationManager still use direct references (to be refactored later)
evacuation_manager.set_hazard_agent(hazard_agent)
evacuation_manager.set_routing_agent(routing_agent)
```

**Reason:** `FloodAgent.set_hazard_agent()` method was removed during MAS refactoring. FloodAgent and HazardAgent now communicate exclusively via MessageQueue.

---

### 4. FloodDataScheduler Initialization (Line 454-459)

**Before:**
```python
flood_scheduler = FloodDataScheduler(
    flood_agent,
    interval_seconds=300,
    ws_manager=ws_manager,
    hazard_agent=hazard_agent  # ❌ Direct forwarding
)
```

**After:**
```python
flood_scheduler = FloodDataScheduler(
    flood_agent,
    interval_seconds=300,
    ws_manager=ws_manager,
    hazard_agent=None  # ✅ FloodAgent handles HazardAgent communication via MessageQueue
)
```

**Reason:** FloodAgent now sends data to HazardAgent via MessageQueue in its `step()` method. The scheduler no longer needs to forward data directly to HazardAgent.

---

## Architecture Diagram

### Old (Before MAS Refactoring)

```
┌──────────────┐
│ FloodAgent   │
└──────┬───────┘
       │
       │ flood_agent.set_hazard_agent(hazard_agent)
       ↓
       │ Direct method call:
       │ hazard_agent.process_flood_data_batch(data)
       │
       ↓
┌──────────────┐
│ HazardAgent  │
└──────────────┘

Issues:
❌ Tight coupling
❌ Synchronous blocking
❌ Cannot scale to multiple agents
```

### New (After MAS Refactoring)

```
┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
│ FloodAgent   │                    │ MessageQueue │                    │ HazardAgent  │
└──────┬───────┘                    └──────┬───────┘                    └──────┬───────┘
       │                                   │                                   │
       │ 1. collect_flood_data()           │                                   │
       │                                   │                                   │
       │ 2. create_inform_message()        │                                   │
       │    (flood_data_batch)             │                                   │
       │                                   │                                   │
       │ 3. send_message(ACLMessage)       │                                   │
       │──────────────────────────────────>│                                   │
       │                                   │                                   │
       │                                   │ 4. queue.put(message)             │
       │                                   │───────────────────────────────────>│
       │                                   │                                   │
       │                                   │         5. step() - poll queue    │
       │                                   │<───────────────────────────────────│
       │                                   │                                   │
       │                                   │ 6. receive_message()              │
       │                                   │───────────────────────────────────>│
       │                                   │                                   │
       │                                   │ 7. return ACLMessage              │
       │                                   │<───────────────────────────────────│
       │                                   │                                   │
       │                                   │    8. _handle_inform_message()    │
       │                                   │    9. process_flood_data_batch()  │
       │                                   │       10. update_graph_edges()    │
       │                                   │                                   │

Benefits:
✅ Decoupled agents
✅ Asynchronous non-blocking
✅ Scalable to 100+ agents
✅ FIPA-ACL standard protocol
```

---

## Verification Logs

**Backend Import Test:**
```bash
cd masfro-backend
uv run python -c "from app.main import app"
```

**Key Log Messages (Success):**
```
2025-11-20 11:27:40 - app.communication.message_queue - INFO - Agent hazard_agent_001 registered with message queue
2025-11-20 11:27:40 - app.agents.hazard_agent - INFO - hazard_agent_001 registered with MessageQueue
2025-11-20 11:27:40 - app.agents.hazard_agent - INFO - hazard_agent_001 built spatial index: 35932 edges in 34 grid cells (avg 1056.8 edges/cell)
2025-11-20 11:27:40 - app.agents.hazard_agent - INFO - hazard_agent_001 initialized with ... geotiff_enabled: True, risk_decay: ENABLED, spatial_filtering: ENABLED (radius=800m)

2025-11-20 11:27:40 - app.communication.message_queue - INFO - Agent flood_agent_001 registered with message queue
2025-11-20 11:27:40 - app.agents.flood_agent - INFO - flood_agent_001 registered with MessageQueue

2025-11-20 11:27:41 - app.services.flood_data_scheduler - INFO - FloodDataScheduler initialized with interval=300s (5.0 minutes), WebSocket broadcasting=enabled, HazardAgent forwarding=disabled

2025-11-20 11:27:41 - app.main - INFO - MAS-FRO system initialized successfully
```

**Key Indicators of Success:**
- ✅ Both agents registered with MessageQueue
- ✅ Spatial index built successfully (35,932 edges in 34 grid cells)
- ✅ Spatial filtering enabled (800m radius)
- ✅ FloodDataScheduler shows "HazardAgent forwarding=disabled"
- ✅ System initialized successfully

---

## Testing MAS Communication

### Start Backend Server
```bash
cd masfro-backend
uv run uvicorn app.main:app --reload
```

### Start Simulation
```bash
curl -X POST "http://localhost:8000/api/simulation/start?mode=light"
```

### Expected Log Pattern (Each Tick)

**FloodAgent Step:**
```
DEBUG - flood_agent_001 performing step at 2025-11-20 11:30:00
INFO - flood_agent_001 sending flood data for 8 locations to hazard_agent_001 via MessageQueue
INFO - flood_agent_001 successfully sent INFORM message to hazard_agent_001 (8 locations)
```

**HazardAgent Step:**
```
DEBUG - hazard_agent_001 performing step at 2025-11-20 11:30:00.100
INFO - hazard_agent_001 processed 1 messages from queue
INFO - hazard_agent_001 received flood data batch from flood_agent_001: 8 locations
DEBUG - Spatial query (indexed): Found 342 edges within 800m of (14.6341, 121.1014) - checked 387 edges in 12 grid cells
INFO - hazard_agent_001 updated 1234 edges with risk scores
```

---

## Migration Impact

### Breaking Changes
1. **FloodAgent:**
   - ❌ `hazard_agent` parameter removed from `__init__`
   - ❌ `set_hazard_agent()` method removed
   - ✅ `message_queue` parameter required
   - ✅ `hazard_agent_id` parameter optional (defaults to "hazard_agent_001")

2. **HazardAgent:**
   - ✅ `message_queue` parameter required

3. **FloodDataScheduler:**
   - ℹ️ `hazard_agent` parameter still exists but should be set to `None`
   - ℹ️ May be refactored to remove this parameter entirely in future

### Backward Compatibility
- **ScoutAgent:** Still uses direct `hazard_agent` reference (not yet refactored)
- **EvacuationManager:** Still uses `set_hazard_agent()` method (not yet refactored)
- **RoutingAgent:** No changes needed

---

## Future Refactoring

### To Be Migrated to MAS:
1. **ScoutAgent** → MessageQueue communication with HazardAgent
2. **EvacuationManager** → MessageQueue communication with HazardAgent and RoutingAgent
3. **FloodDataScheduler** → Remove `hazard_agent` parameter entirely

### Migration Priority:
1. **High:** ScoutAgent (currently has direct hazard_agent reference)
2. **Medium:** EvacuationManager (uses set_hazard_agent)
3. **Low:** FloodDataScheduler (already handles None gracefully)

---

## Rollback Instructions (If Needed)

If you need to revert to the old architecture:

```python
# In main.py:

# 1. Revert HazardAgent initialization
hazard_agent = HazardAgent("hazard_agent_001", environment, enable_geotiff=True)

# 2. Revert FloodAgent initialization
flood_agent = FloodAgent(
    "flood_agent_001",
    environment,
    hazard_agent=hazard_agent,  # Direct reference
    use_simulated=False,
    use_real_apis=True
)

# 3. Re-add direct linking
flood_agent.set_hazard_agent(hazard_agent)

# 4. Revert FloodDataScheduler
flood_scheduler = FloodDataScheduler(
    flood_agent,
    interval_seconds=300,
    ws_manager=ws_manager,
    hazard_agent=hazard_agent  # Direct forwarding
)
```

**Note:** This requires reverting the FloodAgent and HazardAgent code changes as well.

---

## Related Documentation

- **MAS Architecture:** `MAS_REFACTORING_COMPLETE.md`
- **Risk Improvements:** `HAZARD_AGENT_RISK_IMPROVEMENTS.md`
- **WebSocket Missing:** `WEBSOCKET_GRAPH_BROADCASTS_MISSING.md`

---

**End of Document**
