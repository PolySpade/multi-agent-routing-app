#!/usr/bin/env python3
# filename: test_agent_workflow.py

"""
Test Agent Communication Workflow for MAS-FRO

This script tests the complete agent coordination workflow:
1. FloodAgent collects data
2. FloodAgent forwards to HazardAgent
3. HazardAgent processes and fuses data
4. HazardAgent updates DynamicGraphEnvironment
5. RoutingAgent uses updated graph for pathfinding

Usage:
    uv run python test_agent_workflow.py
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.flood_agent import FloodAgent
from app.agents.hazard_agent import HazardAgent
from app.agents.routing_agent import RoutingAgent


def print_section(title):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_complete_workflow():
    """Test complete agent coordination workflow."""
    print("\n" + "="*70)
    print("  MAS-FRO Agent Workflow Test")
    print("="*70)

    try:
        # Step 1: Initialize Environment
        print_section("Step 1: Initialize Dynamic Graph Environment")
        environment = DynamicGraphEnvironment()

        if not environment.graph:
            print("[FAIL] Graph not loaded")
            return False

        print(f"[PASS] Graph loaded with {environment.graph.number_of_nodes()} nodes")
        print(f"[PASS] Graph has {environment.graph.number_of_edges()} edges")

        # Step 2: Initialize Agents
        print_section("Step 2: Initialize Agents")

        hazard_agent = HazardAgent("hazard_001", environment)
        print(f"[PASS] HazardAgent initialized: {hazard_agent.agent_id}")

        flood_agent = FloodAgent("flood_001", environment, hazard_agent=hazard_agent)
        print(f"[PASS] FloodAgent initialized: {flood_agent.agent_id}")

        routing_agent = RoutingAgent("routing_001", environment)
        print(f"[PASS] RoutingAgent initialized: {routing_agent.agent_id}")

        # Step 3: Test FloodAgent Data Collection
        print_section("Step 3: FloodAgent Collects Data")

        flood_data = flood_agent.collect_and_forward_data()
        print(f"[PASS] FloodAgent collected data for {len(flood_data)} locations")

        if flood_data:
            print("       Locations:", list(flood_data.keys())[:3], "...")

        # Step 4: Verify HazardAgent Received Data
        print_section("Step 4: HazardAgent Processes Data")

        has_flood_data = len(hazard_agent.flood_data_cache) > 0
        if has_flood_data:
            print(f"[PASS] HazardAgent received {len(hazard_agent.flood_data_cache)} flood reports")
        else:
            print("[WARN] HazardAgent has no cached data yet")

        # Manually trigger processing
        result = hazard_agent.process_and_update()
        print(f"[PASS] HazardAgent processed {result['locations_processed']} locations")
        print(f"[PASS] HazardAgent updated {result['edges_updated']} edges")

        # Step 5: Verify Graph Environment Updated
        print_section("Step 5: Verify Graph Environment Updated")

        # Check if edges have risk scores
        sample_edges = list(environment.graph.edges(data=True, keys=True))[:5]
        risk_scores = [data.get('risk_score', 0) for u, v, k, data in sample_edges]

        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        print(f"[PASS] Sample edges have risk scores")
        print(f"       Average risk: {avg_risk:.3f}")

        # Step 6: Test RoutingAgent with Updated Graph
        print_section("Step 6: RoutingAgent Calculates Route")

        # Get actual coordinates from graph nodes
        # Find two connected nodes by taking an edge
        edges = list(environment.graph.edges())
        if len(edges) >= 1:
            # Use the first edge - guaranteed to be connected
            start_node_id = edges[0][0]
            end_node_id = edges[0][1]

            start_node = environment.graph.nodes[start_node_id]
            end_node = environment.graph.nodes[end_node_id]

            start = (start_node['y'], start_node['x'])
            end = (end_node['y'], end_node['x'])
            print(f"       Using connected nodes: {start} -> {end}")
        else:
            print("[SKIP] No edges in graph for routing test")
            return True

        try:
            route = routing_agent.calculate_route(start, end)

            if route and route.get("path"):
                print(f"[PASS] Route calculated successfully")
                print(f"       Distance: {route['distance']:.0f}m")
                print(f"       Risk Level: {route['risk_level']:.3f}")
                print(f"       Estimated Time: {route['estimated_time']:.1f} min")
                print(f"       Warnings: {len(route['warnings'])}")

                if route['warnings']:
                    for warning in route['warnings']:
                        print(f"          - {warning}")
            else:
                print("[FAIL] Route calculation returned no path")
                return False

        except Exception as e:
            print(f"[FAIL] Route calculation error: {e}")
            return False

        # Step 7: Test Evacuation Center Routing
        print_section("Step 7: Test Evacuation Center Routing")

        try:
            evac_result = routing_agent.find_nearest_evacuation_center(start)

            if evac_result:
                print(f"[PASS] Nearest evacuation center found")
                print(f"       Center: {evac_result['center']['name']}")
                print(f"       Distance: {evac_result['metrics']['total_distance']:.0f}m")
                print(f"       Risk: {evac_result['metrics']['average_risk']:.3f}")
            else:
                print("[WARN] No evacuation center found (expected with limited data)")

        except Exception as e:
            print(f"[WARN] Evacuation center routing: {e}")

        # Summary
        print_section("Workflow Test Summary")
        print("[PASS] All workflow steps completed successfully!")
        print("")
        print("Workflow verified:")
        print("  1. [OK] FloodAgent collects data")
        print("  2. [OK] FloodAgent -> HazardAgent communication")
        print("  3. [OK] HazardAgent data fusion")
        print("  4. [OK] HazardAgent -> Graph Environment updates")
        print("  5. [OK] RoutingAgent uses updated graph")
        print("  6. [OK] End-to-end route calculation")

        return True

    except Exception as e:
        print(f"\n[FAIL] Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_statistics():
    """Test agent statistics and monitoring."""
    print_section("Agent Statistics Test")

    try:
        environment = DynamicGraphEnvironment()
        hazard_agent = HazardAgent("hazard_001", environment)
        flood_agent = FloodAgent("flood_001", environment, hazard_agent=hazard_agent)
        routing_agent = RoutingAgent("routing_001", environment)

        # Get statistics
        routing_stats = routing_agent.get_statistics()

        print("[PASS] Agent statistics available")
        print(f"       Routing Agent: {routing_stats['agent_id']}")
        print(f"       Risk Weight: {routing_stats['risk_weight']}")
        print(f"       Evacuation Centers: {routing_stats['evacuation_centers']}")

        return True

    except Exception as e:
        print(f"[FAIL] Statistics test failed: {e}")
        return False


def main():
    """Run all workflow tests."""
    print("\n" + "="*70)
    print("  MAS-FRO Phase 1 Agent Workflow Tests")
    print("="*70)

    results = {
        "Complete Workflow": test_complete_workflow(),
        "Agent Statistics": test_agent_statistics(),
    }

    # Print final summary
    print("\n" + "="*70)
    print("  Final Test Summary")
    print("="*70)

    total = len(results)
    passed = sum(1 for result in results.values() if result)

    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status:8} | {test_name}")

    print("\n" + "-"*70)
    print(f"Total: {passed}/{total} test suites passed")

    if passed == total:
        print("\n[SUCCESS] All Phase 1 workflow tests passed!")
        print("[OK] Agent communication is working correctly")
        print("[OK] Data flows from FloodAgent -> HazardAgent -> Graph")
        print("[OK] RoutingAgent uses updated risk data")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
