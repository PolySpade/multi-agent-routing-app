# filename: scripts/diagnostics/check_risk_distribution.py

"""
Diagnostic script to check the actual risk score distribution in the graph.
Use this to verify if edges really have 100% risk as expected.

Author: MAS-FRO Development Team
Date: November 2025
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.environment.graph_manager import DynamicGraphEnvironment
from app.core.config import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_risk_distribution(env: DynamicGraphEnvironment):
    """Analyze and print risk score distribution across all edges."""

    if not env.graph:
        logger.error("Graph not loaded!")
        return

    # Collect risk scores
    risk_scores = []
    edges_by_risk = {
        "0.0 (No Risk)": 0,
        "0.0-0.2 (Very Low)": 0,
        "0.2-0.4 (Low)": 0,
        "0.4-0.6 (Moderate)": 0,
        "0.6-0.8 (High)": 0,
        "0.8-1.0 (Very High)": 0,
        "1.0 (Maximum)": 0
    }

    total_edges = 0

    # Analyze all edges
    for u, v, key, data in env.graph.edges(keys=True, data=True):
        risk = data.get('risk_score', 0.0)
        risk_scores.append(risk)
        total_edges += 1

        # Categorize
        if risk == 0.0:
            edges_by_risk["0.0 (No Risk)"] += 1
        elif risk == 1.0:
            edges_by_risk["1.0 (Maximum)"] += 1
        elif 0.0 < risk < 0.2:
            edges_by_risk["0.0-0.2 (Very Low)"] += 1
        elif 0.2 <= risk < 0.4:
            edges_by_risk["0.2-0.4 (Low)"] += 1
        elif 0.4 <= risk < 0.6:
            edges_by_risk["0.4-0.6 (Moderate)"] += 1
        elif 0.6 <= risk < 0.8:
            edges_by_risk["0.6-0.8 (High)"] += 1
        elif 0.8 <= risk < 1.0:
            edges_by_risk["0.8-1.0 (Very High)"] += 1

    # Print results
    print("\n" + "="*70)
    print("RISK SCORE DISTRIBUTION ANALYSIS")
    print("="*70)
    print(f"\nTotal edges: {total_edges:,}")
    print(f"\nRisk Distribution:")
    print("-" * 70)

    for category, count in edges_by_risk.items():
        percentage = (count / total_edges * 100) if total_edges > 0 else 0
        bar = "█" * int(percentage / 2)  # Scale bar to 50 chars max
        print(f"  {category:20} | {count:6,} ({percentage:5.2f}%) {bar}")

    print("-" * 70)

    # Statistics
    if risk_scores:
        avg_risk = sum(risk_scores) / len(risk_scores)
        max_risk = max(risk_scores)
        min_risk = min(risk_scores)

        print(f"\nStatistics:")
        print(f"  Average Risk: {avg_risk:.4f}")
        print(f"  Minimum Risk: {min_risk:.4f}")
        print(f"  Maximum Risk: {max_risk:.4f}")

    # Threshold analysis
    print(f"\n" + "="*70)
    print("THRESHOLD IMPACT ANALYSIS")
    print("="*70)

    thresholds = [0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]

    print(f"\nEdges that would be BLOCKED at different thresholds:")
    print("-" * 70)

    for threshold in thresholds:
        blocked = sum(1 for r in risk_scores if r >= threshold)
        percentage = (blocked / total_edges * 100) if total_edges > 0 else 0
        passable = total_edges - blocked

        marker = " ← CURRENT" if threshold == 0.2 else ""

        print(f"  Threshold ≥ {threshold:.1f}: "
              f"{blocked:6,} blocked ({percentage:5.2f}%), "
              f"{passable:6,} passable{marker}")

    print("="*70)

    # Check if routing is possible
    print(f"\nROUTABILITY CHECK:")
    print("-" * 70)

    current_threshold = 0.2
    blocked_at_current = sum(1 for r in risk_scores if r >= current_threshold)
    passable_at_current = total_edges - blocked_at_current

    if blocked_at_current == total_edges:
        print(f"  ⚠️  ALL edges are blocked at threshold {current_threshold}")
        print(f"      → NO ROUTING POSSIBLE (should return 404 error)")
    elif passable_at_current < 10:
        print(f"  ⚠️  Only {passable_at_current} edges passable at threshold {current_threshold}")
        print(f"      → Very limited routing options (may fail)")
    else:
        print(f"  ✅ {passable_at_current:,} edges passable at threshold {current_threshold}")
        print(f"      → Routing SHOULD work")

    print("="*70)


def main():
    """Run risk distribution analysis."""
    try:
        print("\n[1] Initializing environment...")
        env = DynamicGraphEnvironment()

        print("[2] Loading graph (this may take a moment)...")
        env.load_graph()

        print(f"[3] Graph loaded: {len(env.graph.nodes):,} nodes, "
              f"{len(env.graph.edges):,} edges")

        print("\n[4] Analyzing risk distribution...")
        analyze_risk_distribution(env)

        print("\n✅ Analysis complete!")
        print("\nInterpretation:")
        print("  • If 'ALL edges blocked' → Backend should return 404 error")
        print("  • If 'Routing SHOULD work' → Backend will return a path")
        print("  • Check frontend console for actual API response")

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
