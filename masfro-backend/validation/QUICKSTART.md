# Validation System - Quick Start Guide

**Fast track to validating your routing algorithms in 5 minutes**

---

## Prerequisites

```bash
# 1. Virtual environment active
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# 2. Graph file exists
ls app/data/marikina_graph.graphml

# 3. Evacuation centers exist
ls app/data/evacuation_centers.csv
```

---

## Quick Test (10 pairs, ~30 seconds)

```bash
cd masfro-backend
uv run python validation/algorithm_comparison.py --pairs 10
```

**Expected output:**
```
ALGORITHM COMPARISON SUMMARY
================================================================================

[SUCCESS RATES]
  Baseline A*:    10/10 (100.0%)
  Risk-Aware A*:  10/10 (100.0%)

[ROUTE DISTANCE]
  Baseline A*:    1437.8m average
  Risk-Aware A*:  1502.9m average
  -> Overhead:    4.52%

[COMPUTATION TIME]
  Baseline A*:    10.99ms average
  Risk-Aware A*:  2.91ms average
  -> Overhead:    -73.53%
```

---

## Full Validation (20,000 pairs, ~90 minutes)

```bash
cd masfro-backend
uv run python validation/algorithm_comparison.py --pairs 20000
```

**Results saved to:** `validation/results/comparison_results_[timestamp].json`

---

## Generate Analysis Report

```bash
# Find results file
ls validation/results/

# Generate report (replace TIMESTAMP)
uv run python validation/statistical_analysis.py \
  validation/results/comparison_results_TIMESTAMP.json \
  --output validation/analysis
```

**Outputs:**
- `validation/analysis/analysis_report.txt` - Detailed report
- `validation/analysis/charts/` - Visualization charts

---

## Key Metrics

### Risk Reduction
- **Target:** >= 15%
- **Excellent:** 25-35%
- **Good:** 15-25%
- **Poor:** < 5%

### Distance Overhead
- **Target:** <= 20%
- **Excellent:** < 10%
- **Acceptable:** 10-20%
- **High:** > 30%

### Computation Time
- **Target:** <= 100ms
- **Excellent:** < 50ms
- **Good:** 50-100ms
- **Slow:** > 200ms

---

## Customization

### Different Risk Weights

```bash
# More safety-focused (70% risk, 30% distance)
uv run python validation/algorithm_comparison.py \
  --pairs 20000 \
  --risk-weight 0.7 \
  --distance-weight 0.3

# Balanced (50% risk, 50% distance)
uv run python validation/algorithm_comparison.py \
  --pairs 20000 \
  --risk-weight 0.5 \
  --distance-weight 0.5
```

### Custom Output Directory

```bash
uv run python validation/algorithm_comparison.py \
  --pairs 20000 \
  --output validation/results_nov20_baseline
```

---

## Troubleshooting

### Issue: No risk reduction shown

**Cause:** Graph edges have no risk data loaded (all risk_score=0.0)

**Solution:** Load flood risk data first
```python
# In your code or simulation setup
from app.agents.hazard_agent import HazardAgent

hazard_agent = HazardAgent(...)
hazard_agent.load_geotiff("rr01", time_step=6)  # Load flood scenario
hazard_agent.update_risk_scores()  # Update graph

# Then run validation
```

### Issue: Low pair generation success rate

**Cause:** Strict distance tolerance or graph connectivity issues

**Solution:** Increase tolerance or attempts (edit route_pair_generator.py)
```python
generator = RoutePairGenerator(
    graph,
    evac_csv,
    distance_tolerance=300.0  # Increased from 200m
)
```

### Issue: Computation too slow

**Solution:** Test with fewer pairs first
```bash
# Test with 1,000 pairs (~5 minutes)
uv run python validation/algorithm_comparison.py --pairs 1000

# Then scale up gradually
```

---

## File Locations

```
validation/
├── algorithm_comparison.py        # Main script
├── route_pair_generator.py        # Pair generation
├── metrics_collector.py           # Metrics collection
├── statistical_analysis.py        # Analysis & viz
├── README.md                      # Full documentation
└── QUICKSTART.md                  # This file

Results:
├── validation/results/
│   └── comparison_results_*.json  # Raw results
└── validation/analysis/
    ├── analysis_report.txt        # Report
    └── charts/                    # Charts
```

---

## Need Help?

1. **Technical details:** See `validation/README.md`
2. **User guide:** See `ROUTING_ALGORITHM_VALIDATION.md`
3. **Implementation:** See `VALIDATION_SYSTEM_SUMMARY.md`
4. **Code comments:** Check module docstrings

---

**Quick Start Version:** 1.0.0
**Last Updated:** November 20, 2025
