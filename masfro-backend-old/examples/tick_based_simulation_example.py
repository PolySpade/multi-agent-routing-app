"""
Tick-Based Simulation Example

Demonstrates how to use the refactored tick-based SimulationManager
for coordinated multi-agent execution.

This example shows:
1. Setting up the SimulationManager with agents
2. Starting a simulation with a specific mode
3. Running ticks to execute agents in a coordinated manner
4. Adding route requests that get processed in the routing phase
5. Time step progression and GeoTIFF scenario synchronization

Author: MAS-FRO Development Team
Date: November 2025
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.flood_agent import FloodAgent
from app.agents.scout_agent import ScoutAgent
from app.agents.hazard_agent import HazardAgent
from app.agents.routing_agent import RoutingAgent
from app.agents.evacuation_manager_agent import EvacuationManagerAgent
from app.services.simulation_manager import get_simulation_manager
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    Main example demonstrating tick-based simulation.
    """
    logger.info("=== Tick-Based Simulation Example ===\n")

    # ========== STEP 1: Initialize Environment and Agents ==========
    logger.info("Step 1: Initializing environment and agents...")

    # Create shared environment
    environment = DynamicGraphEnvironment()

    # Create agents
    flood_agent = FloodAgent(
        agent_id="flood_001",
        environment=environment,
        use_simulated=True,  # Use simulated data for demo
        use_real_apis=False  # Disable real APIs for demo
    )

    scout_agent = ScoutAgent(
        agent_id="scout_001",
        environment=environment,
        simulation_mode=True,  # Use synthetic data for demo
        simulation_scenario=1
    )

    hazard_agent = HazardAgent(
        agent_id="hazard_001",
        environment=environment,
        enable_geotiff=True  # Enable GeoTIFF flood simulation
    )

    routing_agent = RoutingAgent(
        agent_id="routing_001",
        environment=environment
    )

    evacuation_manager = EvacuationManagerAgent(
        agent_id="evac_mgr_001",
        environment=environment
    )

    # Link agents for dependencies
    evacuation_manager.set_routing_agent(routing_agent)
    evacuation_manager.set_hazard_agent(hazard_agent)

    logger.info("✓ Agents initialized\n")

    # ========== STEP 2: Configure SimulationManager ==========
    logger.info("Step 2: Configuring SimulationManager...")

    sim_manager = get_simulation_manager()
    sim_manager.set_agents(
        flood_agent=flood_agent,
        scout_agent=scout_agent,
        hazard_agent=hazard_agent,
        routing_agent=routing_agent,
        evacuation_manager=evacuation_manager,
        environment=environment
    )

    logger.info("✓ SimulationManager configured\n")

    # ========== STEP 3: Start Simulation ==========
    logger.info("Step 3: Starting simulation in MEDIUM mode...")

    start_result = sim_manager.start(mode="medium")
    logger.info(f"✓ Simulation started: {start_result['message']}")
    logger.info(f"  Return period: {start_result['return_period']}")
    logger.info(f"  Time step: {start_result['time_step']}\n")

    # ========== STEP 4: Add Route Requests ==========
    logger.info("Step 4: Adding route requests...")

    # Marikina City Hall to Marikina Sports Center
    sim_manager.add_route_request(
        start=(14.6507, 121.1029),  # City Hall
        end=(14.6391, 121.0957),    # Sports Center
        preferences={"avoid_floods": True}
    )

    logger.info("✓ Route request added\n")

    # ========== STEP 5: Run Simulation Ticks ==========
    logger.info("Step 5: Running simulation ticks...\n")

    # Run 5 ticks to simulate progression
    for tick in range(1, 6):
        logger.info(f"\n{'='*60}")
        logger.info(f"TICK {tick}")
        logger.info(f"{'='*60}\n")

        # Execute one tick
        tick_result = sim_manager.run_tick()

        # Display results
        logger.info(f"\n--- Tick {tick} Results ---")
        logger.info(f"Time step: {tick_result['time_step']}/18")
        logger.info(f"Mode: {tick_result['mode']}")

        # Collection phase results
        collection = tick_result['phases']['collection']
        logger.info(
            f"Collection: {collection['flood_data_collected']} flood points, "
            f"{collection['scout_reports_collected']} scout reports"
        )

        # Fusion phase results
        fusion = tick_result['phases']['fusion']
        logger.info(f"Fusion: {fusion['edges_updated']} edges updated")

        # Routing phase results
        routing = tick_result['phases']['routing']
        logger.info(f"Routing: {routing['routes_processed']} routes processed")

        # Add another route request every 2 ticks
        if tick % 2 == 0:
            logger.info("\n--- Adding new route request ---")
            sim_manager.add_route_request(
                start=(14.6500, 121.1000),
                end=(14.6450, 121.1050),
                preferences={"fastest": True}
            )

    # ========== STEP 6: Check Status ==========
    logger.info("\n\nStep 6: Checking simulation status...")

    status = sim_manager.get_status()
    logger.info(f"\n--- Simulation Status ---")
    logger.info(f"State: {status['state']}")
    logger.info(f"Mode: {status['mode']}")
    logger.info(f"Total ticks: {status['tick_count']}")
    logger.info(f"Current time step: {status['current_time_step']}/18")
    logger.info(f"Return period: {status['return_period']}")
    logger.info(f"Pending routes: {status['pending_routes']}")
    logger.info(f"Runtime: {status.get('current_session_seconds', 0):.2f}s\n")

    # ========== STEP 7: Stop Simulation ==========
    logger.info("Step 7: Stopping simulation...")

    stop_result = sim_manager.stop()
    logger.info(f"✓ Simulation stopped: {stop_result['message']}")
    logger.info(f"  Total runtime: {stop_result['total_runtime_seconds']}s")
    logger.info(f"  Total ticks: {stop_result['tick_count']}\n")

    # ========== STEP 8: Reset Simulation ==========
    logger.info("Step 8: Resetting simulation...")

    reset_result = sim_manager.reset()
    logger.info(f"✓ Simulation reset: {reset_result['message']}")
    logger.info(f"  Previous state: {reset_result['previous_state']}")
    logger.info(f"  Previous ticks: {reset_result['previous_ticks']}\n")

    logger.info("=== Tick-Based Simulation Example Complete ===\n")

    # ========== STEP 9: Demonstrate Time Step Control ==========
    logger.info("\nBonus: Demonstrating explicit time step control...")

    # Start simulation again
    sim_manager.start(mode="heavy")
    logger.info("✓ Simulation restarted in HEAVY mode (rr03 - 10-year flood)\n")

    # Jump to specific time steps
    for time_step in [1, 5, 10, 15, 18]:
        logger.info(f"\n--- Jumping to time step {time_step} ---")
        tick_result = sim_manager.run_tick(time_step=time_step)
        logger.info(
            f"Tick {tick_result['tick']} at time_step {time_step}/18: "
            f"{tick_result['phases']['fusion']['edges_updated']} edges updated"
        )

    # Stop and reset
    sim_manager.stop()
    sim_manager.reset()

    logger.info("\n\n=== All Examples Complete ===")


def example_batch_route_requests():
    """
    Example demonstrating batch route request processing.
    """
    logger.info("\n\n=== Batch Route Request Example ===\n")

    # Get configured sim_manager (assumes main() was run first)
    sim_manager = get_simulation_manager()

    # Start simulation
    sim_manager.start(mode="light")

    # Add multiple route requests
    routes = [
        ((14.650, 121.100), (14.640, 121.110)),
        ((14.645, 121.105), (14.655, 121.095)),
        ((14.652, 121.098), (14.642, 121.108)),
    ]

    for start, end in routes:
        sim_manager.add_route_request(start, end)

    logger.info(f"Added {len(routes)} route requests")

    # Run one tick to process all requests
    tick_result = sim_manager.run_tick()

    routing_result = tick_result['phases']['routing']
    logger.info(
        f"Processed {routing_result['routes_processed']} routes in single tick"
    )

    sim_manager.stop()
    sim_manager.reset()


if __name__ == "__main__":
    # Run main example
    main()

    # Run batch example
    # example_batch_route_requests()
