# filename: masfro-backend/test_scout_agent.py
import time
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.agents.scout_agent import ScoutAgent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.environment.graph_manager import DynamicGraphEnvironment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.core.config import settings

def run_scout_test():
    """
    Initializes, runs a single step, and shuts down the ScoutAgent
    to verify its end-to-end functionality.
    """
    print("--- 🕵️  Starting ScoutAgent Test ---")

    # 1. Setup the necessary components
    # The agent needs an environment instance, even if we don't use it in this test
    print("Initializing environment...")
    environment = DynamicGraphEnvironment()
    if not environment.get_graph():
        print("❌ Test failed: Could not load the graph environment.")
        return

    # Check if credentials are set in the .env file
    if not settings.TWITTER_EMAIL or not settings.TWITTER_PASSWORD:
        print("❌ Test failed: TWITTER_EMAIL and TWITTER_PASSWORD must be set in your .env file.")
        return

    # 2. Initialize the Agent
    scout = ScoutAgent(
        agent_id="scout_tester_01",
        environment=environment,
        email=settings.TWITTER_EMAIL,
        password=settings.TWITTER_PASSWORD
    )

    # 3. Run the Agent's Lifecycle
    # A try...finally block ensures the agent's shutdown method is always called,
    # even if an error occurs during the test. This prevents zombie browser processes.
    try:
        # Start the agent and log in to X.com
        if scout.setup():
            print("\n✅ Agent setup successful (login complete).")
            
            # Run one monitoring cycle
            print("\n--- Performing agent step 1... ---")
            new_tweets = scout.step()
            print(f"--- Step 1 complete. Found {len(new_tweets)} new tweets. ---")

            # You can optionally wait and run another step
            # print("\nWaiting for 10 seconds...")
            # time.sleep(10)
            # print("\n--- Performing agent step 2... ---")
            # new_tweets_2 = scout.step()
            # print(f"--- Step 2 complete. Found {len(new_tweets_2)} new tweets. ---")
            
        else:
            print("\n❌ Test failed: Agent setup (login) was unsuccessful.")

    finally:
        # Clean up and close the browser
        print("\n--- Shutting down agent ---")
        scout.shutdown()
        print("\n--- ✅ ScoutAgent Test Finished ---")


if __name__ == "__main__":
    run_scout_test()