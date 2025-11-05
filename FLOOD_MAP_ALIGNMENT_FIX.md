# Flood Map Alignment Issue - Diagnostic & Fix Guide

**Issue:** Flood simulation maps not aligning properly with Marikina City
**Component:** `MapboxMap.js` (lines 380-538)
**Root Cause:** Coordinate projection or bounding box misalignment

---

## 🔍 Diagnostic Steps

### Step 1: Check Console for Coordinates

When you load the map, check the browser console (F12) for these logs:

```javascript
Original Bounding box (EPSG:3857): [minX, minY, maxX, maxY]
Reprojected Coords (EPSG:4326): [[west, north], [east, north], ...]
```

**Expected values for Marikina City:**
- Latitude: ~14.63° to ~14.75° N
- Longitude: ~121.08° to ~121.12° E

**Example correct output:**
```
Original Bounding box (EPSG:3857): [13467000, 1658000, 13472000, 1664000]
Reprojected Coords (EPSG:4326): [
  [121.085, 14.745],  // top-left
  [121.115, 14.745],  // top-right
  [121.115, 14.635],  // bottom-right
  [121.085, 14.635]   // bottom-left
]
```

---

## 🛠️ Common Issues & Fixes

### Issue 1: Coordinates Outside Marikina Range

**Symptom:** Console shows coordinates far from Marikina (e.g., lat: 0-10 or lng: 100-110)

**Fix:** The GeoTIFF metadata is incorrect. You need to manually set the bounding box.

Replace lines 418-432 in `MapboxMap.js`:

```javascript
// BEFORE (automatic detection)
const bbox = image.getBoundingBox();
const [minX, minY, maxX, maxY] = bbox;

// Reproject bounding box from EPSG:3857 to EPSG:4326
const [west, south] = proj4('EPSG:3857', 'EPSG:4326', [minX, minY]);
const [east, north] = proj4('EPSG:3857', 'EPSG:4326', [maxX, maxY]);

const reprojectedCoords = [
  [west, north], // top-left
  [east, north], // top-right
  [east, south], // bottom-right
  [west, south]  // bottom-left
];
```

```javascript
// AFTER (manual Marikina bounding box)
// Manual bounding box for Marikina City (EPSG:4326)
// Based on actual Marikina boundaries
const west = 121.0800;   // Western edge
const east = 121.1200;   // Eastern edge
const south = 14.6300;   // Southern edge
const north = 14.7500;   // Northern edge

console.log('Using manual Marikina bounding box:', {west, east, south, north});

const reprojectedCoords = [
  [west, north], // top-left
  [east, north], // top-right
  [east, south], // bottom-right
  [west, south]  // bottom-left
];
```

---

### Issue 2: Map Upside Down or Rotated

**Symptom:** Flood map appears but is rotated or flipped

**Fix:** Adjust coordinate order

Try this alternative coordinate order:

```javascript
const reprojectedCoords = [
  [west, south],  // bottom-left (changed)
  [east, south],  // bottom-right
  [east, north],  // top-right
  [west, north]   // top-left
];
```

---

### Issue 3: Map Stretched or Distorted

**Symptom:** Flood map covers wrong area or is stretched

**Fix 1:** Use tighter bounding box around actual flood area

```javascript
// More precise Marikina flood-prone area
const west = 121.0850;
const east = 121.1150;
const south = 14.6400;
const north = 14.7300;
```

**Fix 2:** Check if TIFF is actually in EPSG:3857 or another projection

```javascript
// Try different source projection if 3857 doesn't work
const [west, south] = proj4('EPSG:32651', 'EPSG:4326', [minX, minY]); // UTM Zone 51N
const [east, north] = proj4('EPSG:32651', 'EPSG:4326', [maxX, maxY]);
```

---

## 🎯 Recommended Fix (Most Common Solution)

Replace the entire `loadFloodMap` function (lines 386-531) with this improved version:

```javascript
const loadFloodMap = async () => {
  try {
    console.log('Loading flood map for time step:', floodTimeStep);

    // Remove existing layer and source
    if (mapRef.current.getLayer(floodLayerId)) {
      mapRef.current.removeLayer(floodLayerId);
    }
    if (mapRef.current.getSource(floodLayerId)) {
      mapRef.current.removeSource(floodLayerId);
    }

    const tiffUrl = `${BACKEND_API_URL}/data/timed_floodmaps/rr01/rr01-${floodTimeStep}.tif`;
    console.log('Fetching TIFF from:', tiffUrl);

    const response = await fetch(tiffUrl);

    if (!response.ok) {
      console.error(`Failed to fetch flood map: ${response.status}`);
      return;
    }

    const arrayBuffer = await response.arrayBuffer();
    const tiff = await fromBlob(new Blob([arrayBuffer]));
    const image = await tiff.getImage();
    const width = image.getWidth();
    const height = image.getHeight();

    // TRY 1: Use GeoTIFF metadata
    const bbox = image.getBoundingBox();
    console.log('GeoTIFF bounding box:', bbox);

    // TRY 2: If metadata is wrong, use manual Marikina bounds
    // Uncomment these lines if automatic detection fails:

    const USE_MANUAL_BOUNDS = true; // SET TO TRUE IF AUTOMATIC FAILS

    let west, east, south, north;

    if (USE_MANUAL_BOUNDS) {
      // Manual bounding box for Marikina City flood area
      west = 121.0850;
      east = 121.1150;
      south = 14.6400;
      north = 14.7300;
      console.log('Using MANUAL Marikina bounds:', {west, east, south, north});
    } else {
      // Automatic detection from TIFF
      const [minX, minY, maxX, maxY] = bbox;
      [west, south] = proj4('EPSG:3857', 'EPSG:4326', [minX, minY]);
      [east, north] = proj4('EPSG:3857', 'EPSG:4326', [maxX, maxY]);
      console.log('Using AUTOMATIC bounds:', {west, east, south, north});
    }

    const reprojectedCoords = [
      [west, north], // top-left
      [east, north], // top-right
      [east, south], // bottom-right
      [west, south]  // bottom-left
    ];

    console.log('Final coordinates:', reprojectedCoords);

    const rasters = await image.readRasters();
    if (isCancelled) return;

    // Create canvas (rest of the code remains the same)
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    const imageData = ctx.createImageData(width, height);

    const data = rasters[0];
    let minVal = Infinity;
    let maxVal = -Infinity;

    for (let i = 0; i < data.length; i++) {
      const value = data[i];
      if (value > 0) {
        minVal = Math.min(minVal, value);
        maxVal = Math.max(maxVal, value);
      }
    }

    console.log('Flood depth range:', minVal, 'to', maxVal);

    for (let i = 0; i < data.length; i++) {
      const value = data[i];
      const pixelIndex = i * 4;

      if (value > 0) {
        const normalized = maxVal > minVal ? (value - minVal) / (maxVal - minVal) : 0;
        const grayValue = Math.floor((1 - normalized) * 255);
        const blueMultiplier = 0.7;

        imageData.data[pixelIndex] = Math.floor(grayValue * 0.3 * blueMultiplier);
        imageData.data[pixelIndex + 1] = Math.floor(grayValue * 0.5 * blueMultiplier);
        imageData.data[pixelIndex + 2] = Math.floor(grayValue * blueMultiplier);
        imageData.data[pixelIndex + 3] = Math.floor(200 * (0.3 + normalized * 0.7));
      } else {
        imageData.data[pixelIndex + 3] = 0;
      }
    }

    ctx.putImageData(imageData, 0, 0);

    if (isCancelled || !mapRef.current) return;

    mapRef.current.addSource(floodLayerId, {
      type: 'image',
      url: canvas.toDataURL(),
      coordinates: reprojectedCoords
    });

    const layers = mapRef.current.getStyle().layers;
    let firstSymbolId;
    for (let i = 0; i < layers.length; i++) {
      if (layers[i].type === 'symbol') {
        firstSymbolId = layers[i].id;
        break;
      }
    }

    mapRef.current.addLayer({
      id: floodLayerId,
      type: 'raster',
      source: floodLayerId,
      paint: {
        'raster-opacity': 0.7,
        'raster-fade-duration': 0
      }
    }, firstSymbolId);

    if (mapRef.current.getLayer('route')) {
      mapRef.current.moveLayer('route');
    }

    console.log('✅ Flood map loaded successfully!');

  } catch (error) {
    console.warn('⚠️ Flood map loading failed:', error.message);
  }
};
```

---

## 🧪 Testing Steps

### 1. Enable Manual Bounds
Set `USE_MANUAL_BOUNDS = true` in the code above

### 2. Reload Map
Refresh your browser (Ctrl+R or Cmd+R)

### 3. Check Console
Look for:
```
Using MANUAL Marikina bounds: {west: 121.085, east: 121.115, south: 14.64, north: 14.73}
Final coordinates: [[121.085, 14.73], [121.115, 14.73], [121.115, 14.64], [121.085, 14.64]]
✅ Flood map loaded successfully!
```

### 4. Visual Check
- Flood overlay should now cover Marikina City area
- Blue flood zones should align with roads
- Time slider (1-18) should show flood progression

---

## 🎨 Fine-Tuning Alignment

If the flood map is close but not perfect, adjust these values:

```javascript
// Shift map NORTH (increase both north and south by 0.001-0.01)
south = 14.6450; // was 14.6400
north = 14.7350; // was 14.7300

// Shift map SOUTH (decrease both)
south = 14.6350;
north = 14.7250;

// Shift map EAST (increase both west and east)
west = 121.0900;
east = 121.1200;

// Shift map WEST (decrease both)
west = 121.0800;
east = 121.1100;

// Zoom IN (tighten bounds)
west = 121.0900;
east = 121.1100;
south = 14.6450;
north = 14.7250;

// Zoom OUT (widen bounds)
west = 121.0750;
east = 121.1250;
south = 14.6300;
north = 14.7500;
```

---

## 🔧 Alternative: Check TIFF File Projection

If manual bounds don't work, the TIFF might have incorrect metadata.

### Method 1: Using GDAL (Command Line)

```bash
# Install GDAL
pip install gdal

# Check TIFF info
gdalinfo masfro-backend/app/data/timed_floodmaps/rr01/rr01-1.tif

# Look for:
# - Coordinate System
# - Origin
# - Pixel Size
# - Corner Coordinates
```

### Method 2: Using Python Script

Create `check_tiff_coords.py`:

```python
from osgeo import gdal
import sys

if len(sys.argv) < 2:
    print("Usage: python check_tiff_coords.py <path_to_tiff>")
    sys.exit(1)

tiff_path = sys.argv[1]
dataset = gdal.Open(tiff_path)

if dataset is None:
    print(f"Failed to open {tiff_path}")
    sys.exit(1)

# Get geotransform
gt = dataset.GetGeoTransform()
width = dataset.RasterXSize
height = dataset.RasterYSize

# Calculate corners
minX = gt[0]
maxY = gt[3]
maxX = gt[0] + width * gt[1]
minY = gt[3] + height * gt[5]

print(f"Width: {width}, Height: {height}")
print(f"Bounding Box (original): [{minX}, {minY}, {maxX}, {maxY}]")
print(f"Projection: {dataset.GetProjection()}")

# If in EPSG:3857, convert to EPSG:4326
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

west, south = transformer.transform(minX, minY)
east, north = transformer.transform(maxX, maxY)

print(f"\nConverted to EPSG:4326:")
print(f"West: {west}, East: {east}")
print(f"South: {south}, North: {north}")
print(f"\nExpected for Marikina:")
print(f"Lng: 121.08 to 121.12")
print(f"Lat: 14.63 to 14.75")
```

Run:
```bash
python check_tiff_coords.py masfro-backend/app/data/timed_floodmaps/rr01/rr01-1.tif
```

---

## ✅ Quick Fix Summary

**Most likely solution:** Set `USE_MANUAL_BOUNDS = true` and use:

```javascript
west = 121.0850;
east = 121.1150;
south = 14.6400;
north = 14.7300;
```

This should align the flood maps correctly with Marikina City.

---

**Created:** November 5, 2025
**Issue:** Flood map misalignment
**Status:** Diagnostic guide provided
