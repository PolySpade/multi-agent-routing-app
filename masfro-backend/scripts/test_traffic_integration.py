#!/usr/bin/env python3
# filename: scripts/test_traffic_integration.py
# -*- coding: utf-8 -*-

"""
Test script for Google Maps Traffic API integration.

This script tests the traffic service and agent without running the full
FastAPI server. Use it to verify your API key and configuration.

Usage:
    cd masfro-backend
    uv run python scripts/test_traffic_integration.py
"""

import sys
import os
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.google_traffic_service import GoogleTrafficService
from app.agents.traffic_agent import TrafficAgent
from app.environment.graph_manager import DynamicGraphEnvironment
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_traffic_service():
    """Test 1: GoogleTrafficService basic functionality."""
    print("\n" + "="*70)
    print("TEST 1: Google Traffic Service")
    print("="*70)

    try:
        service = GoogleTrafficService()
        print("[OK] Service initialized successfully")
        print(f"   API Key: {service.api_key[:10]}...{service.api_key[-4:]}")
        print(f"   Cache Duration: {service.cache_duration}s")

        # Test coordinates in Marikina City
        origin = (14.6507, 121.1029)      # Near Marikina City Hall
        destination = (14.6545, 121.1089)  # Near Sports Center

        print(f"\n[INFO] Testing route:")
        print(f"   Origin: {origin}")
        print(f"   Destination: {destination}")

        # First call - should hit API
        print("\n[WAIT] Fetching traffic data from Google Maps...")
        traffic_factor = service.get_traffic_factor(origin, destination)

        print(f"\n[OK] Traffic factor: {traffic_factor:.3f}")

        if traffic_factor < 0.2:
            print("   [GREEN] Status: Light traffic")
        elif traffic_factor < 0.5:
            print("   [YELLOW] Status: Moderate traffic")
        elif traffic_factor < 1.0:
            print("   [ORANGE] Status: Heavy traffic")
        else:
            print("   [RED] Status: Severe congestion")

        # Second call - should use cache
        print("\n[WAIT] Fetching same route again (should use cache)...")
        traffic_factor2 = service.get_traffic_factor(origin, destination)
        print(f"[OK] Cached traffic factor: {traffic_factor2:.3f}")
        print(f"   Cache entries: {len(service.cache)}")

        # Get statistics
        stats = service.get_statistics()
        print(f"\n[STATS] Service Statistics:")
        print(f"   API Requests: {stats['api_requests']}")
        print(f"   Cache Entries: {stats['cache_entries']}")

        return True

    except ValueError as e:
        print(f"\n[ERROR] Configuration Error: {e}")
        print("\n[SOLUTION]:")
        print("   1. Create a .env file in masfro-backend/")
        print("   2. Add: GOOGLE_MAPS_API_KEY=your_key_here")
        print("   3. Get API key from: https://console.cloud.google.com/")
        return False

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_traffic_agent():
    """Test 2: TrafficAgent integration with graph."""
    print("\n" + "="*70)
    print("TEST 2: Traffic Agent Integration")
    print("="*70)

    try:
        # Initialize environment
        print("[WAIT] Loading graph environment...")
        env = DynamicGraphEnvironment()

        if not env.graph:
            print("[ERROR] Failed to load graph")
            return False

        print(f"[OK] Graph loaded: {env.graph.number_of_nodes()} nodes, {env.graph.number_of_edges()} edges")

        # Initialize TrafficAgent
        print("\n[WAIT] Initializing TrafficAgent...")
        agent = TrafficAgent(
            agent_id="traffic_test",
            environment=env,
            update_interval=300,
            sample_interval=500  # Very sparse sampling for testing
        )
        print("[OK] TrafficAgent initialized")

        # Update traffic data
        print("\n[WAIT] Updating graph with traffic data...")
        print("   (This will make ~24 API requests, please wait...)")

        stats = agent.update_traffic_data()

        print(f"\n[OK] Traffic update complete!")
        print(f"\n[STATS] Update Statistics:")
        print(f"   Edges Updated: {stats['edges_updated']}")
        print(f"   Edges Skipped: {stats['edges_skipped']}")
        print(f"   Total Edges: {stats['total_edges']}")
        print(f"   Sample Interval: {stats['sample_interval']}")
        print(f"   Average Traffic Factor: {stats['avg_traffic_factor']:.3f}")
        print(f"   Max Traffic Factor: {stats['max_traffic_factor']:.3f}")
        print(f"   Elapsed Time: {stats['elapsed_seconds']:.1f}s")
        print(f"   API Requests: {stats['api_requests']}")

        # Verify some edges have traffic data
        print("\n[CHECK] Verifying edge attributes...")
        sample_edges = list(env.graph.edges(keys=True, data=True))[:5]

        for u, v, key, data in sample_edges:
            traffic_factor = data.get('traffic_factor', 'NOT SET')
            risk_score = data.get('risk_score', 'NOT SET')
            length = data.get('length', 'NOT SET')

            print(f"   Edge ({u}, {v}, {key}):")
            print(f"      traffic_factor: {traffic_factor}")
            print(f"      risk_score: {risk_score}")
            print(f"      length: {length}")

        # Get agent statistics
        agent_stats = agent.get_statistics()
        print(f"\n[STATS] Agent Statistics:")
        print(f"   Agent ID: {agent_stats['agent_id']}")
        print(f"   Last Update: {agent_stats['last_update']}")
        print(f"   Update Interval: {agent_stats['update_interval']}s")

        return True

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cost_calculation():
    """Test 3: Verify edge cost calculation with traffic."""
    print("\n" + "="*70)
    print("TEST 3: Edge Cost Calculation")
    print("="*70)

    # Simulate edge costs
    length = 1000  # meters

    test_cases = [
        {"risk": 0.0, "traffic": 0.0, "name": "Safe, free-flow"},
        {"risk": 0.3, "traffic": 0.0, "name": "Moderate risk, no traffic"},
        {"risk": 0.0, "traffic": 0.5, "name": "Safe, moderate traffic"},
        {"risk": 0.3, "traffic": 0.5, "name": "Risk + traffic combined"},
        {"risk": 0.7, "traffic": 1.0, "name": "High risk, heavy traffic"},
    ]

    print(f"\nEdge Length: {length}m")
    print(f"\nCost Formula: length × (1 + risk) × (1 + traffic)\n")

    for case in test_cases:
        risk = case["risk"]
        traffic = case["traffic"]
        name = case["name"]

        cost = length * (1.0 + risk) * (1.0 + traffic)
        increase = ((cost - length) / length) * 100

        print(f"[STATS] {name}")
        print(f"   Risk: {risk:.1f}, Traffic: {traffic:.1f}")
        print(f"   Cost: {cost:.0f}m (base: {length}m)")
        print(f"   Increase: +{increase:.1f}%")
        print()

    return True


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("Google Maps Traffic Integration Test Suite")
    print("="*70)

    results = {
        "Traffic Service": test_traffic_service(),
        "Cost Calculation": test_cost_calculation(),
    }

    # Only test agent if service works
    if results["Traffic Service"]:
        results["Traffic Agent"] = test_traffic_agent()
    else:
        results["Traffic Agent"] = None
        print("\n[SKIP] Skipping Traffic Agent test (service not configured)")

    # Summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)

    for test_name, result in results.items():
        if result is True:
            print(f"[PASS] {test_name}: PASSED")
        elif result is False:
            print(f"[FAIL] {test_name}: FAILED")
        else:
            print(f"[SKIP] {test_name}: SKIPPED")

    print("\n" + "="*70)

    # Exit code
    if all(r in [True, None] for r in results.values()):
        print("[OK] All tests passed or skipped")
        return 0
    else:
        print("[FAIL] Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
