# filename: tests/test_agent_viewer_integration.py
import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient
import logging

# Add parent dir to path
sys.path.append(str(Path(__file__).parent.parent))

from app.main import app
from app.services.agent_viewer_service import get_agent_viewer_service

client = TestClient(app)

def test_agent_viewer_endpoints():
    print("Testing /api/v1/agents/...")
    response = client.get("/api/v1/agents/")
    if response.status_code != 200:
        print(f"FAILED to get agents: {response.text}")
        return
    print(f"Agents status: {response.status_code} OK")
    agents = response.json()
    print(f"Found {len(agents)} agents.")

    # Generate some logs
    logger = logging.getLogger("app.agents.test")
    logger.info("Test log message for viewer")
    
    print("Testing /api/v1/agents/logs...")
    response = client.get("/api/v1/agents/logs")
    if response.status_code != 200:
        print(f"FAILED to get logs: {response.text}")
        return
    logs = response.json()
    print(f"Logs status: {response.status_code} OK. Found {len(logs)} logs.")
    
    # Verify our log is there
    found = any("Test log message" in log["message"] for log in logs)
    if found:
        print("SUCCESS: Found test log message in viewer.")
    else:
        print("WARNING: Did not find test log message. (Handler might not be attached to 'app.agents.test' yet)")

def test_scout_injection():
    print("\nTesting Scout Injection...")
    payload = {
        "text": "HELP! Flooding in Marikina near the bridge! #RescuePH",
        "location": "Marikina Bridge",
    }
    response = client.post("/api/v1/agents/scout/inject", json=payload)
    if response.status_code == 200:
        print("SUCCESS: Scout injection accepted.")
        print(response.json())
    else:
        print(f"FAILED Scout injection: {response.status_code} - {response.text}")

def test_flood_injection():
    print("\nTesting Flood Injection...")
    payload = {
        "text": "PAGASA Advisory: Heavy rainfall warning red alert.",
        "type": "pagasa",
        "severity": "critical"
    }
    response = client.post("/api/v1/agents/flood/inject", json=payload)
    if response.status_code == 200:
        print("SUCCESS: Flood injection accepted.")
        print(response.json())
    else:
        print(f"FAILED Flood injection: {response.status_code} - {response.text}")

if __name__ == "__main__":
    # Initialize service first (mimic startup)
    get_agent_viewer_service()
    
    test_agent_viewer_endpoints()
    test_scout_injection()
    test_flood_injection()
