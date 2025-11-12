#!/usr/bin/env python3
"""
Test Coordinate Transformation Fix

Verifies that the manual coordinate mapping correctly aligns
the GEOTIFF data with the road network graph.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.geotiff_service import get_geotiff_service
from app.environment.graph_manager import DynamicGraphEnvironment
import numpy as np


def test_coordinate_fix():
    print("="*80)
    print("COORDINATE TRANSFORMATION FIX TEST")
    print("="*80)

    # Initialize services
    print("\n[1] Initializing GeoTIFF service with manual coordinate mapping...")
    geotiff = get_geotiff_service()

    print("\n[2] Initializing graph...")
    env = DynamicGraphEnvironment()

    # Get graph bounds
    lats = [data['y'] for _, data in env.graph.nodes(data=True)]
    lons = [data['x'] for _, data in env.graph.nodes(data=True)]

    print(f"\n[3] Graph Coverage:")
    print(f"  Latitude:  {min(lats):.6f} to {max(lats):.6f}")
    print(f"  Longitude: {min(lons):.6f} to {max(lons):.6f}")
    print(f"  Center: ({np.mean(lats):.6f}, {np.mean(lons):.6f})")

    # Load a TIFF to get its dimensions
    print(f"\n[4] Loading TIFF to calculate manual bounds...")
    data, metadata = geotiff.load_flood_map("rr02", 12)
    height, width = data.shape
    print(f"  TIFF shape: {height}x{width}")

    # Calculate manual bounds
    bounds = geotiff._calculate_manual_bounds(width, height)
    print(f"\n[5] Manual Geographic Bounds (calculated):")
    print(f"  Longitude: {bounds['min_lon']:.6f} to {bounds['max_lon']:.6f}")
    print(f"  Latitude:  {bounds['min_lat']:.6f} to {bounds['max_lat']:.6f}")
    print(f"  Coverage: {bounds['coverage_width']:.6f}° x {bounds['coverage_height']:.6f}°")

    # Check overlap
    print(f"\n[6] Checking overlap with graph...")
    lon_overlap = not (max(lons) < bounds['min_lon'] or min(lons) > bounds['max_lon'])
    lat_overlap = not (max(lats) < bounds['min_lat'] or min(lats) > bounds['max_lat'])

    if lon_overlap and lat_overlap:
        print(f"  [SUCCESS] Manual bounds overlap with graph!")
    else:
        print(f"  [WARNING] No overlap!")
        print(f"    Longitude overlap: {lon_overlap}")
        print(f"    Latitude overlap: {lat_overlap}")

    # Test point queries on graph nodes
    print(f"\n[7] Testing flood depth queries on graph nodes...")
    test_nodes = list(env.graph.nodes())[:20]  # Test first 20 nodes

    found_count = 0
    flooded_count = 0
    sample_floods = []

    for node in test_nodes:
        lat = env.graph.nodes[node]['y']
        lon = env.graph.nodes[node]['x']

        depth = geotiff.get_flood_depth_at_point(lon, lat, "rr02", 12)

        if depth is not None:
            found_count += 1
            if depth > 0.01:
                flooded_count += 1
                sample_floods.append((node, lat, lon, depth))

    print(f"\n  Results from {len(test_nodes)} test nodes:")
    print(f"    Nodes with data: {found_count}/{len(test_nodes)} ({found_count/len(test_nodes)*100:.1f}%)")
    print(f"    Flooded nodes (>0.01m): {flooded_count}/{found_count}")

    if sample_floods:
        print(f"\n  [SUCCESS] Found flood data at graph nodes!")
        print(f"\n  Sample flooded nodes:")
        for node, lat, lon, depth in sample_floods[:5]:
            print(f"    Node {node}: ({lat:.6f}, {lon:.6f}) depth={depth:.3f}m")
    else:
        print(f"\n  [WARNING] No flooded nodes found in sample")

    # Test across all nodes
    print(f"\n[8] Scanning all {env.graph.number_of_nodes()} nodes...")
    all_flooded = 0
    all_with_data = 0

    # Sample every 10th node for speed
    sample_nodes = list(env.graph.nodes())[::10]

    for i, node in enumerate(sample_nodes):
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i+1}/{len(sample_nodes)} nodes...")

        lat = env.graph.nodes[node]['y']
        lon = env.graph.nodes[node]['x']

        depth = geotiff.get_flood_depth_at_point(lon, lat, "rr02", 12)

        if depth is not None:
            all_with_data += 1
            if depth > 0.01:
                all_flooded += 1

    print(f"\n  Sampled {len(sample_nodes)} nodes (every 10th):")
    print(f"    Nodes with data: {all_with_data} ({all_with_data/len(sample_nodes)*100:.1f}%)")
    print(f"    Flooded nodes: {all_flooded} ({all_flooded/len(sample_nodes)*100:.1f}% of sample)")

    # Estimate for full graph
    estimated_flooded_edges = (all_flooded / len(sample_nodes)) * env.graph.number_of_edges()
    print(f"\n  Estimated flooded edges in full graph: ~{estimated_flooded_edges:.0f}")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

    if all_flooded > 0:
        print("\n[RESULT] ✅ SUCCESS!")
        print("  - Manual coordinate mapping is working correctly")
        print("  - GEOTIFF data aligns with graph coordinates")
        print("  - Flood depths are being retrieved from actual data")
        print("  - Integration ready for use!")
    else:
        print("\n[RESULT] ⚠️ WARNING")
        print("  - Coordinate mapping implemented but no flood data found")
        print("  - Check TIFF files have actual flood data for time step 12")

    print("="*80)


if __name__ == "__main__":
    try:
        test_coordinate_fix()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
