"""
Simulation Visualization Test Script

This script tests the simulation_manager by:
1. Starting a simulation with a chosen mode (light/medium/heavy)
2. Running for a specified duration in seconds
3. Visualizing graph risk score changes over time
4. Displaying flood and scout data being processed
5. Generating statistics and plots

Usage:
    uv run python test_simulation_visualization.py --mode medium --duration 60
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime
import argparse
import json
import os

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.services.simulation_manager import get_simulation_manager
from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.flood_agent import FloodAgent
from app.agents.scout_agent import ScoutAgent
from app.agents.hazard_agent import HazardAgent
from app.agents.routing_agent import RoutingAgent
from app.agents.evacuation_manager_agent import EvacuationManagerAgent


class SimulationVisualizer:
    """Visualizes simulation execution and graph changes."""

    def __init__(self, mode: str = "medium", duration_seconds: int = 60):
        self.mode = mode
        self.duration_seconds = duration_seconds
        self.tick_data = []
        self.simulation_manager = None
        self.environment = None
        self.start_time = None

    async def setup(self):
        """Initialize all agents and simulation manager."""
        print(f"\n{'='*80}")
        print(f"  SIMULATION VISUALIZATION TEST")
        print(f"  Mode: {self.mode.upper()}")
        print(f"  Duration: {self.duration_seconds} seconds")
        print(f"{'='*80}\n")

        # Create environment
        print("📊 Initializing graph environment...")
        self.environment = DynamicGraphEnvironment()
        num_nodes = self.environment.graph.number_of_nodes()
        num_edges = self.environment.graph.number_of_edges()
        print(f"   ✓ Graph loaded: {num_nodes} nodes, {num_edges} edges\n")

        # Create agents
        print("🤖 Initializing agents...")
        hazard_agent = HazardAgent("hazard_001", self.environment)
        flood_agent = FloodAgent("flood_001", self.environment, hazard_agent=hazard_agent)
        scout_agent = ScoutAgent("scout_001", self.environment, simulation_mode=True)
        routing_agent = RoutingAgent("routing_001", self.environment)
        evacuation_manager = EvacuationManagerAgent("evac_001", self.environment)

        # Link agents
        flood_agent.set_hazard_agent(hazard_agent)
        evacuation_manager.set_hazard_agent(hazard_agent)
        evacuation_manager.set_routing_agent(routing_agent)

        print("   ✓ FloodAgent initialized")
        print("   ✓ ScoutAgent initialized (simulation mode)")
        print("   ✓ HazardAgent initialized")
        print("   ✓ RoutingAgent initialized")
        print("   ✓ EvacuationManagerAgent initialized\n")

        # Setup simulation manager
        print("⚙️  Configuring simulation manager...")
        self.simulation_manager = get_simulation_manager()
        self.simulation_manager.set_agents(
            flood_agent=flood_agent,
            scout_agent=scout_agent,
            hazard_agent=hazard_agent,
            routing_agent=routing_agent,
            evacuation_manager=evacuation_manager,
            environment=self.environment,
            ws_manager=None  # No WebSocket for testing
        )
        print("   ✓ Simulation manager configured\n")

    async def run_simulation(self):
        """Run the simulation and collect data."""
        # Start simulation
        print(f"▶️  Starting simulation (mode={self.mode})...")
        result = await self.simulation_manager.start(mode=self.mode)
        print(f"   ✓ Simulation started: {result['message']}")
        print(f"   Return Period: {result['return_period']}")
        print(f"   Initial Time Step: {result['time_step']}/18\n")

        # Track start time
        self.start_time = time.time()
        target_end_time = self.start_time + self.duration_seconds

        # Run ticks based on duration
        print(f"🔄 Running simulation for {self.duration_seconds} seconds...\n")
        print(f"{'Tick':<6} {'Elapsed (s)':<12} {'Events':<8} {'Flood?':<8} {'Scout?':<8} {'Edges':<10} {'Avg Risk':<10}")
        print(f"{'-'*80}")

        tick_num = 0
        while time.time() < target_end_time:
            tick_num += 1
            # Collect pre-tick stats
            pre_risk_scores = [
                self.environment.graph[u][v][k].get('risk_score', 0.0)
                for u, v, k in self.environment.graph.edges(keys=True)
            ]
            pre_avg_risk = sum(pre_risk_scores) / len(pre_risk_scores) if pre_risk_scores else 0.0

            # Run one tick
            tick_result = self.simulation_manager.run_tick()

            # Extract tick data
            clock = self.simulation_manager._simulation_clock
            collection = tick_result['phases']['collection']
            fusion = tick_result['phases']['fusion']

            has_flood = collection['flood_data_collected'] > 0
            has_scout = collection['scout_reports_collected'] > 0
            edges_updated = fusion['edges_updated']

            # Collect post-tick stats
            post_risk_scores = [
                self.environment.graph[u][v][k].get('risk_score', 0.0)
                for u, v, k in self.environment.graph.edges(keys=True)
            ]
            post_avg_risk = sum(post_risk_scores) / len(post_risk_scores) if post_risk_scores else 0.0

            # Calculate elapsed time
            elapsed = time.time() - self.start_time

            # Store tick data
            tick_data = {
                'tick': tick_num,
                'elapsed': elapsed,
                'clock': clock,
                'time_step': self.simulation_manager.current_time_step,
                'events_processed': collection['events_processed'],
                'has_flood': has_flood,
                'has_scout': has_scout,
                'edges_updated': edges_updated,
                'pre_avg_risk': pre_avg_risk,
                'post_avg_risk': post_avg_risk,
                'flood_data': self.simulation_manager.shared_data_bus.get('flood_data', {}),
                'scout_data': self.simulation_manager.shared_data_bus.get('scout_data', [])
            }
            self.tick_data.append(tick_data)

            # Print tick summary
            flood_icon = "🌧️ " if has_flood else "  "
            scout_icon = "📱" if has_scout else "  "
            print(f"{tick_num:<6} {elapsed:<12.2f} {collection['events_processed']:<8} {flood_icon:<8} {scout_icon:<8} {edges_updated:<10} {post_avg_risk:<10.4f}")

            # Wait a bit to simulate real-time
            await asyncio.sleep(0.1)

        print(f"{'-'*80}\n")

        # Stop simulation
        print("⏸️  Stopping simulation...")
        stop_result = await self.simulation_manager.stop()
        print(f"   ✓ Simulation stopped")
        print(f"   Total runtime: {stop_result['total_runtime_seconds']}s")
        print(f"   Total ticks: {stop_result['tick_count']}\n")

    def analyze_results(self):
        """Analyze and display simulation results."""
        print(f"{'='*80}")
        print(f"  SIMULATION ANALYSIS")
        print(f"{'='*80}\n")

        # Overall statistics
        total_ticks = len(self.tick_data)
        ticks_with_flood = sum(1 for t in self.tick_data if t['has_flood'])
        ticks_with_scout = sum(1 for t in self.tick_data if t['has_scout'])
        ticks_with_updates = sum(1 for t in self.tick_data if t['edges_updated'] > 0)

        print("📈 Overall Statistics:")
        print(f"   Total ticks executed: {total_ticks}")
        print(f"   Ticks with flood data: {ticks_with_flood} ({ticks_with_flood/total_ticks*100:.1f}%)")
        print(f"   Ticks with scout data: {ticks_with_scout} ({ticks_with_scout/total_ticks*100:.1f}%)")
        print(f"   Ticks with graph updates: {ticks_with_updates} ({ticks_with_updates/total_ticks*100:.1f}%)\n")

        # Risk score progression
        print("📊 Risk Score Progression:")
        initial_risk = self.tick_data[0]['post_avg_risk']
        peak_risk = max(t['post_avg_risk'] for t in self.tick_data)
        final_risk = self.tick_data[-1]['post_avg_risk']
        peak_tick = next(t['tick'] for t in self.tick_data if t['post_avg_risk'] == peak_risk)

        print(f"   Initial avg risk: {initial_risk:.4f}")
        print(f"   Peak avg risk: {peak_risk:.4f} (at tick {peak_tick})")
        print(f"   Final avg risk: {final_risk:.4f}")
        print(f"   Risk increase: {(final_risk - initial_risk):.4f} ({(final_risk/initial_risk - 1)*100 if initial_risk > 0 else 0:.1f}%)\n")

        # Flood data samples
        flood_ticks = [t for t in self.tick_data if t['has_flood']]
        if flood_ticks:
            print("🌧️  Sample Flood Data:")
            sample = flood_ticks[0]
            flood_data = sample['flood_data']
            if 'river_levels' in flood_data:
                for station, data in list(flood_data['river_levels'].items())[:2]:
                    print(f"   {station}: {data.get('water_level_m', 'N/A')}m ({data.get('status', 'N/A')})")
            if 'weather' in flood_data:
                weather = flood_data['weather']
                print(f"   Rainfall: {weather.get('rainfall_1h_mm', 'N/A')}mm/hr")
            print()

        # Scout data samples
        scout_ticks = [t for t in self.tick_data if t['has_scout']]
        if scout_ticks:
            print("📱 Sample Scout Reports:")
            sample = scout_ticks[0]
            scout_data = sample['scout_data']
            for report in scout_data[:2]:  # Show first 2 reports
                location = report.get('location', 'Unknown')
                severity = report.get('severity', 0)
                report_type = report.get('report_type', 'unknown')
                print(f"   {location}: severity={severity:.2f}, type={report_type}")
            print()

        # Timeline visualization
        print("📉 Risk Timeline (every 5 ticks):")
        print(f"   {'Tick':<8} {'Avg Risk':<12} {'Visual':<40}")
        print(f"   {'-'*60}")
        for i in range(0, len(self.tick_data), 5):
            tick = self.tick_data[i]
            risk = tick['post_avg_risk']
            bar_length = int(risk * 40)
            bar = '█' * bar_length
            print(f"   {tick['tick']:<8} {risk:<12.4f} {bar}")
        print()

        # Save detailed data to JSON
        output_file = Path(f"simulation_test_{self.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w') as f:
            json.dump({
                'mode': self.mode,
                'duration_seconds': self.duration_seconds,
                'statistics': {
                    'total_ticks': total_ticks,
                    'ticks_with_flood': ticks_with_flood,
                    'ticks_with_scout': ticks_with_scout,
                    'initial_risk': initial_risk,
                    'peak_risk': peak_risk,
                    'final_risk': final_risk,
                },
                'tick_data': self.tick_data
            }, f, indent=2, default=str)

        print(f"💾 Detailed results saved to: {output_file}\n")

    async def run(self):
        """Main execution flow."""
        try:
            await self.setup()
            await self.run_simulation()
            self.analyze_results()

            print(f"{'='*80}")
            print(f"  ✅ SIMULATION TEST COMPLETE")
            print(f"{'='*80}\n")

        except Exception as e:
            print(f"\n❌ Error during simulation: {e}")
            import traceback
            traceback.print_exc()

            # Try to stop simulation if it's running
            if self.simulation_manager and self.simulation_manager.is_running:
                print("\n🛑 Attempting to stop simulation...")
                await self.simulation_manager.stop()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Test and visualize flood simulation')
    parser.add_argument(
        '--mode',
        choices=['light', 'medium', 'heavy'],
        default='medium',
        help='Simulation mode (default: medium)'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Duration to run simulation in seconds (default: 60)'
    )

    args = parser.parse_args()

    visualizer = SimulationVisualizer(mode=args.mode, duration_seconds=args.duration)
    await visualizer.run()


if __name__ == "__main__":
    asyncio.run(main())
