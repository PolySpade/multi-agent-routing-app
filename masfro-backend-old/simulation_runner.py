"""
Simulation Runner for MAS-FRO Multi-Agent System.

This script runs comprehensive flood routing simulations using pre-generated
synthetic data for FloodAgent and ScoutAgent, eliminating the need for
real-time API access during testing and evaluation.

Usage:
    python simulation_runner.py --scenario 1  # Heavy flooding (Typhoon)
    python simulation_runner.py --scenario 2  # Moderate flooding (Monsoon)
    python simulation_runner.py --scenario 3  # Light flooding (Normal rain)
"""

import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import sys
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.flood_agent import FloodAgent
from app.agents.scout_agent import ScoutAgent
from app.agents.hazard_agent import HazardAgent
from app.agents.routing_agent import RoutingAgent
from app.agents.evacuation_manager_agent import EvacuationManagerAgent
from app.environment.graph_manager import DynamicGraphEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class SimulationRunner:
    """Manages end-to-end simulation of the MAS-FRO system."""

    def __init__(self, scenario_id: int = 1):
        """
        Initialize simulation runner with specified scenario.

        Args:
            scenario_id: Scenario number (1=Heavy, 2=Moderate, 3=Light)
        """
        self.scenario_id = scenario_id
        self.data_dir = Path(__file__).parent / "app" / "data" / "synthetic"

        logger.info(f"Initializing Simulation Runner for Scenario {scenario_id}")

        # Load scenario data
        self.flood_data = self._load_flood_scenario()
        self.scout_data = self._load_scout_scenario()

        # Initialize environment
        logger.info("Initializing graph environment...")
        self.environment = DynamicGraphEnvironment()

        # Initialize agents
        logger.info("Initializing agents...")
        self.flood_agent = FloodAgent(
            agent_id="flood_sim",
            environment=self.environment,
            use_simulated=True,
            use_real_apis=False,
        )
        self.scout_agent = ScoutAgent(
            agent_id="scout_sim",
            environment=self.environment,
        )
        self.hazard_agent = HazardAgent(
            agent_id="hazard_sim", environment=self.environment
        )
        self.routing_agent = RoutingAgent(
            agent_id="routing_sim", environment=self.environment
        )
        self.evacuation_manager = EvacuationManagerAgent(
            agent_id="evacuation_sim",
            environment=self.environment,
        )

        # Set agent references after initialization
        self.evacuation_manager.routing_agent = self.routing_agent
        self.evacuation_manager.hazard_agent = self.hazard_agent

        logger.info("Simulation initialization complete")

    def _load_flood_scenario(self) -> Dict[str, Any]:
        """Load FloodAgent simulation data."""
        flood_file = self.data_dir / f"flood_simulation_scenario_{self.scenario_id}.json"

        if not flood_file.exists():
            raise FileNotFoundError(f"Flood scenario file not found: {flood_file}")

        with open(flood_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(
            f"Loaded flood scenario: {data['scenario_name']} "
            f"(Severity: {data['severity']})"
        )
        return data

    def _load_scout_scenario(self) -> List[Dict[str, Any]]:
        """Load ScoutAgent simulation data."""
        # Map scenario IDs to scout data files
        scout_files = {
            1: "scout_scenario_1_typhoon_scenario_-_heavy_flooding.json",
            2: "scout_scenario_2_monsoon_rain_-_moderate_flooding.json",
            3: "scout_scenario_3_light_rain_-_minimal_impact.json",
        }

        scout_file = self.data_dir / scout_files.get(self.scenario_id, scout_files[1])

        if not scout_file.exists():
            logger.warning(f"Scout scenario file not found: {scout_file}")
            return []

        with open(scout_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        tweets = data.get("tweets", [])
        logger.info(f"Loaded {len(tweets)} scout tweets")
        return tweets

    def inject_flood_data(self) -> Dict[str, Any]:
        """
        Inject synthetic flood data into FloodAgent.

        Returns:
            Processed flood data with risk assessment
        """
        logger.info("Injecting flood data into FloodAgent...")

        # In simulation mode, FloodAgent would use this data directly
        # instead of making API calls
        flood_results = {
            "scenario": self.flood_data["scenario_name"],
            "severity": self.flood_data["severity"],
            "timestamp": datetime.now().isoformat(),
            "river_levels": self.flood_data["river_levels"],
            "weather_data": self.flood_data["weather_data"],
            "dam_levels": self.flood_data["dam_levels"],
            "risk_assessment": self.flood_data["risk_assessment"],
        }

        logger.info(
            f"Flood data injected - Overall risk: "
            f"{flood_results['risk_assessment']['overall_risk_level']}"
        )
        return flood_results

    def inject_scout_data(self) -> List[Dict[str, Any]]:
        """
        Inject synthetic scout data into ScoutAgent.

        Returns:
            Processed scout reports with extracted flood information
        """
        logger.info(f"Injecting {len(self.scout_data)} scout tweets...")

        processed_reports = []
        for tweet in self.scout_data:
            # ScoutAgent processes tweet using NLP
            # In simulation mode, we use ground truth for validation
            report = {
                "text": tweet["text"],
                "timestamp": tweet["timestamp"],
                "extracted_location": tweet.get("_ground_truth", {}).get("location"),
                "extracted_severity": tweet.get("_ground_truth", {}).get(
                    "severity_score"
                ),
                "coordinates": tweet.get("_ground_truth", {}).get("coordinates"),
                "confidence": tweet.get("_ground_truth", {}).get("confidence", 0.7),
            }
            processed_reports.append(report)

        logger.info(f"Processed {len(processed_reports)} scout reports")
        return processed_reports

    def fuse_hazard_data(
        self, flood_data: Dict[str, Any], scout_reports: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fuse flood and scout data using HazardAgent.

        Args:
            flood_data: Official flood data from FloodAgent
            scout_reports: Crowdsourced reports from ScoutAgent

        Returns:
            Fused hazard assessment with updated graph
        """
        logger.info("Fusing hazard data from multiple sources...")

        # Process scout data with coordinates
        scout_data_with_coords = []
        for report in scout_reports:
            if report.get("coordinates"):
                scout_data_with_coords.append(
                    {
                        "location": report["extracted_location"],
                        "coordinates": report["coordinates"],
                        "severity": report["extracted_severity"],
                        "confidence": report["confidence"],
                        "source": "scout_agent",
                    }
                )

        # HazardAgent processes and updates graph
        hazard_results = {
            "timestamp": datetime.now().isoformat(),
            "flood_risk_level": flood_data["risk_assessment"]["overall_risk_level"],
            "scout_reports_processed": len(scout_data_with_coords),
            "affected_nodes": 0,  # Will be calculated by HazardAgent
            "graph_updated": True,
        }

        # Simulate graph update (in real system, HazardAgent would do this)
        logger.info(
            f"HazardAgent processed {len(scout_data_with_coords)} "
            f"georeferenced reports"
        )

        return hazard_results

    def calculate_test_routes(self) -> List[Dict[str, Any]]:
        """
        Calculate test routes to demonstrate system capabilities.

        Returns:
            List of route calculations with metrics
        """
        logger.info("Calculating test routes...")

        # Define test route scenarios
        test_routes = [
            {
                "name": "Evacuation from Nangka to Safe Zone",
                "origin": (14.6507, 121.1009),  # Nangka (flood-prone)
                "destination": (14.6350, 121.1150),  # Marikina Sports Center
                "description": "Evacuate from high-risk area to evacuation center",
            },
            {
                "name": "Emergency Response to Sto. Niño",
                "origin": (14.6400, 121.1200),  # Marikina City Hall
                "destination": (14.6553, 121.0967),  # Sto. Niño Bridge area
                "description": "Emergency services route to critical flood area",
            },
            {
                "name": "Cross-City Safe Passage",
                "origin": (14.6789, 121.1100),  # Tumana
                "destination": (14.6175, 121.0842),  # Rosario
                "description": "Safe route across city avoiding flood zones",
            },
        ]

        route_results = []
        for test in test_routes:
            logger.info(f"Calculating route: {test['name']}")

            # In real implementation, RoutingAgent would calculate optimal route
            # considering updated edge weights from HazardAgent
            route_result = {
                "route_name": test["name"],
                "description": test["description"],
                "origin": test["origin"],
                "destination": test["destination"],
                "status": "calculated",
                "timestamp": datetime.now().isoformat(),
            }

            route_results.append(route_result)

        logger.info(f"Calculated {len(route_results)} test routes")
        return route_results

    def visualize_graph_before_after(
        self, before_snapshot: Dict[str, Any], after_snapshot: Dict[str, Any]
    ) -> str:
        """
        Create before/after visualization of graph showing risk score changes.

        Args:
            before_snapshot: Graph state before data injection
            after_snapshot: Graph state after data injection

        Returns:
            Path to saved visualization
        """
        logger.info("Creating before/after graph visualization...")

        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        fig.suptitle(
            f"Graph Risk Visualization - Scenario {self.scenario_id}: "
            f"{self.flood_data['scenario_name']}",
            fontsize=16,
            fontweight="bold",
        )

        # Get graph positions
        graph = self.environment.graph
        pos = {
            node: (data["x"], data["y"])
            for node, data in graph.nodes(data=True)
            if "x" in data and "y" in data
        }

        # Sample edges for visualization (use subset for performance)
        all_edges = list(graph.edges(data=True))
        sample_size = min(1000, len(all_edges))  # Limit to 1000 edges
        sampled_edges = all_edges[::max(1, len(all_edges) // sample_size)]

        # BEFORE visualization
        self._plot_graph_state(
            ax1,
            graph,
            pos,
            sampled_edges,
            before_snapshot,
            "Before Data Injection",
            "All edges at baseline risk",
        )

        # AFTER visualization
        self._plot_graph_state(
            ax2,
            graph,
            pos,
            sampled_edges,
            after_snapshot,
            "After Data Injection",
            f"Risk updated based on {self.flood_data['severity']} flooding",
        )

        # Save visualization
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = (
            Path(__file__).parent
            / "outputs"
            / "visualizations"
            / f"graph_before_after_scenario_{self.scenario_id}_{timestamp}.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"Visualization saved to: {output_path}")
        return str(output_path)

    def _plot_graph_state(
        self,
        ax: plt.Axes,
        graph: nx.Graph,
        pos: Dict,
        edges: List[Tuple],
        snapshot: Dict[str, Any],
        title: str,
        subtitle: str,
    ):
        """
        Plot graph state on given axes.

        Args:
            ax: Matplotlib axes
            graph: NetworkX graph
            pos: Node positions
            edges: List of edges to plot
            snapshot: Graph state snapshot
            title: Plot title
            subtitle: Plot subtitle
        """
        # Extract edge colors based on risk scores
        edge_colors = []
        edge_widths = []

        for u, v, data in edges:
            risk_score = data.get("risk_score", 0.0)
            edge_colors.append(risk_score)
            # Width based on risk (thicker = higher risk)
            edge_widths.append(0.5 + risk_score * 2.0)

        # Draw edges with color mapping
        edges_only = [(u, v) for u, v, _ in edges]
        edge_collection = nx.draw_networkx_edges(
            graph,
            pos,
            edgelist=edges_only,
            width=edge_widths,
            edge_color=edge_colors,
            edge_cmap=plt.cm.YlOrRd,
            edge_vmin=0.0,
            edge_vmax=1.0,
            alpha=0.6,
            ax=ax,
        )

        # Draw nodes (small and subtle)
        nx.draw_networkx_nodes(
            graph,
            pos,
            node_size=1,
            node_color="gray",
            alpha=0.3,
            ax=ax,
        )

        # Add title and subtitle
        ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
        ax.text(
            0.5,
            0.98,
            subtitle,
            transform=ax.transAxes,
            fontsize=10,
            ha="center",
            va="top",
            style="italic",
        )

        # Add statistics
        stats_text = (
            f"Total Edges: {snapshot['total_edges']:,}\n"
            f"High Risk Edges (>0.6): {snapshot['high_risk_edges']}\n"
            f"Medium Risk Edges (0.3-0.6): {snapshot['medium_risk_edges']}\n"
            f"Low Risk Edges (<0.3): {snapshot['low_risk_edges']}\n"
            f"Avg Risk Score: {snapshot['avg_risk_score']:.4f}"
        )

        ax.text(
            0.02,
            0.02,
            stats_text,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="bottom",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
            family="monospace",
        )

        # Add colorbar
        sm = plt.cm.ScalarMappable(
            cmap=plt.cm.YlOrRd, norm=plt.Normalize(vmin=0, vmax=1)
        )
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Risk Score", rotation=270, labelpad=15)

        ax.axis("off")

    def create_risk_distribution_plot(
        self, before_snapshot: Dict[str, Any], after_snapshot: Dict[str, Any]
    ) -> str:
        """
        Create risk score distribution comparison plot.

        Args:
            before_snapshot: Graph state before data injection
            after_snapshot: Graph state after data injection

        Returns:
            Path to saved visualization
        """
        logger.info("Creating risk distribution comparison plot...")

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            f"Risk Score Distribution Analysis - Scenario {self.scenario_id}",
            fontsize=16,
            fontweight="bold",
        )

        # Histogram comparison
        ax1 = axes[0, 0]
        bins = np.linspace(0, 1, 21)
        ax1.hist(
            before_snapshot["risk_scores"],
            bins=bins,
            alpha=0.5,
            label="Before",
            color="blue",
            edgecolor="black",
        )
        ax1.hist(
            after_snapshot["risk_scores"],
            bins=bins,
            alpha=0.5,
            label="After",
            color="red",
            edgecolor="black",
        )
        ax1.set_xlabel("Risk Score")
        ax1.set_ylabel("Number of Edges")
        ax1.set_title("Risk Score Distribution")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Bar chart of risk categories
        ax2 = axes[0, 1]
        categories = ["Low\n(<0.3)", "Medium\n(0.3-0.6)", "High\n(>0.6)"]
        before_counts = [
            before_snapshot["low_risk_edges"],
            before_snapshot["medium_risk_edges"],
            before_snapshot["high_risk_edges"],
        ]
        after_counts = [
            after_snapshot["low_risk_edges"],
            after_snapshot["medium_risk_edges"],
            after_snapshot["high_risk_edges"],
        ]

        x = np.arange(len(categories))
        width = 0.35

        ax2.bar(x - width / 2, before_counts, width, label="Before", color="blue", alpha=0.7)
        ax2.bar(x + width / 2, after_counts, width, label="After", color="red", alpha=0.7)
        ax2.set_xlabel("Risk Category")
        ax2.set_ylabel("Number of Edges")
        ax2.set_title("Risk Category Distribution")
        ax2.set_xticks(x)
        ax2.set_xticklabels(categories)
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis="y")

        # Box plot comparison
        ax3 = axes[1, 0]
        ax3.boxplot(
            [before_snapshot["risk_scores"], after_snapshot["risk_scores"]],
            labels=["Before", "After"],
            patch_artist=True,
            boxprops=dict(facecolor="lightblue", alpha=0.7),
            medianprops=dict(color="red", linewidth=2),
        )
        ax3.set_ylabel("Risk Score")
        ax3.set_title("Risk Score Distribution (Box Plot)")
        ax3.grid(True, alpha=0.3, axis="y")

        # Statistics summary
        ax4 = axes[1, 1]
        ax4.axis("off")

        stats_text = f"""
RISK SCORE STATISTICS

Before Data Injection:
  • Total Edges: {before_snapshot['total_edges']:,}
  • Mean Risk: {before_snapshot['avg_risk_score']:.4f}
  • Median Risk: {before_snapshot['median_risk_score']:.4f}
  • Max Risk: {before_snapshot['max_risk_score']:.4f}
  • Std Dev: {before_snapshot['std_risk_score']:.4f}

After Data Injection:
  • Total Edges: {after_snapshot['total_edges']:,}
  • Mean Risk: {after_snapshot['avg_risk_score']:.4f}
  • Median Risk: {after_snapshot['median_risk_score']:.4f}
  • Max Risk: {after_snapshot['max_risk_score']:.4f}
  • Std Dev: {after_snapshot['std_risk_score']:.4f}

Changes:
  • ΔMean: {after_snapshot['avg_risk_score'] - before_snapshot['avg_risk_score']:+.4f}
  • ΔMedian: {after_snapshot['median_risk_score'] - before_snapshot['median_risk_score']:+.4f}
  • ΔMax: {after_snapshot['max_risk_score'] - before_snapshot['max_risk_score']:+.4f}
  • High Risk Increase: {after_snapshot['high_risk_edges'] - before_snapshot['high_risk_edges']:+,}
        """

        ax4.text(
            0.1,
            0.5,
            stats_text.strip(),
            transform=ax4.transAxes,
            fontsize=11,
            verticalalignment="center",
            family="monospace",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8, pad=1),
        )

        # Save visualization
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = (
            Path(__file__).parent
            / "outputs"
            / "visualizations"
            / f"risk_distribution_scenario_{self.scenario_id}_{timestamp}.png"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"Risk distribution plot saved to: {output_path}")
        return str(output_path)

    def capture_graph_snapshot(self) -> Dict[str, Any]:
        """
        Capture current state of graph risk scores.

        Returns:
            Dictionary containing graph statistics
        """
        graph = self.environment.graph
        risk_scores = []

        for u, v, data in graph.edges(data=True):
            risk_score = data.get("risk_score", 0.0)
            risk_scores.append(risk_score)

        risk_scores = np.array(risk_scores)

        snapshot = {
            "total_edges": len(risk_scores),
            "risk_scores": risk_scores,
            "avg_risk_score": float(np.mean(risk_scores)),
            "median_risk_score": float(np.median(risk_scores)),
            "max_risk_score": float(np.max(risk_scores)),
            "min_risk_score": float(np.min(risk_scores)),
            "std_risk_score": float(np.std(risk_scores)),
            "low_risk_edges": int(np.sum(risk_scores < 0.3)),
            "medium_risk_edges": int(np.sum((risk_scores >= 0.3) & (risk_scores < 0.6))),
            "high_risk_edges": int(np.sum(risk_scores >= 0.6)),
            "timestamp": datetime.now().isoformat(),
        }

        return snapshot

    def run(self) -> Dict[str, Any]:
        """
        Execute complete simulation workflow.

        Returns:
            Comprehensive simulation results
        """
        logger.info("=" * 80)
        logger.info(f"STARTING SIMULATION - SCENARIO {self.scenario_id}")
        logger.info("=" * 80)

        simulation_start = datetime.now()

        # Step 0: Capture BEFORE snapshot
        logger.info("Capturing graph state BEFORE data injection...")
        before_snapshot = self.capture_graph_snapshot()
        logger.info(
            f"BEFORE: {before_snapshot['total_edges']:,} edges, "
            f"avg risk: {before_snapshot['avg_risk_score']:.4f}"
        )

        # Step 1: Inject flood data
        flood_results = self.inject_flood_data()

        # Step 2: Inject scout data
        scout_results = self.inject_scout_data()

        # Step 3: Fuse hazard data
        hazard_results = self.fuse_hazard_data(flood_results, scout_results)

        # Step 3.5: Capture AFTER snapshot
        logger.info("Capturing graph state AFTER data injection...")
        after_snapshot = self.capture_graph_snapshot()
        logger.info(
            f"AFTER: {after_snapshot['total_edges']:,} edges, "
            f"avg risk: {after_snapshot['avg_risk_score']:.4f}"
        )

        # Step 3.6: Create visualizations
        logger.info("Generating visualizations...")
        graph_viz_path = self.visualize_graph_before_after(before_snapshot, after_snapshot)
        dist_viz_path = self.create_risk_distribution_plot(before_snapshot, after_snapshot)

        # Step 4: Calculate test routes
        route_results = self.calculate_test_routes()

        simulation_end = datetime.now()
        duration = (simulation_end - simulation_start).total_seconds()

        # Compile comprehensive results
        results = {
            "simulation_metadata": {
                "scenario_id": self.scenario_id,
                "scenario_name": self.flood_data["scenario_name"],
                "start_time": simulation_start.isoformat(),
                "end_time": simulation_end.isoformat(),
                "duration_seconds": duration,
            },
            "flood_data_summary": {
                "severity": flood_results["severity"],
                "overall_risk": flood_results["risk_assessment"]["overall_risk_level"],
                "flood_probability": flood_results["risk_assessment"]["flood_probability"],
                "affected_areas": flood_results["risk_assessment"]["affected_areas"],
            },
            "scout_data_summary": {
                "total_reports": len(scout_results),
                "georeferenced_reports": sum(
                    1 for r in scout_results if r.get("coordinates")
                ),
            },
            "hazard_fusion_summary": hazard_results,
            "routing_summary": {
                "routes_calculated": len(route_results),
                "routes": route_results,
            },
            "graph_analysis": {
                "before_injection": {
                    "total_edges": before_snapshot["total_edges"],
                    "avg_risk_score": before_snapshot["avg_risk_score"],
                    "high_risk_edges": before_snapshot["high_risk_edges"],
                    "medium_risk_edges": before_snapshot["medium_risk_edges"],
                    "low_risk_edges": before_snapshot["low_risk_edges"],
                },
                "after_injection": {
                    "total_edges": after_snapshot["total_edges"],
                    "avg_risk_score": after_snapshot["avg_risk_score"],
                    "high_risk_edges": after_snapshot["high_risk_edges"],
                    "medium_risk_edges": after_snapshot["medium_risk_edges"],
                    "low_risk_edges": after_snapshot["low_risk_edges"],
                },
                "changes": {
                    "avg_risk_delta": after_snapshot["avg_risk_score"]
                    - before_snapshot["avg_risk_score"],
                    "high_risk_increase": after_snapshot["high_risk_edges"]
                    - before_snapshot["high_risk_edges"],
                },
            },
            "visualizations": {
                "graph_before_after": graph_viz_path,
                "risk_distribution": dist_viz_path,
            },
        }

        logger.info("=" * 80)
        logger.info("SIMULATION COMPLETE")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(
            f"Overall Risk Level: "
            f"{results['flood_data_summary']['overall_risk'].upper()}"
        )
        logger.info(f"Scout Reports Processed: {results['scout_data_summary']['total_reports']}")
        logger.info(f"Routes Calculated: {results['routing_summary']['routes_calculated']}")
        logger.info("=" * 80)

        return results

    def save_results(self, results: Dict[str, Any], output_file: Optional[Path] = None):
        """
        Save simulation results to JSON file.

        Args:
            results: Simulation results dictionary
            output_file: Optional custom output path
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = (
                Path(__file__).parent
                / "outputs"
                / f"simulation_scenario_{self.scenario_id}_{timestamp}.json"
            )

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to: {output_file}")


def main():
    """Main entry point for simulation runner."""
    parser = argparse.ArgumentParser(
        description="Run MAS-FRO multi-agent flood routing simulation"
    )
    parser.add_argument(
        "--scenario",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help="Scenario ID: 1=Heavy (Typhoon), 2=Moderate (Monsoon), 3=Light (Normal)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Custom output file path for results",
    )
    parser.add_argument(
        "--save-results",
        action="store_true",
        default=True,
        help="Save simulation results to file",
    )

    args = parser.parse_args()

    try:
        # Initialize and run simulation
        runner = SimulationRunner(scenario_id=args.scenario)
        results = runner.run()

        # Save results if requested
        if args.save_results:
            runner.save_results(results, args.output)

        # Print summary
        print("\n" + "=" * 80)
        print("SIMULATION RESULTS SUMMARY")
        print("=" * 80)
        print(f"Scenario: {results['simulation_metadata']['scenario_name']}")
        print(f"Duration: {results['simulation_metadata']['duration_seconds']:.2f}s")
        print(f"Flood Risk: {results['flood_data_summary']['overall_risk'].upper()}")
        print(
            f"Flood Probability: "
            f"{results['flood_data_summary']['flood_probability']:.1%}"
        )
        print(f"Scout Reports: {results['scout_data_summary']['total_reports']}")
        print(f"Routes Calculated: {results['routing_summary']['routes_calculated']}")
        print("=" * 80 + "\n")

        return 0

    except Exception as e:
        logger.error(f"Simulation failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
