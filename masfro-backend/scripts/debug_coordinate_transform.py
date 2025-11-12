#!/usr/bin/env python3
"""
Debug Coordinate Transformation

Tests the full coordinate transformation pipeline to find where it's failing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.geotiff_service import get_geotiff_service
from app.environment.graph_manager import DynamicGraphEnvironment
from pyproj import Transformer
from rasterio.transform import rowcol
import rasterio
import numpy as np


def debug_transforms():
    print("="*80)
    print("COORDINATE TRANSFORMATION DEBUG")
    print("="*80)

    # Initialize
    geotiff = get_geotiff_service()
    env = DynamicGraphEnvironment()

    # Get a test point from the graph
    test_node = list(env.graph.nodes())[0]
    lat = env.graph.nodes[test_node]['y']
    lon = env.graph.nodes[test_node]['x']

    print(f"\n[TEST POINT]")
    print(f"  Node: {test_node}")
    print(f"  Lat: {lat:.6f}, Lon: {lon:.6f}")

    # Load GEOTIFF
    file_path = geotiff._get_file_path("rr02", 12)
    print(f"\n[GEOTIFF FILE]")
    print(f"  Path: {file_path}")

    with rasterio.open(file_path) as src:
        print(f"  CRS: {src.crs}")
        print(f"  Bounds: {src.bounds}")
        print(f"  Transform: {src.transform}")
        print(f"  Shape: {src.shape}")

        # Read data
        data = src.read(1)
        print(f"\n[GEOTIFF DATA]")
        print(f"  Array shape: {data.shape}")
        print(f"  Data type: {data.dtype}")

        # Calculate valid data statistics
        valid_data = data[~np.isnan(data)]
        print(f"  Valid (non-NaN) pixels: {valid_data.size}/{data.size}")

        if valid_data.size > 0:
            print(f"  Min: {np.min(valid_data):.3f}")
            print(f"  Max: {np.max(valid_data):.3f}")
            print(f"  Mean: {np.mean(valid_data):.3f}")

            # Find where flood data exists
            flooded = valid_data[valid_data > 0.01]
            print(f"  Flooded pixels (>0.01m): {flooded.size}")

            if flooded.size > 0:
                print(f"    Flood depth range: {np.min(flooded):.3f}m to {np.max(flooded):.3f}m")

        # Test transformation
        print(f"\n[TRANSFORMATION TEST]")
        print(f"  Input (WGS84): lon={lon:.6f}, lat={lat:.6f}")

        # Transform to EPSG:3857 (what the code does)
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        x_3857, y_3857 = transformer.transform(lon, lat)
        print(f"  Transformed (EPSG:3857): x={x_3857:.2f}, y={y_3857:.2f}")

        # Check if this is in GEOTIFF bounds
        in_bounds_3857 = (src.bounds.left <= x_3857 <= src.bounds.right and
                         src.bounds.bottom <= y_3857 <= src.bounds.top)
        print(f"  In GEOTIFF bounds? {in_bounds_3857}")

        # Try converting to row/col
        try:
            row, col = rowcol(src.transform, x_3857, y_3857)
            print(f"  Row/Col: row={row}, col={col}")
            print(f"  Valid indices? row in [0,{src.height}), col in [0,{src.width})")

            if 0 <= row < src.height and 0 <= col < src.width:
                value = data[row, col]
                print(f"  Value at this location: {value}")
                if np.isnan(value):
                    print(f"    -> NaN (no flood data)")
                else:
                    print(f"    -> {value:.3f}m flood depth")
            else:
                print(f"  -> OUT OF BOUNDS!")

        except Exception as e:
            print(f"  Error in rowcol: {e}")

        # Also try transforming to the GEOTIFF's actual CRS
        print(f"\n[TRANSFORMATION TO GEOTIFF CRS]")
        if src.crs != "EPSG:3857":
            print(f"  GEOTIFF CRS is {src.crs}, not EPSG:3857!")
            print(f"  The code is using wrong target CRS!")

            transformer2 = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True)
            x_correct, y_correct = transformer2.transform(lon, lat)
            print(f"  Correct transform: x={x_correct:.2f}, y={y_correct:.2f}")

            try:
                row2, col2 = rowcol(src.transform, x_correct, y_correct)
                print(f"  Row/Col: row={row2}, col={col2}")

                if 0 <= row2 < src.height and 0 <= col2 < src.width:
                    value2 = data[row2, col2]
                    print(f"  Value: {value2}")
                    if not np.isnan(value2):
                        print(f"  [SUCCESS] Found flood depth: {value2:.3f}m")
                else:
                    print(f"  Still out of bounds")

            except Exception as e:
                print(f"  Error: {e}")
        else:
            print(f"  CRS matches (EPSG:3857)")

    print("\n" + "="*80)


if __name__ == "__main__":
    try:
        debug_transforms()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
