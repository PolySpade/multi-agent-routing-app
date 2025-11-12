#!/usr/bin/env python3
"""
Test Routing Algorithm with Severe Flood Conditions

This script tests the risk-aware A* routing algorithm under extreme flood conditions:
- Flood Scenario: RR04 (10-year flood), Time Step 18 (hour 18)
- This represents the most severe flooding scenario with 54.9% of roads flooded
- Max risk score: 0.491, Mean risk: 0.073

Test Route:
- Start: 14.6559°N, 121.0922°E
- Destination: 14.6553°N, 121.0990°E
- Expected: Route should avoid high-risk flooded roads
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.hazard_agent import HazardAgent
from app.agents.routing_agent import RoutingAgent
from typing import Dict, Any
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime


class FloodRoutingTester:
    """Test routing algorithm under severe flood conditions."""

    def __init__(self):
        """Initialize test environment."""
        print("="*80)
        print("ROUTING ALGORITHM FLOOD TEST")
        print("Scenario: RR04 (10-Year Flood), Hour 18 - Most Severe Conditions")
        print("="*80)

        # Initialize environment
        print("\n[INIT] Loading road network...")
        self.env = DynamicGraphEnvironment()
        if self.env.graph is None:
            raise RuntimeError("Failed to load graph!")

        print(f"  [OK] Graph loaded: {self.env.graph.number_of_nodes()} nodes, "
              f"{self.env.graph.number_of_edges()} edges")

        # Initialize agents
        print("\n[INIT] Initializing agents...")
        self.hazard_agent = HazardAgent(
            agent_id="hazard_test",
            environment=self.env
        )

        self.routing_agent = RoutingAgent(
            agent_id="routing_test",
            environment=self.env
        )

        print("  [OK] Agents initialized")

        # Output directory
        self.output_dir = Path(__file__).parent.parent / "outputs" / "routing_tests"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def setup_flood_scenario(self, return_period: str = "rr04", time_step: int = 18):
        """
        Configure severe flood scenario and update graph.

        Args:
            return_period: Flood return period (default: rr04 - 10-year flood)
            time_step: Time step (default: 18 - hour 18, peak flooding)
        """
        print(f"\n[FLOOD] Setting up flood scenario: {return_period.upper()}, Step {time_step}")

        # Configure flood scenario
        self.hazard_agent.set_flood_scenario(
            return_period=return_period,
            time_step=time_step
        )

        # Calculate risk scores
        fused_data = {
            "system_wide": {
                "risk_level": 0.0,
                "source": "routing_test"
            }
        }

        risk_scores = self.hazard_agent.calculate_risk_scores(fused_data)

        if not risk_scores:
            print("  [WARNING] No risk scores calculated!")
            return

        print(f"  [OK] Calculated {len(risk_scores)} risk scores")

        # Update graph with risk scores
        self.hazard_agent.update_environment(risk_scores)

        # Get statistics
        risks = list(risk_scores.values())
        flooded_count = sum(1 for r in risks if r > 0.001)

        print(f"  [OK] Flooded edges: {flooded_count}/{len(risks)} ({flooded_count/len(risks)*100:.1f}%)")
        print(f"  [OK] Risk range: {min(risks):.3f} - {max(risks):.3f}")
        print(f"  [OK] Mean risk: {sum(risks)/len(risks):.3f}")

    def test_route(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        preferences: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Test routing algorithm with given coordinates.

        Args:
            start_lat: Starting latitude
            start_lon: Starting longitude
            end_lat: Destination latitude
            end_lon: Destination longitude
            preferences: Optional routing preferences

        Returns:
            Route result dictionary
        """
        print(f"\n[ROUTE] Testing route calculation...")
        print(f"  Start: {start_lat:.4f}°N, {start_lon:.4f}°E")
        print(f"  End: {end_lat:.4f}°N, {end_lon:.4f}°E")

        # Default preferences
        if preferences is None:
            preferences = {
                "avoid_floods": True,
                "route_type": "safest"
            }

        print(f"  Preferences: {preferences}")

        # Find route
        route_result = self.routing_agent.calculate_route(
            start=(start_lat, start_lon),
            end=(end_lat, end_lon),
            preferences=preferences
        )

        # Display results
        print(f"\n[RESULT] Route calculation complete")

        if not route_result.get("path"):
            print("  [WARNING] No route found!")
            print(f"  Warnings: {route_result.get('warnings', [])}")
            return route_result

        print(f"  [OK] Route found!")
        print(f"  Distance: {route_result['distance']:.2f} meters")
        print(f"  Estimated time: {route_result['estimated_time']:.1f} seconds ({route_result['estimated_time']/60:.1f} minutes)")
        print(f"  Risk level: {route_result['risk_level']:.3f}")
        print(f"  Max risk: {route_result['max_risk']:.3f}")
        print(f"  Path nodes: {len(route_result['path'])}")

        if route_result.get('warnings'):
            print(f"  Warnings: {route_result['warnings']}")

        return route_result

    def visualize_route(
        self,
        route_result: Dict[str, Any],
        start_coords: tuple,
        end_coords: tuple,
        output_filename: str = "flood_route_test.png"
    ):
        """
        Visualize the calculated route on the road network.

        Args:
            route_result: Route result from calculate_route()
            start_coords: (lat, lon) tuple for start
            end_coords: (lat, lon) tuple for end
            output_filename: Output filename
        """
        print(f"\n[VIZ] Creating route visualization...")

        if not route_result.get("path"):
            print("  [WARNING] No route to visualize")
            return

        fig, ax = plt.subplots(figsize=(14, 10))

        # Get route path coordinates
        route_coords = route_result["path"]  # List of (lat, lon) tuples

        # Plot all edges (colored by risk)
        for u, v, key, data in self.env.graph.edges(keys=True, data=True):
            u_lat = self.env.graph.nodes[u]['y']
            u_lon = self.env.graph.nodes[u]['x']
            v_lat = self.env.graph.nodes[v]['y']
            v_lon = self.env.graph.nodes[v]['x']
            risk = data.get('risk_score', 0.0)

            # Color by risk (route will be plotted separately on top)
            if risk < 0.001:
                color = '#CCCCCC'  # Gray (no flood)
            elif risk < 0.2:
                color = '#A8E6CF'  # Light green
            elif risk < 0.4:
                color = '#FFD700'  # Gold
            elif risk < 0.6:
                color = '#FF6B35'  # Orange (moderate)
            elif risk < 0.8:
                color = '#E63946'  # Red (high)
            else:
                color = '#990000'  # Dark red (extreme)

            linewidth = 0.5 if risk < 0.001 else 1.0
            alpha = 0.3 if risk < 0.001 else 0.6

            ax.plot([u_lon, v_lon], [u_lat, v_lat],
                   color=color, linewidth=linewidth, alpha=alpha, zorder=1)

        # Plot the route path as a thick blue line on top
        if route_coords and len(route_coords) > 1:
            route_lats = [coord[0] for coord in route_coords]
            route_lons = [coord[1] for coord in route_coords]
            ax.plot(route_lons, route_lats, color='#0066CC', linewidth=4.0,
                   alpha=0.9, zorder=10, solid_capstyle='round', solid_joinstyle='round')

        # Plot start and end points
        start_lat, start_lon = start_coords
        end_lat, end_lon = end_coords

        ax.plot(start_lon, start_lat, 'go', markersize=15,
               label='Start', zorder=20, markeredgecolor='black', markeredgewidth=2)
        ax.plot(end_lon, end_lat, 'r*', markersize=20,
               label='Destination', zorder=20, markeredgecolor='black', markeredgewidth=2)

        # Title and labels
        ax.set_title(
            f"Route Test: RR04 Hour 18 (Most Severe Flood)\n"
            f"Distance: {route_result['distance']:.0f}m | "
            f"Risk: {route_result['risk_level']:.3f} | "
            f"Time: {route_result['estimated_time']/60:.1f} min",
            fontsize=14, fontweight='bold', pad=20
        )

        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.grid(True, alpha=0.2, linestyle='--')

        # Legend
        legend_elements = [
            mpatches.Patch(color='#0066CC', label='Calculated Route'),
            mpatches.Patch(color='#CCCCCC', label='Safe (No Flood)'),
            mpatches.Patch(color='#A8E6CF', label='Minimal Risk'),
            mpatches.Patch(color='#FFD700', label='Low Risk'),
            mpatches.Patch(color='#FF6B35', label='Moderate Risk'),
            mpatches.Patch(color='#E63946', label='High Risk'),
            mpatches.Patch(color='#990000', label='Extreme Risk'),
        ]

        ax.legend(
            handles=legend_elements,
            loc='upper right',
            fontsize=9,
            framealpha=0.95,
            edgecolor='black'
        )

        # Save
        output_path = self.output_dir / output_filename
        plt.tight_layout()
        plt.savefig(output_path, dpi=120, bbox_inches='tight', facecolor='white')
        plt.close()

        print(f"  [OK] Visualization saved: {output_path}")

    def analyze_route_risk(self, route_result: Dict[str, Any]):
        """
        Analyze risk distribution along the route.

        Args:
            route_result: Route result from find_route()
        """
        print(f"\n[ANALYSIS] Route risk analysis...")

        if not route_result.get("path"):
            print("  [WARNING] No route to analyze")
            return

        path_nodes = route_result["path"]

        # Analyze edges in path
        edge_risks = []
        edge_lengths = []
        blocked_edges = 0

        for i in range(len(path_nodes) - 1):
            u = path_nodes[i]
            v = path_nodes[i + 1]

            # Get edge data (handle MultiDiGraph)
            if self.env.graph.has_edge(u, v):
                edge_data = None
                for key in self.env.graph[u][v]:
                    edge_data = self.env.graph[u][v][key]
                    break

                if edge_data:
                    risk = edge_data.get('risk_score', 0.0)
                    length = edge_data.get('length', 0.0)

                    edge_risks.append(risk)
                    edge_lengths.append(length)

                    if risk >= 2:
                        blocked_edges += 1

        # Calculate statistics
        if edge_risks:
            risk_categories = {
                'safe': sum(1 for r in edge_risks if r < 0.001),
                'minimal': sum(1 for r in edge_risks if 0.001 <= r < 0.2),
                'low': sum(1 for r in edge_risks if 0.2 <= r < 0.4),
                'moderate': sum(1 for r in edge_risks if 0.4 <= r < 0.6),
                'high': sum(1 for r in edge_risks if 0.6 <= r < 0.8),
                'extreme': sum(1 for r in edge_risks if r >= 0.8)
            }

            print(f"  Route segments: {len(edge_risks)}")
            print(f"  Risk distribution:")
            for category, count in risk_categories.items():
                percentage = (count / len(edge_risks)) * 100
                print(f"    {category.capitalize()}: {count} segments ({percentage:.1f}%)")

            if blocked_edges > 0:
                print(f"  [WARNING] Route uses {blocked_edges} edges with risk >= 0.9 (normally blocked!)")

    def clear_flood_data(self):
        """Clear all flood risk data from the graph for baseline comparison."""
        print(f"\n[BASELINE] Clearing flood data from graph...")

        edges_cleared = 0
        for u, v, key in self.env.graph.edges(keys=True):
            self.env.graph[u][v][key]['risk_score'] = 0.0
            edges_cleared += 1

        print(f"  [OK] Cleared risk scores from {edges_cleared} edges")
        print(f"  [OK] All edges now have risk_score = 0.0 (no flood)")

    def run_comprehensive_test(self):
        """Run comprehensive routing test with visualization and analysis."""

        # Test coordinates
        start_lat, start_lon = 14.6553, 121.0990
        end_lat, end_lon = 14.6583, 121.1011

        # Test 0: BASELINE - No flood data (ignore floods)
        print(f"\n{'='*80}")
        print("TEST 0: BASELINE ROUTE (No Flood Data)")
        print("This shows what the route would be if flooding was ignored")
        print(f"{'='*80}")

        # Clear flood data for baseline
        self.clear_flood_data()

        route_baseline = self.test_route(
            start_lat, start_lon, end_lat, end_lon,
            preferences={"route_type": "baseline"}
        )

        if route_baseline.get("path"):
            self.analyze_route_risk(route_baseline)
            self.visualize_route(
                route_baseline,
                (start_lat, start_lon),
                (end_lat, end_lon),
                "route_test_baseline.png"
            )

        # Now setup severe flood scenario for flood-aware tests
        self.setup_flood_scenario(return_period="rr04", time_step=18)

        # Test 1: Safest route (avoid floods)
        print(f"\n{'='*80}")
        print("TEST 1: SAFEST ROUTE (Avoid Floods)")
        print(f"{'='*80}")

        route_safest = self.test_route(
            start_lat, start_lon, end_lat, end_lon,
            preferences={"avoid_floods": True, "route_type": "safest"}
        )

        if route_safest.get("path"):
            self.analyze_route_risk(route_safest)
            self.visualize_route(
                route_safest,
                (start_lat, start_lon),
                (end_lat, end_lon),
                "route_test_safest.png"
            )

        # Test 2: Fastest route
        print(f"\n{'='*80}")
        print("TEST 2: FASTEST ROUTE")
        print(f"{'='*80}")

        route_fastest = self.test_route(
            start_lat, start_lon, end_lat, end_lon,
            preferences={"fastest": True, "route_type": "fastest"}
        )

        if route_fastest.get("path"):
            self.analyze_route_risk(route_fastest)
            self.visualize_route(
                route_fastest,
                (start_lat, start_lon),
                (end_lat, end_lon),
                "route_test_fastest.png"
            )

        # Test 3: Balanced route
        print(f"\n{'='*80}")
        print("TEST 3: BALANCED ROUTE")
        print(f"{'='*80}")

        route_balanced = self.test_route(
            start_lat, start_lon, end_lat, end_lon,
            preferences={"route_type": "balanced"}
        )

        if route_balanced.get("path"):
            self.analyze_route_risk(route_balanced)
            self.visualize_route(
                route_balanced,
                (start_lat, start_lon),
                (end_lat, end_lon),
                "route_test_balanced.png"
            )

        # Summary comparison
        print(f"\n{'='*80}")
        print("ROUTE COMPARISON SUMMARY")
        print(f"{'='*80}")

        routes = [
            ("Baseline", route_baseline),
            ("Safest", route_safest),
            ("Fastest", route_fastest),
            ("Balanced", route_balanced)
        ]

        print(f"\n{'Route Type':<12} {'Distance (m)':<15} {'Time (min)':<12} {'Risk':<8} {'Max Risk':<10} {'Status':<10}")
        print("-" * 80)

        for name, route in routes:
            if route.get("path"):
                distance = route['distance']
                time = route['estimated_time'] / 60
                risk = route['risk_level']
                max_risk = route['max_risk']
                status = "Found"
            else:
                distance = 0
                time = 0
                risk = 1.0
                max_risk = 1.0
                status = "No Route"

            print(f"{name:<12} {distance:<15.1f} {time:<12.1f} {risk:<8.3f} {max_risk:<10.3f} {status:<10}")

        # Baseline vs Flood-Aware Comparison
        if route_baseline.get("path") and route_safest.get("path"):
            print(f"\n{'='*80}")
            print("BASELINE vs FLOOD-AWARE ROUTING IMPACT")
            print(f"{'='*80}")

            baseline_dist = route_baseline['distance']
            safest_dist = route_safest['distance']
            dist_diff = safest_dist - baseline_dist
            dist_pct = (dist_diff / baseline_dist) * 100

            baseline_risk = route_baseline['risk_level']
            safest_risk = route_safest['risk_level']
            risk_reduction = baseline_risk - safest_risk
            risk_reduction_pct = (risk_reduction / baseline_risk) * 100 if baseline_risk > 0 else 0

            print(f"\nBaseline Route (Ignoring Floods):")
            print(f"  Distance: {baseline_dist:.1f}m")
            print(f"  Risk: {baseline_risk:.3f} (avg), {route_baseline['max_risk']:.3f} (max)")

            print(f"\nSafest Route (Flood-Aware):")
            print(f"  Distance: {safest_dist:.1f}m")
            print(f"  Risk: {safest_risk:.3f} (avg), {route_safest['max_risk']:.3f} (max)")

            print(f"\nImpact of Flood-Aware Routing:")
            print(f"  Distance Change: {dist_diff:+.1f}m ({dist_pct:+.1f}%)")
            print(f"  Risk Reduction: {risk_reduction:.3f} ({risk_reduction_pct:.1f}%)")

            if dist_diff > 0:
                print(f"  Trade-off: +{dist_diff:.0f}m detour for {risk_reduction_pct:.1f}% risk reduction")
            else:
                print(f"  Win-Win: Shorter distance AND lower risk!")

        print(f"\n[OUTPUT] All visualizations saved to: {self.output_dir}")
        print(f"  - route_test_baseline.png (no flood data)")
        print(f"  - route_test_safest.png (flood-aware, safest)")
        print(f"  - route_test_fastest.png (flood-aware, fastest)")
        print(f"  - route_test_balanced.png (flood-aware, balanced)")

        print(f"\n{'='*80}")
        print("TEST COMPLETE")
        print(f"{'='*80}")


def main():
    """Run routing test with severe flood conditions."""
    try:
        tester = FloodRoutingTester()
        tester.run_comprehensive_test()
        return 0

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
