# Testing 20,000 Routes - Complete Guide

**Version:** 1.0.0
**Date:** November 20, 2025

## Table of Contents

1. [Pre-Flight Checklist](#pre-flight-checklist)
2. [Running the Full Test](#running-the-full-test)
3. [Verifying Test Correctness](#verifying-test-correctness)
4. [Analysis & Interpretation](#analysis--interpretation)
5. [Troubleshooting](#troubleshooting)
6. [Validation Scripts](#validation-scripts)

---

## Pre-Flight Checklist

Before running 20,000 routes, verify your system is ready:

### 1. Environment Setup

```bash
# Navigate to backend directory
cd masfro-backend

# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Verify UV is working
uv --version
```

### 2. Required Files

```bash
# Check graph file exists
ls app/data/marikina_graph.graphml

# Check evacuation centers
ls app/data/evacuation_centers.csv

# Expected: 37 evacuation centers
```

### 3. Risk Data Loading (CRITICAL!)

**⚠️ WARNING:** Without risk scores, the test will show 0% risk reduction!

```python
# Create a script to verify risk scores: check_risk_scores.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.environment.graph_manager import DynamicGraphEnvironment

# Load graph
env = DynamicGraphEnvironment()
graph = env.get_graph()

# Check risk scores
edges_with_risk = sum(1 for u, v, data in graph.edges(data=True)
                      if data.get('risk_score', 0) > 0)
total_edges = len(graph.edges())

print(f"Total edges: {total_edges}")
print(f"Edges with risk > 0: {edges_with_risk}")
print(f"Risk coverage: {edges_with_risk/total_edges*100:.1f}%")

if edges_with_risk == 0:
    print("\n❌ NO RISK SCORES FOUND!")
    print("You must load GeoTIFF data before testing.")
    print("\nTo load risk data:")
    print("  1. Ensure GeoTIFF files exist in app/data/geotiff/")
    print("  2. Run hazard agent to load risk scores")
else:
    print("\n✅ Risk scores are loaded - ready to test!")
```

Run the check:
```bash
uv run python validation/check_risk_scores.py
```

**If risk scores are missing, you need to load them first!**

### 4. System Resources

Ensure you have:
- **Disk space:** ~100 MB free for results
- **RAM:** ~500 MB available
- **Time:** ~90-120 minutes for 20,000 pairs
- **CPU:** Any modern processor (4+ cores recommended)

---

## Running the Full Test

### Quick Test First (Recommended)

Always start with a small test to verify everything works:

```bash
# Test with 10 pairs (~30 seconds)
uv run python validation/algorithm_comparison.py --pairs 10
```

**Expected output:**
```
ALGORITHM COMPARISON SUMMARY
================================================================================

[SUCCESS RATES]
  Baseline A*:    10/10 (100.0%)
  Risk-Aware A*:  10/10 (100.0%)

[RISK SCORES] (0-1 scale, lower = safer)
  Baseline A* average risk:    0.XXXX
  Risk-Aware A* average risk:  0.YYYY
  -> Risk reduction:           ZZ.ZZ%

[ROUTE DISTANCE]
  Baseline A*:    XXXX.Xm average
  Risk-Aware A*:  YYYY.Ym average
  -> Overhead:    Z.ZZ%
```

**✅ Test is working if:**
- Success rates are > 90%
- Risk reduction is > 0% (if risk scores are loaded)
- Distance overhead is < 50%
- Computation time < 100ms per route

**❌ Test is NOT working if:**
- Success rates are < 50%
- Risk reduction is 0% (risk scores not loaded)
- Distance overhead is > 100%
- Many error messages appear

### Medium Test (Recommended)

Test with 1,000 pairs for more confidence (~5 minutes):

```bash
uv run python validation/algorithm_comparison.py --pairs 1000
```

### Full 20,000 Route Test

Once small tests pass, run the full validation:

```bash
# Run 20,000 route pairs
uv run python validation/algorithm_comparison.py --pairs 20000 \
  --output validation/results
```

**Monitor progress:**
- Progress updates every 100 pairs
- Current pair count shown
- Percentage complete displayed

**Timing expectations:**
- Pair generation: ~1-2 minutes
- Route computation: ~85-110 minutes
- Total: ~90-120 minutes

---

## Verifying Test Correctness

### Automated Validation Script

Create `validation/verify_test_results.py`:

```python
"""
Automated Test Results Verification Script

Checks if test results meet validation criteria and identifies issues.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

def load_results(filepath: str) -> Dict:
    """Load results JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def verify_data_completeness(data: Dict) -> Tuple[bool, List[str]]:
    """Verify all expected data is present."""
    issues = []

    # Check metadata
    metadata = data.get('metadata', {})
    if metadata.get('total_metrics', 0) == 0:
        issues.append("No metrics found in results")

    expected_total = metadata.get('baseline_count', 0) + metadata.get('risk_aware_count', 0)
    if metadata.get('total_metrics', 0) != expected_total:
        issues.append(f"Metric count mismatch: {metadata.get('total_metrics')} != {expected_total}")

    # Check statistics exist
    stats = data.get('statistics', {})
    if not stats.get('baseline'):
        issues.append("Missing baseline statistics")
    if not stats.get('risk_aware'):
        issues.append("Missing risk-aware statistics")
    if not stats.get('comparison'):
        issues.append("Missing comparison statistics")

    return len(issues) == 0, issues

def verify_success_rates(data: Dict) -> Tuple[bool, List[str]]:
    """Verify success rates are acceptable."""
    issues = []

    stats = data.get('statistics', {})
    baseline = stats.get('baseline', {})
    risk_aware = stats.get('risk_aware', {})

    baseline_rate = baseline.get('success_rate', 0)
    risk_aware_rate = risk_aware.get('success_rate', 0)

    if baseline_rate < 90:
        issues.append(f"Baseline success rate too low: {baseline_rate:.1f}% (expected >= 90%)")

    if risk_aware_rate < 90:
        issues.append(f"Risk-aware success rate too low: {risk_aware_rate:.1f}% (expected >= 90%)")

    return len(issues) == 0, issues

def verify_risk_scores(data: Dict) -> Tuple[bool, List[str]]:
    """Verify risk scores are loaded and varying."""
    issues = []

    stats = data.get('statistics', {})
    baseline = stats.get('baseline', {})
    risk_aware = stats.get('risk_aware', {})
    comparison = stats.get('comparison', {})

    # Check if risk scores exist
    baseline_risk = baseline.get('avg_risk', 0)
    risk_aware_risk = risk_aware.get('avg_risk', 0)

    if baseline_risk == 0 and risk_aware_risk == 0:
        issues.append("❌ CRITICAL: All risk scores are 0 - GeoTIFF data not loaded!")

    # Check risk reduction
    risk_reduction = comparison.get('risk_reduction', 0)
    if risk_reduction == 0:
        issues.append("⚠️  Warning: 0% risk reduction - risk scores may not be loaded")
    elif risk_reduction < 5:
        issues.append(f"⚠️  Warning: Low risk reduction: {risk_reduction:.2f}% (expected >= 15%)")

    return len(issues) == 0, issues

def verify_performance_metrics(data: Dict) -> Tuple[bool, List[str]]:
    """Verify performance metrics are reasonable."""
    issues = []

    stats = data.get('statistics', {})
    baseline = stats.get('baseline', {})
    risk_aware = stats.get('risk_aware', {})
    comparison = stats.get('comparison', {})

    # Check distance overhead
    distance_overhead = comparison.get('distance_overhead', 0)
    if distance_overhead > 30:
        issues.append(f"⚠️  High distance overhead: {distance_overhead:.2f}% (expected <= 20%)")
    elif distance_overhead < 0:
        issues.append(f"⚠️  Negative distance overhead: {distance_overhead:.2f}% (unexpected)")

    # Check computation time
    baseline_time = baseline.get('avg_computation_time', 0) * 1000  # to ms
    risk_aware_time = risk_aware.get('avg_computation_time', 0) * 1000

    if baseline_time > 200:
        issues.append(f"⚠️  Slow baseline computation: {baseline_time:.2f}ms (expected < 100ms)")

    if risk_aware_time > 200:
        issues.append(f"⚠️  Slow risk-aware computation: {risk_aware_time:.2f}ms (expected < 100ms)")

    return len(issues) == 0, issues

def verify_validation_criteria(data: Dict) -> Tuple[bool, List[str]]:
    """Check if results meet validation criteria."""
    issues = []

    stats = data.get('statistics', {})
    comparison = stats.get('comparison', {})
    baseline = stats.get('baseline', {})
    risk_aware = stats.get('risk_aware', {})

    # Validation criteria from README
    criteria = {
        "Risk reduction >= 15%": comparison.get('risk_reduction', 0) >= 15,
        "Distance overhead <= 20%": comparison.get('distance_overhead', 0) <= 20,
        "Baseline time < 100ms": baseline.get('avg_computation_time', 0) < 0.1,
        "Risk-aware time < 100ms": risk_aware.get('avg_computation_time', 0) < 0.1,
        "Baseline success >= 95%": baseline.get('success_rate', 0) >= 95,
        "Risk-aware success >= 95%": risk_aware.get('success_rate', 0) >= 95,
    }

    failed_criteria = [name for name, passed in criteria.items() if not passed]

    if failed_criteria:
        issues.append("Failed validation criteria:")
        for criterion in failed_criteria:
            issues.append(f"  ❌ {criterion}")

    return len(issues) == 0, issues

def main():
    """Run all verification checks."""
    if len(sys.argv) < 2:
        print("Usage: python verify_test_results.py <results_file.json>")
        print("\nExample:")
        print("  python verify_test_results.py validation/results/comparison_results_20251120_172356.json")
        return 1

    results_file = sys.argv[1]

    if not Path(results_file).exists():
        print(f"❌ Results file not found: {results_file}")
        return 1

    print(f"\n{'=' * 80}")
    print("TEST RESULTS VERIFICATION")
    print(f"{'=' * 80}\n")
    print(f"File: {results_file}\n")

    # Load data
    try:
        data = load_results(results_file)
    except Exception as e:
        print(f"❌ Failed to load results: {e}")
        return 1

    # Display basic info
    metadata = data.get('metadata', {})
    print(f"Total metrics: {metadata.get('total_metrics', 0)}")
    print(f"  Baseline: {metadata.get('baseline_count', 0)}")
    print(f"  Risk-aware: {metadata.get('risk_aware_count', 0)}")
    print(f"Timestamp: {metadata.get('timestamp', 'unknown')}\n")

    # Run verification checks
    checks = [
        ("Data Completeness", verify_data_completeness),
        ("Success Rates", verify_success_rates),
        ("Risk Scores", verify_risk_scores),
        ("Performance Metrics", verify_performance_metrics),
        ("Validation Criteria", verify_validation_criteria),
    ]

    all_passed = True
    all_issues = []

    for check_name, check_func in checks:
        print(f"[Checking] {check_name}...", end=" ")
        passed, issues = check_func(data)

        if passed:
            print("✅ PASS")
        else:
            print("❌ FAIL")
            all_passed = False
            all_issues.extend(issues)
            for issue in issues:
                print(f"  - {issue}")

    print(f"\n{'=' * 80}")

    if all_passed:
        print("✅ ALL CHECKS PASSED - Test results are valid!")
        print("\nYour 20,000 route test is working correctly.")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nIssues found:")
        for issue in all_issues:
            print(f"  - {issue}")
        print("\nPlease address these issues before trusting the results.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

**Usage:**
```bash
# Verify most recent results
uv run python validation/verify_test_results.py \
  validation/results/comparison_results_*.json

# Or specify exact file
uv run python validation/verify_test_results.py \
  validation/results/comparison_results_20251120_172356.json
```

### Manual Verification Checklist

Check these key indicators:

#### 1. Success Rates
```
✅ Good:  >= 95%
⚠️  Fair:  90-95%
❌ Bad:   < 90%
```

#### 2. Risk Reduction
```
✅ Excellent: 25-35%
✅ Good:      15-25%
⚠️  Moderate:  5-15%
❌ Poor:      < 5% or 0%
```

#### 3. Distance Overhead
```
✅ Excellent:  < 10%
✅ Good:       10-20%
⚠️  High:       20-30%
❌ Excessive:  > 30%
```

#### 4. Computation Time
```
✅ Excellent:  < 50ms
✅ Good:       50-100ms
⚠️  Moderate:   100-200ms
❌ Slow:       > 200ms
```

---

## Analysis & Interpretation

### Generate Analysis Report

```bash
# Find your results file
ls validation/results/

# Generate full analysis report
uv run python validation/statistical_analysis.py \
  validation/results/comparison_results_20251120_172356.json \
  --output validation/analysis
```

**Outputs:**
- `validation/analysis/analysis_report.txt` - Detailed text report
- `validation/analysis/charts/` - Visualization charts (if matplotlib installed)

### Key Metrics to Analyze

#### Risk Reduction Percentage

**What it means:** How much safer are risk-aware routes compared to baseline?

**Interpretation:**
- **> 25%:** Exceptional - Algorithm provides significant safety improvement
- **15-25%:** Good - Meaningful risk reduction
- **5-15%:** Moderate - Some improvement but could be better
- **< 5%:** Poor - Algorithm not providing much benefit
- **0%:** Critical - Risk scores not loaded or algorithm not working

**Example:**
```
Baseline A* average risk:    0.4234
Risk-Aware A* average risk:  0.3012
→ Risk reduction:            28.87%
```
This means risk-aware routes are ~29% safer on average.

#### Distance Overhead Percentage

**What it means:** How much longer are risk-aware routes?

**Interpretation:**
- **< 5%:** Minimal - Users won't notice
- **5-10%:** Small - Acceptable trade-off for safety
- **10-20%:** Moderate - Noticeable but reasonable
- **20-30%:** High - May discourage usage
- **> 30%:** Excessive - Likely unacceptable to users

**Example:**
```
Baseline A*:    1052.3m average
Risk-Aware A*:  1124.5m average
→ Overhead:     6.86%
```
Routes are only 6.86% longer - excellent trade-off!

#### High-Risk Segments Avoided

**What it means:** How many dangerous road segments does risk-aware routing avoid?

**Interpretation:**
- **> 5 segments/route:** Excellent avoidance
- **2-5 segments/route:** Good avoidance
- **1-2 segments/route:** Moderate avoidance
- **< 1 segment/route:** Minimal avoidance

**Example:**
```
Baseline A*:    4.23 high-risk segments/route
Risk-Aware A*:  1.15 high-risk segments/route
→ Reduction:    3.08 segments/route
```
Risk-aware routes avoid ~3 dangerous segments per route!

### Statistical Significance

For 20,000 route pairs:
- **Sample size is large** - Results are statistically significant
- **Margin of error:** ±0.5% at 95% confidence
- **Confidence:** Very high if results are consistent

---

## Troubleshooting

### Issue 1: 0% Risk Reduction

**Symptoms:**
```
[RISK SCORES]
  Baseline A* average risk:    0.0000
  Risk-Aware A* average risk:  0.0000
  -> Risk reduction:           0.00%
```

**Cause:** Graph edges have no risk scores loaded (all `risk_score=0.0`)

**Solution:**

1. Check if GeoTIFF files exist:
```bash
ls app/data/geotiff/
# Should see: rr01_step_*.tif files
```

2. Load risk data using HazardAgent:
```python
from app.agents.hazard_agent import HazardAgent
from app.environment.graph_manager import DynamicGraphEnvironment

# Load graph
env = DynamicGraphEnvironment()

# Create hazard agent
hazard_agent = HazardAgent(
    agent_id="hazard_1",
    environment=env,
    geotiff_dir="app/data/geotiff"
)

# Load flood scenario (example: 2-year return, hour 6)
hazard_agent.load_geotiff("rr01", time_step=6)

# Update graph with risk scores
hazard_agent.update_risk_scores()

# Verify
graph = env.get_graph()
risk_edges = sum(1 for u, v, d in graph.edges(data=True) if d.get('risk_score', 0) > 0)
print(f"Edges with risk: {risk_edges}/{len(graph.edges())}")
```

3. Re-run validation with risk scores loaded

### Issue 2: Low Success Rate (< 90%)

**Symptoms:**
```
[SUCCESS RATES]
  Baseline A*:    15234/20000 (76.2%)
  Risk-Aware A*:  14892/20000 (74.5%)
```

**Possible causes:**
1. Graph connectivity issues
2. Evacuation centers not well-distributed
3. Distance tolerance too strict
4. Graph has isolated components

**Solutions:**

A. Check graph connectivity:
```python
import networkx as nx
from app.environment.graph_manager import DynamicGraphEnvironment

env = DynamicGraphEnvironment()
graph = env.get_graph()

# Check if graph is strongly connected
if nx.is_strongly_connected(graph):
    print("Graph is strongly connected")
else:
    components = list(nx.strongly_connected_components(graph))
    print(f"Graph has {len(components)} strongly connected components")
    print(f"Largest component: {len(max(components, key=len))} nodes")
```

B. Increase distance tolerance:
Edit `validation/algorithm_comparison.py:89-90`:
```python
self.generator = RoutePairGenerator(
    self.graph,
    evacuation_csv,
    distance_target=1000.0,
    distance_tolerance=300.0  # Increased from 200m to 300m
)
```

### Issue 3: Computation Too Slow

**Symptoms:**
```
[COMPUTATION TIME]
  Baseline A*:    234.56ms average
  Risk-Aware A*:  312.89ms average
```

**Solutions:**

1. Test with fewer pairs first:
```bash
uv run python validation/algorithm_comparison.py --pairs 1000
```

2. Check graph size:
```python
env = DynamicGraphEnvironment()
graph = env.get_graph()
print(f"Nodes: {len(graph.nodes())}")
print(f"Edges: {len(graph.edges())}")
# If > 50,000 nodes, consider simplifying graph
```

3. Profile the algorithm:
```python
import cProfile
import pstats

cProfile.run('baseline_astar(graph, source, target)', 'profile_stats')
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative')
stats.print_stats(10)
```

### Issue 4: Distance Overhead Too High (> 30%)

**Symptoms:**
```
[ROUTE DISTANCE]
  Baseline A*:    1052.3m average
  Risk-Aware A*:  1523.8m average
  -> Overhead:    44.82%
```

**Possible causes:**
1. Risk weight too high (prioritizing safety over distance)
2. Many high-risk areas forcing long detours
3. Algorithm blocking too many roads

**Solutions:**

A. Adjust risk/distance weights:
```bash
# More balanced (50% risk, 50% distance)
uv run python validation/algorithm_comparison.py \
  --pairs 20000 \
  --risk-weight 0.5 \
  --distance-weight 0.5

# More distance-focused (40% risk, 60% distance)
uv run python validation/algorithm_comparison.py \
  --pairs 20000 \
  --risk-weight 0.4 \
  --distance-weight 0.6
```

B. Check critical risk threshold:
In `app/algorithms/risk_aware_astar.py`, ensure critical threshold is appropriate:
```python
# Don't block roads too aggressively
if risk_score >= 0.9:  # Only block extremely dangerous roads
    return float('inf')
```

---

## Validation Scripts

### Complete Pre-Test Validation Script

Create `validation/pre_test_check.py`:

```python
"""
Pre-Test Validation Script

Runs all checks before starting 20,000 route test.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.environment.graph_manager import DynamicGraphEnvironment
import networkx as nx

def check_graph():
    """Check graph is loaded and valid."""
    print("\n[1/5] Checking graph...")

    env = DynamicGraphEnvironment()
    graph = env.get_graph()

    if graph is None:
        print("  ❌ Graph not loaded")
        return False

    num_nodes = len(graph.nodes())
    num_edges = len(graph.edges())

    print(f"  ✅ Graph loaded: {num_nodes} nodes, {num_edges} edges")

    # Check connectivity
    if nx.is_strongly_connected(graph):
        print("  ✅ Graph is strongly connected")
    else:
        components = list(nx.strongly_connected_components(graph))
        largest = max(components, key=len)
        print(f"  ⚠️  Graph has {len(components)} components")
        print(f"     Largest component: {len(largest)} nodes ({len(largest)/num_nodes*100:.1f}%)")

    return True

def check_evacuation_centers():
    """Check evacuation centers CSV."""
    print("\n[2/5] Checking evacuation centers...")

    csv_path = Path(__file__).parent.parent / "app" / "data" / "evacuation_centers.csv"

    if not csv_path.exists():
        print(f"  ❌ Not found: {csv_path}")
        return False

    # Count lines
    with open(csv_path) as f:
        lines = f.readlines()

    num_centers = len(lines) - 1  # Subtract header
    print(f"  ✅ Found {num_centers} evacuation centers")

    if num_centers < 10:
        print(f"  ⚠️  Warning: Only {num_centers} centers (recommended >= 30)")

    return True

def check_risk_scores():
    """Check if risk scores are loaded."""
    print("\n[3/5] Checking risk scores...")

    env = DynamicGraphEnvironment()
    graph = env.get_graph()

    edges_with_risk = sum(
        1 for u, v, data in graph.edges(data=True)
        if data.get('risk_score', 0) > 0
    )
    total_edges = len(graph.edges())
    coverage = edges_with_risk / total_edges * 100 if total_edges > 0 else 0

    print(f"  Edges with risk > 0: {edges_with_risk}/{total_edges} ({coverage:.1f}%)")

    if edges_with_risk == 0:
        print("  ❌ NO RISK SCORES FOUND!")
        print("\n  To load risk data:")
        print("    1. Ensure GeoTIFF files exist in app/data/geotiff/")
        print("    2. Use HazardAgent.load_geotiff() and update_risk_scores()")
        return False

    if coverage < 10:
        print(f"  ⚠️  Warning: Low risk coverage ({coverage:.1f}%)")
        return False

    print("  ✅ Risk scores are loaded")
    return True

def check_disk_space():
    """Check disk space."""
    print("\n[4/5] Checking disk space...")

    import shutil

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    stat = shutil.disk_usage(results_dir)
    free_mb = stat.free / (1024 * 1024)

    print(f"  Free space: {free_mb:.0f} MB")

    if free_mb < 100:
        print("  ⚠️  Warning: Low disk space (< 100 MB)")
    else:
        print("  ✅ Sufficient disk space")

    return free_mb >= 50

def check_dependencies():
    """Check required dependencies."""
    print("\n[5/5] Checking dependencies...")

    try:
        import networkx
        import numpy
        print("  ✅ NetworkX installed")
        print("  ✅ NumPy installed")

        # Optional
        try:
            import matplotlib
            print("  ✅ Matplotlib installed (visualizations enabled)")
        except ImportError:
            print("  ⚠️  Matplotlib not installed (visualizations disabled)")

        return True

    except ImportError as e:
        print(f"  ❌ Missing dependency: {e}")
        return False

def main():
    """Run all pre-test checks."""
    print("=" * 60)
    print("PRE-TEST VALIDATION")
    print("=" * 60)

    checks = [
        check_graph,
        check_evacuation_centers,
        check_risk_scores,
        check_disk_space,
        check_dependencies,
    ]

    results = [check() for check in checks]

    print("\n" + "=" * 60)

    if all(results):
        print("✅ ALL CHECKS PASSED")
        print("\nYou are ready to run 20,000 route test!")
        print("\nRun:")
        print("  uv run python validation/algorithm_comparison.py --pairs 20000")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above before running the full test.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

**Usage:**
```bash
# Run pre-test validation
uv run python validation/pre_test_check.py
```

---

## Summary

### Step-by-Step Process

1. **Pre-flight checks:**
   ```bash
   uv run python validation/pre_test_check.py
   ```

2. **Quick test (10 pairs):**
   ```bash
   uv run python validation/algorithm_comparison.py --pairs 10
   ```

3. **Verify quick test:**
   ```bash
   uv run python validation/verify_test_results.py validation/results/comparison_results_*.json
   ```

4. **Medium test (1,000 pairs):**
   ```bash
   uv run python validation/algorithm_comparison.py --pairs 1000
   ```

5. **Full test (20,000 pairs):**
   ```bash
   uv run python validation/algorithm_comparison.py --pairs 20000
   ```

6. **Verify full test:**
   ```bash
   uv run python validation/verify_test_results.py validation/results/comparison_results_*.json
   ```

7. **Generate analysis:**
   ```bash
   uv run python validation/statistical_analysis.py \
     validation/results/comparison_results_*.json \
     --output validation/analysis
   ```

8. **Review report:**
   ```bash
   cat validation/analysis/analysis_report.txt
   ```

### Expected Timeline

| Step | Duration | Purpose |
|------|----------|---------|
| Pre-flight checks | 1 min | Verify system ready |
| Quick test (10) | 30 sec | Smoke test |
| Medium test (1,000) | 5 min | Confidence test |
| Full test (20,000) | 90 min | Full validation |
| Analysis | 2 min | Generate reports |
| **Total** | **~98 min** | Complete validation |

---

**Version:** 1.0.0
**Last Updated:** November 20, 2025
**Contact:** MAS-FRO Development Team
