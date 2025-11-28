# Risk Decay Analysis - Current Behavior & Proposed Solution

**Date:** November 18, 2025
**Status:** ⚠️ **ISSUE IDENTIFIED** - Risk does NOT decrease when conditions improve
**Priority:** 🔴 **HIGH** - Affects simulation realism

---

## Current Behavior ❌

### Problem: Risk Only Increases, Never Decreases

**User Question:** "Does my risk slowly go down when the rain slowly stops and the river slowly goes down?"

**Answer:** **No, currently risk does NOT decrease.** Here's why:

### 1. Data Caches Accumulate Forever

```python
# In update_risk()
if scout_data:
    self.scout_data_cache.extend(scout_data)  # Accumulates, never expires

if flood_data:
    self.flood_data_cache[location] = flood_data_entry  # Updates, but never removes old data
```

**Problem:**
- Scout reports from 2 hours ago stay in cache forever
- Old flood measurements never expire
- Even if rain stops, old "heavy rain" reports still affect risk calculation

### 2. Risk Combination Uses max()

```python
# In calculate_risk_scores() - Line 798
combined_risk = max(current_risk, current_risk + environmental_factor)
```

**Problem:**
- `max()` ensures risk can only increase or stay the same
- If current_risk = 0.8 and new environmental_factor = 0.1, risk stays at 0.8
- Risk never decreases, even when new data shows improvement

### 3. Spatial Updates Preserved Indefinitely

```python
# In calculate_risk_scores() - Lines 777-783
# IMPORTANT: Start with existing risk scores from the graph
for u, v, key in self.environment.graph.edges(keys=True):
    existing_risk = self.environment.graph[u][v][key].get('risk_score', 0.0)
    if existing_risk > 0.0:
        risk_scores[(u, v, key)] = existing_risk  # Preserved forever!
```

**Problem:**
- Spatial updates from old scout reports preserved indefinitely
- No time-based decay
- Risk "frozen" at highest historical value

---

## Example Scenario

### Timeline

**Time 0:00** - Heavy Rain
```
Scout Report: "Heavy flooding at SM Marikina, severity=0.8"
→ Risk at SM Marikina: 0.8 ✅
```

**Time 0:30** - Rain Stops
```
Scout Report: "Water receding at SM Marikina, severity=0.2"
→ Risk at SM Marikina: 0.8 ❌ (still high!)
→ EXPECTED: Should decrease to ~0.5 (transitioning)
```

**Time 1:00** - Clear Weather
```
Scout Report: "Roads clear at SM Marikina, severity=0.0"
→ Risk at SM Marikina: 0.8 ❌ (still high!)
→ EXPECTED: Should decrease to ~0.1 (almost safe)
```

**Time 2:00** - Fully Recovered
```
No scout reports (roads safe)
→ Risk at SM Marikina: 0.8 ❌ (still high!)
→ EXPECTED: Should be 0.0 (safe)
```

---

## Proposed Solution: Risk Decay System

### Option 1: Time-Based Decay (Recommended)

Implement exponential decay for risk scores based on data age.

```python
class HazardAgent:
    def __init__(self, ...):
        self.risk_decay_rate = 0.1  # 10% decay per minute
        self.scout_report_ttl_minutes = 30  # Reports expire after 30 min
        self.flood_data_ttl_minutes = 60    # Flood data expires after 60 min

    def apply_time_decay(self, current_risk: float, age_minutes: float) -> float:
        """
        Apply exponential decay to risk based on data age.

        Formula: risk × e^(-decay_rate × age)

        Examples (decay_rate=0.1):
        - Age 0 min: risk × 1.00 = 100% (fresh)
        - Age 5 min: risk × 0.60 = 60%
        - Age 10 min: risk × 0.37 = 37%
        - Age 20 min: risk × 0.14 = 14%
        - Age 30 min: risk × 0.05 = 5%
        """
        import math
        decay_factor = math.exp(-self.risk_decay_rate * age_minutes)
        return current_risk * decay_factor

    def clean_expired_data(self):
        """Remove old data from caches based on TTL."""
        current_time = datetime.now()

        # Remove expired scout reports
        self.scout_data_cache = [
            report for report in self.scout_data_cache
            if (current_time - report['timestamp']).total_seconds() / 60
               < self.scout_report_ttl_minutes
        ]

        # Remove expired flood data
        for location in list(self.flood_data_cache.keys()):
            data_age = (current_time - self.flood_data_cache[location]['timestamp']).total_seconds() / 60
            if data_age > self.flood_data_ttl_minutes:
                del self.flood_data_cache[location]
```

### Option 2: Recalculate from Scratch

Instead of preserving existing risk, recalculate from current data only.

```python
def calculate_risk_scores(self, fused_data: Dict[str, Any]) -> Dict[Tuple, float]:
    # OPTION 2: Start fresh, don't preserve old risk
    risk_scores = {}  # Empty dict, no preservation

    # Only apply risk from:
    # 1. Current GeoTIFF flood depths
    # 2. Current fused data (already filtered by age)
    # 3. Recent spatial updates (within decay window)
```

### Option 3: Hybrid Approach (Best)

Combine time decay with data freshness checks.

```python
def update_risk(self, flood_data, scout_data, time_step):
    # 1. Clean expired data first
    self.clean_expired_data()

    # 2. Update with fresh data
    if flood_data:
        self.flood_data_cache.update(flood_data)
    if scout_data:
        self.scout_data_cache.extend(scout_data)

    # 3. Calculate risk with age-weighted decay
    fused_data = self.fuse_data_with_decay()

    # 4. Apply decay to existing spatial risk
    risk_scores = self.calculate_risk_scores_with_decay(fused_data)

    # 5. Update environment
    self.update_environment(risk_scores)

def fuse_data_with_decay(self) -> Dict[str, Any]:
    """Fuse data with time-based weighting."""
    current_time = datetime.now()
    fused_data = {}

    for report in self.scout_data_cache:
        age_minutes = (current_time - report['timestamp']).total_seconds() / 60
        age_decay = self.apply_time_decay(1.0, age_minutes)

        severity = report['severity'] * age_decay  # Apply decay
        # ... rest of fusion logic

    return fused_data
```

---

## Implementation Approach

### Phase 1: Basic Time Decay (Quick Fix)

**Goal:** Apply decay to scout reports based on age

**Changes:**
1. Add timestamps to all scout reports
2. Implement `apply_time_decay()` method
3. Modify `fuse_data()` to apply age decay
4. Test with scenario: rain stops after 30 minutes

**Effort:** ~2 hours
**Impact:** Medium - Risk will decrease over time

### Phase 2: Cache Expiration (Recommended)

**Goal:** Remove old data completely

**Changes:**
1. Implement `clean_expired_data()` method
2. Call it at start of every `update_risk()`
3. Configure TTL values (30 min for scouts, 60 min for flood)
4. Test with scenario: no new reports for 1 hour

**Effort:** ~3 hours
**Impact:** High - Proper data lifecycle management

### Phase 3: Replacing Risk (Full Solution)

**Goal:** Risk reflects current conditions, not historical max

**Changes:**
1. Modify `calculate_risk_scores()` to use `min()` or recalculate instead of `max()`
2. Add "clear" report type: `{"report_type": "clear", "severity": 0.0}`
3. Implement smooth transitions (don't drop from 0.8 to 0.0 instantly)
4. Test with full scenario: heavy rain → light rain → clear

**Effort:** ~4 hours
**Impact:** Very High - Realistic risk modeling

---

## Recommended Configuration

### Decay Parameters

```python
# Scout Reports (crowdsourced, less reliable)
scout_report_ttl_minutes = 30       # Expire after 30 minutes
scout_decay_rate = 0.1              # 10% decay per minute (fast)

# Flood Data (official, more reliable)
flood_data_ttl_minutes = 60         # Expire after 1 hour
flood_decay_rate = 0.05             # 5% decay per minute (slower)

# Spatial Risk (location-specific)
spatial_risk_decay_rate = 0.08      # 8% decay per minute
spatial_risk_min_threshold = 0.01   # Clear risk below this value
```

### Decay Timeline Examples

**Scout Report: "Flooding, severity=0.8"**

| Time Elapsed | Risk Score | Status |
|-------------|-----------|--------|
| 0 min | 0.800 | Fresh report |
| 5 min | 0.483 | Recent |
| 10 min | 0.291 | Aging |
| 15 min | 0.176 | Old |
| 20 min | 0.106 | Very old |
| 30 min | 0.040 | Expired |

---

## Testing Plan

### Test 1: Rain Stops Scenario

```csv
time_offset,agent,payload
0,scout_agent,"{""severity"": 0.8, ""report_type"": ""flood""}"
300,scout_agent,"{""severity"": 0.4, ""report_type"": ""rain_report""}"
600,scout_agent,"{""severity"": 0.1, ""report_type"": ""clear""}"
900,scout_agent,"{""severity"": 0.0, ""report_type"": ""clear""}"
```

**Expected:**
- Time 0: Risk = 0.8
- Time 5min: Risk = ~0.5 (decay + new lower data)
- Time 10min: Risk = ~0.2 (decay + clear report)
- Time 15min: Risk = ~0.05 (almost clear)

### Test 2: No New Reports (Natural Decay)

```csv
time_offset,agent,payload
0,scout_agent,"{""severity"": 0.8, ""report_type"": ""flood""}"
# No more reports after this
```

**Expected:**
- Time 0: Risk = 0.8
- Time 5min: Risk = 0.48 (decay only)
- Time 10min: Risk = 0.29 (decay only)
- Time 30min: Risk = 0.04 (expired)

---

## API Changes

### Before (No Decay)
```json
{
  "edges_updated": 35932,
  "average_risk": 0.0147,
  "risk_trend": "stable"  // Always stable, never decreases
}
```

### After (With Decay)
```json
{
  "edges_updated": 35932,
  "average_risk": 0.0089,
  "risk_trend": "decreasing",  // New field!
  "risk_change_rate": -0.0058,  // Risk delta per minute
  "active_reports": 3,          // Non-expired reports
  "expired_reports": 5,         // Recently expired
  "oldest_report_age_min": 12   // Age of oldest active report
}
```

---

## Conclusion

### Current State: ❌ Risk Does NOT Decrease

- Risk accumulates and stays at historical maximum
- Old scout reports never expire
- Not realistic for flood simulation

### Recommended: ✅ Implement Time-Based Decay

**Priority: HIGH**

1. **Phase 1** (Quick win): Apply age decay to scout report severity
2. **Phase 2** (Proper solution): Implement cache expiration with TTL
3. **Phase 3** (Best experience): Replace `max()` with smooth transitions

**Benefits:**
- ✅ Risk decreases as conditions improve
- ✅ Old data expires naturally
- ✅ More realistic flood simulation
- ✅ Better user experience (shows recovery)

---

## Next Steps

1. **Decide on approach:** Time decay vs. recalculation vs. hybrid?
2. **Set decay parameters:** How fast should risk decay?
3. **Update CSV scenarios:** Add "clear" reports for testing
4. **Implement & test:** Verify risk decreases correctly
5. **Frontend integration:** Show risk trend arrows (↑ increasing, ↓ decreasing)

**Would you like me to implement the time-based decay system?**
