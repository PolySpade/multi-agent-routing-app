# Flood Map Stretch Fix

**Issue:** Flood map is within Marikina bounds but appears stretched
**Cause:** Aspect ratio mismatch between TIFF image and bounding box

---

## 🔍 Diagnostic Steps

### Step 1: Check TIFF Dimensions in Console

When the flood map loads, check the browser console (F12) for:
```
ArrayBuffer size: 1096168 bytes
```

The image dimensions should be logged. Look for width x height.

### Step 2: Calculate Aspect Ratios

**Current Bounding Box:**
- Width: 121.1150 - 121.0850 = 0.03° longitude
- Height: 14.7300 - 14.6400 = 0.09° latitude
- Aspect Ratio: 0.03 / 0.09 = 0.333 (Width / Height)

**TIFF Image:**
- Need to know actual pixel dimensions
- Typical GeoTIFF: 512x512, 1024x1024, or other

If TIFF is 512x512 (square), but bounding box is 0.333 (tall rectangle), the image will be stretched.

---

## 🛠️ Solution Options

### Option 1: Add Image Dimension Logging

Add this to MapboxMap.js after line 417:

```javascript
const width = image.getWidth();
const height = image.getHeight();
console.log('TIFF dimensions:', width, 'x', height, 'pixels');
console.log('TIFF aspect ratio:', (width / height).toFixed(3));

// Calculate bounding box aspect ratio
const bboxWidth = 121.1150 - 121.0850;
const bboxHeight = 14.7300 - 14.6400;
console.log('Bounding box aspect ratio:', (bboxWidth / bboxHeight).toFixed(3));
console.log('Aspect ratio match:', Math.abs((width/height) - (bboxWidth/bboxHeight)) < 0.1 ? 'GOOD' : 'MISMATCH');
```

### Option 2: Adjust Bounding Box to Match TIFF Aspect Ratio

If TIFF is square (1:1 aspect ratio), adjust bounds:

```javascript
// For SQUARE TIFF (1:1 ratio)
const MARIKINA_BOUNDS = {
  west:  121.0700,  // Wider
  east:  121.1300,  // Wider
  south:  14.6400,
  north:  14.7300
};
```

If TIFF is wider (e.g., 2:1 ratio):

```javascript
// For WIDE TIFF (2:1 ratio)
const MARIKINA_BOUNDS = {
  west:  121.0600,
  east:  121.1400,
  south:  14.6700,
  north:  14.7000
};
```

---

## 🎯 Try These Fixes

### Fix 1: Wider Bounding Box (Most Common)

Replace lines 421-426 in MapboxMap.js:

```javascript
const MARIKINA_BOUNDS = {
  west:  121.0700,  // Expanded westward
  east:  121.1300,  // Expanded eastward
  south:  14.6400,  // Keep same
  north:  14.7300   // Keep same
};
```

### Fix 2: Taller Bounding Box

```javascript
const MARIKINA_BOUNDS = {
  west:  121.0850,  // Keep same
  east:  121.1150,  // Keep same
  south:  14.6200,  // Expanded southward
  north:  14.7500   // Expanded northward
};
```

### Fix 3: Square Bounding Box (1:1 ratio)

```javascript
const MARIKINA_BOUNDS = {
  west:  121.0700,
  east:  121.1300,  // 0.06° width
  south:  14.6400,
  north:  14.7000   // 0.06° height (same as width)
};
```

---

## 🔄 Alternative: Let TIFF Determine Bounds

Replace the entire bounding box section with auto-calculation:

```javascript
const width = image.getWidth();
const height = image.getHeight();

// Center point of Marikina City
const centerLng = 121.1000;
const centerLat = 14.6850;

// Calculate bounds based on TIFF aspect ratio
const tiffAspectRatio = width / height;

// Desired coverage area (in degrees)
let coverageWidth, coverageHeight;

if (tiffAspectRatio > 1) {
  // Wider TIFF
  coverageWidth = 0.06;  // 0.06° longitude
  coverageHeight = coverageWidth / tiffAspectRatio;
} else {
  // Taller TIFF
  coverageHeight = 0.09;  // 0.09° latitude
  coverageWidth = coverageHeight * tiffAspectRatio;
}

const MARIKINA_BOUNDS = {
  west:  centerLng - (coverageWidth / 2),
  east:  centerLng + (coverageWidth / 2),
  south: centerLat - (coverageHeight / 2),
  north: centerLat + (coverageHeight / 2)
};

console.log('Auto-calculated bounds based on TIFF aspect ratio:', MARIKINA_BOUNDS);
```

---

## 📐 Coordinate Order Issues

If the image appears flipped or rotated, try different coordinate orders:

### Current Order (should be correct):
```javascript
const reprojectedCoords = [
  [MARIKINA_BOUNDS.west, MARIKINA_BOUNDS.north], // top-left
  [MARIKINA_BOUNDS.east, MARIKINA_BOUNDS.north], // top-right
  [MARIKINA_BOUNDS.east, MARIKINA_BOUNDS.south], // bottom-right
  [MARIKINA_BOUNDS.west, MARIKINA_BOUNDS.south]  // bottom-left
];
```

### Alternative 1 (Counter-clockwise):
```javascript
const reprojectedCoords = [
  [MARIKINA_BOUNDS.west, MARIKINA_BOUNDS.north], // top-left
  [MARIKINA_BOUNDS.west, MARIKINA_BOUNDS.south], // bottom-left
  [MARIKINA_BOUNDS.east, MARIKINA_BOUNDS.south], // bottom-right
  [MARIKINA_BOUNDS.east, MARIKINA_BOUNDS.north]  // top-right
];
```

### Alternative 2 (Start bottom-left):
```javascript
const reprojectedCoords = [
  [MARIKINA_BOUNDS.west, MARIKINA_BOUNDS.south], // bottom-left
  [MARIKINA_BOUNDS.east, MARIKINA_BOUNDS.south], // bottom-right
  [MARIKINA_BOUNDS.east, MARIKINA_BOUNDS.north], // top-right
  [MARIKINA_BOUNDS.west, MARIKINA_BOUNDS.north]  // top-left
];
```

---

## 🧪 Testing Each Fix

1. Apply a fix
2. Save the file
3. Refresh browser (Ctrl+R)
4. Check console for dimension logs
5. Check visual alignment

Repeat until alignment is correct.

---

**Next:** I'll create an updated MapboxMap.js with auto-aspect-ratio detection.
