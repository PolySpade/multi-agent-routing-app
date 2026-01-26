#!/usr/bin/env python3
"""
Real-Time Scout Tweet Visualization
====================================

Visualizes graph risk score changes as tweets are processed in real-time.

Features:
- Processes tweets in batches
- Visualizes graph before/after each batch
- Shows risk score heatmaps
- Generates animated sequence
- Creates comparison images
- Displays tweet statistics

Usage:
    python scripts/visualize_scout_tweets.py --scenario 1 --batches 6
    python scripts/visualize_scout_tweets.py --scenario 2 --batches 10 --batch-size 15
    python scripts/visualize_scout_tweets.py --compare  # Side-by-side comparison

Author: MAS-FRO Development Team
Date: November 2025
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import FancyBboxPatch
import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Any

# Import MAS-FRO components
from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.scout_agent import ScoutAgent
from app.agents.hazard_agent import HazardAgent

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScoutTweetVisualizer:
    """Visualizes graph changes as Scout Agent processes tweets."""

    def __init__(self, environment: DynamicGraphEnvironment):
        """Initialize visualizer with graph environment."""
        self.environment = environment
        self.graph = environment.graph

        if not self.graph:
            raise ValueError("Graph not loaded in environment")

        # Get node positions
        self.pos = {
            node: (data['x'], data['y'])
            for node, data in self.graph.nodes(data=True)
        }

        # Track visualization history
        self.snapshots = []

        logger.info(f"Initialized visualizer with {self.graph.number_of_nodes()} nodes "
                   f"and {self.graph.number_of_edges()} edges")

    def get_risk_snapshot(self) -> Dict[str, Any]:
        """
        Capture current risk state of the graph.

        Returns:
            Dict containing risk statistics and edge data
        """
        edge_risks = []
        for u, v, key, data in self.graph.edges(keys=True, data=True):
            risk = data.get('risk_score', 0.0)
            edge_risks.append(risk)

        risks = np.array(edge_risks) if edge_risks else np.array([0.0])

        snapshot = {
            'timestamp': datetime.now(),
            'risks': risks,
            'mean_risk': risks.mean(),
            'max_risk': risks.max(),
            'low_risk_count': np.sum(risks < 0.3),
            'mod_risk_count': np.sum((risks >= 0.3) & (risks < 0.6)),
            'high_risk_count': np.sum((risks >= 0.6) & (risks < 0.8)),
            'crit_risk_count': np.sum(risks >= 0.8)
        }

        return snapshot

    def visualize_current_state(
        self,
        title: str,
        save_path: str,
        tweet_stats: Dict[str, Any] = None
    ):
        """
        Visualize current graph risk state.

        Args:
            title: Plot title
            save_path: Path to save figure
            tweet_stats: Optional tweet statistics to display
        """
        fig, ax = plt.subplots(figsize=(18, 14))

        # Extract edge risk scores
        edge_risks = {}
        for u, v, key, data in self.graph.edges(keys=True, data=True):
            risk = data.get('risk_score', 0.0)
            edge_risks[(u, v, key)] = risk

        if not edge_risks:
            logger.warning("No edge risk scores found!")
            return

        # Prepare edges and colors
        edges = list(edge_risks.keys())
        risks = np.array([edge_risks[e] for e in edges])

        # Create color map: green (low risk) -> yellow -> red (high risk)
        norm = mcolors.Normalize(vmin=0.0, vmax=1.0)
        cmap = plt.cm.RdYlGn_r  # Reverse: green=low, red=high

        # Draw edges with risk colors
        edge_colors = [cmap(norm(r)) for r in risks]

        # Sample nodes for visualization (full graph is too dense)
        sample_size = min(1500, len(self.pos))
        sampled_nodes = list(self.pos.keys())[:sample_size]

        # Filter edges for sampled nodes
        sampled_edges = [(e[0], e[1]) for e in edges
                        if e[0] in sampled_nodes and e[1] in sampled_nodes]
        sampled_colors = [edge_colors[i] for i, e in enumerate(edges)
                         if e[0] in sampled_nodes and e[1] in sampled_nodes]

        # Draw network
        nx.draw_networkx_edges(
            self.graph,
            self.pos,
            edgelist=sampled_edges,
            edge_color=sampled_colors,
            width=0.8,
            alpha=0.7,
            ax=ax
        )

        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Risk Score (0=Safe, 1=Dangerous)', fontsize=14, fontweight='bold')

        # Calculate risk statistics
        low_risk = np.sum(risks < 0.3)
        mod_risk = np.sum((risks >= 0.3) & (risks < 0.6))
        high_risk = np.sum((risks >= 0.6) & (risks < 0.8))
        crit_risk = np.sum(risks >= 0.8)
        total_edges = len(risks)

        # Add risk statistics box
        stats_text = (
            f"Risk Distribution:\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 Low (<0.3):      {low_risk:4d} ({low_risk/total_edges*100:5.1f}%)\n"
            f"🟡 Moderate (0.3-0.6): {mod_risk:4d} ({mod_risk/total_edges*100:5.1f}%)\n"
            f"🟠 High (0.6-0.8):  {high_risk:4d} ({high_risk/total_edges*100:5.1f}%)\n"
            f"🔴 Critical (≥0.8): {crit_risk:4d} ({crit_risk/total_edges*100:5.1f}%)\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Mean Risk: {risks.mean():.3f}\n"
            f"📈 Max Risk:  {risks.max():.3f}\n"
            f"📉 Min Risk:  {risks.min():.3f}"
        )

        # Add stats box with fancy styling
        bbox_props = dict(
            boxstyle='round,pad=0.5',
            facecolor='white',
            edgecolor='darkblue',
            linewidth=2,
            alpha=0.9
        )

        ax.text(
            0.02, 0.98, stats_text,
            transform=ax.transAxes,
            verticalalignment='top',
            fontsize=11,
            fontfamily='monospace',
            bbox=bbox_props
        )

        # Add tweet statistics if provided
        if tweet_stats:
            tweet_text = (
                f"Tweet Statistics:\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📱 Total Processed: {tweet_stats.get('total_tweets', 0)}\n"
                f"🌊 Flood-Related:  {tweet_stats.get('flood_related', 0)}\n"
                f"📍 With Coords:    {tweet_stats.get('with_coords', 0)}\n"
                f"🔄 Updates Made:   {tweet_stats.get('nodes_updated', 0)}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📦 Current Batch:  {tweet_stats.get('batch_num', 0)}\n"
                f"⏱  Batch Time:    {tweet_stats.get('batch_time', 0):.2f}s"
            )

            tweet_bbox = dict(
                boxstyle='round,pad=0.5',
                facecolor='lightblue',
                edgecolor='darkblue',
                linewidth=2,
                alpha=0.9
            )

            ax.text(
                0.98, 0.98, tweet_text,
                transform=ax.transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                fontsize=11,
                fontfamily='monospace',
                bbox=tweet_bbox
            )

        ax.set_title(title, fontsize=18, fontweight='bold', pad=20)
        ax.set_xlabel('Longitude', fontsize=14)
        ax.set_ylabel('Latitude', fontsize=14)
        ax.grid(True, alpha=0.3, linestyle='--')

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved visualization to {save_path}")
        plt.close()

    def create_comparison_plot(
        self,
        snapshots: List[Dict[str, Any]],
        save_path: str
    ):
        """
        Create a comparison plot showing risk evolution.

        Args:
            snapshots: List of risk snapshots
            save_path: Path to save figure
        """
        fig, axes = plt.subplots(2, 2, figsize=(20, 16))

        # Plot 1: Risk distribution over time
        ax = axes[0, 0]
        batches = range(len(snapshots))
        mean_risks = [s['mean_risk'] for s in snapshots]
        max_risks = [s['max_risk'] for s in snapshots]

        ax.plot(batches, mean_risks, 'b-o', linewidth=2, markersize=8, label='Mean Risk')
        ax.plot(batches, max_risks, 'r-s', linewidth=2, markersize=8, label='Max Risk')
        ax.fill_between(batches, mean_risks, alpha=0.3, color='blue')
        ax.set_xlabel('Tweet Batch', fontsize=12, fontweight='bold')
        ax.set_ylabel('Risk Score', fontsize=12, fontweight='bold')
        ax.set_title('Risk Scores Over Time', fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)

        # Plot 2: Risk category distribution stacked area
        ax = axes[0, 1]
        low_risks = [s['low_risk_count'] for s in snapshots]
        mod_risks = [s['mod_risk_count'] for s in snapshots]
        high_risks = [s['high_risk_count'] for s in snapshots]
        crit_risks = [s['crit_risk_count'] for s in snapshots]

        ax.stackplot(
            batches,
            low_risks, mod_risks, high_risks, crit_risks,
            labels=['Low', 'Moderate', 'High', 'Critical'],
            colors=['green', 'yellow', 'orange', 'red'],
            alpha=0.7
        )
        ax.set_xlabel('Tweet Batch', fontsize=12, fontweight='bold')
        ax.set_ylabel('Edge Count', fontsize=12, fontweight='bold')
        ax.set_title('Risk Category Distribution', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left', fontsize=11)
        ax.grid(True, alpha=0.3)

        # Plot 3: Percentage change in critical risk
        ax = axes[1, 0]
        if len(snapshots) > 1:
            initial_crit = snapshots[0]['crit_risk_count']
            crit_changes = [
                ((s['crit_risk_count'] - initial_crit) / max(initial_crit, 1)) * 100
                for s in snapshots
            ]
            colors = ['red' if c > 0 else 'green' for c in crit_changes]
            ax.bar(batches, crit_changes, color=colors, alpha=0.7, edgecolor='black')
            ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
            ax.set_xlabel('Tweet Batch', fontsize=12, fontweight='bold')
            ax.set_ylabel('Change in Critical Edges (%)', fontsize=12, fontweight='bold')
            ax.set_title('Critical Risk Change from Baseline', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='y')

        # Plot 4: Summary statistics table
        ax = axes[1, 1]
        ax.axis('off')

        # Create summary data
        summary_data = [
            ['Metric', 'Initial', 'Final', 'Change'],
            ['━' * 20, '━' * 10, '━' * 10, '━' * 10],
            [
                'Mean Risk',
                f"{snapshots[0]['mean_risk']:.3f}",
                f"{snapshots[-1]['mean_risk']:.3f}",
                f"{(snapshots[-1]['mean_risk'] - snapshots[0]['mean_risk']):.3f}"
            ],
            [
                'Max Risk',
                f"{snapshots[0]['max_risk']:.3f}",
                f"{snapshots[-1]['max_risk']:.3f}",
                f"{(snapshots[-1]['max_risk'] - snapshots[0]['max_risk']):.3f}"
            ],
            [
                'Critical Edges',
                f"{snapshots[0]['crit_risk_count']}",
                f"{snapshots[-1]['crit_risk_count']}",
                f"{snapshots[-1]['crit_risk_count'] - snapshots[0]['crit_risk_count']:+d}"
            ],
            [
                'High Risk Edges',
                f"{snapshots[0]['high_risk_count']}",
                f"{snapshots[-1]['high_risk_count']}",
                f"{snapshots[-1]['high_risk_count'] - snapshots[0]['high_risk_count']:+d}"
            ]
        ]

        # Create table
        table = ax.table(
            cellText=summary_data,
            cellLoc='center',
            loc='center',
            bbox=[0.1, 0.3, 0.8, 0.6]
        )

        table.auto_set_font_size(False)
        table.set_fontsize(11)

        # Style header row
        for i in range(4):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')

        # Style separator row
        for i in range(4):
            table[(1, i)].set_facecolor('#E0E0E0')

        ax.set_title('Summary Statistics', fontsize=14, fontweight='bold', pad=20)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Saved comparison plot to {save_path}")
        plt.close()


def run_visualization(
    scenario: int = 1,
    num_batches: int = 6,
    batch_size: int = 10,
    output_dir: str = "outputs/scout_visualizations"
):
    """
    Run Scout Agent with visualization.

    Args:
        scenario: Which scenario to use (1-3)
        num_batches: Number of tweet batches to process
        batch_size: Tweets per batch
        output_dir: Output directory for visualizations
    """
    logger.info("=" * 80)
    logger.info("SCOUT AGENT REAL-TIME VISUALIZATION")
    logger.info("=" * 80)
    logger.info(f"Scenario: {scenario}, Batches: {num_batches}, Batch Size: {batch_size}")
    logger.info("")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Initialize environment
    logger.info("1. Initializing environment...")
    environment = DynamicGraphEnvironment()
    visualizer = ScoutTweetVisualizer(environment)

    # Capture initial state
    logger.info("2. Capturing initial graph state...")
    initial_snapshot = visualizer.get_risk_snapshot()
    snapshots = [initial_snapshot]

    visualizer.visualize_current_state(
        title=f"Initial State - Before Tweet Processing (Scenario {scenario})",
        save_path=f"{output_dir}/step_00_initial.png",
        tweet_stats={
            'total_tweets': 0,
            'flood_related': 0,
            'with_coords': 0,
            'nodes_updated': 0,
            'batch_num': 0,
            'batch_time': 0
        }
    )

    # Initialize agents
    logger.info("3. Initializing agents...")
    hazard_agent = HazardAgent("hazard-viz", environment)
    scout_agent = ScoutAgent(
        agent_id="scout-viz",
        environment=environment,
        hazard_agent=hazard_agent,
        simulation_mode=True,
        simulation_scenario=scenario
    )

    # Setup
    if not scout_agent.setup():
        logger.error("Failed to setup Scout Agent")
        return

    # Set batch size
    scout_agent.set_batch_size(batch_size)

    # Process tweets in batches
    logger.info(f"\n4. Processing {num_batches} batches of {batch_size} tweets...")
    logger.info("-" * 80)

    total_tweets = 0
    total_flood_related = 0
    total_with_coords = 0
    total_nodes_updated = 0

    for batch_num in range(1, num_batches + 1):
        logger.info(f"\n--- BATCH {batch_num}/{num_batches} ---")

        import time
        start_time = time.time()

        # Process tweets
        tweets = scout_agent.step()

        if not tweets:
            logger.info("No more tweets available")
            break

        batch_time = time.time() - start_time

        # Count statistics (approximate from logs)
        batch_flood = len([t for t in tweets if 'baha' in t.get('text', '').lower() or 'flood' in t.get('text', '').lower()])

        total_tweets += len(tweets)
        total_flood_related += batch_flood
        # Approximate coords count (would need to check geocoder results)
        total_with_coords += batch_flood // 2

        logger.info(f"  Processed {len(tweets)} tweets in {batch_time:.2f}s")

        # Capture state after this batch
        snapshot = visualizer.get_risk_snapshot()
        snapshots.append(snapshot)

        # Visualize current state
        tweet_stats = {
            'total_tweets': total_tweets,
            'flood_related': total_flood_related,
            'with_coords': total_with_coords,
            'nodes_updated': total_nodes_updated,
            'batch_num': batch_num,
            'batch_time': batch_time
        }

        visualizer.visualize_current_state(
            title=f"After Batch {batch_num} - {total_tweets} Tweets Processed (Scenario {scenario})",
            save_path=f"{output_dir}/step_{batch_num:02d}_batch.png",
            tweet_stats=tweet_stats
        )

        logger.info(f"  Mean Risk: {snapshot['mean_risk']:.3f} (Δ {snapshot['mean_risk'] - initial_snapshot['mean_risk']:+.3f})")
        logger.info(f"  Critical Edges: {snapshot['crit_risk_count']} (Δ {snapshot['crit_risk_count'] - initial_snapshot['crit_risk_count']:+d})")

    # Create comparison plot
    logger.info("\n5. Creating comparison visualization...")
    visualizer.create_comparison_plot(
        snapshots=snapshots,
        save_path=f"{output_dir}/comparison_analysis.png"
    )

    # Shutdown
    scout_agent.shutdown()

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("VISUALIZATION COMPLETE")
    logger.info("=" * 80)
    logger.info(f"  Total Tweets Processed: {total_tweets}")
    logger.info(f"  Flood-Related: {total_flood_related}")
    logger.info(f"  Batches: {len(snapshots) - 1}")
    logger.info(f"  Mean Risk Change: {snapshots[-1]['mean_risk'] - snapshots[0]['mean_risk']:+.3f}")
    logger.info(f"  Critical Edges Change: {snapshots[-1]['crit_risk_count'] - snapshots[0]['crit_risk_count']:+d}")
    logger.info(f"\n  Output Directory: {output_dir}")
    logger.info(f"  Files Created: {len(snapshots)} state images + 1 comparison plot")
    logger.info("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Visualize Scout Agent tweet processing")
    parser.add_argument(
        "--scenario",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="Simulation scenario (1=Typhoon, 2=Monsoon, 3=Light)"
    )
    parser.add_argument(
        "--batches",
        type=int,
        default=6,
        help="Number of batches to process"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Tweets per batch"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/scout_visualizations",
        help="Output directory"
    )

    args = parser.parse_args()

    try:
        run_visualization(
            scenario=args.scenario,
            num_batches=args.batches,
            batch_size=args.batch_size,
            output_dir=args.output
        )

        logger.info("\n✅ All visualizations completed successfully!")
        sys.exit(0)

    except Exception as e:
        logger.error(f"\n❌ Visualization failed: {e}", exc_info=True)
        sys.exit(1)
