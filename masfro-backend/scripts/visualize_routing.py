#!/usr/bin/env python3
"""
Graph Routing Visualization Tool

Visualizes the road network graph with risk scores and routing results.
Allows testing of the routing agent with different flood scenarios.

Features:
- Risk score heatmap visualization
- Route overlay on graph
- Multiple scenario testing
- Interactive testing mode

Usage:
    python scripts/visualize_routing.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle
import networkx as nx
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

# Import MAS-FRO components
from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.hazard_agent import HazardAgent
from app.agents.routing_agent import RoutingAgent
from app.agents.flood_agent import FloodAgent


class GraphVisualizer:
    """Visualizes road network graph with risk scores and routes."""

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

        print(f"Initialized visualizer with {self.graph.number_of_nodes()} nodes "
              f"and {self.graph.number_of_edges()} edges")

    def visualize_risk_scores(
        self,
        scenario: str = "default",
        save_path: Optional[str] = None,
        show_plot: bool = True
    ):
        """
        Visualize graph with risk scores as edge colors.

        Args:
            scenario: Scenario name for title
            save_path: Path to save figure (optional)
            show_plot: Whether to display plot
        """
        fig, ax = plt.subplots(figsize=(16, 12))

        # Extract edge risk scores
        edge_risks = {}
        for u, v, key, data in self.graph.edges(keys=True, data=True):
            risk = data.get('risk_score', 0.0)
            edge_risks[(u, v, key)] = risk

        if not edge_risks:
            print("No edge risk scores found!")
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
        sample_size = min(1000, len(self.pos))
        sampled_nodes = list(self.pos.keys())[:sample_size]

        # Draw network
        nx.draw_networkx_edges(
            self.graph,
            self.pos,
            edgelist=[(e[0], e[1]) for e in edges if e[0] in sampled_nodes and e[1] in sampled_nodes],
            edge_color=[edge_colors[i] for i, e in enumerate(edges) if e[0] in sampled_nodes and e[1] in sampled_nodes],
            width=0.5,
            alpha=0.6,
            ax=ax
        )

        # Don't draw nodes (too many)
        # Just show the edge network

        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Risk Score (0=Safe, 1=Dangerous)', fontsize=12)

        # Add risk statistics
        low_risk = np.sum(risks < 0.3)
        mod_risk = np.sum((risks >= 0.3) & (risks < 0.6))
        high_risk = np.sum((risks >= 0.6) & (risks < 0.8))
        crit_risk = np.sum(risks >= 0.8)

        stats_text = (
            f"Risk Distribution:\n"
            f"Low (<0.3): {low_risk}\n"
            f"Moderate (0.3-0.6): {mod_risk}\n"
            f"High (0.6-0.8): {high_risk}\n"
            f"Critical (≥0.8): {crit_risk}\n"
            f"Mean Risk: {risks.mean():.3f}"
        )

        ax.text(
            0.02, 0.98, stats_text,
            transform=ax.transAxes,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
            fontsize=10
        )

        ax.set_title(f'Road Network Risk Scores - {scenario}', fontsize=16, fontweight='bold')
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Saved visualization to {save_path}")

        if show_plot:
            plt.show()
        else:
            plt.close()

    def visualize_route(
        self,
        route_path: List[Tuple[float, float]],
        start: Tuple[float, float],
        end: Tuple[float, float],
        route_info: Dict[str, Any],
        scenario: str = "Route",
        save_path: Optional[str] = None,
        show_plot: bool = True
    ):
        """
        Visualize a calculated route on the graph.

        Args:
            route_path: List of (lat, lon) coordinates
            start: Start coordinates
            end: End coordinates
            route_info: Route metadata (distance, risk, etc.)
            scenario: Scenario name for title
            save_path: Path to save figure
            show_plot: Whether to display plot
        """
        fig, ax = plt.subplots(figsize=(16, 12))

        # Draw base graph (sampled)
        sample_size = min(2000, len(self.pos))
        sampled_nodes = list(self.pos.keys())[:sample_size]

        # Draw edges in gray
        nx.draw_networkx_edges(
            self.graph,
            self.pos,
            edgelist=[(u, v) for u, v, k in self.graph.edges(keys=True)
                      if u in sampled_nodes and v in sampled_nodes],
            edge_color='lightgray',
            width=0.3,
            alpha=0.3,
            ax=ax
        )

        # Draw route path
        if route_path and len(route_path) > 1:
            route_lons = [coord[1] for coord in route_path]
            route_lats = [coord[0] for coord in route_path]

            ax.plot(
                route_lons, route_lats,
                'b-',
                linewidth=3,
                alpha=0.7,
                label='Route',
                zorder=10
            )

        # Mark start and end points
        ax.scatter(
            start[1], start[0],
            c='green', s=200, marker='o',
            edgecolors='black', linewidths=2,
            label='Start', zorder=20
        )

        ax.scatter(
            end[1], end[0],
            c='red', s=200, marker='*',
            edgecolors='black', linewidths=2,
            label='End', zorder=20
        )

        # Add route info box
        info_text = (
            f"Route Information:\n"
            f"Distance: {route_info.get('distance', 0)/1000:.2f} km\n"
            f"Est. Time: {route_info.get('estimated_time', 0):.1f} min\n"
            f"Avg Risk: {route_info.get('risk_level', 0):.3f}\n"
            f"Max Risk: {route_info.get('max_risk', 0):.3f}\n"
            f"Segments: {route_info.get('num_segments', 0)}"
        )

        ax.text(
            0.02, 0.98, info_text,
            transform=ax.transAxes,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
            fontsize=11
        )

        # Add warnings if any
        warnings = route_info.get('warnings', [])
        if warnings:
            warning_text = "WARNINGS:\n" + "\n".join(f"- {w}" for w in warnings[:3])
            ax.text(
                0.98, 0.98, warning_text,
                transform=ax.transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8),
                fontsize=10
            )

        ax.set_title(f'Calculated Route - {scenario}', fontsize=16, fontweight='bold')
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.legend(loc='lower right', fontsize=11)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Saved route visualization to {save_path}")

        if show_plot:
            plt.show()
        else:
            plt.close()


def test_routing_scenarios():
    """Test routing agent with different flood scenarios."""

    print("=" * 70)
    print("MAS-FRO Routing Visualization & Testing Tool")
    print("=" * 70)
    print()

    # Initialize environment
    print("Loading graph environment...")
    environment = DynamicGraphEnvironment()

    if not environment.graph:
        print("[ERROR] Failed to load graph!")
        return

    print(f"[OK] Graph loaded: {environment.graph.number_of_nodes()} nodes, "
          f"{environment.graph.number_of_edges()} edges")
    print()

    # Initialize agents
    print("Initializing agents...")
    hazard_agent = HazardAgent("hazard_viz_001", environment)
    flood_agent = FloodAgent(
        "flood_viz_001",
        environment,
        hazard_agent=hazard_agent,
        use_simulated=True,  # Use simulated for testing
        use_real_apis=False
    )
    routing_agent = RoutingAgent("routing_viz_001", environment)

    print("[OK] Agents initialized")
    print()

    # Create visualizer
    visualizer = GraphVisualizer(environment)

    # Test coordinates (Marikina City area)
    test_points = {
        "Marikina City Hall": (14.6507, 121.1029),
        "Marikina Sports Center": (14.6354, 121.1084),
        "SM City Marikina": (14.6303, 121.1084),
        "Loyola Grand Villas": (14.6423, 121.0891)
    }

    print("Test locations:")
    for name, coords in test_points.items():
        print(f"  - {name}: {coords}")
    print()

    # Scenario 1: Default scenario (no flood data)
    print("=" * 70)
    print("SCENARIO 1: Default Graph (No Flood Data)")
    print("=" * 70)

    visualizer.visualize_risk_scores(
        scenario="Default (No Flooding)",
        save_path="outputs/viz_scenario_1_default.png",
        show_plot=False
    )

    # Test route
    start = test_points["Marikina City Hall"]
    end = test_points["SM City Marikina"]

    print(f"\nCalculating route: {start} -> {end}")
    route_result = routing_agent.calculate_route(start, end)

    visualizer.visualize_route(
        route_result['path'],
        start, end,
        route_result,
        scenario="Default (No Flooding)",
        save_path="outputs/viz_route_1_default.png",
        show_plot=False
    )

    print(f"[OK] Route calculated:")
    print(f"   Distance: {route_result['distance']/1000:.2f} km")
    print(f"   Risk: {route_result['risk_level']:.3f}")
    print()

    # Scenario 2: Light flooding (rr01, step 1)
    print("=" * 70)
    print("SCENARIO 2: Light Flooding (2-year return, 1 hour)")
    print("=" * 70)

    hazard_agent.set_flood_scenario("rr01", 1)

    # Trigger data collection and update
    print("Collecting flood data and updating graph...")
    flood_data = flood_agent.collect_and_forward_data()

    # Process the update
    result = hazard_agent.process_and_update()
    print(f"[OK] Graph updated: {result.get('edges_updated', 0)} edges")
    print()

    visualizer.visualize_risk_scores(
        scenario="Light Flooding (RR01, Step 1)",
        save_path="outputs/viz_scenario_2_light.png",
        show_plot=False
    )

    route_result = routing_agent.calculate_route(start, end)

    visualizer.visualize_route(
        route_result['path'],
        start, end,
        route_result,
        scenario="Light Flooding (RR01, Step 1)",
        save_path="outputs/viz_route_2_light.png",
        show_plot=False
    )

    print(f"[OK] Route calculated:")
    print(f"   Distance: {route_result['distance']/1000:.2f} km")
    print(f"   Risk: {route_result['risk_level']:.3f}")
    print()

    # Scenario 3: Severe flooding (rr04, step 12)
    print("=" * 70)
    print("SCENARIO 3: Severe Flooding (25-year return, 12 hours)")
    print("=" * 70)

    hazard_agent.set_flood_scenario("rr04", 12)

    print("Updating graph with severe flood scenario...")
    flood_data = flood_agent.collect_and_forward_data()
    result = hazard_agent.process_and_update()
    print(f"[OK] Graph updated: {result.get('edges_updated', 0)} edges")
    print()

    visualizer.visualize_risk_scores(
        scenario="Severe Flooding (RR04, Step 12)",
        save_path="outputs/viz_scenario_3_severe.png",
        show_plot=False
    )

    route_result = routing_agent.calculate_route(start, end)

    visualizer.visualize_route(
        route_result['path'],
        start, end,
        route_result,
        scenario="Severe Flooding (RR04, Step 12)",
        save_path="outputs/viz_route_3_severe.png",
        show_plot=False
    )

    print(f"[OK] Route calculated:")
    print(f"   Distance: {route_result['distance']/1000:.2f} km")
    print(f"   Risk: {route_result['risk_level']:.3f}")

    if route_result.get('warnings'):
        print(f"   Warnings: {', '.join(route_result['warnings'])}")
    print()

    print("=" * 70)
    print("[SUCCESS] All scenarios completed!")
    print("=" * 70)
    print()
    print("Visualizations saved to outputs/")
    print()
    print("Files created:")
    print("  - viz_scenario_1_default.png - Risk scores (no flooding)")
    print("  - viz_route_1_default.png - Route (no flooding)")
    print("  - viz_scenario_2_light.png - Risk scores (light flooding)")
    print("  - viz_route_2_light.png - Route (light flooding)")
    print("  - viz_scenario_3_severe.png - Risk scores (severe flooding)")
    print("  - viz_route_3_severe.png - Route (severe flooding)")


if __name__ == "__main__":
    # Create outputs directory
    os.makedirs("outputs", exist_ok=True)

    try:
        test_routing_scenarios()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
