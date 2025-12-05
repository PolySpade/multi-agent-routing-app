# Routing Configuration Guide

## Current Weight Settings

### Location
File: `app/agents/routing_agent.py`
- Lines 50-51: Balanced mode defaults
- Lines 140-141: Safest mode weights
- Lines 145-146: Fastest mode weights

### Active Configuration

```python
# BALANCED MODE (default, no preferences)
risk_weight = 0.5
distance_weight = 0.5

# SAFEST MODE (preferences: {"avoid_floods": true})
risk_weight = 0.9
distance_weight = 0.1

# FASTEST MODE (preferences: {"fastest": true})
risk_weight = 0.2
distance_weight = 0.8
```

## Understanding Weight Parameters

### Risk Weight (0.0 - 1.0)
- Higher value = More aggressive avoidance of risky roads
- Lower value = More tolerance for risky roads
- Example: 0.9 means 90% of routing decision is based on avoiding risk

### Distance Weight (0.0 - 1.0)
- Higher value = More emphasis on shortest distance
- Lower value = Less concern about detours
- Example: 0.1 means only 10% of routing decision considers distance

### Constraint
- `risk_weight + distance_weight = 1.0` (must sum to 1)

## Cost Calculation Formula

```
edge_cost = (length × distance_weight) + (length × risk_score × risk_weight)
```

### Example Calculation
For a 1000m road with risk_score = 0.6:

**Safest Mode (0.9/0.1):**
```
cost = (1000 × 0.1) + (1000 × 0.6 × 0.9)
     = 100 + 540
     = 640
```

**Fastest Mode (0.2/0.8):**
```
cost = (1000 × 0.8) + (1000 × 0.6 × 0.2)
     = 800 + 120
     = 920
```

Safest assigns lower cost (640) → prefers safer alternatives
Fastest assigns higher cost (920) → tolerates risk for shorter distance

## Tuning Guidelines

### If Routes Are Too Similar
**Problem:** All three modes return nearly identical routes

**Solutions:**
1. Increase weight spread:
   ```python
   safest: 0.95 / 0.05
   balanced: 0.5 / 0.5
   fastest: 0.15 / 0.85
   ```

2. Lower `max_risk_threshold` in `risk_aware_astar.py`:
   ```python
   max_risk_threshold: float = 0.85  # Was 0.9
   ```

### If Safest Routes Are Too Long
**Problem:** Safest mode takes extremely long detours

**Solutions:**
1. Reduce risk_weight slightly:
   ```python
   risk_weight = 0.8  # Instead of 0.9
   distance_weight = 0.2
   ```

2. Set maximum acceptable detour factor (not currently implemented)

### If Fastest Routes Are Too Dangerous
**Problem:** Fastest mode goes through critical flood zones

**Solutions:**
1. Increase risk_weight:
   ```python
   risk_weight = 0.3  # Instead of 0.2
   distance_weight = 0.7
   ```

2. Lower `max_risk_threshold` to block high-risk roads

## Testing Procedure

After changing weights:

1. **Restart backend:**
   ```bash
   cd masfro-backend
   uvicorn app.main:app --reload
   ```

2. **Test with known coordinates:**
   ```
   Start: 14.6512, 121.0913
   End: 14.6352, 121.0975
   ```

3. **Check backend logs for:**
   ```
   SAFEST MODE: risk_weight=0.9, distance_weight=0.1
   BALANCED MODE: risk_weight=0.5, distance_weight=0.5
   FASTEST MODE: risk_weight=0.2, distance_weight=0.8
   ```

4. **Compare results:**
   - Distance: Fastest < Balanced < Safest
   - Risk: Safest < Balanced < Fastest

5. **Verify differences are significant:**
   - Distance difference should be >10%
   - Risk difference should be >5%

## Recommended Presets by Use Case

### For General Public
```python
safest: 0.85 / 0.15
balanced: 0.6 / 0.4
fastest: 0.3 / 0.7
```

### For Emergency Services
```python
safest: 0.7 / 0.3
balanced: 0.4 / 0.6
fastest: 0.1 / 0.9
```

### For Vulnerable Populations
```python
safest: 0.95 / 0.05
balanced: 0.8 / 0.2
fastest: 0.5 / 0.5
```

## Future Enhancements

Consider implementing:
1. Dynamic weight adjustment based on real-time conditions
2. User-customizable weight sliders in frontend
3. Time-of-day based weight profiles
4. Vehicle-type specific weights (car vs motorcycle vs pedestrian)
