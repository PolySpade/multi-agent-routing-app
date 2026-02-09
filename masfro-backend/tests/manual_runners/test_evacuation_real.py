
import sys
import os
import logging
from typing import Tuple

# Ensure app modules are importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.routing_agent import RoutingAgent
from app.agents.evacuation_manager_agent import EvacuationManagerAgent
from app.services.llm_service import LLMService

def run_real_scenario():
    print("\n=== INITIALIZING REAL ENVIRONMENT (This may take a few seconds) ===")
    
    # 1. Initialize Real Graph Environment
    # This will load 'marikina_graph.graphml' from disk
    env = DynamicGraphEnvironment()
    
    if not env.graph:
        print("❌ CRITICAL: Failed to load road network graph. Cannot proceed.")
        return

    print("✅ Graph Environment Loaded")

    # 2. Initialize Real LLM Service
    # Connects to local Ollama instance
    llm_service = LLMService()
    if not llm_service.is_available():
        print("⚠️ WARNING: LLM Service is reported as unavailable. Check Ollama.")
    else:
        print("✅ LLM Service Connected")

    # 3. Initialize Agents
    routing_agent = RoutingAgent(
        agent_id="routing_agent_real",
        environment=env,
        llm_service=llm_service
    )
    
    evac_manager = EvacuationManagerAgent(
        agent_id="evac_manager_real",
        environment=env
    )
    evac_manager.set_routing_agent(routing_agent)
    
    print("✅ Agents Initialized & Linked")

    # 4. Define Scenario
    # Location: Arbitrary point near Marikina River (e.g., near Riverbanks Center)
    user_location = (14.6300, 121.0800) 
    
    # Distress Call
    distress_message = "Help! I am trapped by floodwaters near the river with my grandfather. We need rescue immediately!"
    
    print(f"\n=== EXECUTING SCENARIO ===")
    print(f"📍 User Location: {user_location}")
    print(f"🆘 Distress Message: '{distress_message}'")
    
    # 5. Execute
    response = evac_manager.handle_distress_call(user_location, distress_message)
    
    # 6. Analyze Results
    print(f"\n=== RESULTS ===")
    print(f"Status: {response.get('status')}")
    
    if response.get('status') == 'success':
        print(f"✅ Action: {response.get('action')}")
        print(f"🏥 Target Center: {response.get('target_center')}")
        print(f"📏 Distance: {response.get('route_summary', {}).get('distance')}m")
        print(f"⏱️ Est. Time: {response.get('route_summary', {}).get('time_min')} mins")
        print(f"⚠️ Risk Level: {response.get('route_summary', {}).get('risk')}")
        print(f"📝 Explanation:\n   {response.get('explanation')}")
        
        # Validation checks
        if "trapped" in distress_message.lower() and response.get('explanation'):
            print("\n[Validation] NLP Context used? Likely YES (Explanation generated)")
    else:
        print(f"❌ Failed: {response.get('message')}")

if __name__ == "__main__":
    run_real_scenario()
