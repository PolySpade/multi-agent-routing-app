# filename: scripts/test_scout_simulation_mode.py

"""
Test Script: Scout Agent Simulation Mode
=========================================

Demonstrates and tests the Scout Agent's simulation mode toggle.

This script shows how to:
1. Initialize Scout Agent in simulation mode
2. Run multiple simulation steps
3. Process synthetic tweets through the complete pipeline
4. Switch between different scenarios

Author: MAS-FRO Development Team
Date: November 2025
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.scout_agent import ScoutAgent
from app.agents.hazard_agent import HazardAgent
from app.environment.graph_manager import DynamicGraphEnvironment
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_simulation_mode(scenario: int = 1, num_steps: int = 6):
    """
    Test Scout Agent simulation mode.

    Args:
        scenario: Which scenario to load (1-3)
        num_steps: Number of simulation steps to run
    """
    logger.info("=" * 80)
    logger.info("SCOUT AGENT SIMULATION MODE TEST")
    logger.info("=" * 80)

    # Initialize environment
    logger.info("\n1. Initializing environment...")
    environment = DynamicGraphEnvironment()

    # Initialize HazardAgent
    logger.info("\n2. Initializing HazardAgent...")
    hazard_agent = HazardAgent("hazard-sim", environment)

    # Initialize ScoutAgent in SIMULATION MODE
    logger.info(f"\n3. Initializing ScoutAgent in SIMULATION MODE (scenario {scenario})...")
    scout_agent = ScoutAgent(
        agent_id="scout-sim",
        environment=environment,
        hazard_agent=hazard_agent,
        simulation_mode=True,  # <-- SIMULATION MODE ENABLED
        simulation_scenario=scenario
    )

    # Link agents
    scout_agent.set_hazard_agent(hazard_agent)

    # Setup agent
    logger.info("\n4. Setting up ScoutAgent...")
    if not scout_agent.setup():
        logger.error("Failed to setup ScoutAgent")
        return False

    # Run simulation steps
    logger.info(f"\n5. Running {num_steps} simulation steps...")
    logger.info("-" * 80)

    total_tweets = 0
    total_reports = 0

    for step_num in range(1, num_steps + 1):
        logger.info(f"\n--- STEP {step_num} ---")
        tweets = scout_agent.step()

        if tweets:
            total_tweets += len(tweets)
            logger.info(f"  Processed {len(tweets)} tweets in this step")

            # Show sample tweets
            for i, tweet in enumerate(tweets[:3], 1):
                logger.info(f"  Sample {i}: {tweet.get('text', 'N/A')[:60]}...")
        else:
            logger.info("  No more tweets available")
            break

    # Shutdown
    logger.info("\n6. Shutting down...")
    scout_agent.shutdown()

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SIMULATION TEST COMPLETE")
    logger.info("=" * 80)
    logger.info(f"  Total steps run: {step_num}")
    logger.info(f"  Total tweets processed: {total_tweets}")
    logger.info(f"  Simulation scenario: {scenario}")
    logger.info("=" * 80)

    return True


def test_all_scenarios():
    """Test all three simulation scenarios."""
    logger.info("\n\n" + "=" * 80)
    logger.info("TESTING ALL SCENARIOS")
    logger.info("=" * 80)

    scenarios = [
        (1, "Typhoon Scenario - Heavy Flooding"),
        (2, "Monsoon Rain - Moderate Flooding"),
        (3, "Light Rain - Minimal Impact")
    ]

    for scenario_num, scenario_name in scenarios:
        logger.info(f"\n\n{'='*80}")
        logger.info(f"SCENARIO {scenario_num}: {scenario_name}")
        logger.info("=" * 80)

        test_simulation_mode(scenario=scenario_num, num_steps=3)


def compare_modes():
    """
    Demonstrate the difference between simulation mode and scraping mode.
    """
    logger.info("\n\n" + "=" * 80)
    logger.info("COMPARING SIMULATION MODE vs SCRAPING MODE")
    logger.info("=" * 80)

    environment = DynamicGraphEnvironment()

    # Simulation mode
    logger.info("\n--- SIMULATION MODE ---")
    scout_sim = ScoutAgent(
        agent_id="scout-sim-demo",
        environment=environment,
        simulation_mode=True,
        simulation_scenario=1
    )
    logger.info("Simulation mode initialization: SUCCESS")
    logger.info("  - No Twitter credentials needed")
    logger.info("  - No Selenium WebDriver needed")
    logger.info("  - Uses synthetic data from files")
    logger.info("  - Deterministic and reproducible")

    # Scraping mode (just show initialization, don't actually run)
    logger.info("\n--- SCRAPING MODE ---")
    logger.info("Scraping mode would require:")
    logger.info("  - Twitter/X credentials (email + password)")
    logger.info("  - Selenium WebDriver and Chrome browser")
    logger.info("  - Active internet connection")
    logger.info("  - Subject to Twitter rate limits and UI changes")
    logger.info("  - Currently NOT WORKING (X.com scraping broken)")

    logger.info("\n" + "=" * 80)
    logger.info("RECOMMENDATION: Use simulation_mode=True for testing")
    logger.info("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Scout Agent simulation mode")
    parser.add_argument(
        "--scenario",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="Simulation scenario to test (1-3)"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=6,
        help="Number of simulation steps to run"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Test all scenarios"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare simulation vs scraping modes"
    )

    args = parser.parse_args()

    try:
        if args.compare:
            compare_modes()
        elif args.all:
            test_all_scenarios()
        else:
            test_simulation_mode(scenario=args.scenario, num_steps=args.steps)

        logger.info("\n✅ All tests completed successfully!")
        sys.exit(0)

    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}", exc_info=True)
        sys.exit(1)
