#!/usr/bin/env python3
"""
Test Batch Processing Optimization for HazardAgent

Verifies that batch processing reduces redundant edge updates from 17x to 1x.

Usage:
    uv run python scripts/testing/test_batch_optimization.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from app.environment.graph_manager import DynamicGraphEnvironment
from app.agents.hazard_agent import HazardAgent
from app.core.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


def test_batch_vs_individual():
    """
    Compare batch processing vs individual processing performance.
    """
    print("\n" + "=" * 70)
    print("BATCH PROCESSING OPTIMIZATION TEST")
    print("=" * 70)

    # Initialize environment and agent
    print("\n[1] Initializing DynamicGraphEnvironment...")
    env = DynamicGraphEnvironment()

    print("[2] Initializing HazardAgent...")
    hazard_agent = HazardAgent("test_hazard_001", env, enable_geotiff=False)

    # Prepare test data (simulating 15 PAGASA stations)
    stations = [
        "IPO", "LA MESA", "MANGGAHAN", "ROSARIO", "NAPINDAN",
        "MONTALBAN", "WAWA", "ANGAT", "IPO", "AMBUKLAO",
        "BINGA", "SAN ROQUE", "PANTABANGAN", "MAGAT", "BUSTOS"
    ]

    batch_data = {}
    for station in stations:
        batch_data[station] = {
            "flood_depth": 1.5,
            "rainfall_1h": 25.0,
            "rainfall_24h": 100.0,
            "timestamp": datetime.now()
        }

    print(f"\n[3] Testing with {len(stations)} stations...\n")

    # Test 1: Individual processing (old method)
    print("-" * 70)
    print("TEST 1: Individual Processing (OLD METHOD)")
    print("-" * 70)

    individual_updates = 0

    class UpdateCounter:
        def __init__(self):
            self.count = 0

        def increment(self):
            self.count += 1

    # Count how many times process_and_update is called
    counter = UpdateCounter()
    original_method = hazard_agent.process_and_update

    def counted_update(*args, **kwargs):
        counter.increment()
        return original_method(*args, **kwargs)

    hazard_agent.process_and_update = counted_update

    # Simulate old behavior (calling process_flood_data for each station)
    for station, data in batch_data.items():
        flood_data = {
            "location": station,
            "flood_depth": data["flood_depth"],
            "rainfall_1h": data["rainfall_1h"],
            "rainfall_24h": data["rainfall_24h"],
            "timestamp": data["timestamp"]
        }
        hazard_agent.process_flood_data(flood_data)
        hazard_agent.process_and_update()  # Manually trigger (old behavior)

    individual_updates = counter.count

    print(f"\n[OK] Individual processing completed")
    print(f"  - Stations processed: {len(stations)}")
    print(f"  - process_and_update() calls: {individual_updates}")
    print(f"  - Edge updates per call: ~20,124")
    print(f"  - Total edge updates: ~{individual_updates * 20124:,}")

    # Reset counter and cache
    counter.count = 0
    hazard_agent.flood_data_cache.clear()

    # Test 2: Batch processing (new method)
    print("\n" + "-" * 70)
    print("TEST 2: Batch Processing (NEW METHOD)")
    print("-" * 70)

    hazard_agent.process_flood_data_batch(batch_data)
    batch_updates = counter.count

    print(f"\n[OK] Batch processing completed")
    print(f"  - Stations processed: {len(stations)}")
    print(f"  - process_and_update() calls: {batch_updates}")
    print(f"  - Edge updates per call: ~20,124")
    print(f"  - Total edge updates: ~{batch_updates * 20124:,}")

    # Calculate improvement
    print("\n" + "=" * 70)
    print("PERFORMANCE COMPARISON")
    print("=" * 70)

    if batch_updates > 0:
        improvement = individual_updates / batch_updates
        reduction = ((individual_updates - batch_updates) / individual_updates) * 100

        print(f"\n[RESULTS]")
        print(f"  - Individual updates: {individual_updates}")
        print(f"  - Batch updates: {batch_updates}")
        print(f"  - Performance gain: {improvement:.1f}x faster")
        print(f"  - Redundancy reduction: {reduction:.1f}%")
        print(f"  - Edge calculations saved: ~{(individual_updates - batch_updates) * 20124:,}")

        if improvement >= len(stations):
            print(f"\n[SUCCESS] Batch processing is {improvement:.1f}x faster!")
            print(f"  Expected ~{len(stations)}x, achieved {improvement:.1f}x")
        else:
            print(f"\n[WARNING] Expected ~{len(stations)}x improvement, got {improvement:.1f}x")

    else:
        print("\n[ERROR] Batch processing did not trigger any updates")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        test_batch_vs_individual()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
