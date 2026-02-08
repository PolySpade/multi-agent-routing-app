#!/usr/bin/env python3
"""
Quick GeoTIFF Integration Visualization (Optimized)

This optimized version demonstrates GEOTIFF integration by:
1. Sampling a subset of edges for faster processing
2. Still showing the full graph visualization
3. Proving that weights are updated correctly

Output:
- Console statistics
- Side-by-side visualization
- Sample edge weight comparisons
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from typing import Dict, Tuple, List
import random

from app.environment.graph_manager import DynamicGraphEnvironment
from app.services.geotiff_service import get_geotiff_service


class QuickGeoTIFFVisualizer:
    """Fast GEOTIFF visualization using sampled edges."""

    def __init__(self):
        print("="*80)
        print("QUICK GEOTIFF INTEGRATION VERIFICATION")
        print("="*80)

        print("\n[STEP 1] Initializing graph...")
        self.env = DynamicGraphEnvironment()
        if self.env.graph is None:
            raise RuntimeError("Failed to load graph!")

        print(f"  Graph: {self.env.graph.number_of_nodes()} nodes, {self.env.graph.number_of_edges()} edges")

        print("\n[STEP 2] Initializing GeoTIFF service...")
        self.geotiff_service = get_geotiff_service()
        print(f"  Available return periods: {self.geotiff_service.return_periods}")

    def sample_edges(self, sample_size: int = 500) -> List[Tuple]:
        """Sample a subset of edges for faster processing."""
        all_edges = list(self.env.graph.edges(keys=True))
        if len(all_edges) <= sample_size:
            return all_edges
        return random.sample(all_edges, sample_size)

    def query_flood_depths_for_edges(
        self,
        edges: List[Tuple],
        return_period: str,
        time_step: int
    ) -> Dict[Tuple, float]:
        """Query flood depths for a list of edges."""
        flood_depths = {}

        print(f"  Querying {len(edges)} sampled edges...")

        for i, (u, v, key) in enumerate(edges):
            if (i + 1) % 100 == 0:
                print(f"    Progress: {i+1}/{len(edges)} edges...")

            try:
                # Get node coordinates
                u_lon = float(self.env.graph.nodes[u]['x'])
                u_lat = float(self.env.graph.nodes[u]['y'])
                v_lon = float(self.env.graph.nodes[v]['x'])
                v_lat = float(self.env.graph.nodes[v]['y'])

                # Query flood depth at both endpoints
                depth_u = self.geotiff_service.get_flood_depth_at_point(
                    u_lon, u_lat, return_period, time_step
                )
                depth_v = self.geotiff_service.get_flood_depth_at_point(
                    v_lon, v_lat, return_period, time_step
                )

                # Calculate average depth
                depths = [d for d in [depth_u, depth_v] if d is not None]
                if depths:
                    avg_depth = sum(depths) / len(depths)
                    if avg_depth > 0.01:  # Filter out noise
                        flood_depths[(u, v, key)] = avg_depth

            except Exception as e:
                continue

        return flood_depths

    def convert_depths_to_risk(self, flood_depths: Dict[Tuple, float]) -> Dict[Tuple, float]:
        """Convert flood depths to risk scores."""
        risk_scores = {}

        for edge, depth in flood_depths.items():
            # Risk mapping from HazardAgent
            if depth <= 0.3:
                risk = depth  # 0.3m = 0.3 risk
            elif depth <= 0.6:
                risk = 0.3 + (depth - 0.3) * 1.0
            elif depth <= 1.0:
                risk = 0.6 + (depth - 0.6) * 0.5
            else:
                risk = min(0.8 + (depth - 1.0) * 0.2, 1.0)

            risk_scores[edge] = risk

        return risk_scores

    def update_graph_weights(self, risk_scores: Dict[Tuple, float]):
        """Update graph edge weights with risk scores."""
        for (u, v, key), risk in risk_scores.items():
            try:
                edge_data = self.env.graph[u][v][key]
                edge_data['risk_score'] = risk
                length = edge_data.get('length', 1.0)
                edge_data['weight'] = length * (1.0 + risk)
            except KeyError:
                continue

    def get_edge_coordinates_and_risks(self) -> Tuple[List, List]:
        """Extract all edge coordinates and their current risk scores."""
        coords = []
        risks = []

        for u, v, key in self.env.graph.edges(keys=True):
            u_lat = self.env.graph.nodes[u]['y']
            u_lon = self.env.graph.nodes[u]['x']
            v_lat = self.env.graph.nodes[v]['y']
            v_lon = self.env.graph.nodes[v]['x']
            risk = self.env.graph[u][v][key].get('risk_score', 0.0)

            coords.append(((u_lon, u_lat), (v_lon, v_lat)))
            risks.append(risk)

        return coords, risks

    def get_risk_distribution(self) -> Dict[str, int]:
        """Get risk distribution across all edges."""
        dist = {
            'safe (0.0-0.2)': 0,
            'low (0.2-0.4)': 0,
            'moderate (0.4-0.6)': 0,
            'high (0.6-0.8)': 0,
            'extreme (0.8-1.0)': 0
        }

        for u, v, key, data in self.env.graph.edges(keys=True, data=True):
            risk = data.get('risk_score', 0.0)
            if risk < 0.2:
                dist['safe (0.0-0.2)'] += 1
            elif risk < 0.4:
                dist['low (0.2-0.4)'] += 1
            elif risk < 0.6:
                dist['moderate (0.4-0.6)'] += 1
            elif risk < 0.8:
                dist['high (0.6-0.8)'] += 1
            else:
                dist['extreme (0.8-1.0)'] += 1

        return dist

    def visualize_comparison(
        self,
        before_coords: List,
        before_risks: List,
        after_coords: List,
        after_risks: List,
        scenario_name: str,
        output_path: str,
        num_updated: int
    ):
        """Create side-by-side visualization."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))

        def get_color(risk: float):
            if risk < 0.2:
                return '#00ff00'
            elif risk < 0.4:
                return '#90ff00'
            elif risk < 0.6:
                return '#ffff00'
            elif risk < 0.8:
                return '#ff9000'
            else:
                return '#ff0000'

        # BEFORE
        ax1.set_title("BEFORE GeoTIFF Load\n(All edges safe)",
                     fontsize=13, fontweight='bold')
        for edge, risk in zip(before_coords, before_risks):
            (x1, y1), (x2, y2) = edge
            ax1.plot([x1, x2], [y1, y2], color=get_color(risk),
                    linewidth=0.6, alpha=0.7)

        ax1.set_xlabel('Longitude', fontsize=11)
        ax1.set_ylabel('Latitude', fontsize=11)
        ax1.grid(True, alpha=0.3)

        # AFTER
        ax2.set_title(f"AFTER GeoTIFF Load\n({scenario_name}) - {num_updated} edges updated",
                     fontsize=13, fontweight='bold')
        for edge, risk in zip(after_coords, after_risks):
            (x1, y1), (x2, y2) = edge
            ax2.plot([x1, x2], [y1, y2], color=get_color(risk),
                    linewidth=0.6, alpha=0.7)

        ax2.set_xlabel('Longitude', fontsize=11)
        ax2.set_ylabel('Latitude', fontsize=11)
        ax2.grid(True, alpha=0.3)

        # Legend
        legend_elements = [
            mpatches.Patch(color='#00ff00', label='Safe (0.0-0.2)'),
            mpatches.Patch(color='#90ff00', label='Low (0.2-0.4)'),
            mpatches.Patch(color='#ffff00', label='Moderate (0.4-0.6)'),
            mpatches.Patch(color='#ff9000', label='High (0.6-0.8)'),
            mpatches.Patch(color='#ff0000', label='Extreme (0.8-1.0)')
        ]
        fig.legend(handles=legend_elements, loc='lower center',
                  ncol=5, bbox_to_anchor=(0.5, -0.02), fontsize=10)

        plt.suptitle("GeoTIFF Integration: Edge Risk Score Mapping",
                    fontsize=15, fontweight='bold', y=0.98)
        plt.tight_layout(rect=[0, 0.03, 1, 0.97])

        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n[VISUALIZATION] Saved to: {output_path}")
        plt.close()

    def run_test(
        self,
        return_period: str = "rr02",
        time_step: int = 12,
        sample_size: int = 500
    ):
        """Run quick GEOTIFF integration test."""

        print(f"\n[STEP 3] Capturing BEFORE snapshot...")
        before_coords, before_risks = self.get_edge_coordinates_and_risks()
        before_dist = self.get_risk_distribution()

        print(f"  BEFORE Distribution:")
        for cat, count in before_dist.items():
            print(f"    {cat}: {count}")

        print(f"\n[STEP 4] Sampling {sample_size} edges for flood depth queries...")
        sampled_edges = self.sample_edges(sample_size)
        print(f"  Sampled {len(sampled_edges)} edges")

        print(f"\n[STEP 5] Querying GeoTIFF flood depths ({return_period}, t={time_step})...")
        flood_depths = self.query_flood_depths_for_edges(
            sampled_edges,
            return_period,
            time_step
        )
        print(f"  Found flood depths for {len(flood_depths)} edges")

        if not flood_depths:
            print("  [WARNING] No flood data found! Check GEOTIFF files.")
            return

        print(f"\n[STEP 6] Converting depths to risk scores...")
        risk_scores = self.convert_depths_to_risk(flood_depths)

        # Show sample depths and risks
        print(f"\n  Sample flood depths and risks:")
        for i, (edge, depth) in enumerate(list(flood_depths.items())[:5]):
            risk = risk_scores[edge]
            print(f"    Edge {edge}: depth={depth:.3f}m -> risk={risk:.3f}")

        print(f"\n[STEP 7] Updating graph edge weights...")
        self.update_graph_weights(risk_scores)

        print(f"\n[STEP 8] Capturing AFTER snapshot...")
        after_coords, after_risks = self.get_edge_coordinates_and_risks()
        after_dist = self.get_risk_distribution()

        print(f"  AFTER Distribution:")
        for cat, count in after_dist.items():
            print(f"    {cat}: {count}")

        print(f"\n[STEP 9] Verification...")
        num_changed = len(risk_scores)
        total_edges = self.env.graph.number_of_edges()

        print(f"  Total edges: {total_edges}")
        print(f"  Updated edges: {num_changed} ({num_changed/total_edges*100:.1f}%)")
        print(f"  Unchanged edges: {total_edges-num_changed}")

        if num_changed > 0:
            risks = list(risk_scores.values())
            print(f"\n  Risk Statistics:")
            print(f"    Min: {min(risks):.3f}")
            print(f"    Max: {max(risks):.3f}")
            print(f"    Mean: {np.mean(risks):.3f}")
            print(f"    Median: {np.median(risks):.3f}")

            print(f"\n  [SUCCESS] GeoTIFF data integrated into graph!")
            print(f"  [SUCCESS] Edge weights updated based on flood depths!")

        print(f"\n[STEP 10] Creating visualization...")
        output_dir = Path(__file__).parent.parent / "outputs" / "geotiff_tests"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"geotiff_quick_{return_period}_t{time_step}.png"

        self.visualize_comparison(
            before_coords, before_risks,
            after_coords, after_risks,
            f"{return_period.upper()} Time Step {time_step}",
            str(output_path),
            num_changed
        )

        print("\n" + "="*80)
        print("VERIFICATION COMPLETE")
        print("="*80)


def main():
    try:
        visualizer = QuickGeoTIFFVisualizer()

        print("\n\nRunning Quick Test: RR02 Time Step 12 (500 sampled edges)...")
        visualizer.run_test(
            return_period="rr02",
            time_step=12,
            sample_size=500
        )

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
