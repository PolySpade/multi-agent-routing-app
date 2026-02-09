
import sys
import os
import time
import logging

# Ensure app modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.routing_agent import RoutingAgent

def run_non_llm_test():
    print("\n=== TESTING CLASSIC EVACUATION (NO LLM) ===")
    
    # 1. Initialize Real Environment (No Mocking)
    env = DynamicGraphEnvironment()
    if not env.graph:
        print("❌ Graph failed to load")
        return

    # 2. Initialize Agent (LLM explicitly disabled or just not used in call)
    # We pass llm_service=None to prove it works without it, 
    # OR we use the real agent but pass query=None
    agent = RoutingAgent("router_classic", env, llm_service=None)
    
    print("✅ Agent initialized (LLM Service: None)")

    # 3. Define Scenario
    # Arbitrary location in Marikina
    user_location = (14.6500, 121.1000) 
    
    print(f"📍 User Location: {user_location}")
    print("🔍 Searching for nearest evacuation center (Algorithm only)...")
    
    start_time = time.time()
    
    # 4. Execute NO-LLM Call
    # passing query=None explicitly (default)
    result = agent.find_nearest_evacuation_center(
        location=user_location,
        max_centers=3,
        query=None 
    )
    
    duration = time.time() - start_time
    
    # 5. Results
    if result:
        print(f"\n✅ RESULT FOUND in {duration:.3f}s:")
        print(f"   Shape: {result.get('center', {}).get('name')}")
        print(f"   Distance: {result.get('metrics', {}).get('total_distance'):.1f}m")
        print(f"   Time: {result.get('metrics', {}).get('estimated_time'):.1f} min")
        
        if "explanation" not in result:
             print("✅ No Explanation generated (Expected for non-LLM flow)")
        else:
             print(f"⚠️ Unexpected Explanation: {result['explanation']}")
             
    else:
        print("❌ No center found.")

if __name__ == "__main__":
    run_non_llm_test()
