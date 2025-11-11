# filename: app/services/geotiff_service.py

"""
GeoTIFF Service for Flood Map Data
===================================

Loads and serves flood depth data from GeoTIFF files for different
return periods and time steps.

Data Structure:
- 4 return periods: rr01, rr02, rr03, rr04
- 18 time steps each (1-18 hours)
- Total: 72 GeoTIFF files
- Resolution: 368x372 pixels
- CRS: EPSG:3857 (Web Mercator)

Author: MAS-FRO Development Team
Date: November 2025
"""

import os
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import numpy as np

# Configure GDAL environment variables BEFORE importing rasterio
# These settings handle non-standard GeoTIFF coordinate reference systems
os.environ['GTIFF_SRS_SOURCE'] = 'EPSG'  # Use official EPSG parameters over GeoTIFF keys
os.environ['GTIFF_HONOUR_NEGATIVE_SCALEY'] = 'YES'  # Handle negative ScaleY values correctly
os.environ['CPL_LOG'] = '/dev/null'  # Suppress GDAL C-level log messages

import rasterio
from rasterio.transform import rowcol
from functools import lru_cache

logger = logging.getLogger(__name__)


class GeoTIFFService:
    """
    Service for loading and querying GeoTIFF flood map data.

    Features:
    - Lazy loading of GeoTIFF files
    - Caching for performance
    - Query flood depth at coordinates
    - Get flood map bounds and metadata
    """

    def __init__(self, data_dir: str = "app/data/timed_floodmaps"):
        """
        Initialize GeoTIFF service.

        Args:
            data_dir: Directory containing GeoTIFF files
        """
        self.data_dir = Path(data_dir)
        self.return_periods = ["rr01", "rr02", "rr03", "rr04"]
        self.time_steps = list(range(1, 19))  # 1-18

        # Cache for loaded GeoTIFF data
        self._cache: Dict[str, np.ndarray] = {}
        self._metadata_cache: Dict[str, Dict] = {}

        # Verify data directory exists
        if not self.data_dir.exists():
            logger.error(f"GeoTIFF data directory not found: {self.data_dir}")
            raise FileNotFoundError(f"Directory not found: {self.data_dir}")

        logger.info(
            f"GeoTIFFService initialized: {len(self.return_periods)} return periods, "
            f"{len(self.time_steps)} time steps"
        )

    def _get_file_path(self, return_period: str, time_step: int) -> Path:
        """
        Get file path for specific return period and time step.

        Args:
            return_period: Return period (rr01, rr02, rr03, rr04)
            time_step: Time step (1-18)

        Returns:
            Path to GeoTIFF file
        """
        return self.data_dir / return_period / f"{return_period}-{time_step}.tif"

    def _get_cache_key(self, return_period: str, time_step: int) -> str:
        """Generate cache key for return period and time step."""
        return f"{return_period}_{time_step}"

    @lru_cache(maxsize=32)
    def load_flood_map(
        self,
        return_period: str = "rr01",
        time_step: int = 1
    ) -> Tuple[np.ndarray, Dict]:
        """
        Load flood map data from GeoTIFF file.

        Args:
            return_period: Return period (rr01, rr02, rr03, rr04)
            time_step: Time step (1-18)

        Returns:
            Tuple of (flood_depth_array, metadata_dict)

        Raises:
            ValueError: If invalid return period or time step
            FileNotFoundError: If GeoTIFF file not found
        """
        # Validate inputs
        if return_period not in self.return_periods:
            raise ValueError(
                f"Invalid return period: {return_period}. "
                f"Valid options: {self.return_periods}"
            )

        if time_step not in self.time_steps:
            raise ValueError(
                f"Invalid time step: {time_step}. "
                f"Valid range: 1-18"
            )

        file_path = self._get_file_path(return_period, time_step)

        if not file_path.exists():
            raise FileNotFoundError(f"GeoTIFF file not found: {file_path}")

        try:
            with rasterio.open(file_path) as src:
                # Read flood depth data
                data = src.read(1)

                # Get metadata
                metadata = {
                    "bounds": {
                        "left": src.bounds.left,
                        "bottom": src.bounds.bottom,
                        "right": src.bounds.right,
                        "top": src.bounds.top
                    },
                    "shape": src.shape,
                    "crs": str(src.crs),
                    "transform": list(src.transform)[:6],  # Affine transform
                    "nodata": src.nodata,
                    "return_period": return_period,
                    "time_step": time_step
                }

                # Calculate statistics
                valid_data = data[~np.isnan(data)]
                flooded_pixels = data[(~np.isnan(data)) & (data > 0.01)]  # >1cm threshold

                metadata["statistics"] = {
                    "total_pixels": int(data.size),
                    "valid_pixels": int(valid_data.size),
                    "flooded_pixels": int(flooded_pixels.size),
                    "min_depth": float(np.min(flooded_pixels)) if flooded_pixels.size > 0 else 0.0,
                    "max_depth": float(np.max(flooded_pixels)) if flooded_pixels.size > 0 else 0.0,
                    "mean_depth": float(np.mean(flooded_pixels)) if flooded_pixels.size > 0 else 0.0,
                }

                logger.debug(
                    f"Loaded {return_period}-{time_step}: "
                    f"{metadata['statistics']['flooded_pixels']} flooded pixels"
                )

                return data, metadata

        except Exception as e:
            logger.error(f"Error loading GeoTIFF {file_path}: {e}")
            raise

    def get_flood_depth_at_point(
        self,
        lon: float,
        lat: float,
        return_period: str = "rr01",
        time_step: int = 1
    ) -> Optional[float]:
        """
        Get flood depth at a specific coordinate.

        Args:
            lon: Longitude (in degrees)
            lat: Latitude (in degrees)
            return_period: Return period (rr01, rr02, rr03, rr04)
            time_step: Time step (1-18)

        Returns:
            Flood depth in meters, or None if outside bounds or NaN
        """
        file_path = self._get_file_path(return_period, time_step)

        try:
            with rasterio.open(file_path) as src:
                # Convert WGS84 (lon, lat) to Web Mercator (x, y)
                from pyproj import Transformer
                transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
                x, y = transformer.transform(lon, lat)

                # Convert coordinates to row, col
                row, col = rowcol(src.transform, x, y)

                # Check if within bounds
                if 0 <= row < src.height and 0 <= col < src.width:
                    depth = src.read(1)[row, col]
                    return float(depth) if not np.isnan(depth) else None
                else:
                    return None

        except Exception as e:
            logger.error(f"Error querying flood depth: {e}")
            return None

    def get_flood_map_as_geojson(
        self,
        return_period: str = "rr01",
        time_step: int = 1,
        threshold: float = 0.01
    ) -> Dict:
        """
        Convert flood map to GeoJSON format for frontend visualization.

        Args:
            return_period: Return period (rr01, rr02, rr03, rr04)
            time_step: Time step (1-18)
            threshold: Minimum depth to include (meters)

        Returns:
            GeoJSON FeatureCollection with flood depth data
        """
        data, metadata = self.load_flood_map(return_period, time_step)

        # For now, return metadata and bounds
        # Full rasterization to GeoJSON would be too large
        # Frontend will fetch the raw TIFF via endpoint instead

        return {
            "type": "FeatureCollection",
            "metadata": metadata,
            "features": []  # Placeholder - use TIFF endpoint for actual data
        }

    def get_available_maps(self) -> List[Dict[str, any]]:
        """
        Get list of all available flood maps.

        Returns:
            List of dicts with return_period and time_step info
        """
        available_maps = []

        for rp in self.return_periods:
            for ts in self.time_steps:
                file_path = self._get_file_path(rp, ts)
                if file_path.exists():
                    available_maps.append({
                        "return_period": rp,
                        "time_step": ts,
                        "file": str(file_path.relative_to(self.data_dir))
                    })

        logger.info(f"Found {len(available_maps)} available flood maps")
        return available_maps


# Global service instance
_geotiff_service: Optional[GeoTIFFService] = None


def get_geotiff_service() -> GeoTIFFService:
    """Get or create global GeoTIFF service instance."""
    global _geotiff_service
    if _geotiff_service is None:
        _geotiff_service = GeoTIFFService()
    return _geotiff_service
