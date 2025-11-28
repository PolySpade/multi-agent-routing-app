# filename: load_risk_scores.py

"""
Load GeoTIFF flood risk scores into the graph.

This script loads flood risk data from GeoTIFF files and updates
the graph edges with risk scores for validation testing.

Usage:
    python load_risk_scores.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.hazard_agent import HazardAgent
from app.environment.graph_manager import DynamicGraphEnvironment

print("\n" + "=" * 60)
print("LOADING RISK SCORES FROM GEOTIFF")
print("=" * 60 + "\n")

# Load graph environment
print("[1/4] Loading graph environment...")
env = DynamicGraphEnvironment()
graph = env.get_graph()

if graph is None:
    print("[FAIL] Could not load graph")
    sys.exit(1)

print(f"[OK] Graph loaded: {len(graph.nodes())} nodes, {len(graph.edges())} edges\n")

# Create hazard agent with GeoTIFF enabled
print("[2/4] Creating hazard agent with GeoTIFF enabled...")
hazard = HazardAgent(
    agent_id="hazard_1",
    environment=env,
    enable_geotiff=True
)
print(f"[OK] Hazard agent created (GeoTIFF enabled: {hazard.is_geotiff_enabled()})\n")

# Set flood scenario
print("[3/4] Setting flood scenario...")
return_period = "rr01"  # 2-year return period
time_step = 6  # Hour 6

print(f"      Return period: {return_period} (2-year)")
print(f"      Time step: {time_step} (hour 6)")

try:
    hazard.set_flood_scenario(return_period=return_period, time_step=time_step)
    print(f"[OK] Scenario set: {hazard.return_period}, time_step={hazard.time_step}\n")
except Exception as e:
    print(f"[FAIL] Error setting flood scenario: {e}\n")
    sys.exit(1)

# Update graph with risk scores
print("[4/4] Updating graph with risk scores...")
try:
    result = hazard.update_risk(
        flood_data={},  # No additional flood data (using GeoTIFF only)
        scout_data=[],  # No scout data
        time_step=time_step
    )
    print("[OK] Risk scores updated\n")
    print(f"  Locations processed: {result.get('locations_processed', 0)}")
    print(f"  Edges updated: {result.get('edges_updated', 0)}")
    print(f"  Average risk: {result.get('average_risk', 0):.4f}")
    print()
except Exception as e:
    print(f"[FAIL] Error updating risk scores: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify risk scores
print("=" * 60)
print("VERIFICATION")
print("=" * 60 + "\n")

edges_with_risk = 0
risk_values = []

for u, v, data in graph.edges(data=True):
    risk = data.get('risk_score', 0)
    if risk > 0:
        edges_with_risk += 1
        risk_values.append(risk)

total_edges = len(graph.edges())
coverage = edges_with_risk / total_edges * 100 if total_edges > 0 else 0

print(f"Total edges: {total_edges:,}")
print(f"Edges with risk > 0: {edges_with_risk:,}")
print(f"Risk coverage: {coverage:.2f}%\n")

if edges_with_risk == 0:
    print("[FAIL] No risk scores were loaded!")
    sys.exit(1)

# Risk statistics
if risk_values:
    avg_risk = sum(risk_values) / len(risk_values)
    min_risk = min(risk_values)
    max_risk = max(risk_values)

    print("Risk Score Statistics:")
    print(f"  Average: {avg_risk:.4f}")
    print(f"  Minimum: {min_risk:.4f}")
    print(f"  Maximum: {max_risk:.4f}\n")

    # Risk distribution
    low_risk = sum(1 for r in risk_values if r < 0.3)
    med_risk = sum(1 for r in risk_values if 0.3 <= r < 0.6)
    high_risk = sum(1 for r in risk_values if r >= 0.6)

    print("Risk Distribution:")
    print(f"  Low risk (< 0.3):      {low_risk:,} ({low_risk/edges_with_risk*100:.1f}%)")
    print(f"  Medium risk (0.3-0.6): {med_risk:,} ({med_risk/edges_with_risk*100:.1f}%)")
    print(f"  High risk (>= 0.6):    {high_risk:,} ({high_risk/edges_with_risk*100:.1f}%)\n")

print("=" * 60)
print("[SUCCESS] Risk scores loaded and ready for testing!")
print("=" * 60 + "\n")

print("Next steps:")
print("  1. Verify: uv run python validation/check_risk_scores.py")
print("  2. Test: uv run python validation/algorithm_comparison.py --pairs 10")
print()
