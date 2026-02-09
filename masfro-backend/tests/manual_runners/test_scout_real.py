import os
import sys
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from unittest.mock import MagicMock
from app.agents.scout_agent import ScoutAgent
from app.environment.graph_manager import DynamicGraphEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TestScoutReal")

def run_test():
    print("==================================================")
    print(" TESTING SCOUT AGENT (REAL LLM)")
    print("==================================================")

    # 1. Setup Environment
    mock_env = MagicMock(spec=DynamicGraphEnvironment)
    mock_mq = MagicMock()
    
    # 2. Initialize Agent
    print("\n[Init] Initializing ScoutAgent...")
    try:
        agent = ScoutAgent(
            agent_id="scout_test_01",
            environment=mock_env,
            message_queue=mock_mq,
            enable_llm=True
        )
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return

    # Check if LLM is actually enabled
    if not agent.is_llm_enabled():
        print("⚠️ WARNING: LLM Service is NOT available. Falling back to NLP.")
    else:
        print("✅ LLM Service is ENABLED.")

    # 3. Define Test Cases (Simulated Tweets)
    test_tweets = [
        "FLOOD ALERT: Water level at Marikina Bridge is rising fast! Now at 16 meters. #MarikinaFloods",
        "Stranded at Tumana, chest deep water. Need rescue immediately!",
        "Just light rain here in Sto. Nino, gutter deep only. Passable to all vehicles.",
        "Traffic heavy near S&R Marikina, flood waters identifiable.", # S&R might not be in CSV
    ]

    # 4. Run Analysis
    print("\n[Test] Processing Reports...")
    
    for i, text in enumerate(test_tweets):
        print(f"\n--- Report {i+1} ---")
        print(f"📝 Input: \"{text}\"")
        
        # Analyze Text
        print("   > Analyzing...", end=" ", flush=True)
        try:
            # We access the internal method directly to see the raw result
            result = agent._analyze_text(text)
            print("Done.")
            
            if result:
                print(f"   ✅ Result: {result}")
                
                # Check Geocoding
                loc_name = result.get('location')
                if loc_name:
                    print(f"   > Geocoding '{loc_name}'...", end=" ", flush=True)
                    coords = agent._geocode_location(loc_name)
                    if coords:
                        print(f"📍 Found: {coords}")
                    else:
                        print("❌ Not found.")
                else:
                    print("   ℹ️ No location extracted.")
            else:
                print("   ❌ No result (None returned).")
                
        except Exception as e:
            print(f"\n   ❌ Error: {e}")

    print("\n==================================================")
    print(" TEST COMPLETE")
    print("==================================================")

if __name__ == "__main__":
    run_test()
