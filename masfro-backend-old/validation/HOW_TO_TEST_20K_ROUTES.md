# How to Test 20,000 Routes - Quick Reference

## Current Status

Based on the pre-test check, your system is **mostly ready** but needs risk data loaded:

- [x] Graph loaded (16,877 nodes, 35,932 edges)
- [x] Evacuation centers loaded (36 centers)
- [x] Disk space available (27,819 MB)
- [x] Dependencies installed (NetworkX, NumPy, Matplotlib)
- [ ] **Risk scores NOT loaded** (0% coverage) ← **FIX THIS FIRST!**

## Critical Issue: Risk Scores Not Loaded

Your existing test shows **0% risk reduction** because the graph edges don't have flood risk data loaded.

### How to Load Risk Scores

You have GeoTIFF files in `app/data/geotiff/`. You need to load them into the graph:

```python
from app.agents.hazard_agent import HazardAgent
from app.environment.graph_manager import DynamicGraphEnvironment

# Load graph
env = DynamicGraphEnvironment()

# Create hazard agent
hazard = HazardAgent(
    agent_id="hazard_1",
    environment=env,
    geotiff_dir="app/data/geotiff"
)

# Load flood scenario (example: 2-year return period, hour 6)
hazard.load_geotiff("rr01", time_step=6)

# Update graph with risk scores
hazard.update_risk_scores()

# Verify it worked
graph = env.get_graph()
risk_edges = sum(1 for u, v, d in graph.edges(data=True) if d.get('risk_score', 0) > 0)
print(f"Edges with risk: {risk_edges}/{len(graph.edges())}")
```

### Verify Risk Scores Loaded

After loading, run:

```bash
uv run python validation/check_risk_scores.py
```

You should see:
```
[OK] Risk scores are loaded and valid!
     You can proceed with validation testing.
```

## Step-by-Step Testing Process

### 1. Pre-Test Validation

Always run this first:

```bash
cd masfro-backend
uv run python validation/pre_test_check.py
```

**Expected:** All 5 checks should pass (currently 4/5 because risk scores missing)

### 2. Quick Test (10 pairs, ~30 seconds)

Test the system with a small sample:

```bash
uv run python validation/algorithm_comparison.py --pairs 10
```

**What to look for:**
- Success rates > 90%
- Risk reduction > 0% (if risk scores loaded)
- No errors

### 3. Medium Test (1,000 pairs, ~5 minutes)

Gain more confidence:

```bash
uv run python validation/algorithm_comparison.py --pairs 1000
```

**What to look for:**
- Success rates > 95%
- Risk reduction 15-30%
- Distance overhead < 20%

### 4. Verify Test Results

After any test, verify the results:

```bash
# Find the most recent results file
ls validation/results/

# Verify it (use actual filename)
uv run python validation/verify_test_results.py \
  validation/results/comparison_results_20251120_172356.json
```

**Expected:** All checks should pass

### 5. Full Test (20,000 pairs, ~90 minutes)

Once small tests pass successfully:

```bash
uv run python validation/algorithm_comparison.py --pairs 20000
```

**Progress:**
- Updates every 100 pairs
- Estimated time: ~84 minutes (based on your system)
- Results saved to: `validation/results/comparison_results_[timestamp].json`

### 6. Generate Analysis Report

After the full test completes:

```bash
# Find your results file
ls validation/results/

# Generate detailed analysis
uv run python validation/statistical_analysis.py \
  validation/results/comparison_results_[timestamp].json \
  --output validation/analysis
```

**Outputs:**
- `validation/analysis/analysis_report.txt` - Detailed report
- `validation/analysis/charts/` - Visualization charts

## Validation Scripts Reference

### Check Risk Scores
```bash
uv run python validation/check_risk_scores.py
```
Shows if GeoTIFF data is loaded into the graph.

### Pre-Test Check
```bash
uv run python validation/pre_test_check.py
```
Runs all 5 pre-flight checks before testing.

### Verify Results
```bash
uv run python validation/verify_test_results.py <results_file.json>
```
Validates test results meet all criteria.

### Run Comparison
```bash
uv run python validation/algorithm_comparison.py --pairs <NUMBER>
```
Runs the actual route comparison test.

### Generate Analysis
```bash
uv run python validation/statistical_analysis.py <results_file.json>
```
Creates detailed statistical analysis and charts.

## Understanding Results

### Success Rates
- **> 95%:** Excellent
- **90-95%:** Good
- **< 90%:** Check graph connectivity

### Risk Reduction
- **25-35%:** Excellent - Algorithm very effective
- **15-25%:** Good - Meaningful improvement
- **5-15%:** Moderate - Some benefit
- **0%:** Critical - Risk data not loaded!

### Distance Overhead
- **< 10%:** Excellent - Minimal extra distance
- **10-20%:** Good - Acceptable trade-off
- **> 30%:** High - May need weight adjustment

### Computation Time
- **< 50ms:** Excellent - Real-time capable
- **50-100ms:** Good - Interactive use
- **> 200ms:** Slow - Consider optimization

## Current Test Results Analysis

Your existing test (100 pairs) shows:

```
Success Rates: 100% (excellent)
Risk Reduction: 0.00% (risk data not loaded!)
Distance Overhead: 5.10% (excellent)
Computation Time: 4.54ms baseline, 1.92ms risk-aware (excellent)
```

**Verdict:** System is fast and working, but needs risk data loaded to be useful!

## Troubleshooting

### Issue: 0% Risk Reduction

**Solution:** Load GeoTIFF data (see "How to Load Risk Scores" above)

### Issue: Low Success Rate (< 90%)

**Possible causes:**
- Graph connectivity issues
- Distance tolerance too strict

**Solution:** Check graph with pre_test_check.py

### Issue: High Distance Overhead (> 30%)

**Solution:** Adjust risk/distance weights:

```bash
# More balanced (50% risk, 50% distance)
uv run python validation/algorithm_comparison.py \
  --pairs 20000 \
  --risk-weight 0.5 \
  --distance-weight 0.5
```

### Issue: Test Too Slow

**Solution:** Test with fewer pairs first:

```bash
uv run python validation/algorithm_comparison.py --pairs 1000
```

## Recommended Workflow

```
1. Load risk scores (HazardAgent.load_geotiff())
   ↓
2. uv run python validation/check_risk_scores.py
   ↓
3. uv run python validation/pre_test_check.py
   ↓
4. uv run python validation/algorithm_comparison.py --pairs 10
   ↓
5. uv run python validation/verify_test_results.py <results>
   ↓
6. uv run python validation/algorithm_comparison.py --pairs 1000
   ↓
7. uv run python validation/verify_test_results.py <results>
   ↓
8. uv run python validation/algorithm_comparison.py --pairs 20000
   ↓
9. uv run python validation/verify_test_results.py <results>
   ↓
10. uv run python validation/statistical_analysis.py <results>
```

## Time Estimates (Your System)

| Test Size | Time | Use Case |
|-----------|------|----------|
| 10 pairs | 30 sec | Quick smoke test |
| 100 pairs | 3 min | Development testing |
| 1,000 pairs | 5 min | Confidence test |
| 20,000 pairs | 84 min | Full validation |

## Documentation

- **Detailed Guide:** `TEST_VALIDATION_GUIDE.md`
- **Quick Start:** `QUICKSTART.md`
- **System README:** `README.md`
- **Validation Summary:** `VALIDATION_SYSTEM_SUMMARY.md`
- **Algorithm Validation:** `ROUTING_ALGORITHM_VALIDATION.md`

## Next Steps

1. **Load risk scores** (see section above)
2. **Run check:** `uv run python validation/check_risk_scores.py`
3. **Quick test:** `uv run python validation/algorithm_comparison.py --pairs 10`
4. **Verify:** `uv run python validation/verify_test_results.py <results>`
5. **Scale up:** Start with 1,000 then move to 20,000

## Questions?

- See `TEST_VALIDATION_GUIDE.md` for detailed troubleshooting
- Check script comments for implementation details
- Review existing documentation in `validation/` directory

---

**Created:** November 20, 2025
**System Status:** Ready except risk scores
**Estimated Full Test Time:** ~84 minutes
