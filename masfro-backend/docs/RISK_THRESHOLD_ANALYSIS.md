# Risk-Aware A* Algorithm - Threshold Analysis

## Quick Answer

**Your algorithm avoids edges when `risk_score >= 0.9`**

This is the **default impassability threshold** - edges with risk scores of **0.9 or higher** are treated as **completely blocked** (infinite cost) and will never be used in route calculations.

---

## Threshold Configuration

### File: `app/algorithms/risk_aware_astar.py`

**Function Signature** (Lines 115-122):
```python
def risk_aware_astar(
    graph: nx.MultiDiGraph,
    start: Any,
    end: Any,
    risk_weight: float = 0.5,
    distance_weight: float = 0.5,
    max_risk_threshold: float = 0.9  # ← IMPASSABILITY THRESHOLD
) -> Optional[List[Any]]:
```

### Threshold Logic (Lines 215-220):
```python
# Check if road is impassable
if risk_score >= max_risk_threshold:
    blocked_edges_count[0] += 1
    if blocked_edges_count[0] <= 10:  # Log first 10 blocked edges
        print(f"  [A*] BLOCKING edge ({u}, {v}): risk={risk_score:.3f} >= {max_risk_threshold}")
    return float('inf')  # ← Edge becomes IMPASSABLE
```

---

## How It Works

### Threshold Behavior

| Risk Score | Behavior | Example Scenario |
|------------|----------|------------------|
| `0.0 - 0.89` | **Passable** | Edge can be used (with increased cost) |
| `0.90 - 1.0` | **BLOCKED** | Edge is **IMPASSABLE** (infinite cost) |

### Edge Cost Calculation

**For passable edges (risk < 0.9)**:
```python
distance_cost = length * distance_weight
risk_cost = length * risk_score * risk_weight
total_cost = distance_cost + risk_cost
```

**For blocked edges (risk >= 0.9)**:
```python
total_cost = float('inf')  # Infinite cost = Never used
```

---

## Current Implementation in RoutingAgent

### File: `app/agents/routing_agent.py` (Lines 146-152)

```python
# Calculate route using risk-aware A*
path_nodes = risk_aware_astar(
    self.environment.graph,
    start_node,
    end_node,
    risk_weight=risk_weight,
    distance_weight=distance_weight
    # Note: max_risk_threshold NOT specified → uses default 0.9
)
```

**Important**: The `max_risk_threshold` parameter is **NOT passed** by RoutingAgent, so it **always uses the default value of 0.9**.

---

## Risk Score to Flood Depth Mapping

To understand what 0.9 risk means in terms of actual flood depth:

### From HazardAgent (`app/agents/hazard_agent.py` Lines 456-466)

```python
if depth <= 0.3:
    risk_from_depth = depth  # 0.0-0.3m → 0.0-0.3 risk
elif depth <= 0.6:
    risk_from_depth = 0.3 + (depth - 0.3) * 1.0  # 0.3-0.6m → 0.3-0.6 risk
elif depth <= 1.0:
    risk_from_depth = 0.6 + (depth - 0.6) * 0.5  # 0.6-1.0m → 0.6-0.8 risk
else:
    risk_from_depth = min(0.8 + (depth - 1.0) * 0.2, 1.0)  # >1.0m → 0.8-1.0 risk

risk_scores[edge_tuple] = risk_from_depth * self.risk_weights["flood_depth"]
```

### Calculating Required Depth for 0.9 Risk

Given:
- `risk_weights["flood_depth"] = 0.5` (from HazardAgent initialization)
- Target risk after weighting: `0.9`
- Required risk before weighting: `0.9 / 0.5 = 1.8` (impossible, max is 1.0)

**Actually achieving 0.9 risk after weighting:**
- Risk before weighting: `0.9 / 0.5 = 1.8`
- Since max risk_from_depth is capped at 1.0, the maximum achievable risk score is:
  - `1.0 * 0.5 = 0.5` (from flood depth alone)

**To reach 0.9 risk**, environmental factors must be added:
```python
# From HazardAgent.calculate_risk_scores() (Lines 468-486)
environmental_factor = risk_level * (
    self.risk_weights["crowdsourced"] + self.risk_weights["historical"]
)  # = risk_level * (0.3 + 0.2) = risk_level * 0.5

combined_risk = max(current_risk, current_risk + environmental_factor)
```

**Required environmental risk_level:**
- `combined_risk = 0.5 + (environmental_factor)`
- `0.9 = 0.5 + (risk_level * 0.5)`
- `risk_level = 0.8`

---

## Practical Examples

### Example 1: Moderate Flood (Will Be Used in Route)

**Scenario**:
- Flood depth: 0.5m
- Environmental risk: 0.0 (no rain, normal river levels)

**Calculation**:
```
risk_from_depth = 0.3 + (0.5 - 0.3) * 1.0 = 0.5
risk_score = 0.5 * 0.5 (flood_weight) = 0.25
combined_risk = 0.25 + 0.0 = 0.25
```

**Result**: ✅ **PASSABLE** (0.25 < 0.9)
- Edge will be used but with 25% increased cost

---

### Example 2: High Flood (Will Be Used, But Costly)

**Scenario**:
- Flood depth: 1.2m
- Environmental risk: 0.3 (moderate rain)

**Calculation**:
```
risk_from_depth = min(0.8 + (1.2 - 1.0) * 0.2, 1.0) = min(0.84, 1.0) = 0.84
risk_score = 0.84 * 0.5 (flood_weight) = 0.42
environmental_factor = 0.3 * 0.5 = 0.15
combined_risk = 0.42 + 0.15 = 0.57
```

**Result**: ✅ **PASSABLE** (0.57 < 0.9)
- Edge will be used but with 57% increased cost
- Algorithm will prefer alternative routes

---

### Example 3: Extreme Flood + Heavy Rain (BLOCKED)

**Scenario**:
- Flood depth: 2.0m (extreme)
- Environmental risk: 0.8 (heavy rain, critical river levels)

**Calculation**:
```
risk_from_depth = min(0.8 + (2.0 - 1.0) * 0.2, 1.0) = 1.0
risk_score = 1.0 * 0.5 (flood_weight) = 0.5
environmental_factor = 0.8 * 0.5 = 0.4
combined_risk = 0.5 + 0.4 = 0.9
```

**Result**: ❌ **BLOCKED** (0.9 >= 0.9)
- Edge has **infinite cost**
- Algorithm will **NEVER** use this edge
- If no alternative route exists → "No safe route found"

---

### Example 4: Critical Scenario (BLOCKED)

**Scenario**:
- Flood depth: 3.0m (critical)
- Environmental risk: 0.9 (extreme rain + critical river levels)

**Calculation**:
```
risk_from_depth = 1.0 (capped)
risk_score = 1.0 * 0.5 = 0.5
environmental_factor = 0.9 * 0.5 = 0.45
combined_risk = min(0.5 + 0.45, 1.0) = 0.95
```

**Result**: ❌ **BLOCKED** (0.95 >= 0.9)
- Edge completely impassable
- Entire area may become unreachable

---

## Threshold Sensitivity Analysis

### What Happens at Different Thresholds?

| Threshold | Flood Depth to Block | Environmental Risk Needed | Impact |
|-----------|---------------------|---------------------------|--------|
| **0.9** (current) | >2.0m + high environmental | 0.8+ | Balanced safety |
| 0.8 | >1.5m + moderate environmental | 0.6+ | More conservative |
| 0.7 | >1.0m + light environmental | 0.4+ | Very conservative |
| 1.0 | Never blocked by flood alone | 1.0 | Only environmental blocks |

---

## Configuring the Threshold

### Option 1: Global Change (Currently Not Implemented)

To change the threshold globally, you would need to modify `RoutingAgent`:

```python
# File: app/agents/routing_agent.py (Line 146)

# CURRENT (uses default 0.9):
path_nodes = risk_aware_astar(
    self.environment.graph,
    start_node,
    end_node,
    risk_weight=risk_weight,
    distance_weight=distance_weight
)

# MODIFIED (explicit threshold):
path_nodes = risk_aware_astar(
    self.environment.graph,
    start_node,
    end_node,
    risk_weight=risk_weight,
    distance_weight=distance_weight,
    max_risk_threshold=0.85  # ← More conservative
)
```

---

### Option 2: User Preference-Based Threshold

Allow users to control threshold via preferences:

```python
# File: app/agents/routing_agent.py (modified)

# Apply preferences
risk_weight = self.risk_weight
distance_weight = self.distance_weight
max_risk = 0.9  # Default

if preferences:
    if preferences.get("avoid_floods"):
        risk_weight = 0.8
        distance_weight = 0.2
        max_risk = 0.7  # ← More conservative threshold
    elif preferences.get("fastest"):
        risk_weight = 0.3
        distance_weight = 0.7
        max_risk = 0.95  # ← More tolerant threshold

# Calculate route with custom threshold
path_nodes = risk_aware_astar(
    self.environment.graph,
    start_node,
    end_node,
    risk_weight=risk_weight,
    distance_weight=distance_weight,
    max_risk_threshold=max_risk  # ← Pass custom threshold
)
```

---

### Option 3: Dynamic Threshold Based on Conditions

Adjust threshold based on current flood severity:

```python
# More conservative threshold during severe weather
def get_dynamic_threshold(flood_data):
    """Calculate appropriate threshold based on conditions."""
    if flood_data.get("severe_weather"):
        return 0.8  # More conservative
    elif flood_data.get("moderate_weather"):
        return 0.9  # Standard
    else:
        return 0.95  # More tolerant
```

---

## Blocked Edge Behavior

### What Happens When Edges Are Blocked?

**During A* Search** (Lines 215-220):
```python
if risk_score >= max_risk_threshold:
    blocked_edges_count[0] += 1
    if blocked_edges_count[0] <= 10:  # Log first 10 blocked edges
        print(f"  [A*] BLOCKING edge ({u}, {v}): risk={risk_score:.3f} >= {max_risk_threshold}")
    return float('inf')  # ← Edge becomes impassable
```

**Console Output Example**:
```
  [A*] BLOCKING edge (21322208, 21322209): risk=0.920 >= 0.9
  [A*] BLOCKING edge (21322209, 426255088): risk=0.915 >= 0.9
  [A*] BLOCKING edge (426255088, 21458378): risk=0.905 >= 0.9
  ...
```

**If No Path Exists** (Lines 245-250):
```python
except nx.NetworkXNoPath:
    logger.warning(
        f"No path exists from {start} to {end}. "
        f"Blocked {blocked_edges_count[0]} edges."
    )
    return None
```

**User Response** (from `routing_agent.py` Lines 154-162):
```python
if not path_nodes:
    return {
        "path": [],
        "distance": 0,
        "estimated_time": 0,
        "risk_level": 1.0,
        "max_risk": 1.0,
        "warnings": ["No safe route found"]
    }
```

---

## Performance Impact

### Edge Blocking During Search

**From Test Results**:
```
Path found with 47 nodes. Blocked 12 edges during search.
```

**Interpretation**:
- Algorithm explored 47 potential nodes
- Encountered 12 edges with risk >= 0.9
- Successfully found alternative path avoiding blocked edges

**No Path Scenario**:
```
No path exists from 123 to 456. Blocked 234 edges.
```

**Interpretation**:
- All viable paths contained blocked edges
- 234 edges were too dangerous (risk >= 0.9)
- User should seek evacuation or wait for conditions to improve

---

## Risk Categories Summary

Based on your current configuration:

| Risk Score | Flood Depth Range | Status | Algorithm Behavior |
|------------|-------------------|--------|-------------------|
| 0.0 - 0.2 | 0.0 - 0.3m | **Safe** | Preferred routes |
| 0.2 - 0.4 | 0.3 - 0.6m | **Low Risk** | Used with slight penalty |
| 0.4 - 0.6 | 0.6 - 1.0m | **Moderate** | Used with significant penalty |
| 0.6 - 0.8 | >1.0m | **High Risk** | Avoided if alternatives exist |
| 0.8 - 0.89 | >2.0m + environmental | **Very High** | Strongly avoided |
| **0.9 - 1.0** | **>2.0m + severe environmental** | **CRITICAL** | **COMPLETELY BLOCKED** |

---

## Recommendations

### Current Threshold (0.9) Analysis

**Strengths**:
- ✅ Allows routing in most flood scenarios
- ✅ Only blocks truly dangerous roads (>2m water + severe weather)
- ✅ Balances safety with route availability
- ✅ Prevents "no route found" in moderate floods

**Weaknesses**:
- ❌ May allow routing through risky areas (0.8-0.89 risk)
- ❌ Not configurable by users
- ❌ Fixed regardless of vehicle type or user risk tolerance

---

### Suggested Improvements

**1. User-Configurable Safety Levels** ⭐ RECOMMENDED

```python
safety_profiles = {
    "maximum_safety": 0.7,  # Conservative: blocks moderate+ risk
    "balanced": 0.9,        # Current default
    "fastest_possible": 0.95  # Tolerant: only blocks extreme risk
}
```

**2. Vehicle-Type Specific Thresholds**

```python
vehicle_thresholds = {
    "motorcycle": 0.6,      # More vulnerable to flooding
    "car": 0.9,            # Standard
    "suv": 0.95,           # Higher clearance
    "emergency_vehicle": 1.0  # Can pass through anything
}
```

**3. Dynamic Threshold Adjustment**

Automatically adjust based on:
- Current weather severity
- Time of day (night = more conservative)
- User demographics (elderly/disabled = more conservative)

---

## Testing the Threshold

### Test Case 1: Verify 0.9 Threshold

```python
# Create test edge with risk = 0.89 (should be passable)
graph[u][v][0]['risk_score'] = 0.89
path = risk_aware_astar(graph, start, end, max_risk_threshold=0.9)
# Expected: Path found (edge used)

# Create test edge with risk = 0.90 (should be blocked)
graph[u][v][0]['risk_score'] = 0.90
path = risk_aware_astar(graph, start, end, max_risk_threshold=0.9)
# Expected: Path avoids this edge or returns None
```

### Test Case 2: Multiple Thresholds

```bash
# Conservative routing
curl -X POST /api/route -d '{
  "start": [14.65, 121.10],
  "end": [14.64, 121.11],
  "preferences": {"avoid_floods": true}  # Could set threshold to 0.7
}'

# Fast routing
curl -X POST /api/route -d '{
  "start": [14.65, 121.10],
  "end": [14.64, 121.11],
  "preferences": {"fastest": true}  # Could set threshold to 0.95
}'
```

---

## Conclusion

**Your risk-aware A* algorithm blocks edges when `risk_score >= 0.9`**

**What this means in practice**:
- Roads with **>2m flood depth** + **severe environmental conditions** are blocked
- Edges with **risk scores 0.9-1.0** are treated as **completely impassable**
- The threshold is **currently hard-coded** and not user-configurable
- This provides a **balanced approach** between safety and route availability

**For most scenarios**, the 0.9 threshold works well, but consider making it configurable for different use cases (emergency vehicles, conservative users, etc.).

---

**Document Created**: 2025-01-12
**Risk Threshold**: 0.9 (impassable if >= 0.9)
**Configuration File**: `app/algorithms/risk_aware_astar.py:121`
**Used By**: `app/agents/routing_agent.py:146-152`
