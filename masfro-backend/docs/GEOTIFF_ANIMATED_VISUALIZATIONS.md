# GeoTIFF Animated Flood Visualizations

## Overview

This document describes the comprehensive animated visualizations created for all 72 GeoTIFF flood scenarios in the multi-agent routing system.

## Generated Outputs

### Animated GIFs (4 files)

Each GIF shows the flood progression over 18 hourly time steps:

1. **flood_animation_rr01.gif** - 2-Year Flood Event
   - 18 frames showing hourly progression
   - Lower severity flood scenario
   - Approximately 16-33% of road network affected

2. **flood_animation_rr02.gif** - 5-Year Flood Event
   - 18 frames showing hourly progression
   - Moderate severity flood scenario
   - Approximately 29-42% of road network affected

3. **flood_animation_rr03.gif** - Higher Return Period
   - 18 frames showing hourly progression
   - Higher severity flood scenario
   - Approximately 38-51% of road network affected

4. **flood_animation_rr04.gif** - 10-Year Flood Event
   - 18 frames showing hourly progression
   - Highest severity flood scenario
   - Approximately 42-54% of road network affected

### Individual Frames (72 files)

Each return period has 18 individual PNG frames:
- `rr01_step_01.png` through `rr01_step_18.png`
- `rr02_step_01.png` through `rr02_step_18.png`
- `rr03_step_01.png` through `rr03_step_18.png`
- `rr04_step_01.png` through `rr04_step_18.png`

## Color Scheme - Dramatic Visualization

The visualizations use an enhanced, dramatic color scheme designed to make moderate and high-risk areas visually striking:

| Risk Level | Color | Hex Code | Description |
|------------|-------|----------|-------------|
| **Safe** | Emerald Green | `#2ECC71` | No flood water (0.0 risk) |
| **Minimal** | Light Green | `#A8E6CF` | 0.0-0.2 risk score |
| **Low** | Gold | `#FFD700` | 0.2-0.4 risk score |
| **MODERATE** | **Bright Red-Orange** | **`#FF6B35`** | **0.4-0.6 risk score** (DRAMATIC!) |
| **HIGH** | Crimson Red | `#E63946` | 0.6-0.8 risk score |
| **EXTREME** | Dark Red/Maroon | `#990000` | 0.8-1.0 risk score |

### Design Rationale

**Dramatic Moderate Colors**: The key enhancement is making moderate-risk areas (0.4-0.6) display in **bright red-orange** instead of yellow. This creates a more dramatic and attention-grabbing visualization, immediately highlighting areas that require caution even before reaching high-risk levels.

**Visual Hierarchy**:
- Safe roads: Green (calm, passable)
- Low risk: Gold (proceed with caution)
- **Moderate risk: RED-ORANGE (WARNING! - significant flood risk)**
- High/Extreme: Deep reds (DANGER! - avoid these routes)

## Frame Details

Each visualization frame includes:

### Map Visualization
- Road network displayed with edges colored by flood risk
- Flooded edges rendered thicker (1.2px) and more opaque (90% alpha)
- Safe edges rendered thinner (0.4px) and more transparent (30% alpha)
- Grid overlay for geographic reference

### Title
- Return period name (e.g., "2-Year Flood", "10-Year Flood")
- Current time step (e.g., "Hour 5/18")

### Statistics Box
- **Flooded Edges**: Count and percentage of affected roads
- **Max Risk**: Highest risk score in current scenario
- **Mean Risk**: Average risk across all edges

### Legend
- Color-coded risk categories with labels
- Positioned in upper right corner

## Technical Specifications

### Image Properties
- **Resolution**: 1680×1200 pixels (14×10 inches at 120 DPI)
- **Format**: PNG (frames), GIF (animations)
- **DPI**: 120 (high quality)
- **Background**: White
- **Grid**: Light gray dashed lines (20% opacity)

### Animation Properties
- **Frame Duration**: 400ms per frame (0.4 seconds)
- **Total Frames**: 18 per GIF
- **Total Duration**: ~7.2 seconds per loop
- **Loop**: Infinite
- **Optimization**: Disabled (preserves quality)

### File Sizes (Approximate)
- Individual PNG frame: ~100-200 KB each
- Animated GIF: ~15-30 MB each (depending on complexity)
- Total output: ~120 MB for all files

## Usage

### Viewing the GIFs

The animated GIFs can be opened with any standard image viewer or web browser:

```bash
# Windows
start outputs/geotiff_animations/flood_animation_rr01.gif

# macOS
open outputs/geotiff_animations/flood_animation_rr01.gif

# Linux
xdg-open outputs/geotiff_animations/flood_animation_rr01.gif
```

### Integration in Documentation

The GIFs can be embedded in markdown documentation:

```markdown
![2-Year Flood Animation](outputs/geotiff_animations/flood_animation_rr01.gif)
```

### Presentation Use

The individual PNG frames can be used for:
- Static presentation slides
- Detailed analysis of specific time steps
- Side-by-side comparisons of different scenarios
- Printed materials

## Regenerating Visualizations

To regenerate all visualizations:

```bash
cd masfro-backend
.venv/Scripts/python.exe scripts/visualize_geotiff_integration.py
```

**Processing Time**: Approximately 15-30 minutes for all 72 scenarios (depends on system performance)

**Output Location**: `masfro-backend/outputs/geotiff_animations/`

## Key Insights from Visualizations

### Flood Progression Patterns

1. **Early Stage (Hours 1-6)**
   - Rapid flood onset
   - RR01: 16% → 30% affected edges
   - RR04: 42% → 51% affected edges

2. **Peak Stage (Hours 7-12)**
   - Maximum flood extent reached
   - Flood depth increases
   - Risk scores stabilize

3. **Late Stage (Hours 13-18)**
   - Gradual flood recession or stabilization
   - Some scenarios show continued increase
   - Pattern varies by return period

### Return Period Comparison

Progressive severity increase as expected:

| Return Period | Hour 10 Flooded Edges | Hour 10 Max Risk |
|---------------|----------------------|------------------|
| RR01 (2-year) | 33.3% | 0.405 |
| RR02 (5-year) | 42.0% | 0.425 |
| RR03 | 50.5% | 0.467 |
| RR04 (10-year) | 54.4% | 0.490 |

### Geographic Patterns

The visualizations reveal:
- Concentrated flooding in low-lying areas
- River-adjacent roads most affected
- Progressive spread from flood origins
- Some areas consistently flooded across all scenarios

## Scientific Accuracy

### Risk Score Calculation

Risk scores are calculated from actual TIFF flood depths using the formula:

```python
if depth <= 0.3m:
    risk = depth  # Linear 0.0-0.3
elif depth <= 0.6m:
    risk = 0.3 + (depth - 0.3) * 1.0  # Linear 0.3-0.6
elif depth <= 1.0m:
    risk = 0.6 + (depth - 0.6) * 0.5  # Linear 0.6-0.8
else:
    risk = min(0.8 + (depth - 1.0) * 0.2, 1.0)  # Capped at 1.0
```

### Geographic Alignment

- **Center Point**: (14.6456°N, 121.10305°E) - Marikina City
- **Coverage**: 0.06° (~6.6 km)
- **Coordinate System**: Manual mapping (EPSG:4326)
- **Coverage Rate**: 98.8% of road network has flood data

## Comparison with Frontend

The backend visualizations align with frontend flood overlays:

| Aspect | Frontend | Backend Visualization |
|--------|----------|----------------------|
| **Purpose** | Real-time user interface | Analysis & documentation |
| **Data Source** | Same TIFF files | Same TIFF files |
| **Coordinates** | (14.6456, 121.10305) | (14.6456, 121.10305) |
| **Coverage** | 0.06° | 0.06° |
| **Colors** | Blue gradient | Dramatic red/orange/green |
| **Update** | Dynamic (user-controlled) | Static frames + GIF |

## Future Enhancements

Potential improvements for future versions:

1. **Interactive HTML Visualizations**
   - Add time slider
   - Click edges for detailed stats
   - Toggle between return periods

2. **Comparison Views**
   - Side-by-side return period comparison
   - Difference maps showing change over time
   - Statistical overlays

3. **Enhanced Annotations**
   - Street names on major roads
   - Landmark labels
   - Flood depth contours

4. **Video Export**
   - MP4/WebM format for better compression
   - Higher frame rate options
   - Narration or captions

5. **3D Visualizations**
   - Elevation-aware rendering
   - Flood depth as vertical dimension
   - Rotatable/zoomable views

## References

- **Source Data**: `app/data/timed_floodmaps/` (72 GeoTIFF files)
- **Service**: `app/services/geotiff_service.py` (coordinate mapping)
- **Agent**: `app/agents/hazard_agent.py` (risk calculation)
- **Visualization**: `scripts/visualize_geotiff_integration.py`
- **Documentation**: `docs/GEOTIFF_INTEGRATION_SUMMARY.md`

---

**Created**: 2025-01-12
**Script Version**: 2.0 (Dramatic Colors + Animations)
**Total Scenarios**: 72 (4 return periods × 18 time steps)
**Output Format**: PNG frames + animated GIFs
