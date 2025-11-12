#!/usr/bin/env python3
"""
Visualize GeoTIFF Integration with Graph Weights

This script demonstrates and verifies that:
1. GeoTIFF flood data is properly loaded
2. Flood depths are mapped to road network edges
3. Edge risk scores and weights are updated correctly
4. Visual comparison of graph before/after GEOTIFF integration

Output:
- Console statistics showing risk score distribution
- Side-by-side visualization of road network (clean vs flooded)
- Sample edge weight comparisons
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from typing import Dict, Tuple, List

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.hazard_agent import HazardAgent
from app.services.geotiff_service import get_geotiff_service


class GeoTIFFIntegrationVisualizer:
    """Visualizes GeoTIFF integration with road network graph."""

    def __init__(self):
        """Initialize visualizer with graph and agents."""
        print("="*80)
        print("GEOTIFF INTEGRATION VERIFICATION & VISUALIZATION")
        print("="*80)

        # Initialize environment and graph
        print("\n[STEP 1] Initializing road network graph...")
        self.env = DynamicGraphEnvironment()
        if self.env.graph is None:
            raise RuntimeError("Failed to load graph!")

        print(f"  Graph loaded: {self.env.graph.number_of_nodes()} nodes, {self.env.graph.number_of_edges()} edges")

        # Initialize GeoTIFF service
        print("\n[STEP 2] Initializing GeoTIFF service...")
        try:
            self.geotiff_service = get_geotiff_service()
            print(f"  GeoTIFF service initialized")
            print(f"  Available return periods: {self.geotiff_service.return_periods}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize GeoTIFF service: {e}")

        # Initialize HazardAgent
        print("\n[STEP 3] Initializing HazardAgent...")
        self.hazard_agent = HazardAgent(
            agent_id="hazard_viz",
            environment=self.env
        )
        print(f"  HazardAgent initialized")

    def capture_edge_weights_snapshot(self) -> Dict[Tuple, float]:
        """Capture current edge risk scores for comparison."""
        snapshot = {}
        for u, v, key, data in self.env.graph.edges(keys=True, data=True):
            risk_score = data.get('risk_score', 0.0)
            snapshot[(u, v, key)] = risk_score
        return snapshot

    def compare_snapshots(
        self,
        before: Dict[Tuple, float],
        after: Dict[Tuple, float]
    ) -> Dict[str, any]:
        """Compare edge risk scores before and after GEOTIFF loading."""
        changed_edges = []
        unchanged_count = 0

        for edge_id, before_risk in before.items():
            after_risk = after.get(edge_id, 0.0)
            if abs(after_risk - before_risk) > 0.001:  # Changed
                changed_edges.append({
                    'edge': edge_id,
                    'before': before_risk,
                    'after': after_risk,
                    'delta': after_risk - before_risk
                })
            else:
                unchanged_count += 1

        return {
            'total_edges': len(before),
            'changed': len(changed_edges),
            'unchanged': unchanged_count,
            'changed_edges': changed_edges
        }

    def get_risk_distribution(self) -> Dict[str, int]:
        """Get distribution of risk scores across edges."""
        distribution = {
            'safe (0.0-0.2)': 0,
            'low (0.2-0.4)': 0,
            'moderate (0.4-0.6)': 0,
            'high (0.6-0.8)': 0,
            'extreme (0.8-1.0)': 0
        }

        for u, v, key, data in self.env.graph.edges(keys=True, data=True):
            risk = data.get('risk_score', 0.0)
            if risk < 0.2:
                distribution['safe (0.0-0.2)'] += 1
            elif risk < 0.4:
                distribution['low (0.2-0.4)'] += 1
            elif risk < 0.6:
                distribution['moderate (0.4-0.6)'] += 1
            elif risk < 0.8:
                distribution['high (0.6-0.8)'] += 1
            else:
                distribution['extreme (0.8-1.0)'] += 1

        return distribution

    def get_edge_coordinates(self) -> List[Tuple]:
        """Extract edge coordinates for plotting."""
        edges_coords = []
        edges_risks = []

        for u, v, key, data in self.env.graph.edges(keys=True, data=True):
            u_lat = self.env.graph.nodes[u]['y']
            u_lon = self.env.graph.nodes[u]['x']
            v_lat = self.env.graph.nodes[v]['y']
            v_lon = self.env.graph.nodes[v]['x']
            risk = data.get('risk_score', 0.0)

            edges_coords.append(((u_lon, u_lat), (v_lon, v_lat)))
            edges_risks.append(risk)

        return edges_coords, edges_risks

    def visualize_comparison(
        self,
        before_coords: List[Tuple],
        before_risks: List[float],
        after_coords: List[Tuple],
        after_risks: List[float],
        scenario_name: str,
        output_path: str
    ):
        """Create side-by-side visualization of graph before/after GEOTIFF."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # Define color mapping function
        def get_color(risk: float):
            """Map risk score to color (green -> yellow -> red)."""
            if risk < 0.2:
                return '#00ff00'  # Green (safe)
            elif risk < 0.4:
                return '#90ff00'  # Yellow-green (low)
            elif risk < 0.6:
                return '#ffff00'  # Yellow (moderate)
            elif risk < 0.8:
                return '#ff9000'  # Orange (high)
            else:
                return '#ff0000'  # Red (extreme)

        # BEFORE plot (should be all green - risk_score=0.0)
        ax1.set_title("BEFORE GeoTIFF Load\n(All edges safe - risk_score=0.0)",
                     fontsize=12, fontweight='bold')
        for edge, risk in zip(before_coords, before_risks):
            (x1, y1), (x2, y2) = edge
            color = get_color(risk)
            ax1.plot([x1, x2], [y1, y2], color=color, linewidth=0.5, alpha=0.7)

        ax1.set_xlabel('Longitude')
        ax1.set_ylabel('Latitude')
        ax1.grid(True, alpha=0.3)

        # AFTER plot (colored by risk from GEOTIFF)
        ax2.set_title(f"AFTER GeoTIFF Load\n({scenario_name})",
                     fontsize=12, fontweight='bold')
        for edge, risk in zip(after_coords, after_risks):
            (x1, y1), (x2, y2) = edge
            color = get_color(risk)
            ax2.plot([x1, x2], [y1, y2], color=color, linewidth=0.5, alpha=0.7)

        ax2.set_xlabel('Longitude')
        ax2.set_ylabel('Latitude')
        ax2.grid(True, alpha=0.3)

        # Add legend
        legend_elements = [
            mpatches.Patch(color='#00ff00', label='Safe (0.0-0.2)'),
            mpatches.Patch(color='#90ff00', label='Low (0.2-0.4)'),
            mpatches.Patch(color='#ffff00', label='Moderate (0.4-0.6)'),
            mpatches.Patch(color='#ff9000', label='High (0.6-0.8)'),
            mpatches.Patch(color='#ff0000', label='Extreme (0.8-1.0)')
        ]
        fig.legend(handles=legend_elements, loc='lower center',
                  ncol=5, bbox_to_anchor=(0.5, -0.05))

        plt.suptitle("GeoTIFF Integration: Edge Risk Score Mapping",
                    fontsize=14, fontweight='bold', y=0.98)
        plt.tight_layout(rect=[0, 0.03, 1, 0.96])

        # Save
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n[VISUALIZATION] Saved to: {output_path}")
        plt.close()

    def run_test(self, return_period: str = "rr01", time_step: int = 10):
        """Run complete GEOTIFF integration test with visualization."""

        print(f"\n[STEP 4] Capturing BEFORE snapshot (clean graph)...")
        before_snapshot = self.capture_edge_weights_snapshot()
        before_coords, before_risks = self.get_edge_coordinates()
        before_dist = self.get_risk_distribution()

        print(f"  BEFORE - Risk Distribution:")
        for category, count in before_dist.items():
            print(f"    {category}: {count} edges")

        print(f"\n[STEP 5] Loading GeoTIFF flood data ({return_period}, time_step={time_step})...")

        # Configure flood scenario
        self.hazard_agent.set_flood_scenario(
            return_period=return_period,
            time_step=time_step
        )

        # Calculate risk scores (this queries GEOTIFF and updates graph)
        print(f"\n[STEP 6] Calculating risk scores from GeoTIFF data...")

        # Prepare minimal fused data (for this test, we focus on GEOTIFF only)
        # In production, this would come from FloodAgent and ScoutAgent
        fused_data = {
            "system_wide": {
                "risk_level": 0.0,  # No additional environmental risk for this test
                "source": "test"
            }
        }

        risk_scores = self.hazard_agent.calculate_risk_scores(fused_data)

        if not risk_scores:
            print("  [WARNING] No risk scores calculated!")
            return

        print(f"  Calculated risk scores for {len(risk_scores)} edges")

        # Update environment with risk scores
        print(f"\n[STEP 7] Updating graph edge weights...")
        self.hazard_agent.update_environment(risk_scores)

        # Capture AFTER snapshot
        print(f"\n[STEP 8] Capturing AFTER snapshot (with flood data)...")
        after_snapshot = self.capture_edge_weights_snapshot()
        after_coords, after_risks = self.get_edge_coordinates()
        after_dist = self.get_risk_distribution()

        print(f"  AFTER - Risk Distribution:")
        for category, count in after_dist.items():
            print(f"    {category}: {count} edges")

        # Compare snapshots
        print(f"\n[STEP 9] Comparing BEFORE vs AFTER...")
        comparison = self.compare_snapshots(before_snapshot, after_snapshot)

        print(f"\n  Total edges: {comparison['total_edges']}")
        print(f"  Changed edges: {comparison['changed']} ({comparison['changed']/comparison['total_edges']*100:.1f}%)")
        print(f"  Unchanged edges: {comparison['unchanged']} ({comparison['unchanged']/comparison['total_edges']*100:.1f}%)")

        # Show sample changed edges
        if comparison['changed'] > 0:
            print(f"\n  Sample changed edges (first 10):")
            for i, edge_info in enumerate(comparison['changed_edges'][:10]):
                u, v, key = edge_info['edge']
                print(f"    Edge ({u}, {v}, {key}): {edge_info['before']:.3f} -> {edge_info['after']:.3f} (delta: +{edge_info['delta']:.3f})")

        # Verify integration worked
        print(f"\n[STEP 10] Verification...")
        if comparison['changed'] > 0:
            print(f"  [SUCCESS] GeoTIFF data successfully integrated into graph!")
            print(f"  [SUCCESS] Edge weights updated based on flood depths!")

            # Calculate statistics
            risks = [edge_info['after'] for edge_info in comparison['changed_edges']]
            print(f"\n  Risk Statistics:")
            print(f"    Min risk: {min(risks):.3f}")
            print(f"    Max risk: {max(risks):.3f}")
            print(f"    Mean risk: {np.mean(risks):.3f}")
            print(f"    Median risk: {np.median(risks):.3f}")
        else:
            print(f"  [WARNING] No edges changed! GeoTIFF may not have flood data for this area.")

        # Create visualization
        print(f"\n[STEP 11] Creating visualization...")
        output_dir = Path(__file__).parent.parent / "outputs" / "geotiff_tests"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"geotiff_integration_{return_period}_t{time_step}.png"

        self.visualize_comparison(
            before_coords=before_coords,
            before_risks=before_risks,
            after_coords=after_coords,
            after_risks=after_risks,
            scenario_name=f"{return_period.upper()} Time Step {time_step}",
            output_path=str(output_path)
        )

        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)


def main():
    """Run GeoTIFF integration visualization test."""
    try:
        visualizer = GeoTIFFIntegrationVisualizer()

        # Test with different scenarios
        print("\n\nRunning Test 1: RR01 (1-year return) Time Step 10...")
        visualizer.run_test(return_period="rr01", time_step=10)

        print("\n\nRunning Test 2: RR04 (10-year return) Time Step 18...")
        # Reset graph for second test
        visualizer.env._load_graph_from_file()
        visualizer.run_test(return_period="rr04", time_step=18)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
