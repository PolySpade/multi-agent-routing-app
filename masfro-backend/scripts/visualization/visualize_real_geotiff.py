#!/usr/bin/env python3
"""
Visualize REAL GeoTIFF Integration

Now that coordinate transformation is fixed, create a visualization
using ACTUAL GEOTIFF flood data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from typing import Dict, Tuple, List

from app.environment.graph_manager import DynamicGraphEnvironment
from app.services.geotiff_service import get_geotiff_service


class RealGeoTIFFVisualizer:
    """Visualize actual GEOTIFF flood data integration."""

    def __init__(self):
        print("="*80)
        print("REAL GEOTIFF INTEGRATION VISUALIZATION")
        print("="*80)

        print("\n[1] Initializing graph...")
        self.env = DynamicGraphEnvironment()
        print(f"  Graph: {self.env.graph.number_of_nodes()} nodes, {self.env.graph.number_of_edges()} edges")

        print("\n[2] Initializing GeoTIFF service...")
        self.geotiff = get_geotiff_service()

    def query_flood_depths_sample(
        self,
        return_period: str,
        time_step: int,
        sample_rate: int = 5
    ) -> Dict[Tuple, float]:
        """Query flood depths for a sample of edges."""
        flood_depths = {}

        edges = list(self.env.graph.edges(keys=True))
        sampled = edges[::sample_rate]  # Sample every Nth edge

        print(f"  Querying {len(sampled)} edges (every {sample_rate}th)...")

        for i, (u, v, key) in enumerate(sampled):
            if (i + 1) % 200 == 0:
                print(f"    Progress: {i+1}/{len(sampled)}...")

            try:
                u_lon = float(self.env.graph.nodes[u]['x'])
                u_lat = float(self.env.graph.nodes[u]['y'])
                v_lon = float(self.env.graph.nodes[v]['x'])
                v_lat = float(self.env.graph.nodes[v]['y'])

                # Query at both endpoints
                depth_u = self.geotiff.get_flood_depth_at_point(u_lon, u_lat, return_period, time_step)
                depth_v = self.geotiff.get_flood_depth_at_point(v_lon, v_lat, return_period, time_step)

                # Average depth
                depths = [d for d in [depth_u, depth_v] if d is not None]
                if depths:
                    avg = sum(depths) / len(depths)
                    if avg > 0.01:
                        flood_depths[(u, v, key)] = avg

            except:
                continue

        return flood_depths

    def convert_depths_to_risk(self, flood_depths: Dict[Tuple, float]) -> Dict[Tuple, float]:
        """Convert depths to risk scores."""
        risk_scores = {}
        for edge, depth in flood_depths.items():
            if depth <= 0.3:
                risk = depth
            elif depth <= 0.6:
                risk = 0.3 + (depth - 0.3) * 1.0
            elif depth <= 1.0:
                risk = 0.6 + (depth - 0.6) * 0.5
            else:
                risk = min(0.8 + (depth - 1.0) * 0.2, 1.0)
            risk_scores[edge] = risk
        return risk_scores

    def update_graph_weights(self, risk_scores: Dict[Tuple, float]):
        """Update graph weights."""
        for (u, v, key), risk in risk_scores.items():
            try:
                edge_data = self.env.graph[u][v][key]
                edge_data['risk_score'] = risk
                length = edge_data.get('length', 1.0)
                edge_data['weight'] = length * (1.0 + risk)
            except KeyError:
                continue

    def get_edge_coordinates_and_risks(self) -> Tuple[List, List]:
        """Extract edge coords and risks."""
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

    def visualize(self, before_coords, before_risks, after_coords, after_risks,
                  scenario, num_updated, output_path):
        """Create visualization."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))

        def get_color(risk):
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
        ax1.set_title("BEFORE GeoTIFF Load\n(All edges safe)", fontsize=13, fontweight='bold')
        for edge, risk in zip(before_coords, before_risks):
            (x1, y1), (x2, y2) = edge
            ax1.plot([x1, x2], [y1, y2], color=get_color(risk), linewidth=0.6, alpha=0.7)

        ax1.set_xlabel('Longitude', fontsize=11)
        ax1.set_ylabel('Latitude', fontsize=11)
        ax1.grid(True, alpha=0.3)

        # AFTER
        ax2.set_title(f"AFTER GeoTIFF Load\n{scenario} - {num_updated} edges updated",
                     fontsize=13, fontweight='bold')
        for edge, risk in zip(after_coords, after_risks):
            (x1, y1), (x2, y2) = edge
            ax2.plot([x1, x2], [y1, y2], color=get_color(risk), linewidth=0.6, alpha=0.7)

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

        plt.suptitle("REAL GeoTIFF Integration: Actual Flood Data",
                    fontsize=15, fontweight='bold', y=0.98)
        plt.tight_layout(rect=[0, 0.03, 1, 0.97])

        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n[SAVED] {output_path}")
        plt.close()

    def run(self, return_period="rr02", time_step=12, sample_rate=5):
        """Run visualization."""

        print(f"\n[3] Capturing BEFORE state...")
        before_coords, before_risks = self.get_edge_coordinates_and_risks()

        print(f"\n[4] Querying REAL GeoTIFF data ({return_period}, t={time_step})...")
        flood_depths = self.query_flood_depths_sample(return_period, time_step, sample_rate)
        print(f"  Found {len(flood_depths)} flooded edges")

        if not flood_depths:
            print("  [WARNING] No flood data found!")
            return

        # Show samples
        print(f"\n  Sample flood depths:")
        for i, (edge, depth) in enumerate(list(flood_depths.items())[:5]):
            print(f"    Edge {edge}: {depth:.3f}m")

        print(f"\n[5] Converting to risk scores...")
        risk_scores = self.convert_depths_to_risk(flood_depths)

        print(f"\n[6] Updating graph weights...")
        self.update_graph_weights(risk_scores)

        print(f"\n[7] Capturing AFTER state...")
        after_coords, after_risks = self.get_edge_coordinates_and_risks()

        print(f"\n[8] Statistics:")
        print(f"  Total edges: {self.env.graph.number_of_edges()}")
        print(f"  Updated edges: {len(risk_scores)}")
        print(f"  Percentage: {len(risk_scores)/self.env.graph.number_of_edges()*100:.1f}%")

        risks = list(risk_scores.values())
        depths = list(flood_depths.values())
        print(f"\n  Flood Depths:")
        print(f"    Min: {min(depths):.3f}m")
        print(f"    Max: {max(depths):.3f}m")
        print(f"    Mean: {np.mean(depths):.3f}m")
        print(f"\n  Risk Scores:")
        print(f"    Min: {min(risks):.3f}")
        print(f"    Max: {max(risks):.3f}")
        print(f"    Mean: {np.mean(risks):.3f}")

        print(f"\n  [SUCCESS] REAL GeoTIFF integration complete!")

        print(f"\n[9] Creating visualization...")
        output_dir = Path(__file__).parent.parent / "outputs" / "geotiff_tests"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"real_geotiff_{return_period}_t{time_step}.png"

        self.visualize(
            before_coords, before_risks,
            after_coords, after_risks,
            f"{return_period.upper()} Time Step {time_step}",
            len(risk_scores),
            str(output_path)
        )

        print("\n" + "="*80)
        print("VISUALIZATION COMPLETE")
        print("="*80)


def main():
    try:
        viz = RealGeoTIFFVisualizer()
        viz.run(return_period="rr02", time_step=12, sample_rate=5)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
