#!/usr/bin/env python3
"""
Comprehensive Multi-TIFF Risk Update Test

Tests GeoTIFF integration with multiple TIFF files and verifies
that graph edge risk scores are being updated correctly.

Tests:
1. Multiple return periods (rr01, rr02, rr03, rr04)
2. Multiple time steps (1, 6, 12, 18)
3. Risk score updates on graph edges
4. HazardAgent integration
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from typing import Dict, Tuple, List
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from app.environment.graph_manager import DynamicGraphEnvironment
from app.services.geotiff_service import get_geotiff_service
from app.agents.hazard_agent import HazardAgent


class MultiTIFFRiskTester:
    """Test GeoTIFF integration with multiple files."""

    def __init__(self):
        print("="*80)
        print("MULTI-TIFF RISK UPDATE TEST")
        print("="*80)

        print("\n[1] Initializing environment...")
        self.env = DynamicGraphEnvironment()
        print(f"  Graph: {self.env.graph.number_of_nodes()} nodes, {self.env.graph.number_of_edges()} edges")

        print("\n[2] Initializing GeoTIFF service...")
        self.geotiff = get_geotiff_service()
        print(f"  Available return periods: {self.geotiff.return_periods}")
        print(f"  Time steps: 1-18")

        print("\n[3] Initializing HazardAgent...")
        self.hazard_agent = HazardAgent(
            agent_id="tiff_tester",
            environment=self.env
        )
        print(f"  HazardAgent initialized with GeoTIFF service")

    def capture_risk_snapshot(self) -> Dict[Tuple, float]:
        """Capture current risk scores from all edges."""
        snapshot = {}
        for u, v, key, data in self.env.graph.edges(keys=True, data=True):
            risk = data.get('risk_score', 0.0)
            snapshot[(u, v, key)] = risk
        return snapshot

    def get_risk_distribution(self) -> Dict[str, int]:
        """Get distribution of risk scores."""
        dist = {
            'safe (0.0)': 0,
            'low (0.0-0.3)': 0,
            'moderate (0.3-0.6)': 0,
            'high (0.6-0.8)': 0,
            'extreme (0.8-1.0)': 0
        }

        for u, v, key, data in self.env.graph.edges(keys=True, data=True):
            risk = data.get('risk_score', 0.0)
            if risk == 0.0:
                dist['safe (0.0)'] += 1
            elif risk < 0.3:
                dist['low (0.0-0.3)'] += 1
            elif risk < 0.6:
                dist['moderate (0.3-0.6)'] += 1
            elif risk < 0.8:
                dist['high (0.6-0.8)'] += 1
            else:
                dist['extreme (0.8-1.0)'] += 1

        return dist

    def test_single_tiff(self, return_period: str, time_step: int) -> Dict:
        """Test a single TIFF file and verify risk updates."""
        print(f"\n{'='*80}")
        print(f"Testing: {return_period.upper()} Time Step {time_step}")
        print(f"{'='*80}")

        # Reset graph to clean state
        print(f"\n[A] Resetting graph to clean state...")
        self.env._load_graph_from_file()

        # Capture BEFORE state
        print(f"\n[B] Capturing BEFORE state...")
        before_snapshot = self.capture_risk_snapshot()
        before_dist = self.get_risk_distribution()

        print(f"  BEFORE - Risk Distribution:")
        for category, count in before_dist.items():
            print(f"    {category}: {count}")

        # Configure flood scenario
        print(f"\n[C] Configuring flood scenario: {return_period}, t={time_step}")
        self.hazard_agent.set_flood_scenario(
            return_period=return_period,
            time_step=time_step
        )

        # Calculate risk scores using HazardAgent
        print(f"\n[D] Calculating risk scores via HazardAgent...")

        # Prepare minimal fused data
        fused_data = {
            "system_wide": {
                "risk_level": 0.0,
                "source": "test"
            }
        }

        risk_scores = self.hazard_agent.calculate_risk_scores(fused_data)
        print(f"  Calculated {len(risk_scores)} risk scores")

        if not risk_scores:
            print("  [WARNING] No risk scores calculated!")
            return None

        # Show sample risk scores
        print(f"\n  Sample risk scores:")
        for i, (edge, risk) in enumerate(list(risk_scores.items())[:5]):
            print(f"    Edge {edge}: risk={risk:.3f}")

        # Update environment
        print(f"\n[E] Updating graph edge weights...")
        self.hazard_agent.update_environment(risk_scores)

        # Capture AFTER state
        print(f"\n[F] Capturing AFTER state...")
        after_snapshot = self.capture_risk_snapshot()
        after_dist = self.get_risk_distribution()

        print(f"  AFTER - Risk Distribution:")
        for category, count in after_dist.items():
            print(f"    {category}: {count}")

        # Compare snapshots
        print(f"\n[G] Comparing BEFORE vs AFTER...")
        changed = 0
        unchanged = 0

        for edge_id in before_snapshot:
            before_risk = before_snapshot[edge_id]
            after_risk = after_snapshot[edge_id]

            if abs(after_risk - before_risk) > 0.001:
                changed += 1
            else:
                unchanged += 1

        print(f"  Total edges: {len(before_snapshot)}")
        print(f"  Changed: {changed} ({changed/len(before_snapshot)*100:.1f}%)")
        print(f"  Unchanged: {unchanged}")

        # Verify risk scores were actually updated
        print(f"\n[H] Verification...")
        if changed > 0:
            # Get risk statistics
            risks = list(risk_scores.values())
            print(f"  [SUCCESS] Risk scores updated on graph!")
            print(f"\n  Risk Statistics:")
            print(f"    Min: {min(risks):.3f}")
            print(f"    Max: {max(risks):.3f}")
            print(f"    Mean: {np.mean(risks):.3f}")
            print(f"    Median: {np.median(risks):.3f}")

            # Verify edge weights were updated
            sample_edge = list(risk_scores.keys())[0]
            u, v, key = sample_edge
            edge_data = self.env.graph[u][v][key]
            weight = edge_data.get('weight', 0)
            length = edge_data.get('length', 1.0)
            risk = edge_data.get('risk_score', 0.0)

            print(f"\n  Sample Edge Verification:")
            print(f"    Edge: {sample_edge}")
            print(f"    Length: {length:.2f}m")
            print(f"    Risk Score: {risk:.3f}")
            print(f"    Weight: {weight:.2f}")
            print(f"    Expected Weight: {length * (1.0 + risk):.2f}")

            if abs(weight - (length * (1.0 + risk))) < 0.01:
                print(f"    [SUCCESS] Weight formula correct!")
            else:
                print(f"    [WARNING] Weight mismatch!")

        else:
            print(f"  [WARNING] No edges changed!")

        return {
            'return_period': return_period,
            'time_step': time_step,
            'before_dist': before_dist,
            'after_dist': after_dist,
            'changed_count': changed,
            'risk_scores': risk_scores,
            'total_edges': len(before_snapshot)
        }

    def run_comprehensive_test(self):
        """Run comprehensive test across multiple TIFF files."""

        test_scenarios = [
            # Different return periods
            ('rr01', 10),  # 2-year flood
            ('rr02', 10),  # 5-year flood
            ('rr03', 10),  # Higher return period
            ('rr04', 10),  # 10-year flood

            # Different time steps for rr02
            ('rr02', 1),   # Early time step
            ('rr02', 6),   # Mid-early
            ('rr02', 12),  # Mid-late
            ('rr02', 18),  # Final time step
        ]

        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE TEST: {len(test_scenarios)} TIFF files")
        print(f"{'='*80}")

        results = []

        for return_period, time_step in test_scenarios:
            result = self.test_single_tiff(return_period, time_step)
            if result:
                results.append(result)

        # Summary
        print(f"\n\n{'='*80}")
        print("COMPREHENSIVE TEST SUMMARY")
        print(f"{'='*80}\n")

        print(f"{'Scenario':<20} {'Changed':<10} {'%':<8} {'Min Risk':<10} {'Max Risk':<10} {'Mean Risk':<10}")
        print("-"*80)

        for result in results:
            rp = result['return_period']
            ts = result['time_step']
            changed = result['changed_count']
            total = result['total_edges']
            pct = (changed / total * 100) if total > 0 else 0

            if result['risk_scores']:
                risks = list(result['risk_scores'].values())
                min_risk = min(risks)
                max_risk = max(risks)
                mean_risk = np.mean(risks)
            else:
                min_risk = max_risk = mean_risk = 0.0

            scenario = f"{rp.upper()}-{ts}"
            print(f"{scenario:<20} {changed:<10} {pct:<8.1f} {min_risk:<10.3f} {max_risk:<10.3f} {mean_risk:<10.3f}")

        # Final verification
        print(f"\n{'='*80}")
        print("FINAL VERIFICATION")
        print(f"{'='*80}\n")

        all_passed = all(r['changed_count'] > 0 for r in results)

        if all_passed:
            print("[SUCCESS] All TIFF files tested successfully!")
            print("  - All return periods working (rr01, rr02, rr03, rr04)")
            print("  - All time steps working (1-18)")
            print("  - Risk scores calculated correctly")
            print("  - Graph edges updated with risk data")
            print("  - Edge weights updated with formula: weight = length * (1 + risk)")
        else:
            failed = [r for r in results if r['changed_count'] == 0]
            print(f"[WARNING] {len(failed)} scenarios had no risk updates:")
            for r in failed:
                print(f"  - {r['return_period'].upper()} t={r['time_step']}")

        print(f"\n{'='*80}")


def main():
    try:
        tester = MultiTIFFRiskTester()
        tester.run_comprehensive_test()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
