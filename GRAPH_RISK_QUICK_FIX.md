# Graph Risk Visualization - Quick Fix Guide

## Problem: Can't See Colored Roads

You should see these colors on the roads:
- 🟡 **Yellow/Light Orange** - Low risk roads (most roads should be this)
- 🟠 **Orange** - Medium risk roads
- 🔴 **Red/Dark Red** - High risk roads

## Quick Diagnostic Steps

### Step 1: Check Backend is Running

```bash
# Test if backend API is working
curl http://localhost:8000/api/graph/statistics
```

**Expected Output:**
```json
{
  "total_edges": 20124,
  "avg_risk_score": 0.0234,
  ...
}
```

If you get an error, start the backend:
```bash
cd masfro-backend
uv run uvicorn app.main:app --reload
```

### Step 2: Check Browser Console

Open your browser's Developer Tools (F12) and check the Console tab for:

**Look for these messages:**
- ✅ "Fetching graph data from: http://localhost:8000/api/graph/edges/geojson..."
- ✅ "Received GeoJSON data: {features: 5000, ...}"

**Common errors:**
- ❌ "Failed to fetch" → Backend not running
- ❌ "CORS error" → Backend CORS not configured (should be fixed already)
- ❌ "404 Not Found" → API route not registered

### Step 3: Manual Layer Addition (Guaranteed to Work)

Instead of using the GraphRiskLayer component, add the layer directly in your MapboxMap.js.

**Add this code RIGHT AFTER your map loads** (around line 72-73):

```javascript
mapRef.current.on('load', () => {
  setIsMapLoaded(true);

  // === ADD GRAPH RISK LAYER HERE ===
  // Fetch and add risk layer immediately
  fetch('http://localhost:8000/api/graph/edges/geojson?sample_size=5000')
    .then(response => response.json())
    .then(geojsonData => {
      console.log('✅ Graph data loaded:', geojsonData.features.length, 'edges');

      // Add source
      mapRef.current.addSource('graph-risk-source', {
        type: 'geojson',
        data: geojsonData
      });

      // Add layer BELOW labels but ABOVE buildings
      const layers = mapRef.current.getStyle().layers;
      let firstSymbolId;
      for (const layer of layers) {
        if (layer.type === 'symbol') {
          firstSymbolId = layer.id;
          break;
        }
      }

      mapRef.current.addLayer({
        id: 'graph-risk-edges',
        type: 'line',
        source: 'graph-risk-source',
        layout: {
          'line-join': 'round',
          'line-cap': 'round'
        },
        paint: {
          'line-color': [
            'interpolate',
            ['linear'],
            ['get', 'risk_score'],
            0.0, '#FFFF00',  // Yellow (low risk)
            0.3, '#FFA500',  // Orange (medium risk)
            0.6, '#FF6347',  // Tomato red (high risk)
            1.0, '#DC143C'   // Crimson (critical risk)
          ],
          'line-width': [
            'interpolate',
            ['linear'],
            ['get', 'risk_score'],
            0.0, 2,    // Thinner for low risk
            0.6, 3,    // Medium thickness
            1.0, 4     // Thicker for high risk
          ],
          'line-opacity': 0.8  // Slightly transparent to see base map
        }
      }, firstSymbolId);  // Insert before labels

      console.log('✅ Graph risk layer added successfully!');
    })
    .catch(error => {
      console.error('❌ Error loading graph data:', error);
    });
});
```

### Step 4: Expected Visual Result

After adding the above code, you should see:

**Immediately on map load:**
- The entire road network of Marikina City visible
- Roads colored mostly **yellow/light orange** (baseline risk ~0.0)
- Some roads might be slightly **orange** if there's recent flood data

**After simulation or flood data:**
- High-risk areas turn **orange to red**
- Color intensity increases with risk level
- Line thickness increases for dangerous roads

### Step 5: Test with Simulated High Risk

To see more dramatic colors, run a simulation:

```bash
cd masfro-backend
uv run python simulation_runner.py --scenario 1
```

This will inject high-risk flood data, and you should see:
- More **red and orange** roads
- Concentrated in flood-prone areas (Nangka, Sto. Niño, etc.)

### Step 6: Layer Order Issues

If you still can't see the roads, the layer might be hidden behind others.

**Check layer visibility in console:**
```javascript
// In browser console
map.getLayer('graph-risk-edges')  // Should return layer object
map.getLayoutProperty('graph-risk-edges', 'visibility')  // Should be 'visible'
```

**Force layer to top:**
```javascript
// Add this after the layer is created
const layers = mapRef.current.getStyle().layers;
mapRef.current.moveLayer('graph-risk-edges', layers[layers.length - 1].id);
```

## Complete Working Example

Here's a minimal working integration:

```javascript
// In MapboxMap.js, around line 60-100

useEffect(() => {
  if (!MAPBOX_TOKEN) return;

  mapboxgl.accessToken = MAPBOX_TOKEN;

  mapRef.current = new mapboxgl.Map({
    container: mapContainerRef.current,
    style: 'mapbox://styles/mapbox/dark-v11',
    center: initialCenterRef.current,
    zoom: initialZoomRef.current,
  });

  mapRef.current.on('load', () => {
    setIsMapLoaded(true);

    // === GRAPH RISK LAYER - SIMPLE VERSION ===
    console.log('🔄 Loading graph risk data...');

    fetch('http://localhost:8000/api/graph/edges/geojson?sample_size=3000')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        console.log('✅ Loaded', data.features.length, 'road segments');

        mapRef.current.addSource('risk-roads', {
          type: 'geojson',
          data: data
        });

        mapRef.current.addLayer({
          id: 'risk-roads-layer',
          type: 'line',
          source: 'risk-roads',
          paint: {
            'line-color': [
              'case',
              ['<', ['get', 'risk_score'], 0.3],
              '#FFFF00',  // Yellow - safe
              ['<', ['get', 'risk_score'], 0.6],
              '#FF8C00',  // Dark orange - caution
              '#FF0000'   // Red - danger
            ],
            'line-width': 2,
            'line-opacity': 0.7
          }
        });

        console.log('✅ Graph risk layer visible!');
      })
      .catch(err => {
        console.error('❌ Failed to load graph:', err);
        alert('Failed to load road risk data. Check backend is running.');
      });
  });

  // ... rest of your code
}, []);
```

## Troubleshooting Checklist

- [ ] Backend running on port 8000
- [ ] No CORS errors in console
- [ ] GeoJSON data loaded (check console)
- [ ] Layer added successfully (check console)
- [ ] Layer is visible (not behind other layers)
- [ ] Zoom level appropriate (10-15 works best)
- [ ] Map style is dark (yellow/orange shows better on dark)

## Why You Might Not See Colors

### Reason 1: All Roads are Low Risk (Yellow on Yellow)
If the background is light and all roads are low risk (yellow), they blend in.

**Fix:** Use dark map style or change low-risk color:
```javascript
0.0, '#00FF00',  // Green instead of yellow
```

### Reason 2: Layer is Behind 3D Buildings
The flood layer or 3D buildings might be covering the risk layer.

**Fix:** Add layer after 3D buildings but before labels

### Reason 3: Line Width Too Thin
At certain zoom levels, thin lines disappear.

**Fix:** Increase line width:
```javascript
'line-width': 3  // or even 4-5
```

### Reason 4: Backend Not Returning Data
The API might be returning empty features.

**Check:**
```bash
curl "http://localhost:8000/api/graph/edges/geojson?sample_size=10"
```

Should return features with `risk_score` property.

## Expected Colors by Risk Score

| Risk Score | Color Code | Color Name | What It Means |
|------------|------------|------------|---------------|
| 0.0 | `#FFFF00` | Yellow | Safe - No flood risk |
| 0.1 | `#FFEB3B` | Light Yellow | Minimal risk |
| 0.2 | `#FFD700` | Gold | Low risk |
| 0.3 | `#FFA500` | Orange | Moderate risk begins |
| 0.4 | `#FF8C00` | Dark Orange | Medium risk |
| 0.5 | `#FF7F50` | Coral | Elevated risk |
| 0.6 | `#FF6347` | Tomato Red | High risk begins |
| 0.7 | `#FF4500` | Orange Red | High risk |
| 0.8 | `#FF0000` | Red | Very high risk |
| 0.9 | `#DC143C` | Crimson | Critical risk |
| 1.0 | `#8B0000` | Dark Red | Maximum danger |

## Test Pattern

1. **Start Backend:** `uvicorn app.main:app --reload`
2. **Open Frontend:** `http://localhost:3000`
3. **Open Browser Console:** Press F12
4. **Look for:** "Graph risk layer visible!" message
5. **Zoom to Marikina:** Should see yellow roads
6. **Run Simulation:** `python simulation_runner.py --scenario 1`
7. **Refresh Page:** Should see orange/red roads in affected areas

## Still Not Working?

If you've tried everything and still can't see the layer, send me:

1. **Console output** (any errors?)
2. **API response:** `curl http://localhost:8000/api/graph/edges/geojson?sample_size=5`
3. **Layer check:** `map.getLayer('graph-risk-edges')`

And I'll help debug further!

---

**Quick Win:** Just add the "Complete Working Example" code above to your MapboxMap.js and you should see colored roads immediately! 🎨
