# filename: app/services/river_proximity_service.py

"""
River Proximity Service for MAS-FRO

Pre-computes per-node distance to nearest waterway (Marikina River, Nangka River,
tributaries) so the HazardAgent can apply a river proximity risk prior on edges.

Risk formula: river_risk = type_weight * exp(-distance_m / decay_distance_m)
  - At riverbank (0m): risk = type_weight (1.0 for rivers)
  - At 200m: risk ~= 0.37 * type_weight
  - At 600m: risk ~= 0.05 * type_weight

Waterway type weights:
  river / tidal_channel -> 1.0
  stream                -> 0.7
  canal / drain         -> 0.4
  ditch                 -> 0.3
"""

import math
import logging
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Waterway OSM type -> risk weight
_WATERWAY_WEIGHTS: Dict[str, float] = {
    "river": 1.0,
    "tidal_channel": 1.0,
    "stream": 0.7,
    "canal": 0.4,
    "drain": 0.4,
    "ditch": 0.3,
}


class RiverProximityService:
    """
    Singleton service that fetches/caches Marikina waterway geometries and
    pre-computes per-node risk scores based on distance to nearest waterway.
    """

    _instance: Optional['RiverProximityService'] = None

    def __new__(cls, cache_file: str, fetch_place: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, cache_file: str, fetch_place: str):
        if self._initialized:
            return
        self.cache_file = Path(cache_file)
        self.fetch_place = fetch_place
        self._geoms_utm: List = []      # list of shapely geometries in UTM
        self._strtree = None             # shapely STRtree spatial index
        self._waterway_weights: List[float] = []  # per-geometry weights
        self._feature_count: int = 0
        self._node_river_data: Dict[int, Dict[str, float]] = {}
        self._loaded: bool = False
        self._initialized = True
        self._load_waterways()

    # ------------------------------------------------------------------ #
    # Internal loading helpers                                             #
    # ------------------------------------------------------------------ #

    def _load_waterways(self) -> None:
        """Load waterway geometries from GeoJSON cache or fetch via OSMnx."""
        try:
            import geopandas as gpd
            from pyproj import CRS
        except ImportError:
            logger.warning("geopandas/pyproj not available — river proximity disabled")
            return

        utm_crs = CRS.from_epsg(32651)  # UTM Zone 51N — covers the Philippines

        # --- Try loading from cached GeoJSON ---
        if self.cache_file.exists():
            try:
                gdf = gpd.read_file(self.cache_file)
                if len(gdf) == 0:
                    logger.warning("Cached waterway file is empty — will re-fetch")
                else:
                    gdf_utm = gdf.to_crs(utm_crs)
                    self._setup_strtree(gdf_utm)
                    logger.info(
                        f"Loaded {self._feature_count} waterway features "
                        f"from cache: {self.cache_file}"
                    )
                    self._loaded = True
                    return
            except Exception as exc:
                logger.warning(f"Failed to read cached waterways ({exc}) — re-fetching")

        # --- Fetch from OSMnx ---
        try:
            import osmnx as ox
        except ImportError:
            logger.warning("osmnx not available — river proximity disabled")
            return

        logger.info(
            f"Fetching waterway features for '{self.fetch_place}' via OSMnx "
            f"(this may take ~10-30 s)..."
        )
        try:
            gdf_wgs84 = ox.features_from_place(
                self.fetch_place,
                tags={"waterway": True},
            )
            # Keep only line features (waterway centrelines, not polygons/points)
            gdf_wgs84 = gdf_wgs84[
                gdf_wgs84.geometry.geom_type.isin(["LineString", "MultiLineString"])
            ].copy()

            if len(gdf_wgs84) == 0:
                logger.warning(
                    "No waterway LineString features found via OSMnx — "
                    "river proximity disabled"
                )
                return

            # Persist cache (WGS84 for portability)
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            gdf_wgs84.reset_index().to_file(self.cache_file, driver="GeoJSON")
            logger.info(
                f"Saved {len(gdf_wgs84)} waterway features to cache: {self.cache_file}"
            )

            gdf_utm = gdf_wgs84.to_crs(utm_crs)
            self._setup_strtree(gdf_utm)
            self._loaded = True
        except Exception as exc:
            logger.error(f"Failed to fetch waterway features: {exc}")

    def _setup_strtree(self, gdf_utm) -> None:
        """Build a shapely STRtree from the projected GeoDataFrame."""
        from shapely.strtree import STRtree

        self._geoms_utm = list(gdf_utm.geometry)
        self._strtree = STRtree(self._geoms_utm)

        # Map each geometry to its waterway-type weight
        ww_col = gdf_utm.get("waterway") if "waterway" in gdf_utm.columns else None
        self._waterway_weights = []
        for i in range(len(self._geoms_utm)):
            if ww_col is not None:
                wtype = str(ww_col.iloc[i]).lower()
            else:
                wtype = "river"
            self._waterway_weights.append(_WATERWAY_WEIGHTS.get(wtype, 0.4))

        self._feature_count = len(self._geoms_utm)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def precompute_node_distances(
        self,
        graph,
        decay_distance_m: float = 200.0,
    ) -> Dict[int, Dict[str, float]]:
        """
        Compute river_distance_m and river_risk for every graph node.

        Projects node lat/lon to UTM, queries the STRtree for the nearest
        waterway geometry, then applies the exponential decay formula:
            risk = type_weight * exp(-distance_m / decay_distance_m)

        Args:
            graph: NetworkX MultiDiGraph from OSMnx (nodes carry 'y'=lat, 'x'=lon).
            decay_distance_m: e-folding distance for risk decay (default 200 m).

        Returns:
            Dict mapping node_id -> {"river_distance_m": float, "river_risk": float}
        """
        if not self._loaded or self._strtree is None:
            logger.warning(
                "RiverProximityService not loaded — skipping node precomputation"
            )
            return {}

        try:
            from pyproj import Transformer
            from shapely.geometry import Point
        except ImportError:
            logger.warning(
                "pyproj/shapely not available — skipping river precomputation"
            )
            return {}

        transformer = Transformer.from_crs(
            "EPSG:4326", "EPSG:32651", always_xy=True
        )
        nodes = list(graph.nodes(data=True))
        logger.info(
            f"Precomputing river proximity distances for {len(nodes)} nodes..."
        )

        node_data: Dict[int, Dict[str, float]] = {}
        for node_id, attrs in nodes:
            lat = attrs.get("y")
            lon = attrs.get("x")
            if lat is None or lon is None:
                node_data[node_id] = {"river_distance_m": 999_999.0, "river_risk": 0.0}
                continue

            x_utm, y_utm = transformer.transform(lon, lat)
            pt = Point(x_utm, y_utm)

            nearest_idx = self._strtree.nearest(pt)
            if nearest_idx is None:
                node_data[node_id] = {"river_distance_m": 999_999.0, "river_risk": 0.0}
                continue

            dist_m: float = pt.distance(self._geoms_utm[nearest_idx])
            weight: float = self._waterway_weights[nearest_idx]
            risk: float = float(np.clip(
                weight * math.exp(-dist_m / max(decay_distance_m, 1.0)),
                0.0, 1.0,
            ))
            node_data[node_id] = {"river_distance_m": dist_m, "river_risk": risk}

        self._node_river_data = node_data

        within_500 = sum(1 for d in node_data.values() if d["river_distance_m"] < 500)
        logger.info(
            f"River proximity precomputed: {len(node_data)} nodes, "
            f"{within_500} within 500 m of a waterway"
        )
        return node_data

    def get_stats(self) -> Dict[str, Any]:
        """Return summary statistics for the admin endpoint."""
        if not self._node_river_data:
            return {
                "loaded": self._loaded,
                "feature_count": self._feature_count,
                "nodes_computed": 0,
            }
        distances = [d["river_distance_m"] for d in self._node_river_data.values()]
        return {
            "loaded": self._loaded,
            "feature_count": self._feature_count,
            "nodes_computed": len(self._node_river_data),
            "nodes_within_200m": sum(1 for d in distances if d < 200),
            "nodes_within_500m": sum(1 for d in distances if d < 500),
            "min_distance_m": round(min(distances), 1) if distances else None,
            "avg_distance_m": round(float(np.mean(distances)), 1) if distances else None,
            "cache_file": str(self.cache_file),
        }


# --------------------------------------------------------------------------- #
# Module-level singleton accessor                                              #
# --------------------------------------------------------------------------- #

_service_instance: Optional[RiverProximityService] = None


def get_river_proximity_service(
    cache_file: str = "app/data/marikina_waterways.geojson",
    fetch_place: str = "Marikina, Metro Manila, Philippines",
) -> RiverProximityService:
    """Get or create the singleton RiverProximityService."""
    global _service_instance
    if _service_instance is None:
        _service_instance = RiverProximityService(
            cache_file=cache_file, fetch_place=fetch_place
        )
    return _service_instance
