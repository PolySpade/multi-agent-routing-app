# MAS-FRO Scripts Directory

**Last Updated:** November 14, 2025
**Total Scripts:** 28 Python files organized into 6 categories

This directory contains utility scripts for development, testing, debugging, and analysis of the MAS-FRO (Multi-Agent System for Flood Route Optimization) application.

---

## 📂 Directory Structure

```
scripts/
├── README.md                   # This file
├── testing/                    # Integration tests (9 scripts)
├── visualization/              # Data visualization tools (5 scripts)
├── diagnostics/                # Debug and troubleshooting (6 scripts)
├── data_generation/            # Synthetic data generators (4 scripts)
├── analysis/                   # Statistical analysis (1 script)
└── utilities/                  # General utilities (3 scripts)
```

---

## 🧪 Testing Scripts (9 files)

**Location:** `scripts/testing/`

Integration tests and validation scripts. These test various system components in isolation.

### test_coordinate_fix.py
- **Purpose:** Validates coordinate transformation fixes between EPSG:4326 and EPSG:3857
- **Tests:** Geographic coordinate conversions for GeoTIFF alignment
- **Usage:** `uv run python scripts/testing/test_coordinate_fix.py`
- **Output:** Console validation messages

### test_data_processing.py
- **Purpose:** Tests the data processing pipeline (19,538 bytes)
- **Tests:** FloodAgent data parsing, database saving, API responses
- **Usage:** `uv run python scripts/testing/test_data_processing.py`
- **Output:** Pass/fail results for data pipeline

### test_flood_agent_services.py
- **Purpose:** Comprehensive FloodAgent service tests (25,865 bytes)
- **Tests:**
  - PAGASA river scraper integration
  - OpenWeatherMap API calls
  - Fallback mechanisms
  - Data validation
- **Usage:** `uv run python scripts/testing/test_flood_agent_services.py`
- **Output:** Detailed test results with API response validation

### test_geotiff_toggle.py
- **Purpose:** Tests GeoTIFF layer toggle functionality
- **Tests:** Frontend layer visibility controls
- **Usage:** `uv run python scripts/testing/test_geotiff_toggle.py`
- **Output:** UI interaction test results

### test_high_risk_scenarios.py
- **Purpose:** Tests routing under extreme flood conditions (25,602 bytes)
- **Tests:**
  - Route calculation during 25-year floods (RR04)
  - Risk-aware pathfinding with high water levels
  - Edge case handling (impassable routes)
- **Usage:** `uv run python scripts/testing/test_high_risk_scenarios.py`
- **Output:** Route comparison data (safest vs baseline)

### test_multi_tiff_risk_update.py
- **Purpose:** Tests simultaneous risk updates from multiple GeoTIFF files
- **Tests:** HazardAgent processing of 72 flood maps
- **Usage:** `uv run python scripts/testing/test_multi_tiff_risk_update.py`
- **Output:** Risk score validation for different return periods

### test_routing_with_flood.py
- **Purpose:** Integration test for flood-aware routing (19,515 bytes)
- **Tests:**
  - RoutingAgent + HazardAgent collaboration
  - A* algorithm with risk weights
  - Route recalculation during floods
- **Usage:** `uv run python scripts/testing/test_routing_with_flood.py`
- **Output:** Routing performance metrics

### test_scout_geocoder_integration.py
- **Purpose:** Tests ScoutAgent geocoding functionality (15,404 bytes)
- **Tests:**
  - Location extraction from tweets
  - Marikina City boundary validation
  - Coordinate accuracy
- **Usage:** `uv run python scripts/testing/test_scout_geocoder_integration.py`
- **Output:** Geocoding accuracy report

### test_scout_simulation_mode.py
- **Purpose:** Tests ScoutAgent simulation mode (6,556 bytes)
- **Tests:** Synthetic tweet processing without live Twitter API
- **Usage:** `uv run python scripts/testing/test_scout_simulation_mode.py`
- **Output:** Simulation mode validation

**Recommendation:** These scripts should eventually migrate to `masfro-backend/tests/integration/` for proper pytest integration.

---

## 📊 Visualization Scripts (5 files)

**Location:** `scripts/visualization/`

Generate visual outputs including charts, maps, and animations.

### visualize_geotiff_integration.py
- **Purpose:** Visualizes GeoTIFF integration with routing system (14,532 bytes)
- **Features:**
  - Displays flood depth overlays on road network
  - Shows route paths with color-coded risk levels
  - Generates comparison maps (baseline vs flood-aware)
- **Usage:** `uv run python scripts/visualization/visualize_geotiff_integration.py`
- **Output:** PNG images in `outputs/` directory
- **Dependencies:** matplotlib, networkx, rasterio

### visualize_geotiff_quick.py
- **Purpose:** Quick GeoTIFF visualization without full system load (12,587 bytes)
- **Features:**
  - Fast preview of flood maps
  - Pixel value inspection
  - Coordinate grid overlay
- **Usage:** `uv run python scripts/visualization/visualize_geotiff_quick.py`
- **Output:** PNG preview images

### visualize_real_geotiff.py
- **Purpose:** Visualizes actual TIFF flood data (9,463 bytes)
- **Features:**
  - Reads real flood map files from `app/data/timed_floodmaps/`
  - Displays depth gradients with legend
  - Shows geographic bounds
- **Usage:** `uv run python scripts/visualization/visualize_real_geotiff.py`
- **Output:** Detailed flood depth maps

### visualize_routing.py
- **Purpose:** Visualizes route paths on OpenStreetMap data (14,910 bytes)
- **Features:**
  - Displays start/end points
  - Shows route paths with waypoints
  - Overlays flood risk zones
  - Generates comparison charts
- **Usage:** `uv run python scripts/visualization/visualize_routing.py`
- **Output:** Route visualization PNGs

### visualize_scout_tweets.py
- **Purpose:** Visualizes ScoutAgent tweet locations (20,163 bytes)
- **Features:**
  - Maps geocoded tweet locations
  - Shows flood report clusters
  - Heatmap of social media activity
  - Timeline visualization
- **Usage:** `uv run python scripts/visualization/visualize_scout_tweets.py`
- **Output:** Tweet location maps with heatmaps
- **Data Source:** Synthetic data from `app/data/synthetic/`

---

## 🔍 Diagnostic Scripts (6 files)

**Location:** `scripts/diagnostics/`

Debugging and troubleshooting tools for development.

### check_flood_tiff_coords.py
- **Purpose:** Inspects GeoTIFF coordinate systems (5,160 bytes)
- **Checks:**
  - Spatial reference (EPSG code)
  - Geographic bounds
  - Pixel resolution
  - Transform matrix
- **Usage:** `uv run python scripts/diagnostics/check_flood_tiff_coords.py app/data/timed_floodmaps/rr01/rr01-1.tif`
- **Output:** Coordinate system details

### check_parallel_edges.py
- **Purpose:** Detects duplicate edges in OSMnx graph (2,645 bytes)
- **Checks:** Parallel roads with same start/end nodes
- **Usage:** `uv run python scripts/diagnostics/check_parallel_edges.py`
- **Output:** List of duplicate edges (if any)

### check_tiff_simple.py
- **Purpose:** Simple TIFF file validation (4,795 bytes)
- **Checks:**
  - File readability
  - Basic metadata
  - Data integrity
- **Usage:** `uv run python scripts/diagnostics/check_tiff_simple.py`
- **Output:** File validation report

### debug_coordinate_transform.py
- **Purpose:** Debugs coordinate transformation issues (5,010 bytes)
- **Features:**
  - Step-by-step transformation logging
  - Compares multiple transformation methods
  - Identifies precision errors
- **Usage:** `uv run python scripts/diagnostics/debug_coordinate_transform.py`
- **Output:** Transformation debug logs

### diagnose_geotiff_data.py
- **Purpose:** Comprehensive GeoTIFF data diagnostics (4,688 bytes)
- **Checks:**
  - Pixel value ranges
  - NoData values
  - Histogram analysis
  - Anomaly detection
- **Usage:** `uv run python scripts/diagnostics/diagnose_geotiff_data.py`
- **Output:** Data quality report

### diagnose_routing.py
- **Purpose:** Diagnoses routing algorithm issues (4,210 bytes)
- **Checks:**
  - Graph connectivity
  - Node accessibility
  - Edge weight validity
  - Path existence
- **Usage:** `uv run python scripts/diagnostics/diagnose_routing.py`
- **Output:** Routing diagnostics report

---

## 📦 Data Generation Scripts (4 files)

**Location:** `scripts/data_generation/`

Generate synthetic data for testing without external API calls.

### create_mock_geotiff_demo.py
- **Purpose:** Creates demo GeoTIFF files for testing (10,669 bytes)
- **Features:**
  - Generates synthetic flood depth data
  - Creates proper geospatial metadata
  - Exports TIFF files with correct projections
- **Usage:** `uv run python scripts/data_generation/create_mock_geotiff_demo.py`
- **Output:** Mock TIFF files in `outputs/` directory

### generate_scout_synthetic_data.py
- **Purpose:** Generates realistic synthetic Twitter data (12,626 bytes)
- **Features:**
  - Creates 3 flood scenarios (typhoon, monsoon, light rain)
  - Generates tweets with Marikina locations
  - Includes metadata (timestamps, coordinates, user info)
  - Produces summary statistics
- **Usage:** `uv run python scripts/data_generation/generate_scout_synthetic_data.py`
- **Output:**
  - `app/data/synthetic/scout_tweets_1.json` (Typhoon scenario)
  - `app/data/synthetic/scout_tweets_2.json` (Monsoon scenario)
  - `app/data/synthetic/scout_tweets_3.json` (Light rain scenario)
  - `app/data/synthetic/scout_data_summary.json`

### run_data_collector.py
- **Purpose:** Manual weather data collection script (3,762 bytes)
- **Features:**
  - Fetches OpenWeatherMap data on-demand
  - Displays formatted weather information
  - Used for testing WeatherService
- **Usage:** `uv run python scripts/data_generation/run_data_collector.py`
- **Output:** Console output with weather data

### run_flood_service_tests.py
- **Purpose:** Tests flood service data collection (3,465 bytes)
- **Tests:**
  - FloodAgent real API integration
  - PAGASA scraper functionality
  - Data parsing and validation
- **Usage:** `uv run python scripts/data_generation/run_flood_service_tests.py`
- **Output:** Test results with actual API data

---

## 📈 Analysis Scripts (1 file)

**Location:** `scripts/analysis/`

Statistical analysis and benchmarking tools.

### analyze_1000_routes.py
- **Purpose:** Large-scale route comparison analysis (26,912 bytes)
- **Features:**
  - Generates 1000 random routes in Marikina City
  - Compares baseline (no flood awareness) vs safest (flood-aware) routes
  - Calculates statistical metrics:
    - Average distance difference
    - Average time difference
    - Risk reduction percentage
    - Route success rates
  - Tests extreme scenario: RR04 (25-year flood), Hour 18 (worst case)
- **Usage:** `uv run python scripts/analysis/analyze_1000_routes.py`
- **Output:**
  - `route_analysis_results.json` - Detailed statistics
  - Console report with charts
- **Runtime:** ~10-15 minutes for 1000 routes
- **Dependencies:** DynamicGraphEnvironment, RoutingAgent, HazardAgent

**Key Metrics:**
- Distance overhead (safest vs baseline)
- Travel time comparison
- Risk score reduction
- Success rate in high-flood scenarios

---

## 🛠️ Utility Scripts (3 files)

**Location:** `scripts/utilities/`

General-purpose utilities for project management.

### count_loc.py
- **Purpose:** Counts lines of code across the project (3,933 bytes)
- **Features:**
  - Recursive directory scanning
  - File type filtering (Python, JS, JSON, etc.)
  - Excludes node_modules, .venv, __pycache__
  - Generates summary report
- **Usage:** `uv run python scripts/utilities/count_loc.py`
- **Output:** Line count statistics by file type

### show_tiff_values_detailed.py
- **Purpose:** Displays detailed pixel values from GeoTIFF files (6,428 bytes)
- **Features:**
  - Reads TIFF data arrays
  - Shows pixel value distribution
  - Identifies min/max/mean values
  - Detects NoData pixels
- **Usage:** `uv run python scripts/utilities/show_tiff_values_detailed.py app/data/timed_floodmaps/rr01/rr01-1.tif`
- **Output:** Detailed pixel statistics

### verify_graph_size.py
- **Purpose:** Verifies OSMnx graph loaded correctly (1,597 bytes)
- **Checks:**
  - Number of nodes (expected: ~5000+)
  - Number of edges (expected: ~10000+)
  - Graph connectivity
  - Spatial extent
- **Usage:** `uv run python scripts/utilities/verify_graph_size.py`
- **Output:** Graph statistics validation

---

## 🚀 Quick Start Guide

### Running Scripts with UV

All scripts should be run using UV to ensure proper virtual environment:

```bash
# General pattern
uv run python scripts/<category>/<script_name>.py

# Examples
uv run python scripts/testing/test_flood_agent_services.py
uv run python scripts/visualization/visualize_routing.py
uv run python scripts/analysis/analyze_1000_routes.py
```

### Common Workflows

#### 1. Testing FloodAgent Integration
```bash
# Test real API calls
uv run python scripts/testing/test_flood_agent_services.py

# Generate synthetic data
uv run python scripts/data_generation/generate_scout_synthetic_data.py

# Run data collector
uv run python scripts/data_generation/run_data_collector.py
```

#### 2. Debugging GeoTIFF Issues
```bash
# Check coordinate system
uv run python scripts/diagnostics/check_flood_tiff_coords.py app/data/timed_floodmaps/rr01/rr01-1.tif

# Diagnose data quality
uv run python scripts/diagnostics/diagnose_geotiff_data.py

# Debug transformations
uv run python scripts/diagnostics/debug_coordinate_transform.py
```

#### 3. Visualizing System Behavior
```bash
# Visualize routes
uv run python scripts/visualization/visualize_routing.py

# Visualize flood maps
uv run python scripts/visualization/visualize_real_geotiff.py

# Visualize scout tweets
uv run python scripts/visualization/visualize_scout_tweets.py
```

#### 4. Performance Analysis
```bash
# Run 1000-route benchmark
uv run python scripts/analysis/analyze_1000_routes.py

# Count lines of code
uv run python scripts/utilities/count_loc.py
```

---

## 📋 Configuration Requirements

### Environment Variables

Ensure `.env` file is configured with:

```bash
# External APIs
OPENWEATHER_API_KEY=your_key_here
GOOGLE_PLACES_API_KEY=your_key_here

# Database (for some scripts)
DATABASE_URL=postgresql://user:pass@localhost:5432/masfro_db

# Coordinates
CITY_CENTER_LAT=14.650
CITY_CENTER_LON=121.100
```

### Data Dependencies

Some scripts require specific data files:

- **GeoTIFF files:** `app/data/timed_floodmaps/rr01/` through `rr04/`
- **Road network:** `app/data/marikina_graph.graphml`
- **Synthetic data:** `app/data/synthetic/scout_*.json`
- **Evacuation centers:** `app/data/evacuation_centers.csv`

---

## 🧹 Maintenance Guidelines

### Adding New Scripts

1. Place script in appropriate category directory
2. Add docstring with purpose, usage, and output
3. Update this README with script details
4. Add executable permissions: `chmod +x scripts/<category>/<script>.py`

### Script Naming Conventions

- **Testing:** `test_*.py`
- **Visualization:** `visualize_*.py`
- **Diagnostics:** `check_*.py`, `debug_*.py`, `diagnose_*.py`
- **Data Generation:** `create_*.py`, `generate_*.py`, `run_*.py`
- **Analysis:** `analyze_*.py`
- **Utilities:** Descriptive names (e.g., `count_loc.py`)

### Deprecation Process

1. Move outdated scripts to `scripts/archive/`
2. Document reason for deprecation in commit message
3. Update this README to remove script entry

---

## 📊 Output Directories

Scripts generate outputs in various locations:

- **Visualizations:** `outputs/`, `outputs/scout_visualizations/`
- **GeoTIFF animations:** `outputs/geotiff_animations/`
- **Test results:** `scripts/*.json` (generated in scripts directory)
- **Logs:** `masfro-backend/logs/`

---

## 🐛 Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Solution: Ensure you're using uv run
uv run python scripts/<category>/<script>.py
```

**Missing Dependencies:**
```bash
# Solution: Sync dependencies
cd masfro-backend
uv sync
```

**GeoTIFF Not Found:**
```bash
# Solution: Verify data directory
ls app/data/timed_floodmaps/rr01/
```

**API Key Errors:**
```bash
# Solution: Check .env file
cat .env | grep API_KEY
```

---

## 📚 Related Documentation

- **Main README:** `../../README.md`
- **TODO List:** `../../TODO.md`
- **Architecture:** `../../docs/ARCHITECTURE_OVERVIEW.md`
- **API Documentation:** `../../docs/API_ENDPOINTS.md`

---

## 📝 Contributing

When modifying scripts:

1. Follow PEP8 style guidelines
2. Add comprehensive docstrings
3. Include usage examples
4. Update this README
5. Test with `uv run` before committing
6. Keep scripts under 500 lines (refactor if needed)

---

## 📧 Support

For questions about specific scripts:
- Check script docstrings: `head -30 scripts/<category>/<script>.py`
- Review related documentation in `docs/`
- Check commit history: `git log scripts/<category>/<script>.py`

---

**Last Updated:** November 14, 2025
**Maintained By:** MAS-FRO Development Team
