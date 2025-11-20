"""
Comprehensive GeoTIFF Graph Update Test

This script tests whether GeoTIFF files properly update graph edge risks.
Tests the complete flow: GeoTIFF -> HazardAgent -> Graph edges

Usage:
    uv run python test_geotiff_graph_update.py
"""
# Fix Windows console encoding for checkmarks
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import sys
from pathlib import Path

# Add app directory to path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.hazard_agent import HazardAgent
from app.services.geotiff_service import GeoTIFFService, get_geotiff_service
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_geotiff_service():
    """Test 1: Verify GeoTIFF service can load files and query depths."""
    print_section("TEST 1: GeoTIFF Service Loading")

    try:
        service = get_geotiff_service()
        print(f"✓ GeoTIFF service initialized")
        print(f"  Data directory: {service.data_dir}")
        print(f"  Return periods: {service.return_periods}")
        print(f"  Time steps: {service.time_steps}")

        # Check available maps
        available_maps = service.get_available_maps()
        print(f"\n✓ Found {len(available_maps)} GeoTIFF files")

        # Show first few maps
        print("\n  Sample maps:")
        for map_info in available_maps[:5]:
            print(f"    - {map_info['return_period']}/time_step_{map_info['time_step']:02d} ({map_info['file']})")

        # Test loading a specific map
        print("\n  Testing map load: rr01, time_step=1")
        flood_data = service.load_flood_map("rr01", 1)

        if flood_data:
            print(f"✓ Successfully loaded GeoTIFF")
            print(f"  Array shape: {flood_data['array'].shape}")
            print(f"  Bounds: {flood_data['bounds']}")
            print(f"  Non-zero pixels: {(flood_data['array'] > 0).sum()}")
            print(f"  Max depth: {flood_data['array'].max():.3f}m")
            print(f"  Mean depth (flooded areas): {flood_data['array'][flood_data['array'] > 0].mean():.3f}m")
        else:
            print("✗ Failed to load GeoTIFF")
            return False

        # Test point query (Marikina City center: ~14.65°N, 121.10°E)
        test_lon, test_lat = 121.10, 14.65
        print(f"\n  Testing point query at ({test_lon}, {test_lat})")

        depth = service.get_flood_depth_at_point(test_lon, test_lat, "rr01", 1)
        print(f"✓ Query successful: depth = {depth}m" if depth is not None else "  No flood at this point")

        return True

    except Exception as e:
        print(f"✗ GeoTIFF service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hazard_agent_geotiff_integration():
    """Test 2: Verify HazardAgent can query GeoTIFF depths for edges."""
    print_section("TEST 2: HazardAgent GeoTIFF Integration")

    try:
        # Initialize environment
        print("Initializing graph environment...")
        environment = DynamicGraphEnvironment()
        print(f"✓ Graph loaded: {len(environment.graph.nodes)} nodes, {len(environment.graph.edges)} edges")

        # Initialize HazardAgent with GeoTIFF enabled
        print("\nInitializing HazardAgent with GeoTIFF enabled...")
        hazard_agent = HazardAgent(
            agent_id="test_hazard_agent",
            environment=environment,
            enable_geotiff=True
        )
        print(f"✓ GeoTIFF enabled: {hazard_agent.is_geotiff_enabled()}")

        # Set flood scenario
        hazard_agent.set_flood_scenario(return_period="rr01", time_step=5)
        print(f"✓ Scenario set: return_period={hazard_agent.return_period}, time_step={hazard_agent.time_step}")

        # Test edge depth query
        print("\nTesting edge flood depth queries...")
        sample_edges = list(environment.graph.edges(keys=True))[:10]

        depths_found = 0
        total_depth = 0.0

        for u, v, key in sample_edges:
            depth = hazard_agent.get_flood_depth_at_edge(u, v)
            if depth is not None and depth > 0:
                depths_found += 1
                total_depth += depth
                u_data = environment.graph.nodes[u]
                v_data = environment.graph.nodes[v]
                print(f"  Edge ({u},{v}): {depth:.3f}m at ({u_data['y']:.4f}, {u_data['x']:.4f})")

        print(f"\n✓ Found flood depths on {depths_found}/{len(sample_edges)} sampled edges")
        if depths_found > 0:
            print(f"  Average depth: {total_depth/depths_found:.3f}m")

        return True, hazard_agent

    except Exception as e:
        print(f"✗ HazardAgent integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_risk_calculation_from_geotiff(hazard_agent):
    """Test 3: Verify risk scores are calculated from GeoTIFF data."""
    print_section("TEST 3: Risk Score Calculation from GeoTIFF")

    try:
        print("Calculating risk scores from GeoTIFF data...")

        # Get all edge flood depths
        edge_flood_depths = hazard_agent.get_edge_flood_depths()
        print(f"✓ Queried flood depths for {len(edge_flood_depths)} edges")

        # Count flooded edges
        flooded_edges = {k: v for k, v in edge_flood_depths.items() if v > 0}
        print(f"  Flooded edges: {len(flooded_edges)}")

        if flooded_edges:
            depths = list(flooded_edges.values())
            print(f"  Min depth: {min(depths):.3f}m")
            print(f"  Max depth: {max(depths):.3f}m")
            print(f"  Mean depth: {sum(depths)/len(depths):.3f}m")

            # Show depth distribution
            low = sum(1 for d in depths if d < 0.3)
            mod = sum(1 for d in depths if 0.3 <= d < 0.6)
            high = sum(1 for d in depths if 0.6 <= d < 1.0)
            crit = sum(1 for d in depths if d >= 1.0)

            print(f"\n  Depth distribution:")
            print(f"    Low (0-0.3m): {low} edges")
            print(f"    Moderate (0.3-0.6m): {mod} edges")
            print(f"    High (0.6-1.0m): {high} edges")
            print(f"    Critical (>1.0m): {crit} edges")

        # Calculate risk scores
        print("\nCalculating risk scores...")
        fused_data = {}  # Empty fused data to test pure GeoTIFF risk
        risk_scores = hazard_agent.calculate_risk_scores(fused_data)

        print(f"✓ Calculated risk scores for {len(risk_scores)} edges")

        # Count risk distribution
        if risk_scores:
            risks = list(risk_scores.values())
            print(f"  Min risk: {min(risks):.4f}")
            print(f"  Max risk: {max(risks):.4f}")
            print(f"  Mean risk: {sum(risks)/len(risks):.4f}")

            low_risk = sum(1 for r in risks if r < 0.3)
            mod_risk = sum(1 for r in risks if 0.3 <= r < 0.6)
            high_risk = sum(1 for r in risks if 0.6 <= r < 0.8)
            crit_risk = sum(1 for r in risks if r >= 0.8)

            print(f"\n  Risk distribution:")
            print(f"    Low (<0.3): {low_risk} edges")
            print(f"    Moderate (0.3-0.6): {mod_risk} edges")
            print(f"    High (0.6-0.8): {high_risk} edges")
            print(f"    Critical (≥0.8): {crit_risk} edges")

            # Show top 5 riskiest edges
            print(f"\n  Top 5 riskiest edges:")
            sorted_risks = sorted(risk_scores.items(), key=lambda x: x[1], reverse=True)[:5]
            for edge_tuple, risk in sorted_risks:
                u, v, key = edge_tuple
                u_data = hazard_agent.environment.graph.nodes[u]
                v_data = hazard_agent.environment.graph.nodes[v]
                print(f"    Edge ({u},{v}): risk={risk:.4f} at ({u_data['y']:.4f}, {u_data['x']:.4f})")

        return True, risk_scores

    except Exception as e:
        print(f"✗ Risk calculation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, {}


def test_graph_edge_update(hazard_agent, risk_scores):
    """Test 4: Verify graph edges are actually updated with risk scores."""
    print_section("TEST 4: Graph Edge Update Verification")

    try:
        # Get initial edge risk values
        print("Checking initial edge risk values...")
        sample_edges = list(hazard_agent.environment.graph.edges(keys=True))[:10]

        print("\n  Initial edge risks (sample):")
        for u, v, key in sample_edges:
            edge_data = hazard_agent.environment.graph[u][v][key]
            initial_risk = edge_data.get('risk_score', 0.0)
            print(f"    Edge ({u},{v}): risk_score={initial_risk:.4f}")

        # Update environment with risk scores
        print("\nUpdating graph environment with risk scores...")
        hazard_agent.update_environment(risk_scores)
        print(f"✓ update_environment() called with {len(risk_scores)} risk scores")

        # Verify edges were updated
        print("\n  Updated edge risks (sample):")
        edges_updated = 0
        edges_unchanged = 0

        for u, v, key in sample_edges:
            edge_data = hazard_agent.environment.graph[u][v][key]
            updated_risk = edge_data.get('risk_score', 0.0)
            expected_risk = risk_scores.get((u, v, key), 0.0)

            status = "✓" if abs(updated_risk - expected_risk) < 0.0001 else "✗"
            print(f"    Edge ({u},{v}): risk_score={updated_risk:.4f} {status}")

            if abs(updated_risk - expected_risk) < 0.0001:
                edges_updated += 1
            else:
                edges_unchanged += 1

        print(f"\n  Summary:")
        print(f"    Edges correctly updated: {edges_updated}")
        print(f"    Edges NOT updated: {edges_unchanged}")

        # Full graph check
        print("\nChecking entire graph...")
        total_edges = len(list(hazard_agent.environment.graph.edges(keys=True)))
        edges_with_risk = 0
        total_risk = 0.0

        for u, v, key in hazard_agent.environment.graph.edges(keys=True):
            edge_data = hazard_agent.environment.graph[u][v][key]
            risk = edge_data.get('risk_score', 0.0)
            if risk > 0:
                edges_with_risk += 1
                total_risk += risk

        print(f"✓ Graph statistics:")
        print(f"  Total edges: {total_edges}")
        print(f"  Edges with risk > 0: {edges_with_risk}")
        print(f"  Percentage at risk: {edges_with_risk/total_edges*100:.2f}%")
        if edges_with_risk > 0:
            print(f"  Average risk (risky edges): {total_risk/edges_with_risk:.4f}")

        return edges_updated > 0

    except Exception as e:
        print(f"✗ Graph edge update test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_update_risk_method():
    """Test 5: Test the complete update_risk() flow."""
    print_section("TEST 5: Complete update_risk() Flow")

    try:
        # Initialize fresh environment and agent
        print("Initializing fresh environment and HazardAgent...")
        environment = DynamicGraphEnvironment()
        hazard_agent = HazardAgent(
            agent_id="test_update_risk",
            environment=environment,
            enable_geotiff=True
        )
        hazard_agent.set_flood_scenario(return_period="rr02", time_step=10)
        print(f"✓ Setup complete: rr02, time_step=10")

        # Check initial graph state
        initial_risky_edges = sum(
            1 for u, v, k in environment.graph.edges(keys=True)
            if environment.graph[u][v][k].get('risk_score', 0.0) > 0
        )
        print(f"  Initial risky edges: {initial_risky_edges}")

        # Call update_risk (simulates SimulationManager calling HazardAgent)
        print("\nCalling update_risk() with empty data...")
        result = hazard_agent.update_risk(
            flood_data={},  # No flood data (pure GeoTIFF test)
            scout_data=[],  # No scout data
            time_step=10
        )

        print(f"✓ update_risk() completed")
        print(f"  Locations processed: {result.get('locations_processed', 0)}")
        print(f"  Edges updated: {result.get('edges_updated', 0)}")
        print(f"  Average risk: {result.get('average_risk', 0):.4f}")
        print(f"  Time step: {result.get('time_step', 0)}")

        # Check graph state after update
        final_risky_edges = sum(
            1 for u, v, k in environment.graph.edges(keys=True)
            if environment.graph[u][v][k].get('risk_score', 0.0) > 0
        )
        print(f"\n  Final risky edges: {final_risky_edges}")
        print(f"  Change: {final_risky_edges - initial_risky_edges:+d} edges")

        # Show sample of updated edges
        print("\n  Sample of edges after update_risk():")
        sample_edges = list(environment.graph.edges(keys=True))[:10]
        for u, v, key in sample_edges:
            edge_data = environment.graph[u][v][key]
            risk = edge_data.get('risk_score', 0.0)
            if risk > 0:
                print(f"    Edge ({u},{v}): risk={risk:.4f} ✓")

        return final_risky_edges > initial_risky_edges

    except Exception as e:
        print(f"✗ update_risk() flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  GeoTIFF Graph Update Diagnostic Test Suite")
    print("=" * 80)
    print("\nThis test verifies that GeoTIFF files properly update graph edge risks.")
    print("Testing the complete flow: GeoTIFF -> HazardAgent -> Graph edges\n")

    results = {}

    # Test 1: GeoTIFF Service
    results['test1'] = test_geotiff_service()

    # Test 2: HazardAgent Integration
    results['test2'], hazard_agent = test_hazard_agent_geotiff_integration()

    # Test 3: Risk Calculation
    if results['test2'] and hazard_agent:
        results['test3'], risk_scores = test_risk_calculation_from_geotiff(hazard_agent)
    else:
        results['test3'] = False
        risk_scores = {}

    # Test 4: Graph Edge Update
    if results['test3'] and hazard_agent:
        results['test4'] = test_graph_edge_update(hazard_agent, risk_scores)
    else:
        results['test4'] = False

    # Test 5: Complete Flow
    results['test5'] = test_update_risk_method()

    # Final Summary
    print_section("TEST SUMMARY")

    test_names = {
        'test1': 'GeoTIFF Service Loading',
        'test2': 'HazardAgent GeoTIFF Integration',
        'test3': 'Risk Score Calculation',
        'test4': 'Graph Edge Update Verification',
        'test5': 'Complete update_risk() Flow'
    }

    passed = sum(results.values())
    total = len(results)

    for test_key, test_name in test_names.items():
        status = "✓ PASS" if results[test_key] else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Overall: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ ALL TESTS PASSED - GeoTIFF is properly updating graph edges!")
    else:
        print("\n✗ SOME TESTS FAILED - GeoTIFF may not be updating graph edges correctly.")
        print("  Check the detailed output above for diagnostics.")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
