# filename: app/services/dem_service.py

"""
DEM (Digital Elevation Model) Service for Terrain-Based Risk Assessment
========================================================================

Loads and queries the Marikina City DEM (marikina_dem.tif) to provide:
- Ground elevation queries at any WGS84 coordinate
- Pre-computed slope and relative elevation arrays
- Flood depth estimation from water surface elevation
- Batch precomputation of graph node elevations

The DEM enables terrain-based "prior" risk scoring: low-lying areas are
marked riskier even before real-time flood data arrives.

Data:
- File: app/data/marikina_dem.tif
- CRS: EPSG:3857 (Web Mercator)
- Resolution: ~31m (211x220 pixels)
- Elevation range: 0-87m

Author: MAS-FRO Development Team
Date: February 2026
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

# Configure GDAL before rasterio import
os.environ.setdefault('GTIFF_SRS_SOURCE', 'EPSG')
os.environ.setdefault('CPL_LOG', os.devnull)

import rasterio
from pyproj import Transformer
from scipy.ndimage import uniform_filter

logger = logging.getLogger(__name__)


class DEMService:
    """
    Service for querying terrain data from a DEM GeoTIFF.

    Provides elevation, slope, and relative elevation queries,
    plus flood depth estimation via water surface interpolation.
    """

    def __init__(
        self,
        dem_path: str = "app/data/marikina_dem.tif",
        regional_radius_pixels: int = 65,
    ) -> None:
        """
        Initialize the DEM service.

        Args:
            dem_path: Path to the DEM GeoTIFF file.
            regional_radius_pixels: Radius for regional-scale relative elevation (~2km window).
        """
        self._path = Path(dem_path)
        if not self._path.exists():
            raise FileNotFoundError(f"DEM file not found: {self._path}")

        with rasterio.open(self._path) as src:
            self._data: np.ndarray = src.read(1).astype(np.float32)
            self._transform = src.transform
            self._bounds = src.bounds
            self._crs = src.crs
            self._height, self._width = self._data.shape
            self._nodata = src.nodata

        # Mask nodata values with NaN
        if self._nodata is not None:
            self._data[self._data == self._nodata] = np.nan

        # WGS84 (EPSG:4326) -> Web Mercator (EPSG:3857) transformer
        self._transformer = Transformer.from_crs(
            "EPSG:4326", "EPSG:3857", always_xy=True
        )

        # Pre-compute slope array (degrees)
        self._slope_array = self._compute_slope()

        # Pre-compute relative elevation at local scale (meters above/below neighborhood mean)
        self._relative_elevation = self._compute_relative_elevation()

        # Pre-compute relative elevation at regional scale (wider window catches floodplains)
        self._relative_elevation_regional = self._compute_relative_elevation(
            radius_pixels=regional_radius_pixels
        )

        # WGS84 bounds for quick coverage checks
        inv_transformer = Transformer.from_crs(
            "EPSG:3857", "EPSG:4326", always_xy=True
        )
        lon_min, lat_min = inv_transformer.transform(
            self._bounds.left, self._bounds.bottom
        )
        lon_max, lat_max = inv_transformer.transform(
            self._bounds.right, self._bounds.top
        )
        self._wgs84_bounds = {
            "min_lon": lon_min,
            "max_lon": lon_max,
            "min_lat": lat_min,
            "max_lat": lat_max,
        }

        logger.info(
            f"DEMService initialized: {self._width}x{self._height}px, "
            f"elevation range [{np.nanmin(self._data):.1f}, {np.nanmax(self._data):.1f}]m, "
            f"CRS={self._crs}, regional_radius={regional_radius_pixels}px"
        )

    def _compute_slope(self) -> np.ndarray:
        """Compute slope in degrees from elevation data using numpy gradient."""
        # Pixel size in meters (approximate from transform)
        pixel_x = abs(self._transform.a)  # meters per pixel (x)
        pixel_y = abs(self._transform.e)  # meters per pixel (y)

        dy, dx = np.gradient(self._data, pixel_y, pixel_x)
        slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
        return np.degrees(slope_rad)

    def _compute_relative_elevation(self, radius_pixels: int = 5) -> np.ndarray:
        """
        Compute relative elevation: difference from neighborhood mean.

        Negative values indicate depressions (flood-prone).
        Uses scipy uniform_filter (O(n) regardless of kernel size via separable filters).

        Args:
            radius_pixels: Half-size of the averaging window.

        Returns:
            Array of (elevation - local_mean) in meters.
        """
        mask = ~np.isnan(self._data)
        data_filled = np.where(mask, self._data, 0.0).astype(np.float64)
        mask_f64 = mask.astype(np.float64)

        kernel_size = 2 * radius_pixels + 1

        # uniform_filter computes mean over the window (O(n) via separable 1D passes)
        # NaN-aware mean = sum(values) / count(valid) = data_mean / mask_mean
        data_mean = uniform_filter(data_filled, size=kernel_size, mode='reflect')
        mask_mean = uniform_filter(mask_f64, size=kernel_size, mode='reflect')

        # Avoid division by zero where entire window is NaN
        safe_mask_mean = np.maximum(mask_mean, 1e-10)
        local_mean = (data_mean / safe_mask_mean).astype(np.float32)

        rel_elev = self._data - local_mean
        rel_elev[~mask] = np.nan

        return rel_elev

    def _to_pixel(self, lon: float, lat: float) -> Optional[Tuple[int, int]]:
        """
        Convert WGS84 lon/lat to pixel (row, col).

        Returns None if out of bounds.
        """
        # Transform to EPSG:3857
        x, y = self._transformer.transform(lon, lat)

        # Check bounds
        if not (self._bounds.left <= x <= self._bounds.right and
                self._bounds.bottom <= y <= self._bounds.top):
            return None

        # Convert to pixel coordinates (round instead of truncate to avoid
        # systematic off-by-one bias at pixel boundaries)
        col_f, row_f = ~self._transform * (x, y)
        row, col = round(row_f), round(col_f)

        # Bounds check
        if 0 <= row < self._height and 0 <= col < self._width:
            return row, col
        return None

    def get_elevation(self, lon: float, lat: float) -> Optional[float]:
        """
        Get ground elevation at a WGS84 coordinate.

        Args:
            lon: Longitude (degrees)
            lat: Latitude (degrees)

        Returns:
            Elevation in meters, or None if out of bounds.
        """
        pixel = self._to_pixel(lon, lat)
        if pixel is None:
            return None
        row, col = pixel
        val = self._data[row, col]
        return float(val) if not np.isnan(val) else None

    def get_elevations_batch(
        self, coords: List[Tuple[float, float]]
    ) -> List[Optional[float]]:
        """
        Batch query elevations for multiple (lon, lat) coordinates.

        Args:
            coords: List of (lon, lat) tuples.

        Returns:
            List of elevations (meters) or None for each coordinate.
        """
        results: List[Optional[float]] = []
        for lon, lat in coords:
            results.append(self.get_elevation(lon, lat))
        return results

    def get_slope(self, lon: float, lat: float) -> Optional[float]:
        """
        Get terrain slope at a WGS84 coordinate.

        Args:
            lon: Longitude
            lat: Latitude

        Returns:
            Slope in degrees, or None if out of bounds.
        """
        pixel = self._to_pixel(lon, lat)
        if pixel is None:
            return None
        row, col = pixel
        val = self._slope_array[row, col]
        return float(val) if not np.isnan(val) else None

    def get_relative_elevation(self, lon: float, lat: float) -> Optional[float]:
        """
        Get relative elevation (meters above/below neighborhood mean).

        Negative values indicate depressions that are flood-prone.

        Args:
            lon: Longitude
            lat: Latitude

        Returns:
            Relative elevation in meters, or None if out of bounds.
        """
        pixel = self._to_pixel(lon, lat)
        if pixel is None:
            return None
        row, col = pixel
        val = self._relative_elevation[row, col]
        return float(val) if not np.isnan(val) else None

    def get_regional_relative_elevation(self, lon: float, lat: float) -> Optional[float]:
        """
        Get regional-scale relative elevation (meters above/below wide neighborhood mean).

        Uses a larger window than get_relative_elevation() to detect wide floodplains
        where the local window sees everything as "flat".

        Args:
            lon: Longitude
            lat: Latitude

        Returns:
            Regional relative elevation in meters, or None if out of bounds.
        """
        pixel = self._to_pixel(lon, lat)
        if pixel is None:
            return None
        row, col = pixel
        val = self._relative_elevation_regional[row, col]
        return float(val) if not np.isnan(val) else None

    def check_line_of_sight(
        self,
        lon1: float,
        lat1: float,
        lon2: float,
        lat2: float,
        max_elevation: float,
        num_samples: int = 5,
    ) -> bool:
        """
        Check if terrain between two points stays below a max elevation.

        Samples N evenly-spaced interior points along the line from (lon1,lat1)
        to (lon2,lat2). If any sample elevation exceeds max_elevation, returns
        False (barrier detected — a ridge or levee blocks water flow).

        Args:
            lon1, lat1: Start point (WGS84)
            lon2, lat2: End point (WGS84)
            max_elevation: Maximum allowed elevation (meters, typically WSE)
            num_samples: Number of interior sample points

        Returns:
            True if line of sight is clear (no barrier), False if blocked.
        """
        if num_samples < 1:
            return True

        for i in range(1, num_samples + 1):
            t = i / (num_samples + 1)
            sample_lon = lon1 + t * (lon2 - lon1)
            sample_lat = lat1 + t * (lat2 - lat1)
            elev = self.get_elevation(sample_lon, sample_lat)
            if elev is None:
                continue  # Outside DEM coverage — skip
            if elev > max_elevation:
                return False  # Barrier detected
        return True

    def estimate_flood_depth(
        self, lon: float, lat: float, water_surface_elevation: float
    ) -> Optional[float]:
        """
        Estimate flood depth at a point given a water surface elevation.

        Args:
            lon: Longitude
            lat: Latitude
            water_surface_elevation: Water surface elevation in meters.

        Returns:
            Estimated flood depth (meters), or None if out of bounds.
            Returns 0.0 if ground is above the water surface.
        """
        ground_elev = self.get_elevation(lon, lat)
        if ground_elev is None:
            return None
        return max(0.0, water_surface_elevation - ground_elev)

    def precompute_node_elevations(
        self, graph: Any
    ) -> Dict[int, Dict[str, Optional[float]]]:
        """
        Batch-query elevations for all graph nodes and store as node attributes.

        Args:
            graph: NetworkX MultiDiGraph with nodes having 'x' (lon) and 'y' (lat) attrs.

        Returns:
            Dict mapping node_id -> {elevation, slope, relative_elevation}.
        """
        node_elevations: Dict[int, Dict[str, Optional[float]]] = {}
        valid_count = 0

        for node_id, node_data in graph.nodes(data=True):
            lon = node_data.get('x')
            lat = node_data.get('y')

            if lon is None or lat is None:
                continue

            elev = self.get_elevation(lon, lat)
            slope = self.get_slope(lon, lat)
            rel_elev = self.get_relative_elevation(lon, lat)
            reg_rel_elev = self.get_regional_relative_elevation(lon, lat)

            info = {
                "elevation": elev,
                "slope": slope,
                "relative_elevation": rel_elev,
                "regional_relative_elevation": reg_rel_elev,
            }
            node_elevations[node_id] = info

            # Store on graph node as well for O(1) lookup
            graph.nodes[node_id]['dem_elevation'] = elev
            graph.nodes[node_id]['dem_slope'] = slope
            graph.nodes[node_id]['dem_relative_elevation'] = rel_elev
            graph.nodes[node_id]['dem_regional_relative_elevation'] = reg_rel_elev

            if elev is not None:
                valid_count += 1

        total = len(node_elevations)
        logger.info(
            f"Precomputed DEM elevations for {valid_count}/{total} nodes "
            f"({valid_count/total*100:.1f}% coverage)" if total > 0
            else "No graph nodes to precompute"
        )

        return node_elevations

    def is_within_coverage(self, lon: float, lat: float) -> bool:
        """Check if a WGS84 coordinate falls within the DEM coverage area."""
        b = self._wgs84_bounds
        return (b["min_lon"] <= lon <= b["max_lon"] and
                b["min_lat"] <= lat <= b["max_lat"])

    def get_bounds(self) -> Dict[str, float]:
        """Get DEM coverage bounds in WGS84."""
        return dict(self._wgs84_bounds)


# Singleton instance
_dem_service: Optional[DEMService] = None


def get_dem_service(
    dem_path: str = "app/data/marikina_dem.tif",
    regional_radius_pixels: int = 65,
) -> DEMService:
    """Get or create the global DEM service singleton."""
    global _dem_service
    if _dem_service is None:
        _dem_service = DEMService(dem_path, regional_radius_pixels=regional_radius_pixels)
    return _dem_service
