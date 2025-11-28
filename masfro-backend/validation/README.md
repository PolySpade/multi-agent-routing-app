# Routing Algorithm Validation System

**Version:** 1.0.0
**Author:** MAS-FRO Development Team
**Date:** November 2025

## Overview

This validation system compares the performance of two routing algorithms used in the MAS-FRO (Multi-Agent System for Flood Route Optimization) project:

1. **Baseline A*** - Traditional distance-only routing (shortest path)
2. **Risk-Aware A*** - Flood risk-aware routing (safest path considering flood risk)

The system generates 20,000 random source-target pairs (with ~1km distance constraint), computes routes using both algorithms, and compares:
- Average flood risk exposure
- Computation time
- Distance overhead
- High-risk segment avoidance

## Purpose

**Validate that the Risk-Aware A* algorithm produces safer evacuation routes** compared to baseline distance-only routing, while maintaining acceptable performance characteristics.

## System Architecture

```
validation/
├── __init__.py                    # Package initialization
├── route_pair_generator.py        # Generates random source-target pairs
├── metrics_collector.py           # Collects and aggregates metrics
├── algorithm_comparison.py        # Main comparison script
├── statistical_analysis.py        # Analysis and visualization
└── README.md                      # This file

Results structure:
validation/results/
├── comparison_results_YYYYMMDD_HHMMSS.json  # Raw metrics data
└── analysis/
    ├── analysis_report.txt                   # Detailed text report
    └── charts/                               # Visualization charts
        ├── risk_comparison.png
        ├── performance_overhead.png
        └── computation_time.png
```

## Installation

### Prerequisites

1. **UV package manager** (already installed for MAS-FRO project)
2. **Python 3.10+**
3. **Graph data** (`marikina_graph.graphml` in `app/data/`)
4. **Evacuation centers** (`evacuation_centers.csv` in `app/data/`)

### Optional Dependencies

For visualizations, install matplotlib:

```bash
uv add matplotlib
```

## Usage

### Quick Start

Run the full validation with 20,000 route pairs:

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Run comparison
uv run python validation/algorithm_comparison.py --pairs 20000
```

### Command-Line Options

```bash
uv run python validation/algorithm_comparison.py [OPTIONS]

Options:
  --pairs NUM              Number of route pairs to test (default: 20000)
  --output DIR             Output directory (default: validation/results)
  --risk-weight FLOAT      Risk weight for risk-aware A* (default: 0.6)
  --distance-weight FLOAT  Distance weight for risk-aware A* (default: 0.4)
```

### Examples

**Test with 1,000 pairs (quick test):**
```bash
uv run python validation/algorithm_comparison.py --pairs 1000
```

**Full validation with custom weights:**
```bash
uv run python validation/algorithm_comparison.py \
  --pairs 20000 \
  --risk-weight 0.7 \
  --distance-weight 0.3 \
  --output validation/results_custom
```

**Analyze existing results:**
```bash
uv run python validation/statistical_analysis.py \
  validation/results/comparison_results_20251120_143022.json \
  --output validation/analysis
```

## How It Works

### Step 1: Route Pair Generation

The `RoutePairGenerator` class:
1. Loads evacuation centers from CSV
2. Maps centers to nearest graph nodes (within 500m)
3. Randomly selects target (evacuation center node)
4. Finds source node approximately 1km away (±200m tolerance)
5. Verifies path exists using NetworkX

**Distance Constraint:** 800m - 1200m (1km ± 200m)

### Step 2: Route Computation

For each source-target pair, both algorithms compute a route:

**Baseline A***
- Minimizes total distance only
- Formula: `cost = edge_length`
- No consideration of flood risk

**Risk-Aware A***
- Balances distance and flood risk
- Formula: `cost = (distance × distance_weight) + (risk × distance × risk_weight)`
- Default weights: 60% risk, 40% distance
- Blocks roads with risk >= 0.9 (critical flood danger)

### Step 3: Metrics Collection

For each route, metrics are collected:

| Metric | Description |
|--------|-------------|
| `computation_time` | Time taken to compute route (seconds) |
| `total_distance` | Total route distance (meters) |
| `average_risk` | Distance-weighted average risk (0-1 scale) |
| `max_risk` | Maximum risk on any segment (0-1) |
| `high_risk_segments` | Count of segments with risk >= 0.6 |
| `critical_risk_segments` | Count of segments with risk >= 0.9 |
| `num_segments` | Total number of road segments |
| `success` | Whether route was found |

### Step 4: Statistical Analysis

Aggregate statistics computed:
- Average values for all metrics
- Min/max ranges
- Success rates
- Risk reduction percentage
- Distance overhead percentage
- Computation time overhead percentage

### Step 5: Report Generation

The system produces:
1. **Console summary** - Immediate feedback during execution
2. **JSON results** - Complete raw data for further analysis
3. **Text report** - Detailed analysis with conclusions
4. **Visualizations** - Charts comparing key metrics (if matplotlib available)

## Output Files

### comparison_results_[timestamp].json

Complete metrics data in JSON format:

```json
{
  "metadata": {
    "total_metrics": 40000,
    "baseline_count": 20000,
    "risk_aware_count": 20000,
    "timestamp": "2025-11-20T14:30:22"
  },
  "metrics": [
    {
      "source_node": 12345,
      "target_node": 67890,
      "algorithm": "baseline",
      "success": true,
      "computation_time": 0.0234,
      "total_distance": 1050.5,
      "average_risk": 0.4523,
      ...
    },
    ...
  ],
  "statistics": {
    "baseline": { ... },
    "risk_aware": { ... },
    "comparison": { ... }
  }
}
```

### analysis_report.txt

Detailed text report with:
- Executive summary
- Algorithm-specific statistics
- Comparative analysis
- Validation conclusions

### Visualization Charts

**risk_comparison.png**
- Bar chart comparing average risk scores
- High-risk segments per route

**performance_overhead.png**
- Distance overhead percentage
- Computation time overhead percentage

**computation_time.png**
- Average computation time comparison (milliseconds)

## Expected Results

Based on the algorithm design, we expect:

### ✅ Success Criteria

1. **Risk Reduction:** Risk-Aware A* should reduce average risk by **15-30%**
2. **Distance Overhead:** Should add less than **20%** extra distance
3. **Time Overhead:** Should add less than **50%** computation time
4. **High-Risk Avoidance:** Should avoid 2-5 high-risk segments per route

### 📊 Sample Output

```
ALGORITHM COMPARISON SUMMARY
================================================================================

📊 SUCCESS RATES:
  Baseline A*:    19845/20000 (99.2%)
  Risk-Aware A*:  19823/20000 (99.1%)

🛡️  RISK SCORES (0-1 scale, lower = safer):
  Baseline A* average risk:    0.4234
  Risk-Aware A* average risk:  0.3012
  → Risk reduction:            28.87%

📏 ROUTE DISTANCE:
  Baseline A*:    1052.3m average
  Risk-Aware A*:  1124.5m average
  → Overhead:     6.86%

⏱️  COMPUTATION TIME:
  Baseline A*:    23.45ms average
  Risk-Aware A*:  31.67ms average
  → Overhead:     35.04%

✅ VALIDATION RESULT:
  Risk-Aware A* successfully reduces average risk by 28.87%
  while adding only 6.86% distance overhead.
```

## Testing Individual Components

### Test Route Pair Generator

```bash
uv run python validation/route_pair_generator.py
```

Expected output:
```
Testing Route Pair Generator...
✓ Loaded graph with 12345 nodes
✓ Initialized generator
  Target nodes: 35

Generating 10 test pairs...
✓ Generated 10 pairs:
  1. 123456 -> 234567 (987.3m)
  2. 345678 -> 456789 (1042.1m)
  ...
```

### Test Metrics Collector

```bash
uv run python validation/metrics_collector.py
```

### Test Statistical Analysis

```bash
# First run comparison to generate results
uv run python validation/algorithm_comparison.py --pairs 100

# Then analyze
uv run python validation/statistical_analysis.py \
  validation/results/comparison_results_*.json
```

## Troubleshooting

### Graph Not Found

**Error:** `❌ Failed to load graph. Ensure marikina_graph.graphml exists.`

**Solution:**
```bash
# Check if graph file exists
ls app/data/marikina_graph.graphml

# If missing, download the map
uv run python scripts/download_map.py
```

### Evacuation Centers CSV Missing

**Error:** `❌ Evacuation centers CSV not found`

**Solution:**
```bash
# Verify CSV exists
ls app/data/evacuation_centers.csv

# Should contain 37 evacuation centers for Marikina City
```

### Low Pair Generation Success Rate

**Warning:** `⚠ Only generated 15000/20000 pairs (75.0%)`

**Causes:**
- Graph connectivity issues
- Too strict distance tolerance
- Limited evacuation center coverage

**Solutions:**
- Increase `max_attempts_per_pair` in code
- Adjust `distance_tolerance` (e.g., ±300m instead of ±200m)
- Add more evacuation centers to CSV

### Matplotlib Not Available

**Warning:** `Matplotlib not available - visualizations disabled`

**Solution:**
```bash
uv add matplotlib
```

Visualization charts will be skipped but text reports will still be generated.

## Performance Considerations

### Computation Time Estimates

| Route Pairs | Estimated Time | Notes |
|-------------|----------------|-------|
| 100 | ~30 seconds | Quick test |
| 1,000 | ~5 minutes | Medium test |
| 10,000 | ~45 minutes | Large test |
| 20,000 | ~90 minutes | Full validation |

Time varies based on:
- CPU speed
- Graph size (12,000+ nodes)
- Average path length
- Risk calculation complexity

### Memory Usage

- **Graph in memory:** ~50-100 MB
- **Metrics storage:** ~5-10 MB per 10,000 routes
- **Total peak usage:** ~200-300 MB for 20,000 pairs

### Optimization Tips

1. **Parallel processing** (future enhancement):
   - Process pairs in parallel using multiprocessing
   - Could reduce time by 50-70% on multi-core CPUs

2. **Batch processing:**
   - Process in batches of 1,000 pairs
   - Save intermediate results
   - Resume if interrupted

3. **Graph caching:**
   - Graph is already loaded once and reused
   - No need for optimization

## Interpreting Results

### Risk Reduction

- **> 20%:** Excellent - Algorithm significantly improves safety
- **10-20%:** Good - Meaningful risk reduction
- **5-10%:** Moderate - Some improvement
- **< 5%:** Poor - Limited benefit

### Distance Overhead

- **< 10%:** Excellent - Minimal extra distance
- **10-20%:** Acceptable - Reasonable trade-off
- **20-30%:** High - May discourage users
- **> 30%:** Excessive - Not practical

### Computation Time

- **< 50ms:** Excellent - Real-time capable
- **50-100ms:** Good - Acceptable for interactive use
- **100-200ms:** Moderate - Noticeable delay
- **> 200ms:** Slow - May need optimization

## Validation Criteria

The Risk-Aware A* algorithm is considered **VALIDATED** if:

1. ✅ Average risk reduction >= 15%
2. ✅ Distance overhead <= 20%
3. ✅ Computation time <= 100ms average
4. ✅ Success rate >= 95%
5. ✅ High-risk segment reduction >= 2 per route

## Future Enhancements

### Planned Features

1. **Parallel Processing**
   - Use multiprocessing for faster computation
   - Target: 4x speedup on quad-core CPU

2. **Statistical Significance Testing**
   - T-tests for risk reduction
   - Confidence intervals
   - P-values for validation

3. **Scenario Testing**
   - Compare across different rainfall intensities
   - Test multiple return periods (RR01-RR04)
   - Vary time steps (1-18 hours)

4. **Interactive Visualization**
   - Web-based dashboard
   - Real-time progress monitoring
   - Interactive charts with zoom/pan

5. **Route Visualization**
   - Plot actual routes on map
   - Show risk heatmap overlay
   - Compare baseline vs risk-aware paths

## Technical Details

### Risk Score Calculation

Risk scores are calculated by the `HazardAgent` using GeoTIFF flood depth maps:

```python
risk_score = min(flood_depth / 2.0, 1.0)  # Normalized to 0-1
```

- 0.0-0.2: Low risk (0-40cm water)
- 0.2-0.6: Moderate risk (40cm-1.2m water)
- 0.6-0.9: High risk (1.2m-1.8m water)
- 0.9-1.0: Critical risk (>1.8m water, impassable)

### Graph Structure

- **Nodes:** Road intersections and points
  - Attributes: `x` (longitude), `y` (latitude)
- **Edges:** Road segments
  - Attributes: `length` (meters), `risk_score` (0-1)
- **Type:** NetworkX MultiDiGraph (directed, multiple edges allowed)

### Algorithms

Both algorithms use NetworkX's `astar_path` function with custom weight and heuristic functions:

- **Heuristic:** Haversine distance (great-circle distance)
- **Weight:** Distance only (baseline) or distance + risk (risk-aware)

## Support

For issues or questions:

1. Check this README
2. Review code comments in validation modules
3. Check main project documentation
4. Contact MAS-FRO development team

## License

Part of the MAS-FRO project. See main project README for license information.

---

**Last Updated:** November 20, 2025
**Version:** 1.0.0
