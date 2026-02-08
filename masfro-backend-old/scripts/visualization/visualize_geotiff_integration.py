#!/usr/bin/env python3
"""
Comprehensive GeoTIFF Integration Visualizer with Animated GIFs

This script:
1. Tests ALL 72 GeoTIFF files (4 return periods × 18 time steps)
2. Creates dramatic visualizations with enhanced color scheme
3. Generates animated GIFs showing flood progression over time
4. Outputs individual frames and summary statistics

Output:
- 4 animated GIFs (one per return period: rr01, rr02, rr03, rr04)
- 72 individual frame images
- Console statistics for each scenario
- Comprehensive summary report
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
from PIL import Image
from datetime import datetime

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.hazard_agent import HazardAgent
from app.services.geotiff_service import get_geotiff_service


class GeoTIFFAnimatedVisualizer:
    """Create animated visualizations of GeoTIFF flood progression."""

    def __init__(self):
        """Initialize visualizer with graph and agents."""
        print("="*80, flush=True)
        print("COMPREHENSIVE GEOTIFF INTEGRATION VISUALIZER", flush=True)
        print("Creating Animated GIFs for All Return Periods", flush=True)
        print("="*80, flush=True)

        # Initialize environment and graph
        print("\n[INIT] Loading road network graph...", flush=True)
        self.env = DynamicGraphEnvironment()
        if self.env.graph is None:
            raise RuntimeError("Failed to load graph!")

        print(f"  [OK] Graph loaded: {self.env.graph.number_of_nodes()} nodes, "
              f"{self.env.graph.number_of_edges()} edges", flush=True)

        # Initialize GeoTIFF service
        print("\n[INIT] Initializing GeoTIFF service...")
        self.geotiff_service = get_geotiff_service()
        print(f"  [OK] GeoTIFF service ready")
        print(f"  [OK] Return periods: {', '.join(self.geotiff_service.return_periods)}")

        # Initialize HazardAgent
        print("\n[INIT] Initializing HazardAgent...")
        self.hazard_agent = HazardAgent(
            agent_id="hazard_animator",
            environment=self.env
        )
        print(f"  [OK] HazardAgent ready")

        # Output directory
        self.output_dir = Path(__file__).parent.parent / "outputs" / "geotiff_animations"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n[INIT] Output directory: {self.output_dir}")

    def get_dramatic_color(self, risk: float) -> str:
        """
        Map risk score to DRAMATIC color scheme.
        Moderate and higher risks use red tones for visual impact.

        Args:
            risk: Risk score (0.0 - 1.0)

        Returns:
            Hex color string
        """
        if risk < 0.001:
            return '#2ECC71'  # Emerald green (safe - no flood)
        elif risk < 0.2:
            return '#A8E6CF'  # Light green (minimal risk)
        elif risk < 0.4:
            return '#FFD700'  # Gold (low risk)
        elif risk < 0.6:
            # DRAMATIC: Moderate is now RED/ORANGE instead of yellow
            return '#FF6B35'  # Bright red-orange (moderate - DRAMATIC!)
        elif risk < 0.8:
            return '#E63946'  # Crimson red (high risk)
        else:
            return '#990000'  # Dark red/maroon (extreme risk)

    def get_edge_coordinates(self) -> Tuple[List[Tuple], List[float]]:
        """Extract edge coordinates and risk scores for plotting."""
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

    def get_risk_statistics(self) -> Dict[str, any]:
        """Get comprehensive risk statistics."""
        risks = []
        distribution = {
            'safe (0.0)': 0,
            'minimal (0.0-0.2)': 0,
            'low (0.2-0.4)': 0,
            'moderate (0.4-0.6)': 0,
            'high (0.6-0.8)': 0,
            'extreme (0.8-1.0)': 0
        }

        for u, v, key, data in self.env.graph.edges(keys=True, data=True):
            risk = data.get('risk_score', 0.0)
            risks.append(risk)

            if risk < 0.001:
                distribution['safe (0.0)'] += 1
            elif risk < 0.2:
                distribution['minimal (0.0-0.2)'] += 1
            elif risk < 0.4:
                distribution['low (0.2-0.4)'] += 1
            elif risk < 0.6:
                distribution['moderate (0.4-0.6)'] += 1
            elif risk < 0.8:
                distribution['high (0.6-0.8)'] += 1
            else:
                distribution['extreme (0.8-1.0)'] += 1

        return {
            'distribution': distribution,
            'min': min(risks) if risks else 0.0,
            'max': max(risks) if risks else 0.0,
            'mean': np.mean(risks) if risks else 0.0,
            'median': np.median(risks) if risks else 0.0,
            'total_edges': len(risks),
            'flooded_edges': sum(1 for r in risks if r > 0.001)
        }

    def create_frame(
        self,
        coords: List[Tuple],
        risks: List[float],
        return_period: str,
        time_step: int,
        stats: Dict[str, any],
        output_path: Path
    ):
        """
        Create a single visualization frame.

        Args:
            coords: Edge coordinates
            risks: Edge risk scores
            return_period: Return period (rr01, rr02, etc.)
            time_step: Time step (1-18)
            stats: Risk statistics
            output_path: Output file path
        """
        fig, ax = plt.subplots(figsize=(14, 10))

        # Plot edges colored by risk
        for edge, risk in zip(coords, risks):
            (x1, y1), (x2, y2) = edge
            color = self.get_dramatic_color(risk)
            # Make flooded edges thicker and more visible
            linewidth = 1.2 if risk > 0.001 else 0.4
            alpha = 0.9 if risk > 0.001 else 0.3
            ax.plot([x1, x2], [y1, y2], color=color, linewidth=linewidth, alpha=alpha)

        # Title with scenario info
        rp_names = {
            'rr01': '2-Year Flood',
            'rr02': '5-Year Flood',
            'rr03': 'Higher Return Period',
            'rr04': '10-Year Flood'
        }
        title = f"{rp_names.get(return_period, return_period.upper())} - Hour {time_step}/18"
        ax.set_title(title, fontsize=18, fontweight='bold', pad=20)

        # Add statistics text box
        stats_text = (
            f"Flooded Edges: {stats['flooded_edges']:,} / {stats['total_edges']:,} "
            f"({stats['flooded_edges']/stats['total_edges']*100:.1f}%)\n"
            f"Max Risk: {stats['max']:.3f} | Mean Risk: {stats['mean']:.3f}"
        )
        ax.text(
            0.02, 0.98, stats_text,
            transform=ax.transAxes,
            fontsize=11,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='black')
        )

        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.grid(True, alpha=0.2, linestyle='--')

        # Enhanced legend with dramatic colors
        legend_elements = [
            mpatches.Patch(color='#2ECC71', label='Safe (No Flood)'),
            mpatches.Patch(color='#A8E6CF', label='Minimal (0.0-0.2)'),
            mpatches.Patch(color='#FFD700', label='Low (0.2-0.4)'),
            mpatches.Patch(color='#FF6B35', label='MODERATE (0.4-0.6)'),
            mpatches.Patch(color='#E63946', label='HIGH (0.6-0.8)'),
            mpatches.Patch(color='#990000', label='EXTREME (0.8-1.0)')
        ]
        ax.legend(
            handles=legend_elements,
            loc='upper right',
            fontsize=10,
            framealpha=0.95,
            edgecolor='black'
        )

        plt.tight_layout()
        plt.savefig(output_path, dpi=120, bbox_inches='tight', facecolor='white')
        plt.close()

    def process_return_period(self, return_period: str) -> List[Path]:
        """
        Process all time steps for a single return period.

        Args:
            return_period: Return period (rr01, rr02, rr03, rr04)

        Returns:
            List of frame file paths
        """
        print(f"\n{'='*80}")
        print(f"PROCESSING: {return_period.upper()}")
        print(f"{'='*80}")

        frame_paths = []

        for time_step in range(1, 19):  # 1-18
            print(f"\n[{return_period.upper()}] Time Step {time_step}/18...")

            # Reset graph to clean state
            self.env._load_graph_from_file()

            # Configure flood scenario
            self.hazard_agent.set_flood_scenario(
                return_period=return_period,
                time_step=time_step
            )

            # Calculate risk scores
            fused_data = {
                "system_wide": {
                    "risk_level": 0.0,
                    "source": "animation_test"
                }
            }

            risk_scores = self.hazard_agent.calculate_risk_scores(fused_data)

            if risk_scores:
                print(f"  [OK] Calculated {len(risk_scores)} risk scores")
                # Update graph
                self.hazard_agent.update_environment(risk_scores)
            else:
                print(f"  [WARNING] No risk scores calculated")

            # Get edge data
            coords, risks = self.get_edge_coordinates()

            # Get statistics
            stats = self.get_risk_statistics()

            print(f"  [OK] Flooded: {stats['flooded_edges']}/{stats['total_edges']} edges "
                  f"({stats['flooded_edges']/stats['total_edges']*100:.1f}%)")
            print(f"  [OK] Risk range: {stats['min']:.3f} - {stats['max']:.3f} "
                  f"(mean: {stats['mean']:.3f})")

            # Create frame
            frame_path = self.output_dir / f"{return_period}_step_{time_step:02d}.png"
            self.create_frame(
                coords=coords,
                risks=risks,
                return_period=return_period,
                time_step=time_step,
                stats=stats,
                output_path=frame_path
            )

            frame_paths.append(frame_path)
            print(f"  [OK] Frame saved: {frame_path.name}")

        return frame_paths

    def create_gif(self, frame_paths: List[Path], output_path: Path, duration: int = 500):
        """
        Create animated GIF from frames.

        Args:
            frame_paths: List of frame image paths
            output_path: Output GIF path
            duration: Duration per frame in milliseconds
        """
        print(f"\n[GIF] Creating animation: {output_path.name}")

        # Load all frames
        frames = []
        for frame_path in frame_paths:
            frame = Image.open(frame_path)
            frames.append(frame)

        # Save as animated GIF
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,  # Infinite loop
            optimize=False  # Keep quality high
        )

        print(f"  [OK] GIF created: {output_path}")
        print(f"  [OK] Frames: {len(frames)}, Duration: {duration}ms per frame")

        # Calculate file size
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  [OK] File size: {file_size_mb:.2f} MB")

    def run_comprehensive_test(self):
        """Run comprehensive test of all TIFF files and create GIFs."""

        print("\n" + "="*80)
        print("STARTING COMPREHENSIVE GEOTIFF TEST")
        print(f"Total scenarios to process: 72 (4 return periods × 18 time steps)")
        print("="*80)

        start_time = datetime.now()
        all_results = {}

        # Process each return period
        for return_period in self.geotiff_service.return_periods:

            # Process all time steps and get frame paths
            frame_paths = self.process_return_period(return_period)

            # Create animated GIF
            gif_path = self.output_dir / f"flood_animation_{return_period}.gif"
            self.create_gif(frame_paths, gif_path, duration=400)  # 400ms = 0.4s per frame

            all_results[return_period] = {
                'frames': len(frame_paths),
                'gif_path': gif_path
            }

        # Final summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "="*80)
        print("COMPREHENSIVE TEST COMPLETE!")
        print("="*80)
        print(f"\n[TIME] Total processing time: {duration:.1f} seconds")
        print(f"\n[SUMMARY]:")
        print(f"  - Total scenarios tested: 72")
        print(f"  - Total frames created: {sum(r['frames'] for r in all_results.values())}")
        print(f"  - Animated GIFs created: {len(all_results)}")

        print(f"\n[ANIMATED GIFS]:")
        for rp, result in all_results.items():
            print(f"  - {rp.upper()}: {result['gif_path'].name} ({result['frames']} frames)")

        print(f"\n[OUTPUT] All files saved to: {self.output_dir}")

        print("\n" + "="*80)
        print("VISUALIZATION COMPLETE")
        print("="*80)


def main():
    """Run comprehensive GeoTIFF visualization with animations."""
    try:
        visualizer = GeoTIFFAnimatedVisualizer()
        visualizer.run_comprehensive_test()
        return 0

    except Exception as e:
        print(f"\n[ERROR] Visualization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
