
"""
Standalone Agent Runner for MAS-FRO

This script allows running individual agents in isolation for testing and debugging.
It mocks necessary dependencies (DynamicGraphEnvironment, MessageQueue) and
executes the agent's step() method in a loop.

Usage:
    python run_standalone_agent.py --agent flood
    python run_standalone_agent.py --agent scout --scenario 1
"""

import argparse
import time
import logging
import sys
import os
from unittest.mock import MagicMock
from datetime import datetime

# Ensure 'app' module can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("StandaloneRunner")

# Mock Classes
class MockMessageQueue:
    """Mocks the MessageQueue to capture and print messages instead of sending them."""
    def __init__(self):
        self.messages = []

    def register_agent(self, agent_id):
        logger.info(f"[MockMessageQueue] Registered agent: {agent_id}")

    def send_message(self, message):
        logger.info(f"[MockMessageQueue] Message captured from {message.sender} to {message.receiver}")
        logger.info(f"  Content: {message.content}")
        self.messages.append(message)

class MockEnvironment:
    """Mocks the DynamicGraphEnvironment."""
    def __init__(self):
        self.graph = MagicMock()
        logger.info("[MockEnvironment] Initialized mock environment")

# Agent Runner Functions
def run_flood_agent(args):
    try:
        from app.agents.flood_agent import FloodAgent
    except ImportError as e:
        logger.error(f"Failed to import FloodAgent: {e}")
        return

    logger.info("Initializing FloodAgent...")
    env = MockEnvironment()
    mq = MockMessageQueue()
    
    agent = FloodAgent(
        agent_id="flood_agent_standalone",
        environment=env,
        message_queue=mq,
        use_simulated=not args.real, # If real APIs enabled, disable simulation (or keep as fallback)
        use_real_apis=args.real, 
        enable_llm=False 
    )

    logger.info("Starting FloodAgent loop...")
    try:
        step_count = 0
        while True:
            step_count += 1
            logger.info(f"--- Step {step_count} ---")
            agent.step()
            
            if args.once:
                break
                
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Stopping FloodAgent...")

def run_scout_agent(args):
    try:
        from app.agents.scout_agent import ScoutAgent
    except ImportError as e:
        logger.error(f"Failed to import ScoutAgent: {e}")
        return

    logger.info("Initializing ScoutAgent...")
    env = MockEnvironment()
    mq = MockMessageQueue()
    
    agent = ScoutAgent(
        agent_id="scout_agent_standalone",
        environment=env,
        message_queue=mq,
        simulation_scenario=args.scenario,
        use_ml_in_simulation=False, # Disable ML for lighter standalone test
        enable_llm=False
    )
    
    if hasattr(agent, 'setup'):
        agent.setup()

    logger.info("Starting ScoutAgent loop...")
    try:
        step_count = 0
        while True:
            step_count += 1
            logger.info(f"--- Step {step_count} ---")
            agent.step()
            
            if args.once:
                break
                
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Stopping ScoutAgent...")

def main():
    parser = argparse.ArgumentParser(description="Run MAS-FRO agents in standalone mode.")
    parser.add_argument("--agent", type=str, required=True, choices=["flood", "scout"], help="Agent to run")
    parser.add_argument("--interval", type=int, default=5, help="Interval between steps in seconds")
    parser.add_argument("--once", action="store_true", help="Run only one step and exit")
    parser.add_argument("--scenario", type=int, default=1, help="Simulation scenario (for ScoutAgent)")
    parser.add_argument("--real", action="store_true", help="Enable Real APIs (FloodAgent)")

    args = parser.parse_args()

    if args.agent == "flood":
        # Pass the real flag to the agent runner
        run_flood_agent(args)
    elif args.agent == "scout":
        run_scout_agent(args)
    else:
        logger.error(f"Unknown agent: {args.agent}")

if __name__ == "__main__":
    main()
