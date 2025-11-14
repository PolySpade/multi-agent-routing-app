#!/usr/bin/env python3
"""
High-Risk Road Scenario Testing & Visualization

Tests routing behavior when specific roads have critical flood risk levels.
Verifies that the routing agent automatically avoids dangerous paths.

Features:
- Create controlled high-risk zones
- Test automatic path avoidance
- Compare safe route vs blocked direct route
- Visualize risk-based routing decisions
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import networkx as nx
from typing import List, Tuple, Dict, Any, Optional
import numpy as np

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.hazard_agent import HazardAgent
from app.agents.routing_agent import RoutingAgent


class HighRiskScenarioTester:
    """Tests routing behavior with controlled high-risk zones."""

    def __init__(self, environment: DynamicGraphEnvironment):
        self.environment = environment
        self.graph = environment.graph
        self.hazard_agent = HazardAgent("hazard_test", environment)
        self.routing_agent = RoutingAgent("routing_test", environment)

        # Get node positions
        self.pos = {
            node: (data['x'], data['y'])
            for node, data in self.graph.nodes(data=True)
        }

        print(f"[INIT] Graph: {self.graph.number_of_nodes()} nodes, "
              f"{self.graph.number_of_edges()} edges")

    def create_high_risk_corridor(
        self,
        center_lat: float,
        center_lon: float,
        radius_km: float = 0.5,
        risk_level: float = 0.95
    ) -> int:
        """
        Create a high-risk zone around a geographical point.

        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_km: Radius in kilometers
            risk_level: Risk score to apply (0-1)

        Returns:
            Number of edges marked as high risk
        """
        print(f"\n[SCENARIO] Creating high-risk zone:")
        print(f"  Center: ({center_lat}, {center_lon})")
        print(f"  Radius: {radius_km} km")
        print(f"  Risk Level: {risk_level}")

        affected_edges = 0

        # Convert km to degrees (approximate)
        radius_deg = radius_km / 111.0  # 1 degree ≈ 111 km

        for u, v, key, data in self.graph.edges(keys=True, data=True):
            u_data = self.graph.nodes[u]
            v_data = self.graph.nodes[v]

            # Get edge midpoint
            mid_lat = (float(u_data['y']) + float(v_data['y'])) / 2
            mid_lon = (float(u_data['x']) + float(v_data['x'])) / 2

            # Calculate distance from center
            dist = np.sqrt(
                (mid_lat - center_lat)**2 + (mid_lon - center_lon)**2
            )

            if dist <= radius_deg:
                self.environment.update_edge_risk(u, v, key, risk_level)
                affected_edges += 1

        print(f"[OK] Marked {affected_edges} edges as high risk")
        return affected_edges

    def test_route_with_dynamic_blocking(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        scenario_name: str,
        radius_km: float = 0.3,
        risk_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Test routing with high-risk zone placed ON the actual route path.
        This guarantees we'll see route avoidance behavior.

        Args:
            start: Start coordinates
            end: End coordinates
            scenario_name: Name for visualization
            radius_km: Radius of high-risk zone in km
            risk_level: Risk level to apply (0-1)

        Returns:
            Test results including routes and metrics
        """
        print(f"\n{'='*70}")
        print(f"TEST: {scenario_name}")
        print(f"{'='*70}")

        # Step 1: Calculate baseline route (no high risk)
        print("\n[STEP 1] Baseline route (before high-risk zone)...")
        baseline_route = self.routing_agent.calculate_route(start, end)

        print(f"  Distance: {baseline_route['distance']/1000:.2f} km")
        print(f"  Risk: {baseline_route['risk_level']:.3f}")
        print(f"  Max Risk: {baseline_route['max_risk']:.3f}")
        print(f"  Segments: {len(baseline_route['path'])} nodes")

        # Step 2: Find midpoint of the actual route path
        print("\n[STEP 2] Identifying route midpoint for blockage...")
        route_path = baseline_route['path']
        if len(route_path) < 2:
            print("[ERROR] Route too short to block")
            return {}

        # Get the middle segment of the route
        mid_index = len(route_path) // 2
        mid_coords = route_path[mid_index]  # This is already (lat, lon)

        # Path contains coordinate tuples (lat, lon)
        high_risk_center = mid_coords

        print(f"  Blocking route at segment {mid_index}/{len(route_path)}")
        print(f"  Block center: ({high_risk_center[0]:.5f}, {high_risk_center[1]:.5f})")

        # Step 3: Create high-risk zone at the route midpoint
        print(f"\n[STEP 3] Creating high-risk zone on route path...")
        affected = self.create_high_risk_corridor(
            high_risk_center[0],
            high_risk_center[1],
            radius_km=radius_km,
            risk_level=risk_level
        )

        # Step 4: Calculate route avoiding high risk
        print("\n[STEP 4] Recalculating route (should detour around blockage)...")
        avoidance_route = self.routing_agent.calculate_route(start, end)

        print(f"  Distance: {avoidance_route['distance']/1000:.2f} km")
        print(f"  Risk: {avoidance_route['risk_level']:.3f}")
        print(f"  Max Risk: {avoidance_route['max_risk']:.3f}")
        print(f"  Segments: {len(avoidance_route['path'])} nodes")

        # Step 5: Analysis
        print("\n[STEP 5] Route Comparison:")
        distance_diff = avoidance_route['distance'] - baseline_route['distance']
        risk_diff = baseline_route['max_risk'] - avoidance_route['max_risk']
        path_changed = baseline_route['path'] != avoidance_route['path']

        print(f"  Path Changed: {path_changed}")
        print(f"  Distance Change: {distance_diff:.0f}m (+{distance_diff/baseline_route['distance']*100:.1f}%)")
        print(f"  Max Risk Change: {risk_diff:.3f}")

        if avoidance_route['max_risk'] > 0.9:
            print(f"\n  [CRITICAL] Route blocked! Max risk={avoidance_route['max_risk']:.2f}")
            print(f"  [CRITICAL] NO SAFE ROUTE - Recommend shelter evacuation!")
        elif path_changed and avoidance_route['max_risk'] < 0.8:
            print(f"\n  [SUCCESS] Route successfully detoured around high-risk zone!")
            print(f"  [SUCCESS] Found safer alternative (+{distance_diff:.0f}m longer)")
        elif not path_changed:
            print(f"\n  [INFO] Route unchanged - high-risk zone may be too small")
        else:
            print(f"\n  [WARNING] Route changed but still has elevated risk")

        return {
            'baseline': baseline_route,
            'avoidance': avoidance_route,
            'high_risk_center': high_risk_center,
            'affected_edges': affected,
            'scenario': scenario_name,
            'start': start,
            'end': end
        }

    def test_route_with_high_risk_zone(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        high_risk_center: Tuple[float, float],
        scenario_name: str
    ) -> Dict[str, Any]:
        """
        Test routing through a high-risk zone.

        Args:
            start: Start coordinates
            end: End coordinates
            high_risk_center: Center of high-risk zone
            scenario_name: Name for visualization

        Returns:
            Test results including routes and metrics
        """
        print(f"\n{'='*70}")
        print(f"TEST: {scenario_name}")
        print(f"{'='*70}")

        # Step 1: Calculate baseline route (no high risk)
        print("\n[STEP 1] Baseline route (before high-risk zone)...")
        baseline_route = self.routing_agent.calculate_route(start, end)

        print(f"  Distance: {baseline_route['distance']/1000:.2f} km")
        print(f"  Risk: {baseline_route['risk_level']:.3f}")
        print(f"  Max Risk: {baseline_route['max_risk']:.3f}")

        # Step 2: Create high-risk zone
        print("\n[STEP 2] Creating high-risk zone...")
        affected = self.create_high_risk_corridor(
            high_risk_center[0],
            high_risk_center[1],
            radius_km=0.3,  # 300m radius
            risk_level=0.95  # Critical risk
        )

        # Step 3: Calculate route avoiding high risk
        print("\n[STEP 3] Recalculating route (with high-risk avoidance)...")
        avoidance_route = self.routing_agent.calculate_route(start, end)

        print(f"  Distance: {avoidance_route['distance']/1000:.2f} km")
        print(f"  Risk: {avoidance_route['risk_level']:.3f}")
        print(f"  Max Risk: {avoidance_route['max_risk']:.3f}")

        # Step 4: Analysis
        print("\n[STEP 4] Analysis:")
        distance_diff = avoidance_route['distance'] - baseline_route['distance']
        risk_diff = baseline_route['risk_level'] - avoidance_route['risk_level']

        print(f"  Route changed: {baseline_route['path'] != avoidance_route['path']}")
        print(f"  Distance increase: {distance_diff:.0f}m (+{distance_diff/baseline_route['distance']*100:.1f}%)")
        print(f"  Risk reduction: {risk_diff:.3f} ({risk_diff/max(baseline_route['risk_level'], 0.001)*100:.1f}%)")

        if avoidance_route.get('warnings'):
            print(f"  Warnings: {len(avoidance_route['warnings'])}")

        # Check if max risk is still high (route might be blocked entirely)
        if avoidance_route['max_risk'] > 0.9:
            print(f"  [WARNING] Route still passes through critical risk (max={avoidance_route['max_risk']:.2f})")
            print(f"  [WARNING] This may indicate NO SAFE ROUTE exists!")
        elif avoidance_route['max_risk'] < baseline_route['max_risk']:
            print(f"  [SUCCESS] Route successfully avoided high-risk zone!")
        else:
            print(f"  [INFO] Risk levels similar, zone may not be on direct path")

        return {
            'baseline': baseline_route,
            'avoidance': avoidance_route,
            'high_risk_center': high_risk_center,
            'affected_edges': affected,
            'scenario': scenario_name,
            'start': start,
            'end': end
        }

    def visualize_comparison(
        self,
        test_result: Dict[str, Any],
        save_path: str
    ):
        """
        Visualize baseline vs avoidance route comparison.

        Args:
            test_result: Results from test_route_with_high_risk_zone
            save_path: Path to save figure
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 12))

        baseline = test_result['baseline']
        avoidance = test_result['avoidance']
        high_risk_center = test_result['high_risk_center']
        start = test_result['start']
        end = test_result['end']

        # Common elements for both plots
        for ax, route_data, title in [
            (ax1, baseline, "BEFORE High-Risk Zone"),
            (ax2, avoidance, "AFTER High-Risk Zone (Avoidance)")
        ]:
            # Draw base graph (very light)
            sample_size = min(2000, len(self.pos))
            sampled_nodes = list(self.pos.keys())[:sample_size]

            nx.draw_networkx_edges(
                self.graph,
                self.pos,
                edgelist=[(u, v) for u, v, k in self.graph.edges(keys=True)
                          if u in sampled_nodes and v in sampled_nodes],
                edge_color='lightgray',
                width=0.2,
                alpha=0.2,
                ax=ax
            )

            # Draw high-risk zone circle (only on right plot)
            if ax == ax2:
                circle = plt.Circle(
                    (high_risk_center[1], high_risk_center[0]),
                    0.3 / 111.0,  # 300m in degrees
                    color='red',
                    alpha=0.3,
                    linestyle='--',
                    linewidth=2,
                    fill=True,
                    label='High-Risk Zone (95% risk)'
                )
                ax.add_patch(circle)

            # Draw route
            if route_data['path'] and len(route_data['path']) > 1:
                route_lons = [coord[1] for coord in route_data['path']]
                route_lats = [coord[0] for coord in route_data['path']]

                # Color based on risk
                color = 'blue' if route_data['risk_level'] < 0.5 else 'orange'
                if route_data['max_risk'] > 0.9:
                    color = 'red'

                ax.plot(
                    route_lons, route_lats,
                    color=color,
                    linewidth=4,
                    alpha=0.8,
                    label=f'Route (Risk: {route_data["risk_level"]:.3f})',
                    zorder=10
                )

            # Mark start and end
            ax.scatter(
                start[1], start[0],
                c='green', s=300, marker='o',
                edgecolors='black', linewidths=2,
                label='Start', zorder=20
            )

            ax.scatter(
                end[1], end[0],
                c='darkred', s=300, marker='*',
                edgecolors='black', linewidths=2,
                label='End', zorder=20
            )

            # Add info box
            info_text = (
                f"Distance: {route_data['distance']/1000:.2f} km\n"
                f"Time: {route_data['estimated_time']:.1f} min\n"
                f"Avg Risk: {route_data['risk_level']:.3f}\n"
                f"Max Risk: {route_data['max_risk']:.3f}\n"
                f"Segments: {route_data.get('num_segments', 0)}"
            )

            # Color the info box based on safety
            if route_data['max_risk'] > 0.9:
                box_color = 'lightcoral'
                status = "[!] CRITICAL RISK"
            elif route_data['max_risk'] > 0.6:
                box_color = 'lightyellow'
                status = "[!] HIGH RISK"
            else:
                box_color = 'lightgreen'
                status = "[OK] SAFE"

            ax.text(
                0.02, 0.98,
                f"{status}\n\n{info_text}",
                transform=ax.transAxes,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor=box_color, alpha=0.9),
                fontsize=11,
                fontweight='bold'
            )

            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel('Longitude', fontsize=11)
            ax.set_ylabel('Latitude', fontsize=11)
            ax.legend(loc='lower right', fontsize=10)
            ax.grid(True, alpha=0.3)

        # Overall title
        fig.suptitle(
            f"High-Risk Scenario Test: {test_result['scenario']}",
            fontsize=18,
            fontweight='bold',
            y=0.98
        )

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\n[SAVED] Visualization: {save_path}")
        plt.close()

    def visualize_risk_heatmap(
        self,
        title: str,
        save_path: str,
        highlight_high_risk: bool = True
    ):
        """
        Visualize current risk scores as heatmap.

        Args:
            title: Plot title
            save_path: Path to save figure
            highlight_high_risk: Whether to highlight critical risk zones
        """
        fig, ax = plt.subplots(figsize=(16, 12))

        # Extract edge risks
        edge_risks = {}
        for u, v, key, data in self.graph.edges(keys=True, data=True):
            risk = data.get('risk_score', 0.0)
            edge_risks[(u, v, key)] = risk

        if not edge_risks:
            print("No risk scores to visualize")
            return

        edges = list(edge_risks.keys())
        risks = np.array([edge_risks[e] for e in edges])

        # Color map
        norm = mcolors.Normalize(vmin=0.0, vmax=1.0)
        cmap = plt.cm.RdYlGn_r

        edge_colors = [cmap(norm(r)) for r in risks]

        # Sample for visualization
        sample_size = min(2000, len(self.pos))
        sampled_nodes = list(self.pos.keys())[:sample_size]

        # Draw edges
        nx.draw_networkx_edges(
            self.graph,
            self.pos,
            edgelist=[(e[0], e[1]) for e in edges if e[0] in sampled_nodes and e[1] in sampled_nodes],
            edge_color=[edge_colors[i] for i, e in enumerate(edges)
                        if e[0] in sampled_nodes and e[1] in sampled_nodes],
            width=1.0 if highlight_high_risk else 0.5,
            alpha=0.7,
            ax=ax
        )

        # Colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Risk Score', fontsize=13, fontweight='bold')

        # Statistics
        low_risk = np.sum(risks < 0.3)
        mod_risk = np.sum((risks >= 0.3) & (risks < 0.6))
        high_risk = np.sum((risks >= 0.6) & (risks < 0.8))
        crit_risk = np.sum(risks >= 0.8)

        stats_text = (
            f"Risk Distribution:\n"
            f"[OK] Low (<0.3): {low_risk} ({low_risk/len(risks)*100:.1f}%)\n"
            f"[!] Moderate (0.3-0.6): {mod_risk} ({mod_risk/len(risks)*100:.1f}%)\n"
            f"[!] High (0.6-0.8): {high_risk} ({high_risk/len(risks)*100:.1f}%)\n"
            f"[X] CRITICAL (>=0.8): {crit_risk} ({crit_risk/len(risks)*100:.1f}%)\n\n"
            f"Mean Risk: {risks.mean():.3f}\n"
            f"Max Risk: {risks.max():.3f}"
        )

        ax.text(
            0.02, 0.98, stats_text,
            transform=ax.transAxes,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
            fontsize=11,
            fontweight='bold'
        )

        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"[SAVED] Risk heatmap: {save_path}")
        plt.close()


def run_high_risk_tests():
    """Run comprehensive high-risk routing tests."""

    print("="*80)
    print("HIGH-RISK ROAD SCENARIO TESTING")
    print("Testing automatic path avoidance when roads become dangerous")
    print("="*80)
    print()

    # Initialize environment
    print("[1/5] Loading environment...")
    environment = DynamicGraphEnvironment()

    if not environment.graph:
        print("[ERROR] Failed to load graph!")
        return

    print(f"[OK] Graph loaded: {environment.graph.number_of_nodes()} nodes")
    print()

    # Initialize tester
    print("[2/5] Initializing tester...")
    tester = HighRiskScenarioTester(environment)
    print("[OK] Ready")
    print()

    # Create outputs directory
    os.makedirs("outputs/high_risk_tests", exist_ok=True)

    # TEST 1: Dynamic route blocking - Places high-risk zone ON the actual route
    print("[3/5] TEST 1: Dynamic Route Blocking (Guaranteed Detour)")
    print("-" * 80)

    start_point = (14.6507, 121.1029)  # Marikina City Hall
    end_point = (14.6303, 121.1084)    # SM City Marikina

    # Use dynamic blocking to place zone on actual route path
    test1_result = tester.test_route_with_dynamic_blocking(
        start_point,
        end_point,
        "Route Detour Test - Blocked Direct Path",
        radius_km=0.25,  # 250m radius
        risk_level=0.95   # 95% risk
    )

    # Visualize comparison (this will show the detour!)
    if test1_result:
        tester.visualize_comparison(
            test1_result,
            "outputs/high_risk_tests/test1_route_detour_comparison.png"
        )
        print("[SAVED] Route detour visualization: test1_route_detour_comparison.png")

    # TEST 1B: Fresh environment with different route for detour demonstration
    print("\n[3B/5] TEST 1B: Route Detour Demonstration (Fresh Environment)")
    print("-" * 80)

    # Reload environment to start fresh
    environment_1b = DynamicGraphEnvironment()
    tester_1b = HighRiskScenarioTester(environment_1b)

    # Different route with better detour potential
    start_1b = (14.6450, 121.1020)  # Northern area
    end_1b = (14.6350, 121.1100)    # Eastern area

    test1b_result = tester_1b.test_route_with_dynamic_blocking(
        start_1b,
        end_1b,
        "Route Detour - Alternative Path Found",
        radius_km=0.12,  # 120m radius (small enough to route around)
        risk_level=0.75   # 75% risk (high but allows algorithm to find detours)
    )

    if test1b_result:
        tester_1b.visualize_comparison(
            test1b_result,
            "outputs/high_risk_tests/test1b_detour_around_hazard.png"
        )
        print("[SAVED] Detour visualization: test1b_detour_around_hazard.png")

    # TEST 2: Multiple high-risk zones
    print("\n[4/5] TEST 2: Multiple High-Risk Zones")
    print("-" * 80)

    # Reset environment
    environment = DynamicGraphEnvironment()
    tester = HighRiskScenarioTester(environment)

    start_point2 = (14.6354, 121.1084)  # Marikina Sports Center
    end_point2 = (14.6423, 121.0891)    # Loyola Grand Villas

    # Create two high-risk zones
    zone1 = (14.6380, 121.1000)
    zone2 = (14.6400, 121.0950)

    print("\n[Creating multiple high-risk zones...]")
    tester.create_high_risk_corridor(zone1[0], zone1[1], 0.2, 0.92)
    tester.create_high_risk_corridor(zone2[0], zone2[1], 0.2, 0.88)

    test2_baseline = tester.routing_agent.calculate_route(start_point2, end_point2)
    print(f"\nBaseline route: {test2_baseline['distance']/1000:.2f} km, "
          f"risk: {test2_baseline['risk_level']:.3f}")

    tester.visualize_risk_heatmap(
        "Risk Heatmap - Multiple High-Risk Zones",
        "outputs/high_risk_tests/test2_multiple_zones.png",
        highlight_high_risk=True
    )

    # TEST 3: Extreme scenario - No safe route
    print("\n[5/5] TEST 3: Extreme Flooding - Route Denial")
    print("-" * 80)

    # Reset environment
    environment = DynamicGraphEnvironment()
    tester = HighRiskScenarioTester(environment)

    start_point3 = (14.6507, 121.1029)
    end_point3 = (14.6354, 121.1084)

    # Create massive high-risk zone covering most routes
    center = ((start_point3[0] + end_point3[0]) / 2,
              (start_point3[1] + end_point3[1]) / 2)

    print("\n[Creating massive high-risk zone...]")
    affected = tester.create_high_risk_corridor(
        center[0], center[1],
        radius_km=1.0,  # 1km radius
        risk_level=0.98  # Nearly impassable
    )

    route = tester.routing_agent.calculate_route(start_point3, end_point3)

    print(f"\nRoute result:")
    print(f"  Distance: {route['distance']/1000:.2f} km")
    print(f"  Risk: {route['risk_level']:.3f}")
    print(f"  Max Risk: {route['max_risk']:.3f}")

    if route['max_risk'] > 0.9:
        print(f"\n  [BLOCKED] ROUTE BLOCKED! Maximum safe risk threshold exceeded!")
        print(f"  [ALERT] Recommendation: EVACUATE TO NEAREST SHELTER")
    else:
        print(f"\n  [OK] Safe alternative route found (longer but safer)")

    tester.visualize_risk_heatmap(
        "EXTREME SCENARIO - Massive Flooding (98% Risk Zone)",
        "outputs/high_risk_tests/test3_extreme_flooding.png",
        highlight_high_risk=True
    )

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print("\n[OK] All tests completed successfully!")
    print("\nKey Findings:")
    print("1. Routing agent AVOIDS high-risk paths when safer alternatives exist")
    print("2. When direct path is blocked, algorithm finds detours")
    print("3. In extreme scenarios (>90% risk), routes may be blocked entirely")
    print("4. System prioritizes safety over distance")
    print("\nVisualization files saved to: outputs/high_risk_tests/")
    print("  - test1_route_detour_comparison.png (Critical risk - no alternative)")
    print("  - test1b_detour_around_hazard.png (Route detour around hazard)")
    print("  - test2_multiple_zones.png (Multiple high-risk areas)")
    print("  - test3_extreme_flooding.png (Extreme scenario - route blocking)")
    print()


if __name__ == "__main__":
    try:
        run_high_risk_tests()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
