# filename: validation/check_risk_scores.py

"""
Risk Score Verification Script

Checks if GeoTIFF flood risk data is loaded into the graph.

Usage:
    python validation/check_risk_scores.py

Author: MAS-FRO Development Team
Date: November 2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.environment.graph_manager import DynamicGraphEnvironment


def check_risk_scores():
    """Check if risk scores are loaded in the graph."""
    print("\n" + "=" * 60)
    print("RISK SCORE VERIFICATION")
    print("=" * 60 + "\n")

    # Load graph
    print("Loading graph...")
    env = DynamicGraphEnvironment()
    graph = env.get_graph()

    if graph is None:
        print("❌ Failed to load graph")
        return 1

    # Check risk scores
    print("Analyzing risk scores...\n")

    edges_with_risk = 0
    risk_values = []

    for u, v, data in graph.edges(data=True):
        risk = data.get('risk_score', 0)
        if risk > 0:
            edges_with_risk += 1
            risk_values.append(risk)

    total_edges = len(graph.edges())
    coverage = edges_with_risk / total_edges * 100 if total_edges > 0 else 0

    # Display results
    print(f"Total edges: {total_edges:,}")
    print(f"Edges with risk > 0: {edges_with_risk:,}")
    print(f"Risk coverage: {coverage:.2f}%\n")

    if edges_with_risk == 0:
        print("[FAIL] NO RISK SCORES FOUND!")
        print("\n[WARNING] Without risk scores, validation will show 0% risk reduction!")
        print("\nTo load risk data:")
        print("  1. Ensure GeoTIFF files exist in app/data/geotiff/")
        print("     - Files should match pattern: rr0X_step_YY.tif")
        print("     - Example: rr01_step_06.tif (2-year return, hour 6)")
        print("\n  2. Load risk scores using HazardAgent:")
        print("\n     from app.agents.hazard_agent import HazardAgent")
        print("     from app.environment.graph_manager import DynamicGraphEnvironment")
        print("\n     env = DynamicGraphEnvironment()")
        print("     hazard = HazardAgent(")
        print("         agent_id='hazard_1',")
        print("         environment=env,")
        print("         geotiff_dir='app/data/geotiff'")
        print("     )")
        print("\n     hazard.load_geotiff('rr01', time_step=6)")
        print("     hazard.update_risk_scores()")
        print("\n  3. Re-run this script to verify\n")
        return 1

    # Risk score statistics
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
        print(f"  Low risk (< 0.3):     {low_risk:,} ({low_risk/edges_with_risk*100:.1f}%)")
        print(f"  Medium risk (0.3-0.6): {med_risk:,} ({med_risk/edges_with_risk*100:.1f}%)")
        print(f"  High risk (>= 0.6):    {high_risk:,} ({high_risk/edges_with_risk*100:.1f}%)\n")

    if coverage < 10:
        print("[WARNING] Low risk coverage (< 10%)")
        print("          Risk scores may not be fully loaded.\n")
        return 1

    print("[OK] Risk scores are loaded and valid!")
    print("     You can proceed with validation testing.\n")
    return 0


if __name__ == "__main__":
    sys.exit(check_risk_scores())
