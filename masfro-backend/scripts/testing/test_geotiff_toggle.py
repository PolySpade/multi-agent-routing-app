#!/usr/bin/env python3
"""
Test script for GeoTIFF enable/disable functionality.

This script demonstrates the new GeoTIFF control feature in HazardAgent.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.hazard_agent import HazardAgent


def test_geotiff_toggle():
    """Test GeoTIFF enable/disable functionality."""

    print("=" * 70)
    print("GeoTIFF Toggle Feature Test")
    print("=" * 70)

    # Initialize environment
    print("\n[STEP 1] Initializing DynamicGraphEnvironment...")
    env = DynamicGraphEnvironment()
    print(f"  [OK] Graph loaded with {env.graph.number_of_nodes()} nodes, "
          f"{env.graph.number_of_edges()} edges")

    # Test 1: Default initialization (GeoTIFF enabled)
    print("\n[TEST 1] Default Initialization (GeoTIFF Enabled)")
    print("-" * 70)
    hazard_agent_default = HazardAgent("hazard_test_default", env)

    assert hazard_agent_default.is_geotiff_enabled() == True, "Default should be enabled"
    assert hazard_agent_default.geotiff_service is not None, "Service should be initialized"

    print(f"  [OK] GeoTIFF enabled: {hazard_agent_default.is_geotiff_enabled()}")
    print(f"  [OK] GeoTIFF service available: {hazard_agent_default.geotiff_service is not None}")
    print(f"  [OK] Return period: {hazard_agent_default.return_period}")
    print(f"  [OK] Time step: {hazard_agent_default.time_step}")

    # Test 2: Initialize with GeoTIFF disabled
    print("\n[TEST 2] Initialize with GeoTIFF Disabled")
    print("-" * 70)
    hazard_agent_disabled = HazardAgent("hazard_test_disabled", env, enable_geotiff=False)

    assert hazard_agent_disabled.is_geotiff_enabled() == False, "Should be disabled"
    assert hazard_agent_disabled.geotiff_service is None, "Service should NOT be initialized"

    print(f"  [OK] GeoTIFF enabled: {hazard_agent_disabled.is_geotiff_enabled()}")
    print(f"  [OK] GeoTIFF service available: {hazard_agent_disabled.geotiff_service is not None}")

    # Test 3: Runtime enable/disable
    print("\n[TEST 3] Runtime Enable/Disable")
    print("-" * 70)

    # Start with enabled
    hazard_agent_runtime = HazardAgent("hazard_test_runtime", env)
    print(f"  Initial state: enabled={hazard_agent_runtime.is_geotiff_enabled()}")

    # Disable
    hazard_agent_runtime.disable_geotiff()
    assert hazard_agent_runtime.is_geotiff_enabled() == False, "Should be disabled"
    print(f"  [OK] After disable(): enabled={hazard_agent_runtime.is_geotiff_enabled()}")

    # Enable
    hazard_agent_runtime.enable_geotiff()
    assert hazard_agent_runtime.is_geotiff_enabled() == True, "Should be enabled"
    print(f"  [OK] After enable(): enabled={hazard_agent_runtime.is_geotiff_enabled()}")

    # Test 4: Query behavior when disabled
    print("\n[TEST 4] Query Behavior When Disabled")
    print("-" * 70)

    hazard_agent_query = HazardAgent("hazard_test_query", env)

    # Query with GeoTIFF enabled
    hazard_agent_query.enable_geotiff()
    edge_depths_enabled = hazard_agent_query.get_edge_flood_depths()
    print(f"  [OK] GeoTIFF enabled: {len(edge_depths_enabled)} edges with flood data")

    # Query with GeoTIFF disabled
    hazard_agent_query.disable_geotiff()
    edge_depths_disabled = hazard_agent_query.get_edge_flood_depths()
    print(f"  [OK] GeoTIFF disabled: {len(edge_depths_disabled)} edges with flood data (expected: 0)")

    assert len(edge_depths_disabled) == 0, "Should return empty dict when disabled"

    # Test 5: Scenario change
    print("\n[TEST 5] Scenario Change")
    print("-" * 70)

    hazard_agent_scenario = HazardAgent("hazard_test_scenario", env)

    # Set different scenarios
    scenarios = [
        ("rr01", 1, "2-year flood, hour 1"),
        ("rr02", 10, "5-year flood, hour 10"),
        ("rr03", 15, "10-year flood, hour 15"),
        ("rr04", 18, "25-year flood, hour 18 (worst case)")
    ]

    for return_period, time_step, description in scenarios:
        hazard_agent_scenario.set_flood_scenario(return_period, time_step)
        assert hazard_agent_scenario.return_period == return_period
        assert hazard_agent_scenario.time_step == time_step
        print(f"  [OK] {description}: {return_period} step {time_step}")

    # Test 6: Enable after initialization (service initialization)
    print("\n[TEST 6] Enable After Disabled Initialization")
    print("-" * 70)

    hazard_agent_late_enable = HazardAgent("hazard_test_late_enable", env, enable_geotiff=False)
    print(f"  Initial: enabled={hazard_agent_late_enable.is_geotiff_enabled()}, "
          f"service={hazard_agent_late_enable.geotiff_service is not None}")

    # Enable (should initialize service)
    hazard_agent_late_enable.enable_geotiff()
    print(f"  After enable(): enabled={hazard_agent_late_enable.is_geotiff_enabled()}, "
          f"service={hazard_agent_late_enable.geotiff_service is not None}")

    assert hazard_agent_late_enable.is_geotiff_enabled() == True, "Should be enabled"
    assert hazard_agent_late_enable.geotiff_service is not None, "Service should be initialized"

    # Summary
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED [OK]")
    print("=" * 70)
    print("\nFeature Summary:")
    print("  [OK] Default initialization: GeoTIFF enabled")
    print("  [OK] Optional initialization: GeoTIFF disabled")
    print("  [OK] Runtime enable/disable: Working")
    print("  [OK] Query behavior: Correct (empty when disabled)")
    print("  [OK] Scenario changes: Working")
    print("  [OK] Late enable: Service initialized correctly")


if __name__ == "__main__":
    try:
        test_geotiff_toggle()
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
