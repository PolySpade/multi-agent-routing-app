# filename: masfro-backend/test_graph_updates.py

import random
import osmnx as ox
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.environment.graph_manager import DynamicGraphEnvironment

def verify_risk_update():
    print("--- Starting Graph Update Verification ---")

    # Force OSMnx to clear its cache to ensure a fresh download.
    # log_console=True will give us more detailed download status.
    try:
        print("Attempting to clear OSMnx cache...")
        ox.settings.use_cache = True
        ox.settings.log_console = True
        ox.clear_cache()
        print("Cache cleared successfully.")
    except Exception as e:
        print(f"Could not clear cache: {e}")

    # 1. Initialize the environment.
    env = DynamicGraphEnvironment()

    # 2. Check if the graph was loaded successfully.
    graph = env.get_graph()
    if graph is None or graph.number_of_edges() == 0:
        print("\n❌ FAILURE: Graph is empty or could not be loaded. Aborting verification.")
        print("   Please check your internet connection and ensure you can access openstreetmap.org.")
        return

    print(f"Graph loaded with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")

    # The rest of the script is the same...
    random_edge = random.choice(list(graph.edges(keys=True, data=True)))
    u, v, key, initial_data = random_edge

    print("\n" + "="*40)
    print(f"🕵️  INSPECTING RANDOM EDGE:")
    print(f"     Nodes: ({u}) -> ({v})")
    print(f"     Key: {key}")
    print("="*40)

    print("\n--- 🔎 BEFORE UPDATE ---")
    initial_length = initial_data.get('length', 'N/A')
    initial_risk = initial_data.get('risk_score', 'N/A')
    initial_weight = initial_data.get('weight', 'N/A')
    print(f"  Length: {initial_length:.2f}")
    print(f"  Risk Score: {initial_risk}")
    print(f"  A* Weight (length * risk): {initial_weight:.2f}")

    new_risk_factor = 10.0
    print(f"\n--- ⚡️ APPLYING UPDATE: Setting risk_score to {new_risk_factor} ---")
    env.update_edge_risk(u, v, key, new_risk_factor)

    print("\n--- 🔎 AFTER UPDATE ---")
    updated_data = graph.edges[u, v, key]
    updated_risk = updated_data.get('risk_score', 'N/A')
    updated_weight = updated_data.get('weight', 'N/A')
    print(f"  Length: {initial_length:.2f} (should be unchanged)")
    print(f"  New Risk Score: {updated_risk}")
    print(f"  New A* Weight: {updated_weight:.2f}")

    expected_weight = initial_length * new_risk_factor
    if abs(updated_weight - expected_weight) < 1e-9:
        print("\n✅ SUCCESS: The A* weight was correctly updated (length * new risk score).")
    else:
        print(f"\n❌ FAILURE: The new weight {updated_weight} does not match the expected {expected_weight}.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_risk_update()