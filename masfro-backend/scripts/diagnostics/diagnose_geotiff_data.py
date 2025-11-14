#!/usr/bin/env python3
"""
Diagnose GeoTIFF Data Availability

Checks:
1. GEOTIFF file can be loaded
2. GEOTIFF has non-zero flood data
3. GEOTIFF coordinate bounds
4. Graph node coordinate bounds
5. Coordinate overlap

This helps identify if there's a coordinate mismatch between GEOTIFF and graph.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.geotiff_service import get_geotiff_service
from app.environment.graph_manager import DynamicGraphEnvironment
import numpy as np


def diagnose_geotiff():
    print("="*80)
    print("GEOTIFF DATA DIAGNOSIS")
    print("="*80)

    # Initialize services
    print("\n[1] Initializing GeoTIFF service...")
    geotiff = get_geotiff_service()
    print(f"  Available return periods: {geotiff.return_periods}")

    print("\n[2] Initializing graph...")
    env = DynamicGraphEnvironment()
    print(f"  Graph nodes: {env.graph.number_of_nodes()}")

    # Check GEOTIFF data
    print("\n[3] Checking GEOTIFF data for rr02, time_step=12...")
    try:
        arr, metadata = geotiff.load_flood_map("rr02", 12)

        print(f"  GEOTIFF loaded successfully")
        print(f"  Array shape: {arr.shape}")
        print(f"  Array dtype: {arr.dtype}")
        print(f"  Bounds: {metadata['bounds']}")

        # Check for non-zero data
        non_zero = np.count_nonzero(arr)
        total = arr.size
        max_val = np.max(arr)
        min_val = np.min(arr)

        print(f"\n  Data Statistics:")
        print(f"    Non-zero pixels: {non_zero}/{total} ({non_zero/total*100:.2f}%)")
        print(f"    Min value: {min_val:.3f}")
        print(f"    Max value: {max_val:.3f}")
        print(f"    Mean value: {np.mean(arr):.3f}")
        print(f"    Flooded pixels (>0.01m): {metadata['statistics']['flooded_pixels']}")

        if non_zero > 0:
            print(f"\n  [OK] GEOTIFF contains flood data!")
        else:
            print(f"\n  [WARNING] GEOTIFF has no flood data (all zeros)")

    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

    # Check graph coordinates
    print("\n[4] Checking graph coordinate bounds...")
    lats = [data['y'] for _, data in env.graph.nodes(data=True)]
    lons = [data['x'] for _, data in env.graph.nodes(data=True)]

    print(f"  Latitude range: {min(lats):.6f} to {max(lats):.6f}")
    print(f"  Longitude range: {min(lons):.6f} to {max(lons):.6f}")

    # Check overlap
    print("\n[5] Checking coordinate overlap...")
    try:
        arr, metadata = geotiff.load_flood_map("rr02", 12)
        tiff_bounds = metadata['bounds']
        graph_lat_range = (min(lats), max(lats))
        graph_lon_range = (min(lons), max(lons))

        print(f"  GEOTIFF bounds: left={tiff_bounds['left']:.6f}, right={tiff_bounds['right']:.6f}")
        print(f"                  bottom={tiff_bounds['bottom']:.6f}, top={tiff_bounds['top']:.6f}")
        print(f"  Graph lat range: {graph_lat_range[0]:.6f} to {graph_lat_range[1]:.6f}")
        print(f"  Graph lon range: {graph_lon_range[0]:.6f} to {graph_lon_range[1]:.6f}")

        # Check if ranges overlap
        lat_overlap = not (graph_lat_range[1] < tiff_bounds['bottom'] or graph_lat_range[0] > tiff_bounds['top'])
        lon_overlap = not (graph_lon_range[1] < tiff_bounds['left'] or graph_lon_range[0] > tiff_bounds['right'])

        if lat_overlap and lon_overlap:
            print(f"\n  [OK] Coordinates overlap!")
        else:
            print(f"\n  [WARNING] No coordinate overlap!")
            print(f"    Latitude overlap: {lat_overlap}")
            print(f"    Longitude overlap: {lon_overlap}")

    except Exception as e:
        print(f"  [ERROR] {e}")

    # Test point queries
    print("\n[6] Testing point queries at graph nodes...")
    test_nodes = list(env.graph.nodes())[:10]

    for i, node in enumerate(test_nodes):
        lat = env.graph.nodes[node]['y']
        lon = env.graph.nodes[node]['x']

        depth = geotiff.get_flood_depth_at_point(lon, lat, "rr02", 12)

        if depth is not None and depth > 0:
            print(f"  Node {node} ({lat:.6f}, {lon:.6f}): depth={depth:.3f}m [FLOODED]")
        else:
            print(f"  Node {node} ({lat:.6f}, {lon:.6f}): no flood data")

    print("\n" + "="*80)
    print("DIAGNOSIS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    try:
        diagnose_geotiff()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
