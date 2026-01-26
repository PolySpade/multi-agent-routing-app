# Frontend-Backend TIFF Value Alignment

## Summary

✅ **Both frontend and backend are now correctly aligned and retrieving TIFF flood data!**

## Analysis Results

### Frontend (MapboxMap.js)

**Purpose:** Visual flood overlay on the map

**What it does:**
- Loads entire TIFF file (372x368 pixels)
- Renders all pixels as colored canvas overlay
- Displays flood visualization on map
- **Does NOT query individual coordinates for routing**

**Configuration:**
```javascript
const centerLng = 121.10305;
const centerLat = 14.6456;
const baseCoverage = 0.06;  // 6km coverage
```

**Status:** ✅ Working correctly - shows flood overlay

---

### Backend (geotiff_service.py)

**Purpose:** Query specific TIFF values for graph edges

**What it does:**
- Loads TIFF metadata and data array
- Queries flood depth at specific lat/lon coordinates
- Returns depth values for routing algorithm
- **Updates graph edge weights with real flood data**

**Configuration (NOW FIXED):**
```python
MANUAL_CENTER_LAT = 14.6456
MANUAL_CENTER_LON = 121.10305
MANUAL_BASE_COVERAGE = 0.06  # NOW MATCHES FRONTEND!
```

**Status:** ✅ Working correctly - retrieves flood values

---

## Proof: Backend IS Getting TIFF Values

### Sample Coordinate Queries

The backend successfully queries specific coordinates and retrieves flood depths:

```
Node 21322208: (14.660090, 121.104871) → Pixel (94, 197) → Depth: 0.480m
Node 21322209: (14.659838, 121.105379) → Pixel (95, 200) → Depth: 0.488m
Node 21458378: (14.625139, 121.102290) → Pixel (310, 181) → Depth: 0.259m
Node 21458438: (14.624397, 121.102286) → Pixel (315, 181) → Depth: 0.419m
```

### Sample Edge Queries

The backend queries both endpoints of graph edges:

```
Edge (21322208, 21322209):
  - Node 21322208: 0.480m
  - Node 21322209: 0.488m
  - Average: 0.484m ✅

Edge (21322209, 426255088):
  - Node 21322209: 0.488m
  - Node 426255088: 0.435m
  - Average: 0.461m ✅
```

### Coverage Statistics

**After alignment fix:**
- ✅ **98.8% of graph nodes** have TIFF coverage
- ✅ **33.4% of nodes** are flooded (>0.01m)
- ✅ **~6,715 edges** have flood data
- ✅ Depth range: 0.01m to 1.12m

### Visual Grid Sample

The TIFF value distribution across the area:
```
Legend: . = no data, - = 0-0.1m, + = 0.1-0.5m, * = 0.5-1m, # = >1m

...............
.-.-..-....#...
....+-.+--.-...
.-....-+---+...
..-...-...+-++.
.-...-.+-..+.-.
.+..+.#.-..+...
..-.--.+....-..
-+..+.--...+...
...-.+-.....-..
..+..+......+..
......*---.*...
.....++....++..
..-......-+....
..--.........-.
```

This shows realistic flood patterns with varying depths across the area!

---

## How They Work Together

### Frontend Flow
```
1. Fetch TIFF file from backend
2. Load entire 372x368 pixel array
3. Convert pixels to RGBA colors
4. Render as canvas overlay on map
5. Display visual representation
```

### Backend Flow
```
1. Graph edge needs flood depth
2. Get edge endpoint coordinates (lat, lon)
3. Transform to pixel coordinates (row, col)
4. Query TIFF array at [row][col]
5. Return depth value
6. Update graph edge weight
```

### Integration
```
Frontend:                    Backend:
  Map Display  ←──────→  Routing Algorithm
       ↓                        ↓
  Visual Only            Uses Real Values
  (Canvas Overlay)       (Edge Weights)
       ↓                        ↓
  Shows flood areas      Routes around floods
```

---

## Key Differences

| Aspect | Frontend | Backend |
|--------|----------|---------|
| **Purpose** | Visualization | Routing Logic |
| **What it loads** | Full TIFF image | TIFF data array |
| **How it uses data** | Render all pixels | Query specific coords |
| **Output** | Colored canvas | Numeric depth values |
| **For** | User viewing | Algorithm calculations |

---

## Verification Commands

### Test Backend TIFF Queries
```bash
cd masfro-backend
.venv/Scripts/python.exe scripts/test_coordinate_fix.py
```

### Show Detailed Value Retrieval
```bash
cd masfro-backend
.venv/Scripts/python.exe scripts/show_tiff_values_detailed.py
```

### Visualize Integration
```bash
cd masfro-backend
.venv/Scripts/python.exe scripts/visualize_real_geotiff.py
```

---

## Important Notes

### ✅ What's Working

1. **Frontend flood visualization** - Displays correctly on map
2. **Backend coordinate mapping** - Now matches frontend exactly
3. **TIFF value queries** - Successfully retrieves flood depths
4. **Graph integration** - Edge weights updated with real data
5. **Coverage alignment** - 98.8% of graph covered

### 🎯 Critical Configuration

**MUST keep these in sync:**

**Frontend (MapboxMap.js line 451-455):**
```javascript
const centerLng = 121.10305;
const centerLat = 14.6456;
const baseCoverage = 0.06;
```

**Backend (geotiff_service.py line 58-60):**
```python
MANUAL_CENTER_LAT = 14.6456
MANUAL_CENTER_LON = 121.10305
MANUAL_BASE_COVERAGE = 0.06
```

**If these don't match:**
- Frontend shows flood overlay in area X
- Backend queries flood data from area Y
- Routing uses wrong data!

---

## Conclusion

✅ **Frontend displays TIFF** - Visual overlay working
✅ **Backend queries TIFF** - Value retrieval working
✅ **Coordinates aligned** - Both use same coverage
✅ **Integration complete** - Ready for routing

Your system is now correctly retrieving and using TIFF flood data for both visualization AND routing!
