# filename: app/services/google_traffic_service.py

"""
Google Maps Traffic Service for MAS-FRO

Integrates real-time traffic data from Google Maps Directions API
to enhance route optimization with current traffic conditions.

API Documentation:
https://developers.google.com/maps/documentation/directions/overview

Author: MAS-FRO Development Team
Date: November 2025
"""

import os
import logging
import requests
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

load_dotenv()
logger = logging.getLogger(__name__)


class GoogleTrafficService:
    """
    Service for fetching and processing real-time traffic data from Google Maps.

    Uses the Google Directions API to get traffic-aware travel times and
    converts them into traffic factors for graph edge weighting.

    Attributes:
        api_key: Google Maps API key
        base_url: Google Directions API endpoint
        cache: Traffic data cache with timestamps
        cache_duration: How long to cache traffic data (seconds)
        request_count: Number of API requests made (for monitoring)
        max_requests_per_minute: Rate limiting threshold
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_duration: int = 300  # 5 minutes default
    ):
        """
        Initialize Google Traffic Service.

        Args:
            api_key: Google Maps API key (defaults to env variable)
            cache_duration: Cache duration in seconds (default: 300)
        """
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google Maps API key not found. "
                "Set GOOGLE_MAPS_API_KEY environment variable."
            )

        self.base_url = "https://maps.googleapis.com/maps/api/directions/json"
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_duration = cache_duration
        self.request_count = 0
        self.max_requests_per_minute = 60  # Google's default limit

        logger.info(
            f"GoogleTrafficService initialized with cache_duration={cache_duration}s"
        )

    def get_traffic_factor(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        departure_time: Optional[datetime] = None
    ) -> float:
        """
        Get traffic factor for a route segment.

        Args:
            origin: Starting coordinates (latitude, longitude)
            destination: Ending coordinates (latitude, longitude)
            departure_time: Departure time (defaults to now)

        Returns:
            Traffic factor (0.0 = free-flow, higher = more delay)
                0.0-0.2: Light traffic
                0.2-0.5: Moderate traffic
                0.5-1.0: Heavy traffic
                1.0+: Severe congestion

        Example:
            >>> service = GoogleTrafficService()
            >>> factor = service.get_traffic_factor(
            ...     (14.6507, 121.1029),
            ...     (14.6545, 121.1089)
            ... )
            >>> print(f"Traffic factor: {factor:.2f}")
        """
        # Check cache first
        cache_key = self._get_cache_key(origin, destination)
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            age = (datetime.now() - cached_data["timestamp"]).total_seconds()

            if age < self.cache_duration:
                logger.debug(f"Cache hit for {cache_key} (age: {age:.0f}s)")
                return cached_data["traffic_factor"]

        # Fetch from API
        try:
            traffic_factor = self._fetch_traffic_data(
                origin,
                destination,
                departure_time or datetime.now()
            )

            # Update cache
            self.cache[cache_key] = {
                "traffic_factor": traffic_factor,
                "timestamp": datetime.now()
            }

            return traffic_factor

        except Exception as e:
            logger.error(f"Failed to fetch traffic data: {e}")
            return 0.0  # Default to free-flow on error

    def _fetch_traffic_data(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        departure_time: datetime
    ) -> float:
        """
        Fetch traffic data from Google Directions API.

        Args:
            origin: Starting coordinates
            destination: Ending coordinates
            departure_time: When the trip will start

        Returns:
            Calculated traffic factor

        Raises:
            Exception: If API request fails
        """
        # Rate limiting
        self._check_rate_limit()

        # Build request parameters
        params = {
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
            "key": self.api_key,
            "departure_time": int(departure_time.timestamp()),
            "mode": "driving",
            "traffic_model": "best_guess"  # or "pessimistic", "optimistic"
        }

        logger.debug(f"Requesting traffic data: {origin} -> {destination}")

        # Make API request
        response = requests.get(self.base_url, params=params, timeout=10)
        self.request_count += 1

        if response.status_code != 200:
            raise Exception(
                f"Google API error: {response.status_code} - {response.text}"
            )

        data = response.json()

        if data["status"] != "OK":
            raise Exception(f"Google API status: {data['status']}")

        # Extract traffic information
        route = data["routes"][0]
        leg = route["legs"][0]

        # Get duration with and without traffic
        duration_in_traffic = leg.get("duration_in_traffic", {}).get("value", 0)
        duration = leg["duration"]["value"]

        # Calculate traffic factor
        if duration > 0 and duration_in_traffic > 0:
            # traffic_factor represents relative delay
            traffic_factor = (duration_in_traffic - duration) / duration
            traffic_factor = max(0.0, traffic_factor)  # Ensure non-negative
        else:
            traffic_factor = 0.0

        logger.info(
            f"Traffic data: {origin} -> {destination}: "
            f"normal={duration}s, traffic={duration_in_traffic}s, "
            f"factor={traffic_factor:.3f}"
        )

        return traffic_factor

    def update_graph_traffic(
        self,
        graph,
        sample_interval: int = 10
    ) -> Dict[str, Any]:
        """
        Update graph edges with traffic data.

        This method samples edges from the graph and fetches traffic data
        for representative segments. Due to API rate limits, it samples
        rather than querying every edge.

        Args:
            graph: NetworkX graph to update
            sample_interval: Update every Nth edge (default: 10)
                Lower = more accurate but more API calls
                Higher = fewer API calls but less granular

        Returns:
            Dictionary with update statistics

        Example:
            >>> service = GoogleTrafficService()
            >>> env = DynamicGraphEnvironment()
            >>> stats = service.update_graph_traffic(env.graph, sample_interval=20)
            >>> print(f"Updated {stats['edges_updated']} edges")
        """
        logger.info(f"Updating graph traffic data (sampling every {sample_interval} edges)")

        edges_updated = 0
        edges_skipped = 0
        total_traffic_factor = 0.0
        max_traffic = 0.0
        start_time = time.time()

        # Sample edges to avoid hitting API limits
        edge_list = list(graph.edges(keys=True, data=True))
        sampled_edges = edge_list[::sample_interval]

        for u, v, key, data in sampled_edges:
            try:
                # Get node coordinates
                origin = (graph.nodes[u]['y'], graph.nodes[u]['x'])
                destination = (graph.nodes[v]['y'], graph.nodes[v]['x'])

                # Fetch traffic factor
                traffic_factor = self.get_traffic_factor(origin, destination)

                # Update edge attribute
                graph[u][v][key]['traffic_factor'] = traffic_factor

                # Update statistics
                edges_updated += 1
                total_traffic_factor += traffic_factor
                max_traffic = max(max_traffic, traffic_factor)

                # Small delay to avoid rate limiting
                time.sleep(0.05)  # 50ms delay between requests

            except Exception as e:
                logger.warning(f"Failed to update edge ({u}, {v}, {key}): {e}")
                graph[u][v][key]['traffic_factor'] = 0.0
                edges_skipped += 1

        # Propagate traffic factors to non-sampled edges using interpolation
        self._interpolate_traffic(graph, sampled_edges)

        elapsed = time.time() - start_time
        avg_traffic = total_traffic_factor / edges_updated if edges_updated > 0 else 0.0

        stats = {
            "edges_updated": edges_updated,
            "edges_skipped": edges_skipped,
            "total_edges": len(edge_list),
            "sample_interval": sample_interval,
            "avg_traffic_factor": avg_traffic,
            "max_traffic_factor": max_traffic,
            "elapsed_seconds": elapsed,
            "api_requests": self.request_count
        }

        logger.info(
            f"Traffic update complete: {edges_updated} edges updated, "
            f"avg_traffic={avg_traffic:.3f}, max_traffic={max_traffic:.3f}, "
            f"time={elapsed:.1f}s"
        )

        return stats

    def _interpolate_traffic(
        self,
        graph,
        sampled_edges: List[Tuple[Any, Any, Any, Dict]]
    ):
        """
        Interpolate traffic factors for non-sampled edges.

        Uses spatial interpolation to estimate traffic on nearby roads
        based on sampled edges.

        Args:
            graph: NetworkX graph
            sampled_edges: List of sampled edges with traffic data
        """
        # Build spatial index of sampled edges
        from ..algorithms.risk_aware_astar import haversine_distance

        for u, v, key, data in graph.edges(keys=True, data=True):
            if 'traffic_factor' in data:
                continue  # Already has traffic data

            # Find nearest sampled edge
            edge_center = (
                (graph.nodes[u]['y'] + graph.nodes[v]['y']) / 2,
                (graph.nodes[u]['x'] + graph.nodes[v]['x']) / 2
            )

            nearest_distance = float('inf')
            nearest_traffic = 0.0

            for su, sv, skey, sdata in sampled_edges:
                if 'traffic_factor' not in graph[su][sv][skey]:
                    continue

                sample_center = (
                    (graph.nodes[su]['y'] + graph.nodes[sv]['y']) / 2,
                    (graph.nodes[su]['x'] + graph.nodes[sv]['x']) / 2
                )

                distance = haversine_distance(edge_center, sample_center)

                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_traffic = graph[su][sv][skey]['traffic_factor']

            # Apply interpolated traffic factor
            graph[u][v][key]['traffic_factor'] = nearest_traffic

    def _get_cache_key(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float]
    ) -> str:
        """Generate cache key for origin-destination pair."""
        return f"{origin[0]:.4f},{origin[1]:.4f}->{destination[0]:.4f},{destination[1]:.4f}"

    def _check_rate_limit(self):
        """Check if we're exceeding rate limits."""
        if self.request_count >= self.max_requests_per_minute:
            logger.warning(
                f"Approaching rate limit ({self.request_count} requests). "
                "Consider increasing cache duration or reducing update frequency."
            )

    def clear_cache(self):
        """Clear the traffic data cache."""
        cache_size = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared traffic cache ({cache_size} entries)")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get service statistics.

        Returns:
            Dictionary with service metrics
        """
        return {
            "api_requests": self.request_count,
            "cache_entries": len(self.cache),
            "cache_duration": self.cache_duration,
            "max_requests_per_minute": self.max_requests_per_minute
        }
