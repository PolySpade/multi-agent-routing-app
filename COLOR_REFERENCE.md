# Graph Risk Colors - Visual Reference

## What Colors You Should See

### 🟡 Yellow Roads (Risk: 0.0 - 0.3) - SAFE
- **Color Code:** `#FFFF00`
- **Description:** Bright yellow, clearly visible on dark map
- **Meaning:** Safe to travel - no flood risk
- **Most Common:** 95%+ of roads will be this color normally

### 🟠 Orange Roads (Risk: 0.3 - 0.6) - CAUTION
- **Color Code:** `#FFA500`
- **Description:** Orange, clearly distinguishable from yellow
- **Meaning:** Moderate flood risk - use caution
- **Common:** Appears in low-lying areas during rain

### 🔴 Red Roads (Risk: 0.6 - 1.0) - DANGER
- **Color Code:** `#FF6347` to `#DC143C`
- **Description:** Tomato red to crimson, very obvious
- **Meaning:** High flood risk - avoid or evacuate
- **Rare:** Only appears during actual flooding events

## Visual Examples

```
Normal Conditions (No Flooding):
━━━━━━━━━━━━━━━━━━━━  All roads yellow (safe)

Light Rain:
━━━━━━━━━━━━━━━━━━━━  Mostly yellow
━━━━ Orange ━━━━━━━━  Some orange in flood-prone areas

Heavy Flooding (Typhoon):
━━━━━━━━━━━━━━━━━━━━  Yellow (elevated areas)
━━━━ Orange ━━━━━━━━  Orange (moderate risk)
▬▬▬▬ RED ▬▬▬▬▬▬▬▬▬▬  Red (high-risk areas like Nangka)
```

## Line Thickness

- **Thin lines (2px):** Low risk (0.0-0.6)
- **Medium lines (3px):** High risk (0.6-0.8)
- **Thick lines (4px):** Critical risk (0.8-1.0)

## How to Verify Colors Are Showing

### Check 1: Open Browser Console (F12)
Look for:
```
✅ Loaded graph data: {totalEdges: 5000, sampled: true}
✅ Graph risk layer added successfully!
```

### Check 2: Visual Check
Zoom to Marikina City (zoom level 12-14) and you should see:
- **Web of yellow lines** covering the entire city
- Lines following actual road patterns
- Clearer at higher zoom levels

### Check 3: Click on a Road
Click on any colored line and you should see a popup showing:
- Risk Level: X%
- Category: LOW/MEDIUM/HIGH
- Road Type: residential/primary/etc

## Troubleshooting: "I Still Don't See Colors"

### Problem 1: Roads Exist But Wrong Color
**Issue:** You see roads but they're all gray/white
**Fix:** The layer might be using default styling
**Solution:** Check console for errors in the `paint` configuration

### Problem 2: No Roads At All
**Issue:** You don't see any new lines on the map
**Fix:** Layer might be hidden behind other layers
**Solution:** Add layer with `beforeId` parameter to control z-order

### Problem 3: Roads Flash Then Disappear
**Issue:** You see roads briefly then they vanish
**Fix:** Another layer might be removing/overwriting them
**Solution:** Add layer in a separate `setTimeout` or after all other layers

### Problem 4: Only See Yellow (No Variation)
**Issue:** All roads are yellow, no orange/red
**Reason:** This is NORMAL! It means no flooding currently
**To Test:** Run simulation:
```bash
uv run python simulation_runner.py --scenario 1
```
Then refresh the page. You should see orange/red roads in affected areas.

## Color Test Pattern

To test if colors are working correctly, temporarily change the colors to something obvious:

```javascript
'line-color': [
  'interpolate',
  ['linear'],
  ['get', 'risk_score'],
  0.0, '#00FF00',   // GREEN instead of yellow (easier to see)
  0.3, '#0000FF',   // BLUE instead of orange
  0.6, '#FF00FF',   // MAGENTA instead of red
  1.0, '#FF0000'    // RED
]
```

If you see **green roads**, the layer is working! Change back to proper colors.

## Expected View by Zoom Level

### Zoom 10 (City View)
- Lines are thin and densely packed
- Colors blend together
- Hard to see individual roads

### Zoom 12-13 (Neighborhood View) ⭐ BEST
- Individual roads clearly visible
- Colors distinct and easy to identify
- Line thickness noticeable

### Zoom 15+ (Street View)
- Roads very clear
- Can see intersection patterns
- Best for detailed risk assessment

## Map Style Compatibility

### Works Best With:
- ✅ `mapbox://styles/mapbox/dark-v11` (current)
- ✅ `mapbox://styles/mapbox/navigation-night-v1`
- ✅ `mapbox://styles/mapbox/satellite-streets-v12`

### Harder to See:
- ⚠️ `mapbox://styles/mapbox/light-v11` (yellow blends with white)
- ⚠️ `mapbox://styles/mapbox/streets-v12` (colors less distinct)

## Quick Color Visibility Test

Run this in browser console after map loads:

```javascript
// Check if layer exists
map.getLayer('graph-risk-edges')
// Should return: {id: "graph-risk-edges", type: "line", ...}

// Check if source has data
map.getSource('graph-risk-source')._data.features.length
// Should return: 5000 (or your sample size)

// Check first feature has risk score
map.getSource('graph-risk-source')._data.features[0].properties.risk_score
// Should return: number between 0.0 and 1.0

// Force layer visible
map.setLayoutProperty('graph-risk-edges', 'visibility', 'visible')

// Move layer to top (most visible)
const layers = map.getStyle().layers;
map.moveLayer('graph-risk-edges', layers[layers.length - 1].id)
```

## Sample Risk Data Response

When you call the API, you should get data like this:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [[121.0943, 14.6507], [121.0945, 14.6510]]
      },
      "properties": {
        "risk_score": 0.15,        ← This determines color
        "risk_category": "low",     ← low/medium/high
        "highway": "residential"
      }
    }
  ]
}
```

## Final Checklist

Before asking for help, verify:

- [ ] Backend is running (curl http://localhost:8000/api/graph/statistics)
- [ ] API returns data (curl http://localhost:8000/api/graph/edges/geojson?sample_size=10)
- [ ] Console shows "Graph risk layer added successfully!"
- [ ] No JavaScript errors in console
- [ ] Zoom level is 12-14 (best visibility)
- [ ] Map style is dark-v11
- [ ] Layer visibility is 'visible'
- [ ] Source has features (check in console)

If all checked and still no colors, share:
1. Console screenshot
2. API response (curl command output)
3. Map zoom level and center coordinates

---

**Remember:** Most roads will be YELLOW under normal conditions. To see orange/red roads, you need actual flood data or run a simulation!
