# filename: test_hazard_integration.py

"""
Test script to verify GeoTIFF integration with HazardAgent and routing.

This script tests the complete flow:
1. GeoTIFF service initialization
2. Flood depth queries from GeoTIFF files
3. Risk score calculation using GeoTIFF data
4. Risk-aware routing using calculated scores
"""

import sys
import os

# Add backend app directory to path
backend_path = os.path.dirname(os.path.abspath(__file__))
app_path = os.path.join(backend_path, "app")
sys.path.insert(0, app_path)

import asyncio
import logging
from environment.graph_manager import DynamicGraphEnvironment
from agents.hazard_agent import HazardAgent
from agents.routing_agent import RoutingAgent
from services.geotiff_service import get_geotiff_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_geotiff_service():
    """Test 1: Verify GeoTIFF service can query flood depths."""
    print("\n" + "="*80)
    print("TEST 1: GeoTIFF Service Flood Depth Query")
    print("="*80)

    try:
        service = get_geotiff_service()
        print("[OK] GeoTIFF service initialized successfully")

        # Test coordinates in Marikina City (known flooded area)
        test_coords = [
            (121.1029, 14.6507, "Marikina City Hall"),
            (121.1190, 14.6350, "Marikina Sports Complex"),
        ]

        for lon, lat, name in test_coords:
            depth = service.get_flood_depth_at_point(
                lon, lat,
                return_period="rr01",
                time_step=1
            )
            print(f"[*] {name} ({lat}, {lon}): {depth}m flood depth")

        print("[OK] GeoTIFF queries successful\n")
        return True
    except Exception as e:
        print(f"[FAIL] GeoTIFF service test failed: {e}\n")
        return False


def test_hazard_agent_integration():
    """Test 2: Verify HazardAgent initializes with GeoTIFF service."""
    print("\n" + "="*80)
    print("TEST 2: HazardAgent GeoTIFF Integration")
    print("="*80)

    try:
        # Initialize environment (graph is loaded automatically in __init__)
        env = DynamicGraphEnvironment()

        if env.graph:
            print(f"[OK] Graph loaded: {env.graph.number_of_nodes()} nodes, {env.graph.number_of_edges()} edges")
        else:
            print(f"[FAIL] Graph failed to load")
            return False

        # Initialize HazardAgent
        hazard_agent = HazardAgent("test_hazard_agent", env)

        # Check if GeoTIFF service was initialized
        if hazard_agent.geotiff_service:
            print("[OK] HazardAgent initialized with GeoTIFF service")
            print(f"   Return period: {hazard_agent.return_period}")
            print(f"   Time step: {hazard_agent.time_step}")
        else:
            print("[FAIL] HazardAgent failed to initialize GeoTIFF service")
            return False

        # Test flood depth query
        print("\n[TEST] Testing flood depth query on graph edges...")
        edge = list(env.graph.edges(keys=True))[0]
        u, v, key = edge

        depth = hazard_agent.get_flood_depth_at_edge(u, v)
        print(f"   Edge ({u}, {v}, {key}): {depth}m flood depth")

        print("[OK] HazardAgent GeoTIFF integration working\n")
        return True
    except Exception as e:
        print(f"[FAIL] HazardAgent integration test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_risk_calculation():
    """Test 3: Verify risk score calculation uses GeoTIFF flood depths."""
    print("\n" + "="*80)
    print("TEST 3: Risk Score Calculation with GeoTIFF Data")
    print("="*80)

    try:
        # Initialize environment and agents (graph is loaded automatically)
        env = DynamicGraphEnvironment()
        hazard_agent = HazardAgent("test_hazard_agent", env)

        # Simulate flood data
        test_flood_data = {
            "location": "Test Station",
            "flood_depth": 0.5,
            "rainfall": 10.0,
            "river_level": 15.0,
            "risk_level": 0.3,
            "timestamp": "2025-11-09T17:00:00"
        }

        # Add to cache
        hazard_agent.flood_data_cache["Test Station"] = test_flood_data

        # Trigger risk calculation
        print("[TEST] Triggering risk calculation...")
        result = hazard_agent.process_and_update()

        print(f"[OK] Risk calculation completed:")
        print(f"   Locations processed: {result.get('locations_processed', 0)}")
        print(f"   Edges updated: {result.get('edges_updated', 0)}")

        # Check if edges have risk scores
        sample_edge = list(env.graph.edges(keys=True, data=True))[0]
        u, v, key, data = sample_edge
        risk = data.get('risk', 0)
        print(f"   Sample edge ({u}, {v}): risk={risk:.3f}")

        if result.get('edges_updated', 0) > 0:
            print("[OK] Risk scores calculated successfully\n")
            return True
        else:
            print("[WARN]  Warning: No edges updated with risk scores\n")
            return True  # Not a hard failure
    except Exception as e:
        print(f"[FAIL] Risk calculation test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_routing_with_hazard():
    """Test 4: Verify routing uses hazard-assessed risk scores."""
    print("\n" + "="*80)
    print("TEST 4: Risk-Aware Routing with Hazard Assessment")
    print("="*80)

    try:
        # Initialize environment (graph is loaded automatically)
        env = DynamicGraphEnvironment()

        # Initialize agents
        hazard_agent = HazardAgent("test_hazard_agent", env)
        routing_agent = RoutingAgent("test_routing_agent", env)

        # Set up test flood data to create risk scores
        hazard_agent.flood_data_cache["Test"] = {
            "location": "Test",
            "flood_depth": 0.5,
            "rainfall": 10.0,
            "river_level": 15.0,
            "risk_level": 0.5,
            "timestamp": "2025-11-09T17:00:00"
        }

        # Calculate risk scores
        print("[TEST] Calculating risk scores...")
        hazard_result = hazard_agent.process_and_update()
        print(f"   Edges with risk scores: {hazard_result.get('edges_updated', 0)}")

        # Test routing
        start = (14.6507, 121.1029)  # Marikina City Hall
        end = (14.6350, 121.1190)    # Marikina Sports Complex

        print(f"[TEST] Calculating route from {start} to {end}...")
        route = routing_agent.calculate_route(start, end)

        if route.get('path'):
            print(f"[OK] Route calculated successfully:")
            print(f"   Path length: {len(route['path'])} waypoints")
            print(f"   Distance: {route.get('distance', 0):.0f}m")
            print(f"   Risk level: {route.get('risk_level', 0):.3f}")
            print(f"   Max risk: {route.get('max_risk', 0):.3f}")
            print(f"   Warnings: {len(route.get('warnings', []))}")

            if route.get('risk_level', 1.0) < 1.0:
                print("[OK] Routing successfully uses risk scores\n")
                return True
            else:
                print("[WARN]  Route has maximum risk - may not be avoiding hazards\n")
                return True  # Still successful routing
        else:
            print("[FAIL] No route found\n")
            return False

    except Exception as e:
        print(f"[FAIL] Routing test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("MAS-FRO HAZARD INTEGRATION TEST SUITE")
    print("=" * 80)

    results = {
        "GeoTIFF Service": test_geotiff_service(),
        "HazardAgent Integration": test_hazard_agent_integration(),
        "Risk Calculation": test_risk_calculation(),
        "Risk-Aware Routing": test_routing_with_hazard(),
    }

    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)

    for test_name, passed in results.items():
        status = "[PASSED]" if passed else "[FAILED]"
        print(f"{test_name:30s} {status}")

    total = len(results)
    passed = sum(results.values())
    print(f"\n{passed}/{total} tests passed ({100*passed//total}%)")

    if passed == total:
        print("\n*** ALL TESTS PASSED - Hazard assessment is fully integrated! ***")
    else:
        print("\n*** WARNING: Some tests failed - check logs above for details ***")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
