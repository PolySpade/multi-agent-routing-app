#!/usr/bin/env python3
"""
Check GeoTIFF Coordinates for Flood Maps

This script reads a GeoTIFF file and displays its coordinate information
to help diagnose alignment issues.

Usage:
    python check_flood_tiff_coords.py app/data/timed_floodmaps/rr01/rr01-1.tif
"""

import sys
from pathlib import Path

try:
    from osgeo import gdal, osr
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    print("WARNING: GDAL not available. Using alternative method...")

def check_with_gdal(tiff_path):
    """Check TIFF coordinates using GDAL."""
    dataset = gdal.Open(str(tiff_path))

    if dataset is None:
        print(f"❌ Failed to open {tiff_path}")
        return

    # Get basic info
    width = dataset.RasterXSize
    height = dataset.RasterYSize
    gt = dataset.GetGeoTransform()
    proj = dataset.GetProjection()

    # Calculate corners
    minX = gt[0]
    maxY = gt[3]
    maxX = gt[0] + width * gt[1]
    minY = gt[3] + height * gt[5]

    print("\n" + "="*60)
    print("📍 GeoTIFF Coordinate Information")
    print("="*60)
    print(f"\n📄 File: {tiff_path.name}")
    print(f"📐 Dimensions: {width} x {height} pixels")
    print(f"\n🗺️  Bounding Box (Original Projection):")
    print(f"   Min X: {minX:,.2f}")
    print(f"   Max X: {maxX:,.2f}")
    print(f"   Min Y: {minY:,.2f}")
    print(f"   Max Y: {maxY:,.2f}")

    # Parse projection
    srs = osr.SpatialReference()
    srs.ImportFromWkt(proj)
    proj_name = srs.GetAttrValue('PROJCS') or srs.GetAttrValue('GEOGCS') or 'Unknown'
    auth_name = srs.GetAttrValue('AUTHORITY', 0) or 'Unknown'
    auth_code = srs.GetAttrValue('AUTHORITY', 1) or 'Unknown'

    print(f"\n🌐 Projection: {proj_name}")
    print(f"   EPSG Code: {auth_name}:{auth_code}")

    # If EPSG:3857, convert to lat/lng
    if auth_code == '3857':
        from pyproj import Transformer
        transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

        west, south = transformer.transform(minX, minY)
        east, north = transformer.transform(maxX, maxY)

        print(f"\n✅ Converted to EPSG:4326 (Lat/Lng):")
        print(f"   West:  {west:.6f}°")
        print(f"   East:  {east:.6f}°")
        print(f"   South: {south:.6f}°")
        print(f"   North: {north:.6f}°")

        print(f"\n📊 Expected for Marikina City:")
        print(f"   Longitude: 121.08° to 121.12°")
        print(f"   Latitude:  14.63° to 14.75°")

        # Check if in range
        in_lng_range = 121.05 <= west <= 121.15 and 121.05 <= east <= 121.15
        in_lat_range = 14.60 <= south <= 14.80 and 14.60 <= north <= 14.80

        if in_lng_range and in_lat_range:
            print(f"\n✅ COORDINATES LOOK CORRECT for Marikina!")
        else:
            print(f"\n❌ COORDINATES ARE OUTSIDE MARIKINA RANGE!")
            print(f"   This explains the misalignment issue.")
            print(f"\n💡 Solution: Use manual bounds in MapboxMap.js")

    elif auth_code == '32651':  # UTM Zone 51N
        print(f"\n⚠️ Using UTM Zone 51N projection")
        print(f"   This needs conversion to EPSG:4326 in the frontend")

    else:
        print(f"\n⚠️ Unknown or custom projection")
        print(f"   May need manual coordinate specification")

    print("\n" + "="*60)

    dataset = None


def check_with_geotiff(tiff_path):
    """Check TIFF coordinates using geotiff library."""
    try:
        from geotiff import GeoTiff

        geo_tiff = GeoTiff(str(tiff_path))
        bbox = geo_tiff.tif_bBox

        print("\n" + "="*60)
        print("📍 GeoTIFF Coordinate Information (geotiff library)")
        print("="*60)
        print(f"\n📄 File: {tiff_path.name}")
        print(f"\n🗺️  Bounding Box:")
        print(f"   {bbox}")

        if len(bbox) == 4:
            minX, minY, maxX, maxY = bbox[0]
            print(f"\n   Min X: {minX:,.2f}")
            print(f"   Max X: {maxX:,.2f}")
            print(f"   Min Y: {minY:,.2f}")
            print(f"   Max Y: {maxY:,.2f}")

        print("\n💡 If coordinates look wrong, use manual bounds in MapboxMap.js")
        print("="*60)

    except Exception as e:
        print(f"❌ Error with geotiff library: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_flood_tiff_coords.py <path_to_tiff>")
        print("\nExample:")
        print("  python check_flood_tiff_coords.py app/data/timed_floodmaps/rr01/rr01-1.tif")
        sys.exit(1)

    tiff_path = Path(sys.argv[1])

    if not tiff_path.exists():
        print(f"❌ File not found: {tiff_path}")
        sys.exit(1)

    print(f"\n🔍 Checking flood TIFF coordinates...")

    if GDAL_AVAILABLE:
        check_with_gdal(tiff_path)
    else:
        print("\n⚠️ GDAL not installed. Trying alternative method...")
        print("   To install GDAL: pip install gdal")
        print("   Or install via conda: conda install gdal")
        check_with_geotiff(tiff_path)


if __name__ == "__main__":
    main()
