# WebSocket Graph Broadcasts - MISSING Implementation

**Status:** ❌ **Graph update broadcasts are NOT implemented**
**Date:** November 20, 2025

---

## Summary

Your backend **does NOT** broadcast graph edge risk updates via WebSocket, even though:
- ✅ GeoTIFF integration is working (verified by tests)
- ✅ Graph edges ARE being updated with risk scores
- ✅ Frontend has a `risk_update` message handler (line 100-103 in `useWebSocket.js`)
- ❌ Backend NEVER sends `risk_update` messages

---

## Current WebSocket Broadcasts

### Backend Broadcasts (masfro-backend/app/main.py)

```python
# ConnectionManager class has 3 broadcast methods:

1. broadcast_flood_update(flood_data)        # ✓ Implemented
2. broadcast_critical_alert(...)             # ✓ Implemented
3. broadcast_scheduler_update(status)        # ✓ Implemented
```

**Missing:** `broadcast_graph_update()` or `broadcast_risk_update()`

---

### Frontend Message Handlers (masfro-frontend/src/hooks/useWebSocket.js)

```javascript
switch (data.type) {
  case 'connection':         // ✓ Receives
  case 'system_status':      // ✓ Receives
  case 'statistics_update':  // ✓ Receives
  case 'flood_update':       // ✓ Receives
  case 'critical_alert':     // ✓ Receives
  case 'scheduler_update':   // ✓ Receives
  case 'risk_update':        // ❌ NEVER RECEIVES (handler exists but no backend broadcast!)
  case 'pong':               // ✓ Receives
}
```

**Line 100-103:**
```javascript
case 'risk_update':
  // Handle risk level updates
  console.log('⚠️ Risk update received:', data);
  break;
```

The frontend is **ready** to receive risk updates, but the backend never sends them!

---

## Where to Add Graph Broadcasts

### Option 1: In SimulationManager (Recommended)

**File:** `masfro-backend/app/services/simulation_manager.py:627-678`

```python
async def _run_fusion_phase(self) -> Dict[str, Any]:
    """Phase 2: Data fusion and graph update by HazardAgent."""

    # ... existing code ...

    # Call HazardAgent's update_risk method
    update_result = self.hazard_agent.update_risk(
        flood_data=flood_data,
        scout_data=scout_data,
        time_step=self.current_time_step
    )

    phase_result["edges_updated"] = update_result.get("edges_updated", 0)
    self.shared_data_bus["graph_updated"] = True

    # ✅ ADD THIS: Broadcast graph update via WebSocket
    if self.ws_manager and update_result.get("edges_updated", 0) > 0:
        await self._broadcast_graph_update(update_result)

    return phase_result

async def _broadcast_graph_update(self, update_result: Dict[str, Any]):
    """Broadcast graph risk update to WebSocket clients."""
    await self.ws_manager.broadcast({
        "type": "risk_update",
        "edges_updated": update_result.get("edges_updated", 0),
        "average_risk": update_result.get("average_risk", 0.0),
        "risk_trend": update_result.get("risk_trend", "stable"),
        "time_step": update_result.get("time_step", 1),
        "timestamp": datetime.now().isoformat()
    })
```

---

### Option 2: In ConnectionManager (Alternative)

**File:** `masfro-backend/app/main.py` (add to ConnectionManager class)

```python
async def broadcast_graph_update(
    self,
    edges_updated: int,
    average_risk: float,
    risk_trend: str,
    time_step: int,
    sample_edges: Optional[List[Dict]] = None
):
    """
    Broadcast graph edge risk update to all connected clients.

    Args:
        edges_updated: Number of edges with updated risk scores
        average_risk: Average risk across all edges
        risk_trend: Risk trend ("increasing", "decreasing", "stable")
        time_step: Current simulation time step (1-18)
        sample_edges: Optional sample of updated edges for visualization
    """
    if not self.active_connections:
        return  # No clients to broadcast to

    message = {
        "type": "risk_update",
        "edges_updated": edges_updated,
        "average_risk": round(average_risk, 4),
        "risk_trend": risk_trend,
        "time_step": time_step,
        "sample_edges": sample_edges[:10] if sample_edges else [],
        "timestamp": datetime.now().isoformat(),
        "source": "hazard_agent"
    }

    await self.broadcast(message)
    logger.info(
        f"Broadcasted graph update: {edges_updated} edges, "
        f"avg_risk={average_risk:.4f}, trend={risk_trend}"
    )
```

Then call it from SimulationManager:
```python
await self.ws_manager.broadcast_graph_update(
    edges_updated=update_result["edges_updated"],
    average_risk=update_result["average_risk"],
    risk_trend=update_result["risk_trend"],
    time_step=self.current_time_step
)
```

---

### Option 3: In HazardAgent.update_environment() (Direct)

**File:** `masfro-backend/app/agents/hazard_agent.py:1109-1138`

```python
def update_environment(self, risk_scores: Dict[Tuple, float]) -> None:
    """Update graph edges with calculated risk scores."""

    if not self.environment or not self.environment.graph:
        logger.warning("No environment graph to update")
        return

    updated_count = 0
    for edge_tuple, risk_score in risk_scores.items():
        u, v, key = edge_tuple
        if self.environment.graph.has_edge(u, v, key):
            self.environment.graph[u][v][key]["risk_score"] = risk_score
            self.environment.graph[u][v][key]["last_risk_update"] = get_philippine_time()
            updated_count += 1

    logger.info(f"{self.agent_id} updated {updated_count} edges with risk scores")

    # ✅ ADD THIS: Trigger WebSocket broadcast (if ws_manager available)
    if hasattr(self, 'ws_manager') and self.ws_manager:
        # Would need to make this method async or use asyncio.create_task
        # This approach is less clean than Option 1
        pass
```

**Note:** This option requires making `update_environment()` async or using background tasks. Not recommended.

---

## Recommended Implementation

**Use Option 1 (SimulationManager) because:**

1. ✅ SimulationManager already has `ws_manager` instance
2. ✅ SimulationManager orchestrates all updates
3. ✅ Centralized broadcast logic
4. ✅ Already async (no refactoring needed)
5. ✅ Broadcasts only when simulation is running

---

## Implementation Steps

### Step 1: Add broadcast method to SimulationManager

```python
# In masfro-backend/app/services/simulation_manager.py

async def _broadcast_graph_update(self, update_result: Dict[str, Any]):
    """Broadcast graph risk update to WebSocket clients."""
    if not self.ws_manager:
        return

    await self.ws_manager.broadcast({
        "type": "risk_update",
        "data": {
            "edges_updated": update_result.get("edges_updated", 0),
            "average_risk": update_result.get("average_risk", 0.0),
            "risk_trend": update_result.get("risk_trend", "stable"),
            "risk_change_rate": update_result.get("risk_change_rate", 0.0),
            "time_step": update_result.get("time_step", 1),
            "active_reports": update_result.get("active_reports", 0)
        },
        "timestamp": datetime.now().isoformat(),
        "source": "hazard_agent"
    })
```

### Step 2: Call it from _run_fusion_phase

```python
# In _run_fusion_phase() method, after update_risk():

update_result = self.hazard_agent.update_risk(
    flood_data=flood_data,
    scout_data=scout_data,
    time_step=self.current_time_step
)

phase_result["edges_updated"] = update_result.get("edges_updated", 0)
self.shared_data_bus["graph_updated"] = True

# ✅ Broadcast to WebSocket clients
if update_result.get("edges_updated", 0) > 0:
    await self._broadcast_graph_update(update_result)

logger.info(
    f"HazardAgent updated {phase_result['edges_updated']} edges "
    f"(time_step={self.current_time_step})"
)
```

### Step 3: Test the implementation

```bash
# 1. Start backend
cd masfro-backend
uv run uvicorn app.main:app --reload

# 2. Start simulation
curl -X POST "http://localhost:8000/api/simulation/start?mode=moderate"

# 3. Connect WebSocket client (browser console)
const ws = new WebSocket('ws://localhost:8000/ws/route-updates');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'risk_update') {
    console.log('RISK UPDATE:', data);
  }
};

# 4. Check frontend console logs
# Should see: "⚠️ Risk update received: {...}"
```

---

## Frontend Integration (Already Done!)

The frontend is **already ready** to handle `risk_update` messages:

**File:** `masfro-frontend/src/hooks/useWebSocket.js:100-103`

```javascript
case 'risk_update':
  // Handle risk level updates
  console.log('⚠️ Risk update received:', data);
  break;
```

**To make use of the data:**

```javascript
case 'risk_update':
  setGraphRiskData(data.data);  // Store in state
  console.log('⚠️ Risk update received:', {
    edges: data.data.edges_updated,
    avgRisk: data.data.average_risk,
    trend: data.data.risk_trend,
    timeStep: data.data.time_step
  });
  break;
```

Then use `graphRiskData` in your map component to re-render edge colors!

---

## Expected Behavior After Fix

1. **Simulation starts** → `POST /api/simulation/start`
2. **Each tick (every few seconds):**
   - HazardAgent updates graph edges with GeoTIFF data
   - SimulationManager broadcasts `risk_update` via WebSocket
   - Frontend receives update and console logs: `⚠️ Risk update received`
   - Map re-renders edges with updated risk colors

3. **User sees:**
   - Green edges turn yellow/orange/red as flood progresses
   - Real-time visual feedback of changing flood conditions
   - Time step indicator updating (1 → 2 → ... → 18)

---

## Summary

**Problem:** Graph edges ARE being updated, but frontend doesn't know about it.

**Root Cause:** Missing WebSocket broadcast for graph updates.

**Solution:** Add `_broadcast_graph_update()` to SimulationManager and call it after HazardAgent.update_risk().

**Effort:** ~10 lines of code

**Impact:** Frontend will immediately see graph edge risk updates in real-time!

---

## Quick Fix Code (Copy-Paste Ready)

Add this to `masfro-backend/app/services/simulation_manager.py`:

```python
# After the _run_fusion_phase method, add:

async def _broadcast_graph_update(self, update_result: Dict[str, Any]):
    """Broadcast graph risk update to WebSocket clients."""
    if not self.ws_manager:
        return

    await self.ws_manager.broadcast({
        "type": "risk_update",
        "data": {
            "edges_updated": update_result.get("edges_updated", 0),
            "average_risk": update_result.get("average_risk", 0.0),
            "risk_trend": update_result.get("risk_trend", "stable"),
            "time_step": update_result.get("time_step", 1)
        },
        "timestamp": datetime.now().isoformat()
    })
```

Then modify `_run_fusion_phase` around line 660:

```python
# After line 670 (after update_result is returned), add:

if update_result.get("edges_updated", 0) > 0:
    await self._broadcast_graph_update(update_result)
```

That's it! Your frontend will start receiving graph updates.
