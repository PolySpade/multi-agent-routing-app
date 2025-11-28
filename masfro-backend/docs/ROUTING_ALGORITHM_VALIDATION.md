# Routing Algorithm Validation Guide

**Project:** MAS-FRO (Multi-Agent System for Flood Route Optimization)
**Purpose:** Validate risk-aware A* routing algorithm effectiveness
**Date:** November 20, 2025

---

## Executive Summary

This document describes the validation system built to verify that the **Risk-Aware A* algorithm** produces safer evacuation routes compared to baseline distance-only routing.

### Key Objectives

1. ✅ Compare average flood risk exposure between algorithms
2. ✅ Measure computation time overhead
3. ✅ Analyze distance overhead (extra distance traveled)
4. ✅ Validate across 20,000 random 1km route pairs

### Validation Hypothesis

**"The Risk-Aware A* algorithm will reduce average flood risk exposure by at least 15% compared to baseline A* routing, while maintaining distance overhead below 20% and computation time under 100ms per route."**

---

## System Components

### 1. Route Pair Generator (`route_pair_generator.py`)

**Purpose:** Generate random source-target pairs for testing

**Features:**
- Maps 37 evacuation centers to graph nodes
- Generates source nodes ~1km from targets (±200m tolerance)
- Validates path existence before inclusion
- Tracks generation statistics

**Key Class:** `RoutePairGenerator`

```python
generator = RoutePairGenerator(
    graph=road_network,
    evacuation_centers_csv="app/data/evacuation_centers.csv",
    distance_target=1000.0,  # 1km
    distance_tolerance=200.0  # ±200m
)

pairs = generator.generate_pairs(count=20000)
# Returns: [(source, target, distance), ...]
```

### 2. Metrics Collector (`metrics_collector.py`)

**Purpose:** Collect and aggregate performance metrics

**Metrics Collected:**

| Metric | Type | Description |
|--------|------|-------------|
| `computation_time` | float | Seconds to compute route |
| `total_distance` | float | Total route distance (meters) |
| `average_risk` | float | Distance-weighted avg risk (0-1) |
| `max_risk` | float | Highest risk segment (0-1) |
| `high_risk_segments` | int | Segments with risk >= 0.6 |
| `critical_risk_segments` | int | Segments with risk >= 0.9 |
| `success` | bool | Whether route was found |

**Key Classes:** `RouteMetrics`, `MetricsCollector`

```python
collector = MetricsCollector()

metric = collector.collect_from_path(
    source=start_node,
    target=end_node,
    algorithm='risk_aware',
    path=computed_path,
    computation_time=0.0234,
    risk_metrics=risk_data
)

# Get aggregate statistics
stats = collector.get_aggregate_statistics('risk_aware')
comparison = collector.compare_algorithms()
```

### 3. Algorithm Comparison (`algorithm_comparison.py`)

**Purpose:** Main script to run full validation

**Process:**
1. Load graph and evacuation centers
2. Generate 20,000 route pairs
3. Compute routes using both algorithms
4. Collect metrics for each route
5. Generate comparison statistics
6. Save results to JSON

**Usage:**

```bash
# Full validation (20,000 pairs)
uv run python validation/algorithm_comparison.py --pairs 20000

# Quick test (1,000 pairs)
uv run python validation/algorithm_comparison.py --pairs 1000

# Custom output directory
uv run python validation/algorithm_comparison.py \
  --pairs 20000 \
  --output validation/results_nov20
```

### 4. Statistical Analysis (`statistical_analysis.py`)

**Purpose:** Analyze results and generate reports

**Outputs:**
- Detailed text report
- Visualization charts (if matplotlib available)
- Statistical summaries

**Usage:**

```bash
uv run python validation/statistical_analysis.py \
  validation/results/comparison_results_20251120_143022.json \
  --output validation/analysis
```

---

## Running the Validation

### Prerequisites Checklist

- [ ] UV package manager installed
- [ ] Virtual environment activated (`.venv\Scripts\activate`)
- [ ] Graph file exists (`app/data/marikina_graph.graphml`)
- [ ] Evacuation centers CSV exists (`app/data/evacuation_centers.csv`)
- [ ] All validation modules created

### Step-by-Step Execution

#### Step 1: Activate Environment

```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

#### Step 2: Quick Test (Optional)

Test with 100 pairs to verify everything works:

```bash
uv run python validation/algorithm_comparison.py --pairs 100
```

Expected output:
```
Initializing algorithm comparison...
  Graph nodes: 12345
  Graph edges: 23456
  Risk weight: 0.6
  Distance weight: 0.4
✓ Initialization complete

Generating 100 route pairs...
  Progress: 100/100 pairs generated (100.0% success rate)
✓ Generated 100 valid pairs

Computing routes for all pairs...
  Progress: 100/100 pairs (100.0%)
✓ Completed all route computations

ALGORITHM COMPARISON SUMMARY
...
```

#### Step 3: Full Validation

Run with 20,000 pairs:

```bash
uv run python validation/algorithm_comparison.py --pairs 20000
```

**Expected Duration:** ~60-90 minutes

**Progress Indicators:**
- Pair generation: Shows progress every 100 pairs
- Route computation: Shows progress every 100 pairs
- Final summary displayed at end

#### Step 4: Generate Analysis Report

After completion, analyze the results:

```bash
# Find the generated results file
ls validation/results/

# Run analysis (replace TIMESTAMP with actual value)
uv run python validation/statistical_analysis.py \
  validation/results/comparison_results_TIMESTAMP.json \
  --output validation/analysis
```

#### Step 5: Review Results

**Console Summary** - Displayed immediately after completion

**JSON Results** - `validation/results/comparison_results_TIMESTAMP.json`
- Complete raw data
- All individual route metrics
- Aggregate statistics

**Text Report** - `validation/analysis/analysis_report.txt`
- Executive summary
- Detailed statistics
- Conclusions

**Charts** - `validation/analysis/charts/`
- `risk_comparison.png` - Risk score comparison
- `performance_overhead.png` - Distance/time overhead
- `computation_time.png` - Computation time comparison

---

## Understanding the Results

### Success Metrics

#### 1. Risk Reduction

**Formula:** `(baseline_risk - risk_aware_risk) / baseline_risk × 100%`

**Interpretation:**
- **25-35%:** Excellent - Significant safety improvement
- **15-25%:** Good - Meaningful risk reduction ✅ **Target**
- **5-15%:** Moderate - Some benefit
- **< 5%:** Poor - Algorithm not effective

**Example:**
```
Baseline A* average risk:    0.4234
Risk-Aware A* average risk:  0.3012
→ Risk reduction:            28.87%  ✅ EXCELLENT
```

#### 2. Distance Overhead

**Formula:** `(risk_aware_dist - baseline_dist) / baseline_dist × 100%`

**Interpretation:**
- **< 10%:** Excellent - Minimal detour
- **10-20%:** Acceptable - Reasonable trade-off ✅ **Target**
- **20-30%:** High - Users may resist longer routes
- **> 30%:** Excessive - Not practical

**Example:**
```
Baseline A*:    1052.3m average
Risk-Aware A*:  1124.5m average
→ Overhead:     6.86%  ✅ EXCELLENT
```

#### 3. Computation Time

**Target:** < 100ms average (for real-time routing)

**Interpretation:**
- **< 50ms:** Excellent - Instant response
- **50-100ms:** Good - Acceptable latency ✅ **Target**
- **100-200ms:** Moderate - Noticeable delay
- **> 200ms:** Slow - Needs optimization

**Example:**
```
Baseline A*:    23.45ms average
Risk-Aware A*:  31.67ms average
→ Overhead:     35.04%  ✅ GOOD
```

#### 4. High-Risk Segment Avoidance

**Metric:** Average reduction in segments with risk >= 0.6

**Interpretation:**
- **> 3 segments:** Excellent - Major safety improvement
- **2-3 segments:** Good - Significant avoidance ✅ **Target**
- **1-2 segments:** Moderate - Some benefit
- **< 1 segment:** Poor - Limited impact

**Example:**
```
Baseline A*:    4.23 high-risk segments/route
Risk-Aware A*:  1.45 high-risk segments/route
→ Reduction:    2.78 segments/route  ✅ EXCELLENT
```

### Validation Decision

**VALIDATED** if all criteria met:

- ✅ Risk reduction >= 15%
- ✅ Distance overhead <= 20%
- ✅ Computation time <= 100ms
- ✅ Success rate >= 95%
- ✅ High-risk segment reduction >= 2

**Example Validation Result:**

```
✅ VALIDATION SUCCESSFUL

The Risk-Aware A* algorithm successfully reduces flood risk exposure
by 28.87% compared to baseline distance-only routing.

Key findings:
- Routes are 28.87% safer on average
- Avoid 2.78 high-risk segments per route
- Add only 6.86% extra distance
- Computation time overhead: 35.04%

The algorithm is VALIDATED for use in flood evacuation routing.
```

---

## Technical Specifications

### Route Pair Generation Constraints

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Target distance | 1000m (1km) | Typical evacuation distance |
| Distance tolerance | ±200m | Allows 800-1200m range |
| Source selection | Random graph node | Unbiased sampling |
| Target selection | Evacuation center node | Realistic evacuation scenario |
| Path validation | NetworkX has_path() | Ensures route exists |

### Algorithm Parameters

**Baseline A***
```python
# Cost function
cost = edge_length

# No risk consideration
# Finds shortest path by distance only
```

**Risk-Aware A***
```python
# Cost function
cost = (distance × distance_weight) + (risk × distance × risk_weight)

# Default weights
risk_weight = 0.6      # 60% weight on safety
distance_weight = 0.4  # 40% weight on distance

# Road blocking
if risk_score >= 0.9:
    cost = infinity  # Impassable
```

### Risk Score Scale

| Risk Score | Water Depth | Category | Road Status |
|------------|-------------|----------|-------------|
| 0.0 - 0.2 | 0 - 40cm | Low | Safe |
| 0.2 - 0.6 | 40cm - 1.2m | Moderate | Caution |
| 0.6 - 0.9 | 1.2m - 1.8m | High | Dangerous |
| 0.9 - 1.0 | > 1.8m | Critical | Impassable |

---

## Output File Reference

### 1. comparison_results_[timestamp].json

**Location:** `validation/results/`

**Structure:**

```json
{
  "metadata": {
    "total_metrics": 40000,
    "baseline_count": 20000,
    "risk_aware_count": 20000,
    "timestamp": "2025-11-20T14:30:22.123456"
  },
  "metrics": [
    {
      "source_node": 123456789,
      "target_node": 987654321,
      "algorithm": "baseline",
      "success": true,
      "computation_time": 0.0234,
      "path_length_nodes": 15,
      "total_distance": 1052.3,
      "average_risk": 0.4523,
      "max_risk": 0.7234,
      "high_risk_segments": 4,
      "critical_risk_segments": 0,
      "num_segments": 14,
      "error_message": "",
      "timestamp": "2025-11-20T14:30:22.234567"
    },
    ...
  ],
  "statistics": {
    "baseline": {
      "total_routes": 20000,
      "successful_routes": 19845,
      "failed_routes": 155,
      "success_rate": 99.225,
      "avg_computation_time": 0.02345,
      "avg_distance": 1052.3,
      "avg_risk": 0.4234,
      "avg_max_risk": 0.6123,
      "avg_high_risk_segments": 4.23,
      "avg_critical_risk_segments": 0.12
    },
    "risk_aware": {
      ...
    },
    "comparison": {
      "risk_reduction": 28.87,
      "distance_overhead": 6.86,
      "time_overhead": 35.04,
      ...
    }
  }
}
```

### 2. analysis_report.txt

**Location:** `validation/analysis/`

**Sections:**
1. Header and metadata
2. Executive summary
3. Baseline A* statistics
4. Risk-Aware A* statistics
5. Comparative analysis
6. Conclusions

### 3. Visualization Charts

**risk_comparison.png**
- Side-by-side bar chart
- Average risk scores (0-1 scale)
- High-risk segments per route

**performance_overhead.png**
- Bar chart showing percentages
- Distance overhead
- Computation time overhead

**computation_time.png**
- Bar chart in milliseconds
- Baseline vs Risk-Aware average computation time

---

## Troubleshooting Guide

### Issue: Low Pair Generation Success Rate

**Symptom:** `⚠ Only generated 15000/20000 pairs (75.0%)`

**Causes:**
1. Graph connectivity issues (disconnected components)
2. Too strict distance tolerance
3. Limited evacuation center coverage in area

**Solutions:**

```python
# Option 1: Increase tolerance
generator = RoutePairGenerator(
    graph,
    evac_csv,
    distance_target=1000.0,
    distance_tolerance=300.0  # Increased to ±300m
)

# Option 2: Increase max attempts
pairs = generator.generate_pairs(
    count=20000,
    max_attempts_per_pair=200  # Increased from 100
)
```

### Issue: High Failure Rate in Route Computation

**Symptom:** Success rate < 95%

**Causes:**
1. Graph has disconnected components
2. Risk threshold too strict (blocks too many roads)
3. Missing risk scores on edges

**Solutions:**

```python
# Check graph connectivity
import networkx as nx
if not nx.is_strongly_connected(graph):
    # Graph has disconnected components
    largest = max(nx.strongly_connected_components(graph), key=len)
    graph = graph.subgraph(largest)

# Adjust risk threshold
risk_aware_astar(
    graph, start, end,
    max_risk_threshold=0.95  # More permissive (default: 0.9)
)
```

### Issue: Computation Takes Too Long

**Symptom:** 20,000 pairs taking > 2 hours

**Solutions:**

1. **Test with smaller sample first:**
   ```bash
   uv run python validation/algorithm_comparison.py --pairs 5000
   ```

2. **Process in batches:**
   ```python
   # Modify algorithm_comparison.py to save every 1000 pairs
   # Resume from last saved batch if interrupted
   ```

3. **Optimize graph (future):**
   - Reduce to essential nodes
   - Pre-compute commonly used paths

### Issue: Memory Error

**Symptom:** System runs out of memory

**Causes:**
- Graph too large
- Too many metrics stored in memory

**Solutions:**

```python
# Flush metrics to disk periodically
if len(collector.metrics) > 5000:
    collector.save_to_json(f"partial_results_{batch}.json")
    collector.metrics.clear()
```

---

## Advanced Usage

### Custom Risk Weights

Test different risk/distance trade-offs:

```bash
# More emphasis on safety (70% risk, 30% distance)
uv run python validation/algorithm_comparison.py \
  --pairs 20000 \
  --risk-weight 0.7 \
  --distance-weight 0.3

# More emphasis on distance (50% risk, 50% distance)
uv run python validation/algorithm_comparison.py \
  --pairs 20000 \
  --risk-weight 0.5 \
  --distance-weight 0.5
```

### Batch Processing

Process in smaller batches for long-running validation:

```bash
# Batch 1 (pairs 1-5000)
uv run python validation/algorithm_comparison.py \
  --pairs 5000 \
  --output validation/results/batch1

# Batch 2 (pairs 5001-10000)
uv run python validation/algorithm_comparison.py \
  --pairs 5000 \
  --output validation/results/batch2

# ... etc
```

### Scenario Testing

Test with different flood scenarios:

```python
# Modify hazard_agent.py to load different GeoTIFF
# Example: Test with different return periods

# RR01 (2-year flood)
hazard_agent.load_geotiff("rr01", time_step=6)

# RR04 (10-year flood)
hazard_agent.load_geotiff("rr04", time_step=6)
```

---

## Best Practices

### 1. Always Run Quick Test First

```bash
# Test with 100 pairs before full validation
uv run python validation/algorithm_comparison.py --pairs 100
```

Verify:
- ✅ Graph loads correctly
- ✅ Pair generation works
- ✅ Both algorithms compute routes
- ✅ Metrics collected properly

### 2. Monitor Progress

Check console output regularly:
- Pair generation progress
- Route computation progress
- Success rates
- Any warnings or errors

### 3. Save Results with Descriptive Names

```bash
# Use descriptive output directories
uv run python validation/algorithm_comparison.py \
  --pairs 20000 \
  --output validation/results/baseline_validation_nov20

# Or with custom parameters
uv run python validation/algorithm_comparison.py \
  --pairs 20000 \
  --risk-weight 0.7 \
  --output validation/results/high_risk_weight_validation
```

### 4. Analyze Results Immediately

After validation completes, run analysis right away:

```bash
uv run python validation/statistical_analysis.py \
  validation/results/comparison_results_*.json \
  --output validation/analysis
```

Review text report while results are fresh.

### 5. Archive Important Results

```bash
# Create archive directory
mkdir -p validation/archive/nov20_baseline

# Copy results
cp validation/results/comparison_results_*.json validation/archive/nov20_baseline/
cp -r validation/analysis/ validation/archive/nov20_baseline/
```

---

## Validation Checklist

### Pre-Validation

- [ ] Graph file exists and loads successfully
- [ ] Evacuation centers CSV complete (37 centers)
- [ ] Virtual environment activated
- [ ] Quick test (100 pairs) passes
- [ ] Sufficient disk space (~500 MB)
- [ ] Sufficient time allocated (90-120 minutes)

### During Validation

- [ ] Monitor console output for errors
- [ ] Check pair generation success rate (should be > 80%)
- [ ] Verify route computation progressing
- [ ] Note any warnings or unusual behavior

### Post-Validation

- [ ] Results file generated
- [ ] Success rate >= 95%
- [ ] Risk reduction >= 15%
- [ ] Distance overhead <= 20%
- [ ] Computation time reasonable
- [ ] Analysis report generated
- [ ] Charts created (if matplotlib available)
- [ ] Results archived with descriptive name

---

## Appendix: File Locations

```
masfro-backend/
├── app/
│   ├── data/
│   │   ├── marikina_graph.graphml        # Road network graph
│   │   └── evacuation_centers.csv        # 37 evacuation centers
│   ├── algorithms/
│   │   ├── baseline_astar.py             # Baseline algorithm
│   │   └── risk_aware_astar.py           # Risk-aware algorithm
│   └── environment/
│       └── graph_manager.py              # Graph management
├── validation/
│   ├── __init__.py
│   ├── route_pair_generator.py           # Pair generation
│   ├── metrics_collector.py              # Metrics collection
│   ├── algorithm_comparison.py           # Main comparison script
│   ├── statistical_analysis.py           # Analysis & visualization
│   ├── README.md                         # Technical documentation
│   ├── results/
│   │   └── comparison_results_*.json     # Results files
│   └── analysis/
│       ├── analysis_report.txt           # Text report
│       └── charts/                       # Visualization charts
└── ROUTING_ALGORITHM_VALIDATION.md       # This document
```

---

## Contact & Support

For questions or issues:

1. Check this validation guide
2. Review `validation/README.md` for technical details
3. Check code comments in validation modules
4. Contact MAS-FRO development team

---

**Document Version:** 1.0.0
**Last Updated:** November 20, 2025
**Author:** MAS-FRO Development Team
