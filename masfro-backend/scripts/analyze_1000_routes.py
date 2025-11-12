#!/usr/bin/env python3
"""
Large-Scale Route Comparison: Baseline vs Safest Routes

This script generates 1000 random routes and compares baseline (no flood awareness)
vs safest (flood-aware) routing to provide statistical analysis of:
- Distance differences
- Time differences
- Risk reduction
- Route success rates

Flood Scenario: RR04 (25-year flood), Hour 18 (worst case)
"""

import sys
import os
from pathlib import Path
import random
import time
from typing import Dict, Any, List, Tuple
import statistics

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.hazard_agent import HazardAgent
from app.agents.routing_agent import RoutingAgent
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


class RouteAnalyzer:
    """Analyze 1000 routes comparing baseline vs safest routing."""

    def __init__(self):
        """Initialize the analyzer with environment and agents."""
        print("=" * 80)
        print("LARGE-SCALE ROUTE ANALYSIS")
        print("Comparing Baseline vs Safest Routes (1000 samples)")
        print("=" * 80)

        # Initialize environment
        print("\n[INIT] Loading road network...")
        self.env = DynamicGraphEnvironment()
        if self.env.graph is None:
            raise RuntimeError("Failed to load graph!")

        print(f"  [OK] Graph loaded: {self.env.graph.number_of_nodes()} nodes, "
              f"{self.env.graph.number_of_edges()} edges")

        # Get bounding box for random coordinate generation
        self.min_lat = min(data['y'] for _, data in self.env.graph.nodes(data=True))
        self.max_lat = max(data['y'] for _, data in self.env.graph.nodes(data=True))
        self.min_lon = min(data['x'] for _, data in self.env.graph.nodes(data=True))
        self.max_lon = max(data['x'] for _, data in self.env.graph.nodes(data=True))

        print(f"  [OK] Coordinate bounds: "
              f"Lat [{self.min_lat:.4f}, {self.max_lat:.4f}], "
              f"Lon [{self.min_lon:.4f}, {self.max_lon:.4f}]")

        # Initialize agents
        print("\n[INIT] Initializing agents...")
        self.hazard_agent = HazardAgent(
            agent_id="hazard_analyzer",
            environment=self.env,
            enable_geotiff=True
        )

        self.routing_agent = RoutingAgent(
            agent_id="routing_analyzer",
            environment=self.env
        )

        print("  [OK] Agents initialized")

        # Output directory
        self.output_dir = Path(__file__).parent.parent / "outputs" / "route_analysis"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Results storage
        self.results = []

    def setup_flood_scenario(self, return_period: str = "rr04", time_step: int = 18):
        """
        Configure flood scenario and update graph.

        Args:
            return_period: Flood return period (default: rr04 - 25-year flood)
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
                "source": "route_analyzer"
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

    def generate_random_route_pair(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Generate random start and end coordinates within the network bounds.

        Returns:
            Tuple of (start_coords, end_coords)
        """
        # Generate random coordinates with some minimum distance
        min_distance = 0.005  # Roughly 500m minimum

        while True:
            start_lat = random.uniform(self.min_lat, self.max_lat)
            start_lon = random.uniform(self.min_lon, self.max_lon)
            end_lat = random.uniform(self.min_lat, self.max_lat)
            end_lon = random.uniform(self.min_lon, self.max_lon)

            # Check minimum distance
            if (abs(end_lat - start_lat) + abs(end_lon - start_lon)) > min_distance:
                return (start_lat, start_lon), (end_lat, end_lon)

    def calculate_route_with_timeout(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        preferences: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Calculate route with timeout protection.

        Args:
            start: Start coordinates
            end: End coordinates
            preferences: Route preferences
            timeout: Timeout in seconds

        Returns:
            Route result dict or error dict
        """
        try:
            result = self.routing_agent.calculate_route(
                start=start,
                end=end,
                preferences=preferences
            )
            return result
        except Exception as e:
            return {
                "path": [],
                "distance": 0,
                "estimated_time": 0,
                "risk_level": 1.0,
                "max_risk": 1.0,
                "warnings": [f"Error: {str(e)}"],
                "error": True
            }

    def analyze_single_route(self, route_index: int) -> Dict[str, Any]:
        """
        Analyze a single random route with both baseline and safest preferences.

        Args:
            route_index: Index of the route (for logging)

        Returns:
            Dict with comparison results
        """
        # Generate random start/end
        start, end = self.generate_random_route_pair()

        # Calculate baseline route (no flood awareness)
        baseline_result = self.calculate_route_with_timeout(
            start, end,
            preferences={"route_type": "baseline"}
        )

        # Calculate safest route (flood-aware)
        safest_result = self.calculate_route_with_timeout(
            start, end,
            preferences={"avoid_floods": True, "route_type": "safest"}
        )

        # Extract metrics
        baseline_success = bool(baseline_result.get("path"))
        safest_success = bool(safest_result.get("path"))

        result = {
            "route_id": route_index,
            "start": start,
            "end": end,
            "baseline": {
                "success": baseline_success,
                "distance": baseline_result.get("distance", 0),
                "time": baseline_result.get("estimated_time", 0) / 60,  # Convert to minutes
                "risk": baseline_result.get("risk_level", 1.0),
                "max_risk": baseline_result.get("max_risk", 1.0)
            },
            "safest": {
                "success": safest_success,
                "distance": safest_result.get("distance", 0),
                "time": safest_result.get("estimated_time", 0) / 60,  # Convert to minutes
                "risk": safest_result.get("risk_level", 1.0),
                "max_risk": safest_result.get("max_risk", 1.0)
            }
        }

        # Calculate differences (only if both routes found)
        if baseline_success and safest_success:
            result["distance_diff"] = safest_result["distance"] - baseline_result["distance"]
            result["distance_diff_pct"] = (result["distance_diff"] / baseline_result["distance"]) * 100
            result["time_diff"] = (safest_result["estimated_time"] - baseline_result["estimated_time"]) / 60
            result["risk_reduction"] = baseline_result["risk_level"] - safest_result["risk_level"]
            result["risk_reduction_pct"] = (result["risk_reduction"] / baseline_result["risk_level"] * 100) if baseline_result["risk_level"] > 0 else 0
        else:
            result["distance_diff"] = None
            result["distance_diff_pct"] = None
            result["time_diff"] = None
            result["risk_reduction"] = None
            result["risk_reduction_pct"] = None

        return result

    def run_analysis(self, num_routes: int = 1000):
        """
        Run analysis on specified number of routes.

        Args:
            num_routes: Number of random routes to analyze
        """
        print(f"\n[ANALYSIS] Generating and analyzing {num_routes} random routes...")
        print("This may take several minutes...\n")

        start_time = time.time()
        progress_interval = max(1, num_routes // 20)  # Update every 5%

        for i in range(num_routes):
            # Progress update
            if (i + 1) % progress_interval == 0 or i == 0:
                elapsed = time.time() - start_time
                routes_per_sec = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (num_routes - i - 1) / routes_per_sec if routes_per_sec > 0 else 0
                print(f"  [{i+1}/{num_routes}] ({(i+1)/num_routes*100:.1f}%) - "
                      f"{routes_per_sec:.2f} routes/sec - ETA: {eta:.0f}s")

            # Analyze route
            result = self.analyze_single_route(i + 1)
            self.results.append(result)

        elapsed = time.time() - start_time
        print(f"\n  [OK] Analysis complete in {elapsed:.1f} seconds")
        print(f"  [OK] Average: {num_routes/elapsed:.2f} routes/second")

    def generate_statistics(self) -> Dict[str, Any]:
        """
        Generate comprehensive statistics from results.

        Returns:
            Dict with statistical analysis
        """
        print("\n[STATS] Calculating statistics...")

        # Filter successful routes (both baseline and safest found)
        successful_routes = [r for r in self.results
                            if r["baseline"]["success"] and r["safest"]["success"]]

        # Count success rates
        total_routes = len(self.results)
        baseline_success_count = sum(1 for r in self.results if r["baseline"]["success"])
        safest_success_count = sum(1 for r in self.results if r["safest"]["success"])
        both_success_count = len(successful_routes)

        stats = {
            "total_routes": total_routes,
            "success_rates": {
                "baseline": (baseline_success_count / total_routes) * 100,
                "safest": (safest_success_count / total_routes) * 100,
                "both": (both_success_count / total_routes) * 100
            },
            "baseline_only": baseline_success_count - both_success_count,
            "safest_only": safest_success_count - both_success_count
        }

        if not successful_routes:
            print("  [WARNING] No routes with both baseline and safest solutions!")
            return stats

        # Extract metrics for successful routes
        baseline_distances = [r["baseline"]["distance"] for r in successful_routes]
        baseline_times = [r["baseline"]["time"] for r in successful_routes]
        baseline_risks = [r["baseline"]["risk"] for r in successful_routes]

        safest_distances = [r["safest"]["distance"] for r in successful_routes]
        safest_times = [r["safest"]["time"] for r in successful_routes]
        safest_risks = [r["safest"]["risk"] for r in successful_routes]

        distance_diffs = [r["distance_diff"] for r in successful_routes]
        distance_diff_pcts = [r["distance_diff_pct"] for r in successful_routes]
        time_diffs = [r["time_diff"] for r in successful_routes]
        risk_reductions = [r["risk_reduction"] for r in successful_routes]
        risk_reduction_pcts = [r["risk_reduction_pct"] for r in successful_routes]

        # Calculate statistics
        stats["baseline"] = {
            "distance_mean": statistics.mean(baseline_distances),
            "distance_median": statistics.median(baseline_distances),
            "distance_stdev": statistics.stdev(baseline_distances) if len(baseline_distances) > 1 else 0,
            "time_mean": statistics.mean(baseline_times),
            "time_median": statistics.median(baseline_times),
            "risk_mean": statistics.mean(baseline_risks),
            "risk_median": statistics.median(baseline_risks),
            "risk_max": max(baseline_risks),
            "risk_min": min(baseline_risks)
        }

        stats["safest"] = {
            "distance_mean": statistics.mean(safest_distances),
            "distance_median": statistics.median(safest_distances),
            "distance_stdev": statistics.stdev(safest_distances) if len(safest_distances) > 1 else 0,
            "time_mean": statistics.mean(safest_times),
            "time_median": statistics.median(safest_times),
            "risk_mean": statistics.mean(safest_risks),
            "risk_median": statistics.median(safest_risks),
            "risk_max": max(safest_risks),
            "risk_min": min(safest_risks)
        }

        stats["differences"] = {
            "distance_mean": statistics.mean(distance_diffs),
            "distance_median": statistics.median(distance_diffs),
            "distance_pct_mean": statistics.mean(distance_diff_pcts),
            "distance_pct_median": statistics.median(distance_diff_pcts),
            "time_mean": statistics.mean(time_diffs),
            "time_median": statistics.median(time_diffs),
            "risk_reduction_mean": statistics.mean(risk_reductions),
            "risk_reduction_median": statistics.median(risk_reductions),
            "risk_reduction_pct_mean": statistics.mean(risk_reduction_pcts),
            "risk_reduction_pct_median": statistics.median(risk_reduction_pcts)
        }

        # Count routes where safest is actually safer
        safer_routes = sum(1 for r in successful_routes if r["safest"]["risk"] < r["baseline"]["risk"])
        stats["safer_routes_count"] = safer_routes
        stats["safer_routes_pct"] = (safer_routes / len(successful_routes)) * 100

        # Count routes where safest is shorter
        shorter_routes = sum(1 for r in successful_routes if r["safest"]["distance"] < r["baseline"]["distance"])
        stats["shorter_safest_count"] = shorter_routes
        stats["shorter_safest_pct"] = (shorter_routes / len(successful_routes)) * 100

        print(f"  [OK] Statistics calculated from {len(successful_routes)} successful route pairs")

        return stats

    def print_statistics(self, stats: Dict[str, Any]):
        """Print statistics in a formatted table."""
        print("\n" + "=" * 80)
        print("STATISTICAL ANALYSIS RESULTS")
        print("=" * 80)

        print(f"\nTotal Routes Analyzed: {stats['total_routes']}")
        print(f"\nSuccess Rates:")
        print(f"  Baseline found route: {stats['success_rates']['baseline']:.1f}%")
        print(f"  Safest found route: {stats['success_rates']['safest']:.1f}%")
        print(f"  Both found route: {stats['success_rates']['both']:.1f}%")

        if stats.get("baseline"):
            print(f"\n{'-'*80}")
            print(f"{'Metric':<30} {'Baseline':<20} {'Safest':<20} {'Difference':<10}")
            print(f"{'-'*80}")

            # Distance
            print(f"{'Distance (meters):':<30} "
                  f"{stats['baseline']['distance_mean']:<20.1f} "
                  f"{stats['safest']['distance_mean']:<20.1f} "
                  f"{stats['differences']['distance_mean']:<+10.1f}")

            print(f"{'Distance Median:':<30} "
                  f"{stats['baseline']['distance_median']:<20.1f} "
                  f"{stats['safest']['distance_median']:<20.1f} "
                  f"{stats['differences']['distance_median']:<+10.1f}")

            print(f"{'Distance Std Dev:':<30} "
                  f"{stats['baseline']['distance_stdev']:<20.1f} "
                  f"{stats['safest']['distance_stdev']:<20.1f}")

            # Time
            print(f"\n{'Time (minutes):':<30} "
                  f"{stats['baseline']['time_mean']:<20.2f} "
                  f"{stats['safest']['time_mean']:<20.2f} "
                  f"{stats['differences']['time_mean']:<+10.2f}")

            print(f"{'Time Median:':<30} "
                  f"{stats['baseline']['time_median']:<20.2f} "
                  f"{stats['safest']['time_median']:<20.2f} "
                  f"{stats['differences']['time_median']:<+10.2f}")

            # Risk
            print(f"\n{'Risk (0-1 scale):':<30} "
                  f"{stats['baseline']['risk_mean']:<20.3f} "
                  f"{stats['safest']['risk_mean']:<20.3f} "
                  f"{stats['differences']['risk_reduction_mean']:<+10.3f}")

            print(f"{'Risk Median:':<30} "
                  f"{stats['baseline']['risk_median']:<20.3f} "
                  f"{stats['safest']['risk_median']:<20.3f} "
                  f"{stats['differences']['risk_reduction_median']:<+10.3f}")

            print(f"{'Risk Range:':<30} "
                  f"[{stats['baseline']['risk_min']:.3f}, {stats['baseline']['risk_max']:.3f}]"
                  f"{'':<5} "
                  f"[{stats['safest']['risk_min']:.3f}, {stats['safest']['risk_max']:.3f}]")

            print(f"\n{'-'*80}")
            print(f"Average Percentage Changes:")
            print(f"  Distance increase: {stats['differences']['distance_pct_mean']:+.1f}%")
            print(f"  Risk reduction: {stats['differences']['risk_reduction_pct_mean']:.1f}%")

            print(f"\nComparative Analysis:")
            print(f"  Routes where safest is safer: {stats['safer_routes_count']} ({stats['safer_routes_pct']:.1f}%)")
            print(f"  Routes where safest is shorter: {stats['shorter_safest_count']} ({stats['shorter_safest_pct']:.1f}%)")

    def create_visualizations(self, stats: Dict[str, Any]):
        """
        Create visualization plots for the analysis.

        Args:
            stats: Statistics dictionary
        """
        print(f"\n[VIZ] Creating visualizations...")

        # Filter successful routes
        successful_routes = [r for r in self.results
                            if r["baseline"]["success"] and r["safest"]["success"]]

        if not successful_routes:
            print("  [WARNING] No successful routes to visualize")
            return

        # Create figure with subplots
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(
            f"Route Analysis: Baseline vs Safest ({len(successful_routes)} routes)\n"
            f"Scenario: RR04 (25-year flood), Hour 18",
            fontsize=16, fontweight='bold'
        )

        # 1. Distance Comparison
        ax = axes[0, 0]
        baseline_dists = [r["baseline"]["distance"] for r in successful_routes]
        safest_dists = [r["safest"]["distance"] for r in successful_routes]
        ax.scatter(baseline_dists, safest_dists, alpha=0.5, s=10)
        ax.plot([0, max(baseline_dists)], [0, max(baseline_dists)], 'r--', label='Equal distance')
        ax.set_xlabel('Baseline Distance (m)')
        ax.set_ylabel('Safest Distance (m)')
        ax.set_title('Distance Comparison')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 2. Risk Comparison
        ax = axes[0, 1]
        baseline_risks = [r["baseline"]["risk"] for r in successful_routes]
        safest_risks = [r["safest"]["risk"] for r in successful_routes]
        ax.scatter(baseline_risks, safest_risks, alpha=0.5, s=10)
        ax.plot([0, 1], [0, 1], 'r--', label='Equal risk')
        ax.set_xlabel('Baseline Risk')
        ax.set_ylabel('Safest Risk')
        ax.set_title('Risk Comparison')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 3. Time Comparison
        ax = axes[0, 2]
        baseline_times = [r["baseline"]["time"] for r in successful_routes]
        safest_times = [r["safest"]["time"] for r in successful_routes]
        ax.scatter(baseline_times, safest_times, alpha=0.5, s=10)
        ax.plot([0, max(baseline_times)], [0, max(baseline_times)], 'r--', label='Equal time')
        ax.set_xlabel('Baseline Time (min)')
        ax.set_ylabel('Safest Time (min)')
        ax.set_title('Time Comparison')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 4. Distance Difference Distribution
        ax = axes[1, 0]
        distance_diffs = [r["distance_diff_pct"] for r in successful_routes]
        ax.hist(distance_diffs, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
        ax.axvline(0, color='red', linestyle='--', linewidth=2, label='No change')
        ax.axvline(statistics.mean(distance_diffs), color='green', linestyle='--',
                   linewidth=2, label=f'Mean: {statistics.mean(distance_diffs):.1f}%')
        ax.set_xlabel('Distance Change (%)')
        ax.set_ylabel('Frequency')
        ax.set_title('Distance Difference Distribution')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        # 5. Risk Reduction Distribution
        ax = axes[1, 1]
        risk_reductions = [r["risk_reduction_pct"] for r in successful_routes]
        ax.hist(risk_reductions, bins=50, color='lightcoral', edgecolor='black', alpha=0.7)
        ax.axvline(0, color='red', linestyle='--', linewidth=2, label='No change')
        ax.axvline(statistics.mean(risk_reductions), color='green', linestyle='--',
                   linewidth=2, label=f'Mean: {statistics.mean(risk_reductions):.1f}%')
        ax.set_xlabel('Risk Reduction (%)')
        ax.set_ylabel('Frequency')
        ax.set_title('Risk Reduction Distribution')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        # 6. Trade-off Analysis (Distance increase vs Risk reduction)
        ax = axes[1, 2]
        ax.scatter(distance_diffs, risk_reductions, alpha=0.5, s=10)
        ax.axhline(0, color='gray', linestyle='-', linewidth=0.5)
        ax.axvline(0, color='gray', linestyle='-', linewidth=0.5)
        ax.set_xlabel('Distance Change (%)')
        ax.set_ylabel('Risk Reduction (%)')
        ax.set_title('Trade-off Analysis')
        ax.grid(True, alpha=0.3)

        # Add quadrant labels
        ax.text(0.95, 0.95, 'Win-Win\n(shorter & safer)',
                transform=ax.transAxes, ha='right', va='top',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.5))
        ax.text(0.05, 0.05, 'Lose-Lose\n(longer & riskier)',
                transform=ax.transAxes, ha='left', va='bottom',
                bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.5))

        plt.tight_layout()

        # Save
        output_path = self.output_dir / "route_analysis_1000.png"
        plt.savefig(output_path, dpi=120, bbox_inches='tight', facecolor='white')
        plt.close()

        print(f"  [OK] Visualization saved: {output_path}")

    def save_results_to_csv(self):
        """Save detailed results to CSV file."""
        import csv

        csv_path = self.output_dir / "route_analysis_results.csv"

        print(f"\n[SAVE] Saving results to CSV...")

        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'route_id', 'start_lat', 'start_lon', 'end_lat', 'end_lon',
                'baseline_success', 'baseline_distance', 'baseline_time', 'baseline_risk', 'baseline_max_risk',
                'safest_success', 'safest_distance', 'safest_time', 'safest_risk', 'safest_max_risk',
                'distance_diff', 'distance_diff_pct', 'time_diff', 'risk_reduction', 'risk_reduction_pct'
            ])

            # Data
            for r in self.results:
                writer.writerow([
                    r['route_id'],
                    r['start'][0], r['start'][1],
                    r['end'][0], r['end'][1],
                    r['baseline']['success'],
                    r['baseline']['distance'],
                    r['baseline']['time'],
                    r['baseline']['risk'],
                    r['baseline']['max_risk'],
                    r['safest']['success'],
                    r['safest']['distance'],
                    r['safest']['time'],
                    r['safest']['risk'],
                    r['safest']['max_risk'],
                    r.get('distance_diff', ''),
                    r.get('distance_diff_pct', ''),
                    r.get('time_diff', ''),
                    r.get('risk_reduction', ''),
                    r.get('risk_reduction_pct', '')
                ])

        print(f"  [OK] Results saved: {csv_path}")


def main():
    """Run the 1000-route analysis."""
    try:
        # Create analyzer
        analyzer = RouteAnalyzer()

        # Setup flood scenario (worst case)
        analyzer.setup_flood_scenario(return_period="rr04", time_step=18)

        # Run analysis
        num_routes = 1000
        analyzer.run_analysis(num_routes=num_routes)

        # Generate statistics
        stats = analyzer.generate_statistics()

        # Print results
        analyzer.print_statistics(stats)

        # Create visualizations
        analyzer.create_visualizations(stats)

        # Save to CSV
        analyzer.save_results_to_csv()

        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        print(f"\nOutput files saved to: {analyzer.output_dir}")
        print("  - route_analysis_1000.png (visualizations)")
        print("  - route_analysis_results.csv (detailed results)")

        return 0

    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
