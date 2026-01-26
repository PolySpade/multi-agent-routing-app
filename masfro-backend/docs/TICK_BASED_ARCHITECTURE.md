# Tick-Based Synchronization Architecture

**Date:** November 18, 2025
**Status:** ✅ IMPLEMENTED
**Architecture Pattern:** Tick-Based Synchronization with Central Orchestration

---

## 📋 Overview

The MAS-FRO system has been refactored from a **tightly-coupled, event-driven architecture** to a **tick-based synchronization pattern** managed by a central `SimulationManager`. This eliminates race conditions, ensures deterministic execution order, and properly synchronizes GeoTIFF time steps with agent operations.

### Key Benefits

✅ **Decoupled Agents:** Agents no longer call each other directly
✅ **Ordered Execution:** Collection → Fusion → Routing guaranteed
✅ **Time Synchronization:** GeoTIFF time steps align with simulation ticks
✅ **Thread Safety:** Graph updates protected by locks
✅ **Reproducibility:** Deterministic execution for testing

---

## 🏗️ Architecture Overview

### Before: Tightly Coupled (Problems)

```
FloodAgent.step()
    └─► FloodAgent.collect_and_forward_data()
        └─► self.hazard_agent.process_flood_data_batch()  ❌ Direct call
            └─► HazardAgent.update_environment()
                └─► environment.update_edge_risk()  ❌ Potential race condition

ScoutAgent.step()
    └─► self.hazard_agent.process_scout_data()  ❌ Direct call

RoutingAgent.calculate_route()  ❌ May read during graph update
```

**Issues:**
- Tight coupling between agents
- No execution order guarantees
- Race conditions on graph reads/writes
- GeoTIFF time step not synchronized
- Blocking operations

### After: Tick-Based (Solution)

```
SimulationManager.run_tick(time_step)
    │
    ├─► Phase 1: Collection
    │   ├─► flood_data = FloodAgent.collect_and_forward_data()  ✓ Returns data
    │   └─► scout_data = ScoutAgent.step()                       ✓ Returns data
    │
    ├─► Phase 2: Fusion (Graph Update)
    │   ├─► HazardAgent.set_flood_scenario(time_step)
    │   └─► HazardAgent.update_risk(flood_data, scout_data, time_step)
    │       └─► environment.update_edge_risk() [LOCKED]  ✓ Thread-safe
    │
    ├─► Phase 3: Routing (Read Updated Graph)
    │   └─► EvacuationManager.handle_route_request()  ✓ Reads after update
    │
    └─► Phase 4: Time Advancement
        └─► current_time_step += 1
```

**Guarantees:**
- ✓ Graph updated BEFORE routing calculations
- ✓ GeoTIFF time step matches simulation time
- ✓ Thread-safe graph operations
- ✓ Decoupled agent implementations

---

## 🔧 Component Details

### 1. SimulationManager (`app/services/simulation_manager.py`)

**Central orchestrator for tick-based execution.**

#### Key Methods

```python
class SimulationManager:
    def start(mode: str = "light") -> Dict[str, Any]:
        """Start simulation with specified flood scenario."""
        # mode: "light" (rr01), "medium" (rr02), "heavy" (rr03)
        # Configures HazardAgent GeoTIFF scenario

    def run_tick(time_step: Optional[int] = None) -> Dict[str, Any]:
        """Execute one simulation tick."""
        # Phases: Collection → Fusion → Routing → Advancement

    def add_route_request(start, end, preferences):
        """Queue route request for next tick."""

    def stop() -> Dict[str, Any]:
        """Pause simulation."""

    def reset() -> Dict[str, Any]:
        """Reset to initial state, clear graph risks."""
```

#### Shared Data Bus

```python
shared_data_bus = {
    "flood_data": {},          # FloodAgent output
    "scout_data": [],          # ScoutAgent output
    "graph_updated": False,    # HazardAgent status
    "pending_routes": []       # Route requests queue
}
```

#### Mode to GeoTIFF Mapping

```python
MODE_TO_RETURN_PERIOD = {
    "light": "rr01",   # 2-year flood
    "medium": "rr02",  # 5-year flood
    "heavy": "rr03"    # 10-year flood
}
```

---

### 2. FloodAgent Refactoring

**CHANGE:** Remove direct `HazardAgent` calls, return data instead.

#### Before (❌ Tight Coupling)

```python
def collect_and_forward_data(self) -> Dict[str, Any]:
    combined_data = {}
    # ... collect data ...

    if combined_data:
        self.send_to_hazard_agent(combined_data)  # ❌ Direct call
    return combined_data
```

#### After (✓ Decoupled)

```python
def collect_and_forward_data(self) -> Dict[str, Any]:
    """
    Collect flood data from ALL sources.

    NOTE: Returns data instead of forwarding to HazardAgent.
    SimulationManager handles data forwarding in fusion phase.
    """
    combined_data = {}
    # ... collect data ...

    if combined_data:
        logger.info(
            f"[COLLECTED] {len(combined_data)} data points "
            f"ready for fusion phase"
        )
    return combined_data  # ✓ No direct agent calls
```

---

### 3. HazardAgent Enhancement

**ADDITION:** New `update_risk()` method for SimulationManager integration.

#### New Method

```python
def update_risk(
    self,
    flood_data: Dict[str, Any],
    scout_data: List[Dict[str, Any]],
    time_step: int
) -> Dict[str, Any]:
    """
    Update risk assessment (called by SimulationManager).

    This is the entry point for tick-based architecture.
    Receives data from SimulationManager, updates caches,
    sets GeoTIFF scenario, and updates graph.

    Args:
        flood_data: Flood data from FloodAgent
        scout_data: Scout reports from ScoutAgent
        time_step: Current simulation time (1-18)

    Returns:
        {
            "locations_processed": int,
            "edges_updated": int,
            "time_step": int,
            "timestamp": str
        }
    """
    # Clear previous caches
    self.flood_data_cache.clear()
    self.scout_data_cache.clear()

    # Update caches from external data
    for location, data in flood_data.items():
        flood_data_entry = {
            "location": location,
            "flood_depth": data.get("flood_depth", 0.0),
            "rainfall_1h": data.get("rainfall_1h", 0.0),
            "rainfall_24h": data.get("rainfall_24h", 0.0),
            "timestamp": data.get("timestamp")
        }
        self.flood_data_cache[location] = flood_data_entry

    self.scout_data_cache = scout_data.copy()

    # Process data and update graph
    fused_data = self.fuse_data()
    risk_scores = self.calculate_risk_scores(fused_data)
    self.update_environment(risk_scores)

    return {
        "locations_processed": len(fused_data),
        "edges_updated": len(risk_scores),
        "time_step": time_step,
        "timestamp": get_philippine_time().isoformat()
    }
```

#### GeoTIFF Time Step Sync

The `SimulationManager` automatically sets the GeoTIFF scenario before calling `update_risk()`:

```python
# In SimulationManager._run_fusion_phase()
return_period = MODE_TO_RETURN_PERIOD[self._mode]
self.hazard_agent.set_flood_scenario(
    return_period=return_period,
    time_step=self.current_time_step
)
```

---

### 4. DynamicGraphEnvironment Thread Safety

**ADDITION:** Thread locks to prevent race conditions.

#### Enhanced with Locking

```python
class DynamicGraphEnvironment:
    def __init__(self):
        # ... existing code ...

        # Thread safety
        self._lock = Lock()
        self._is_updating = False

    def update_edge_risk(self, u, v, key, risk_factor: float):
        """Update edge risk (thread-safe)."""
        with self._lock:
            self._is_updating = True
            try:
                edge_data = self.graph.edges[u, v, key]
                edge_data['risk_score'] = risk_factor
                edge_data['weight'] = edge_data['length'] * (1.0 + risk_factor)
            finally:
                self._is_updating = False

    def batch_update_edge_risks(self, risk_updates: dict):
        """Batch update multiple edges (more efficient)."""
        with self._lock:
            self._is_updating = True
            try:
                updated_count = 0
                for (u, v, key), risk_factor in risk_updates.items():
                    edge_data = self.graph.edges[u, v, key]
                    edge_data['risk_score'] = risk_factor
                    edge_data['weight'] = edge_data['length'] * (1.0 + risk_factor)
                    updated_count += 1
                logger.info(f"Batch updated {updated_count} edges")
            finally:
                self._is_updating = False

    def is_updating(self) -> bool:
        """Check if update in progress."""
        return self._is_updating
```

---

## 📊 Execution Flow

### Tick Lifecycle (Detailed)

#### Phase 1: Collection

```python
def _run_collection_phase(self) -> Dict[str, Any]:
    # Clear previous tick's data
    self.shared_data_bus["flood_data"] = {}
    self.shared_data_bus["scout_data"] = []

    # Collect from FloodAgent
    flood_data = self.flood_agent.collect_and_forward_data()
    self.shared_data_bus["flood_data"] = flood_data

    # Collect from ScoutAgent
    scout_tweets = self.scout_agent.step()
    self.shared_data_bus["scout_data"] = scout_tweets

    return {
        "flood_data_collected": len(flood_data),
        "scout_reports_collected": len(scout_tweets),
        "errors": []
    }
```

#### Phase 2: Fusion

```python
def _run_fusion_phase(self) -> Dict[str, Any]:
    # Update GeoTIFF scenario
    return_period = MODE_TO_RETURN_PERIOD[self._mode]
    self.hazard_agent.set_flood_scenario(
        return_period=return_period,
        time_step=self.current_time_step
    )

    # Get collected data from shared bus
    flood_data = self.shared_data_bus.get("flood_data", {})
    scout_data = self.shared_data_bus.get("scout_data", [])

    # Call HazardAgent's update_risk
    update_result = self.hazard_agent.update_risk(
        flood_data=flood_data,
        scout_data=scout_data,
        time_step=self.current_time_step
    )

    self.shared_data_bus["graph_updated"] = True

    return {
        "edges_updated": update_result.get("edges_updated", 0),
        "errors": []
    }
```

#### Phase 3: Routing

```python
def _run_routing_phase(self) -> Dict[str, Any]:
    # Get pending route requests
    pending_routes = self.shared_data_bus.get("pending_routes", [])

    # Process each request
    for route_request in pending_routes:
        start = route_request.get("start")
        end = route_request.get("end")
        preferences = route_request.get("preferences")

        # Call EvacuationManager (which calls RoutingAgent)
        route_result = self.evacuation_manager.handle_route_request(
            start=start,
            end=end,
            preferences=preferences
        )

    # Clear processed routes
    self.shared_data_bus["pending_routes"] = []

    return {
        "routes_processed": len(pending_routes),
        "errors": []
    }
```

#### Phase 4: Advancement

```python
def _run_advancement_phase(self) -> Dict[str, Any]:
    # Auto-increment time step (wraps at 18)
    next_time_step = (self.current_time_step % 18) + 1

    return {
        "next_time_step": next_time_step,
        "next_tick": self.tick_count + 1
    }
```

---

## 🔄 Time Step Management

### GeoTIFF Time Slices (1-18 Hours)

The simulation supports 18 hourly time steps, each corresponding to a GeoTIFF flood depth map:

```
Time Step 1:  rr01_step_01.tif, rr02_step_01.tif, rr03_step_01.tif
Time Step 2:  rr01_step_02.tif, rr02_step_02.tif, rr03_step_02.tif
...
Time Step 18: rr01_step_18.tif, rr02_step_18.tif, rr03_step_18.tif
```

### Auto-Increment vs Explicit Control

```python
# Auto-increment (wraps at 18)
sim_manager.run_tick()  # time_step auto-increments

# Explicit time step
sim_manager.run_tick(time_step=5)  # Jump to hour 5
```

### Mode Selection

```python
# Light flood scenario (2-year return period)
sim_manager.start(mode="light")  # Uses rr01 GeoTIFFs

# Medium flood scenario (5-year return period)
sim_manager.start(mode="medium")  # Uses rr02 GeoTIFFs

# Heavy flood scenario (10-year return period)
sim_manager.start(mode="heavy")  # Uses rr03 GeoTIFFs
```

---

## 📝 Usage Examples

### Basic Example

```python
from app.services.simulation_manager import get_simulation_manager

# Get manager instance
sim_manager = get_simulation_manager()

# Configure agents
sim_manager.set_agents(
    flood_agent=flood_agent,
    scout_agent=scout_agent,
    hazard_agent=hazard_agent,
    routing_agent=routing_agent,
    evacuation_manager=evacuation_manager,
    environment=environment
)

# Start simulation
sim_manager.start(mode="medium")

# Add route request
sim_manager.add_route_request(
    start=(14.6507, 121.1029),  # Marikina City Hall
    end=(14.6391, 121.0957),    # Marikina Sports Center
    preferences={"avoid_floods": True}
)

# Run ticks
for i in range(10):
    result = sim_manager.run_tick()
    print(f"Tick {i+1}: {result['phases']['fusion']['edges_updated']} edges updated")

# Stop and reset
sim_manager.stop()
sim_manager.reset()
```

### Advanced Example (Time Step Control)

```python
# Start in heavy mode
sim_manager.start(mode="heavy")

# Jump to specific time steps
for time_step in [1, 6, 12, 18]:
    result = sim_manager.run_tick(time_step=time_step)
    print(f"Hour {time_step}: {result['phases']['fusion']['edges_updated']} edges")

# Check status
status = sim_manager.get_status()
print(f"Ticks: {status['tick_count']}, Time: {status['current_time_step']}/18")
```

### Batch Route Processing

```python
# Queue multiple route requests
routes = [
    ((14.650, 121.100), (14.640, 121.110)),
    ((14.645, 121.105), (14.655, 121.095)),
    ((14.652, 121.098), (14.642, 121.108)),
]

for start, end in routes:
    sim_manager.add_route_request(start, end)

# Process all in one tick
result = sim_manager.run_tick()
print(f"Processed {result['phases']['routing']['routes_processed']} routes")
```

---

## 🧪 Testing

### Example Test Case

```python
def test_tick_based_execution_order():
    """Test that phases execute in correct order."""
    sim_manager = SimulationManager()
    sim_manager.set_agents(...)
    sim_manager.start(mode="light")

    # Mock data collection
    flood_agent.collect_and_forward_data = Mock(return_value={"test": "data"})
    scout_agent.step = Mock(return_value=[])

    # Run tick
    result = sim_manager.run_tick()

    # Verify order
    assert result["phases"]["collection"]["flood_data_collected"] == 1
    assert result["phases"]["fusion"]["edges_updated"] >= 0
    assert result["tick"] == 1
    assert result["time_step"] == 2  # Auto-incremented
```

---

## 🚀 Migration Guide

### For Existing Code

#### If you have code that directly calls agents:

**Before:**
```python
# ❌ Old way (tight coupling)
flood_agent.step()  # Internally calls HazardAgent
hazard_agent.process_flood_data(data)
```

**After:**
```python
# ✓ New way (via SimulationManager)
sim_manager.run_tick()  # Coordinates all agents
```

#### If you have route calculation code:

**Before:**
```python
# ❌ Old way (direct routing call)
route = routing_agent.calculate_route(start, end)
```

**After:**
```python
# ✓ New way (queued for next tick)
sim_manager.add_route_request(start, end)
sim_manager.run_tick()  # Processes queued routes
```

---

## 🔍 Debugging

### Enable Detailed Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Tick Results

```python
result = sim_manager.run_tick()

# Check each phase
print("Collection:", result["phases"]["collection"])
print("Fusion:", result["phases"]["fusion"])
print("Routing:", result["phases"]["routing"])
print("Advancement:", result["phases"]["advancement"])
```

### Check Shared Data Bus

```python
print("Flood data:", sim_manager.shared_data_bus["flood_data"])
print("Scout data:", sim_manager.shared_data_bus["scout_data"])
print("Pending routes:", sim_manager.shared_data_bus["pending_routes"])
```

---

## 📚 API Reference

### SimulationManager Methods

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `start(mode)` | mode: str | Dict | Start simulation |
| `stop()` | - | Dict | Pause simulation |
| `reset()` | - | Dict | Reset to initial state |
| `run_tick(time_step)` | time_step: Optional[int] | Dict | Execute one tick |
| `add_route_request(start, end, preferences)` | Coords, Dict | None | Queue route request |
| `get_status()` | - | Dict | Get current status |
| `set_agents(...)` | Agent instances | None | Configure agents |

### HazardAgent New Method

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `update_risk(flood_data, scout_data, time_step)` | Dict, List, int | Dict | Update risk assessment |

### DynamicGraphEnvironment New Methods

| Method | Args | Returns | Description |
|--------|------|---------|-------------|
| `batch_update_edge_risks(risk_updates)` | Dict[(u,v,k): risk] | None | Batch update edges |
| `is_updating()` | - | bool | Check update status |

---

## ⚠️ Important Notes

### Thread Safety
- Graph updates are protected by locks
- Do not manually access `environment.graph` during ticks
- Use `environment.is_updating()` to check update status

### Time Step Constraints
- Time steps must be 1-18 (hourly progression)
- Auto-increment wraps at 18 back to 1
- GeoTIFF scenarios must match mode selection

### Route Request Queueing
- Route requests are processed in FIFO order
- Routes are calculated AFTER graph updates in each tick
- Clear pending routes manually if needed

---

## 📊 Performance Characteristics

| Operation | Time Complexity | Notes |
|-----------|----------------|-------|
| Single tick execution | O(V + E) | V=nodes, E=edges |
| Graph update (single edge) | O(1) | With lock overhead |
| Graph batch update | O(n) | n=edges to update |
| Route request queue | O(1) | Append operation |
| Route processing | O(E log V) | A* pathfinding |

---

## 🎯 Summary

The tick-based architecture provides:

✅ **Decoupling:** Agents communicate via shared data bus
✅ **Order:** Guaranteed execution sequence
✅ **Sync:** GeoTIFF time steps match simulation time
✅ **Safety:** Thread-safe graph operations
✅ **Testability:** Deterministic execution

**Key Principle:** The `SimulationManager` orchestrates all agent interactions, ensuring proper data flow and preventing race conditions.

---

**For full example usage, see:** `examples/tick_based_simulation_example.py`
**For implementation details, see:** `app/services/simulation_manager.py`
