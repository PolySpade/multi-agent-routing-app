#!/usr/bin/env python3
"""Simple TIFF coordinate checker"""

import sys
import struct
from pathlib import Path

def read_tiff_basic(tiff_path):
    """Read basic TIFF information."""
    with open(tiff_path, 'rb') as f:
        # Read byte order
        byte_order = f.read(2)
        if byte_order == b'II':
            endian = '<'  # Little-endian
        elif byte_order == b'MM':
            endian = '>'  # Big-endian
        else:
            print("ERROR: Not a valid TIFF file")
            return

        # Read magic number
        magic = struct.unpack(f'{endian}H', f.read(2))[0]
        if magic != 42 and magic != 43:
            print("ERROR: Invalid TIFF magic number")
            return

        print("="*60)
        print("TIFF File Information")
        print("="*60)
        print(f"File: {tiff_path.name}")
        print(f"Byte Order: {'Little-endian' if endian == '<' else 'Big-endian'}")
        print(f"TIFF Version: {magic}")

        # For more detailed info, we need libraries
        print("\nNOTE: For detailed coordinate info, install:")
        print("  pip install gdal")
        print("  OR")
        print("  pip install rasterio")
        print("="*60)


def check_with_rasterio(tiff_path):
    """Check using rasterio if available."""
    try:
        import rasterio
        from rasterio.warp import transform_bounds

        with rasterio.open(tiff_path) as src:
            print("\n" + "="*60)
            print("GeoTIFF Coordinate Information (rasterio)")
            print("="*60)
            print(f"\nFile: {tiff_path.name}")
            print(f"Dimensions: {src.width} x {src.height} pixels")
            print(f"CRS: {src.crs}")
            print(f"\nBounds (original projection):")
            print(f"  Left:   {src.bounds.left:.2f}")
            print(f"  Bottom: {src.bounds.bottom:.2f}")
            print(f"  Right:  {src.bounds.right:.2f}")
            print(f"  Top:    {src.bounds.top:.2f}")

            # Try to transform to EPSG:4326
            if src.crs and src.crs.to_epsg() == 3857:
                bounds_4326 = transform_bounds(
                    src.crs,
                    'EPSG:4326',
                    src.bounds.left,
                    src.bounds.bottom,
                    src.bounds.right,
                    src.bounds.top
                )

                print(f"\nConverted to EPSG:4326 (Lat/Lng):")
                print(f"  West:  {bounds_4326[0]:.6f} degrees")
                print(f"  South: {bounds_4326[1]:.6f} degrees")
                print(f"  East:  {bounds_4326[2]:.6f} degrees")
                print(f"  North: {bounds_4326[3]:.6f} degrees")

                print(f"\nExpected for Marikina City:")
                print(f"  Longitude: 121.08 to 121.12")
                print(f"  Latitude:  14.63 to 14.75")

                # Check alignment
                west, south, east, north = bounds_4326
                lng_ok = 121.05 <= west <= 121.15 and 121.05 <= east <= 121.15
                lat_ok = 14.60 <= south <= 14.80 and 14.60 <= north <= 14.80

                if lng_ok and lat_ok:
                    print(f"\n[OK] Coordinates are within Marikina range")
                else:
                    print(f"\n[ERROR] Coordinates are OUTSIDE Marikina range!")
                    print(f"  This is why the map is misaligned.")
                    print(f"\n  SOLUTION: Use manual bounds in MapboxMap.js:")
                    print(f"    west = 121.0850")
                    print(f"    east = 121.1150")
                    print(f"    south = 14.6400")
                    print(f"    north = 14.7300")
            else:
                print(f"\nProjection: {src.crs}")
                print(f"  (Not EPSG:3857 - may need special handling)")

            print("="*60)
            return True

    except ImportError:
        return False
    except Exception as e:
        print(f"ERROR with rasterio: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_tiff_simple.py <path_to_tiff>")
        print("\nExample:")
        print("  python check_tiff_simple.py app/data/timed_floodmaps/rr01/rr01-1.tif")
        sys.exit(1)

    tiff_path = Path(sys.argv[1])

    if not tiff_path.exists():
        print(f"ERROR: File not found: {tiff_path}")
        sys.exit(1)

    # Try rasterio first
    if check_with_rasterio(tiff_path):
        return

    # Fallback to basic info
    print("\nWARNING: rasterio not installed. Showing basic info only.")
    print("  For full coordinate info, install: pip install rasterio\n")
    read_tiff_basic(tiff_path)


if __name__ == "__main__":
    main()
