# Graph Risk Visualization - Frontend Integration Guide

## Overview

This guide shows how to display **color-coded risk scores** on your Mapbox map, allowing users to visualize flood risk levels across the entire road network in real-time.

## Architecture

### Backend API (FastAPI)
- **Endpoint:** `GET /api/graph/edges/geojson`
- **Returns:** GeoJSON FeatureCollection with LineString geometries
- **Features:** Risk scores, categories, road types for each edge

### Frontend Component (React + Mapbox GL JS)
- **Component:** `GraphRiskLayer.js`
- **Integration:** Hook-based layer manager
- **Visualization:** Color-coded lines with risk-based styling

## Backend Setup ✅ Complete

The backend API is already set up and ready to use:

### Endpoints Available

#### 1. Get Graph Edges as GeoJSON
```http
GET /api/graph/edges/geojson?sample_size=5000&min_risk=0.0&max_risk=1.0
```

**Query Parameters:**
- `sample_size` (optional): Number of edges to return (default: all, recommended: 5000)
- `min_risk` (optional): Minimum risk score (0.0-1.0)
- `max_risk` (optional): Maximum risk score (0.0-1.0)

**Response:**
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
        "edge_id": "node1-node2",
        "risk_score": 0.75,
        "risk_category": "high",
        "length": 125.5,
        "highway": "residential"
      }
    }
  ],
  "properties": {
    "total_edges": 5000,
    "sampled": true,
    "filters": {"min_risk": null, "max_risk": null}
  }
}
```

#### 2. Get Graph Statistics
```http
GET /api/graph/statistics
```

**Response:**
```json
{
  "total_edges": 20124,
  "avg_risk_score": 0.0234,
  "median_risk_score": 0.0,
  "max_risk_score": 0.85,
  "min_risk_score": 0.0,
  "std_risk_score": 0.0456,
  "low_risk_edges": 19000,
  "medium_risk_edges": 1000,
  "high_risk_edges": 124,
  "risk_distribution": {
    "0.0-0.1": 18500,
    "0.1-0.2": 800,
    ...
  }
}
```

## Frontend Integration

### Step 1: Import the Component

In your `MapboxMap.js`:

```javascript
import GraphRiskLayer from './GraphRiskLayer';
import mapboxgl from 'mapbox-gl';
```

### Step 2: Add State for Layer Control

```javascript
const [showRiskLayer, setShowRiskLayer] = useState(true);
const [riskLayerStats, setRiskLayerStats] = useState(null);
```

### Step 3: Initialize the Layer

Add this inside your MapboxMap component, after map initialization:

```javascript
// Initialize graph risk layer
const riskLayer = GraphRiskLayer({
  map: mapRef.current,
  visible: showRiskLayer,
  sampleSize: 5000,  // Adjust for performance
  minRisk: 0.0,      // Optional: filter by risk
  maxRisk: 1.0       // Optional: filter by risk
});

// Update stats when available
useEffect(() => {
  if (riskLayer.stats) {
    setRiskLayerStats(riskLayer.stats);
  }
}, [riskLayer.stats]);
```

### Step 4: Add Toggle Control (Optional)

Add a button to toggle the risk layer:

```jsx
<button
  onClick={() => setShowRiskLayer(!showRiskLayer)}
  style={{
    position: 'absolute',
    top: '120px',
    right: '10px',
    zIndex: 1000,
    padding: '10px 15px',
    background: showRiskLayer ? '#4CAF50' : '#f44336',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold',
    boxShadow: '0 2px 4px rgba(0,0,0,0.3)'
  }}
>
  {showRiskLayer ? '🟢 Risk Layer ON' : '🔴 Risk Layer OFF'}
</button>
```

### Step 5: Add Statistics Display (Optional)

Show current risk statistics:

```jsx
{riskLayerStats && (
  <div style={{
    position: 'absolute',
    bottom: '20px',
    left: '10px',
    background: 'rgba(0,0,0,0.8)',
    color: 'white',
    padding: '15px',
    borderRadius: '8px',
    fontSize: '12px',
    zIndex: 1000
  }}>
    <h4 style={{ margin: '0 0 10px 0', fontSize: '14px' }}>
      Graph Risk Statistics
    </h4>
    <p style={{ margin: '4px 0' }}>
      Total Edges: {riskLayerStats.total_edges?.toLocaleString()}
    </p>
    <p style={{ margin: '4px 0' }}>
      Avg Risk: {(riskLayerStats.avg_risk_score * 100).toFixed(1)}%
    </p>
    <p style={{ margin: '4px 0' }}>
      <span style={{ color: '#FFD700' }}>●</span> Low Risk: {riskLayerStats.low_risk_edges?.toLocaleString()}
    </p>
    <p style={{ margin: '4px 0' }}>
      <span style={{ color: '#FFA500' }}>●</span> Medium Risk: {riskLayerStats.medium_risk_edges?.toLocaleString()}
    </p>
    <p style={{ margin: '4px 0' }}>
      <span style={{ color: '#DC143C' }}>●</span> High Risk: {riskLayerStats.high_risk_edges?.toLocaleString()}
    </p>
  </div>
)}
```

## Complete Integration Example

Here's a complete example of how to modify your `MapboxMap.js`:

```javascript
// At the top of MapboxMap.js
import GraphRiskLayer from './GraphRiskLayer';

export default function MapboxMap({ /* existing props */ }) {
  // Existing state...
  const [showRiskLayer, setShowRiskLayer] = useState(true);
  const [riskLayerControl, setRiskLayerControl] = useState(null);

  // After map initialization (in the useEffect where map loads)
  useEffect(() => {
    if (isMapLoaded && mapRef.current) {
      // Initialize risk layer
      const layerControl = GraphRiskLayer({
        map: mapRef.current,
        visible: showRiskLayer,
        sampleSize: 5000
      });

      setRiskLayerControl(layerControl);
    }
  }, [isMapLoaded, showRiskLayer]);

  // In your JSX return
  return (
    <div style={{ position: 'relative', width: '100%', height: '100vh' }}>
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%' }} />

      {/* Risk Layer Toggle Button */}
      <button
        onClick={() => setShowRiskLayer(!showRiskLayer)}
        style={{
          position: 'absolute',
          top: '120px',
          right: '10px',
          zIndex: 1000,
          padding: '10px 15px',
          background: showRiskLayer ? '#4CAF50' : '#f44336',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px',
          fontWeight: 'bold',
          boxShadow: '0 2px 4px rgba(0,0,0,0.3)'
        }}
      >
        {showRiskLayer ? '🟢 Risk Layer ON' : '🔴 Risk Layer OFF'}
      </button>

      {/* Statistics Display */}
      {riskLayerControl?.stats && (
        <div style={{
          position: 'absolute',
          bottom: '20px',
          left: '10px',
          background: 'rgba(0,0,0,0.8)',
          color: 'white',
          padding: '15px',
          borderRadius: '8px',
          fontSize: '12px',
          zIndex: 1000,
          maxWidth: '250px'
        }}>
          <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', fontWeight: 'bold' }}>
            Road Network Risk
          </h4>
          <p style={{ margin: '4px 0' }}>
            Total Roads: {riskLayerControl.stats.total_edges?.toLocaleString()}
          </p>
          <p style={{ margin: '4px 0' }}>
            Avg Risk: {(riskLayerControl.stats.avg_risk_score * 100).toFixed(1)}%
          </p>
          <div style={{ marginTop: '8px', borderTop: '1px solid rgba(255,255,255,0.3)', paddingTop: '8px' }}>
            <p style={{ margin: '4px 0' }}>
              <span style={{ color: '#FFFF00' }}>●</span> Safe: {riskLayerControl.stats.low_risk_edges?.toLocaleString()}
            </p>
            <p style={{ margin: '4px 0' }}>
              <span style={{ color: '#FFA500' }}>●</span> Caution: {riskLayerControl.stats.medium_risk_edges?.toLocaleString()}
            </p>
            <p style={{ margin: '4px 0' }}>
              <span style={{ color: '#DC143C' }}>●</span> Danger: {riskLayerControl.stats.high_risk_edges?.toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* Loading indicator */}
      {riskLayerControl?.isLoading && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          background: 'rgba(0,0,0,0.8)',
          color: 'white',
          padding: '20px',
          borderRadius: '8px',
          zIndex: 10000
        }}>
          Loading road risk data...
        </div>
      )}

      {/* Error display */}
      {riskLayerControl?.error && (
        <div style={{
          position: 'absolute',
          top: '10px',
          left: '50%',
          transform: 'translateX(-50%)',
          background: '#f44336',
          color: 'white',
          padding: '10px 20px',
          borderRadius: '4px',
          zIndex: 10000
        }}>
          Error: {riskLayerControl.error}
        </div>
      )}

      {/* Existing components */}
      {/* ... flood alerts, other controls, etc ... */}
    </div>
  );
}
```

## Color Scheme

The visualization uses an intuitive color scheme based on risk levels:

| Risk Score | Color | Meaning | Line Width |
|------------|-------|---------|------------|
| 0.0 - 0.3 | 🟡 Yellow | Low Risk - Safe passage | 1px |
| 0.3 - 0.6 | 🟠 Orange | Medium Risk - Caution advised | 2px |
| 0.6 - 1.0 | 🔴 Red | High Risk - Avoid or evacuate | 3px |

## Performance Optimization

### Sample Size Recommendations

```javascript
// For development/testing (fast loading)
sampleSize: 1000

// For production (good balance)
sampleSize: 5000

// For full network (slow, use with caution)
sampleSize: null  // Returns all edges
```

### Risk Filtering

Show only high-risk areas:
```javascript
GraphRiskLayer({
  map: mapRef.current,
  visible: true,
  minRisk: 0.6,    // Only show high-risk edges
  sampleSize: 2000
});
```

Show only low-to-medium risk:
```javascript
GraphRiskLayer({
  map: mapRef.current,
  visible: true,
  maxRisk: 0.6,    // Exclude high-risk edges
  sampleSize: 5000
});
```

## Interactive Features

### Click on Road for Details

When users click on a colored road segment, a popup shows:
- Risk Score (percentage)
- Risk Category (low/medium/high)
- Road Type (residential, primary, etc.)

### Cursor Changes

- Default: Standard cursor
- Hover over risk road: Pointer cursor (indicating clickable)

## Testing

### 1. Start Backend
```bash
cd masfro-backend
uv run uvicorn app.main:app --reload
```

### 2. Test API Endpoints
```bash
# Test GeoJSON endpoint
curl http://localhost:8000/api/graph/edges/geojson?sample_size=100

# Test statistics endpoint
curl http://localhost:8000/api/graph/statistics
```

### 3. Start Frontend
```bash
cd masfro-frontend
npm run dev
```

### 4. Verify Visualization
1. Open `http://localhost:3000` in browser
2. Check browser console for "Fetching graph data" logs
3. Verify colored roads appear on map
4. Click on a colored road to see popup
5. Toggle risk layer on/off with button

## Troubleshooting

### No colored roads appear

1. **Check backend is running:**
   ```bash
   curl http://localhost:8000/api/graph/statistics
   ```

2. **Check browser console:**
   - Look for API errors
   - Verify GeoJSON data is received

3. **Check map initialization:**
   - Ensure `map.isStyleLoaded()` is true before adding layer

### Colors not updating

1. **Refresh data manually:**
   ```javascript
   riskLayerControl.refreshData();
   riskLayerControl.refreshStats();
   ```

2. **Check risk scores in backend:**
   - Verify edges have `risk_score` attribute
   - Run simulation or inject test data

### Performance issues

1. **Reduce sample size:**
   ```javascript
   sampleSize: 1000  // Reduce from 5000
   ```

2. **Add risk filtering:**
   ```javascript
   minRisk: 0.3  // Only show medium/high risk
   ```

3. **Disable layer when not needed:**
   ```javascript
   setShowRiskLayer(false)
   ```

## Advanced Customization

### Custom Color Scheme

Modify the color interpolation in `GraphRiskLayer.js`:

```javascript
'line-color': [
  'interpolate',
  ['linear'],
  ['get', 'risk_score'],
  0.0, '#00FF00',  // Green for safe
  0.5, '#FFFF00',  // Yellow for moderate
  1.0, '#FF0000'   // Red for danger
]
```

### Animated Risk Changes

Add transitions for smooth color updates:

```javascript
paint: {
  'line-color': [...],
  'line-color-transition': {
    duration: 1000,
    delay: 0
  }
}
```

### Risk Heatmap Effect

Instead of individual lines, create a heatmap:

```javascript
map.addLayer({
  id: 'risk-heatmap',
  type: 'heatmap',
  source: sourceIdRef.current,
  paint: {
    'heatmap-weight': ['get', 'risk_score'],
    'heatmap-intensity': 1,
    'heatmap-radius': 20,
    'heatmap-opacity': 0.7
  }
});
```

## Summary

You now have:
- ✅ **Backend API** serving graph risk data in GeoJSON format
- ✅ **Frontend component** for Mapbox visualization
- ✅ **Color-coded roads** showing risk levels
- ✅ **Interactive features** (click for details, hover effects)
- ✅ **Statistics display** showing network-wide risk metrics
- ✅ **Toggle control** to show/hide layer
- ✅ **Performance optimization** via sampling

The visualization will **automatically update** when:
- Simulation data is injected (backend)
- FloodAgent collects new data
- ScoutAgent processes tweets
- HazardAgent updates risk scores

Next steps:
1. Integrate into your MapboxMap component
2. Test with different scenarios
3. Customize colors and styling
4. Add real-time updates via WebSocket (optional)

---

**Files Created:**
- `masfro-backend/app/api/graph_routes.py` - Backend API endpoints
- `masfro-frontend/src/components/GraphRiskLayer.js` - Frontend visualization component

**Status:** ✅ Ready to use!
