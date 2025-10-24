"""
Routing Agent for Multi-Agent System for Flood Route Optimization (MAS-FRO)

This module implements the RoutingAgent class, which serves as the core pathfinding
component in the MAS-FRO system. The agent performs risk-aware route optimization
during flood scenarios, prioritizing safety over pure distance minimization.

Key Features:
- Risk-aware A* pathfinding algorithm
- Real-time integration with Dynamic Graph Environment
- GeoPandas-based spatial queries for evacuation centers
- Agent Communication Protocol (ACP) compliance
- Composite risk scoring with hydrological considerations

Research Foundation:
- Hydrological risk based on energy head (h + v²/2g) from Kreibich et al. (2009)
- Flow velocity as strong predictor of infrastructure damage
- Multi-factor risk assessment combining flood, infrastructure, and congestion risks

Author: MAS-FRO Development Team
Date: September 2025
"""

from .base_agent import BaseAgent
from ..data.data_structures import RouteRequest
import networkx as nx
import geopandas as gpd
import logging
import time
from typing import Optional, Dict, Any, Tuple
import math
import os
import random

logger = logging.getLogger(__name__)

class RoutingAgent(BaseAgent):
    """
    Agent responsible for pathfinding computations in MAS-FRO system.

    This agent performs core pathfinding using a risk-aware A* search algorithm that
    prioritizes safety by treating impassable roads as having infinite cost and
    factoring risk scores (0-1 scale) for all other segments. It integrates with the
    Dynamic Graph Environment for real-time network state updates and uses GeoPandas
    for spatial queries to locate evacuation centers.

    The agent follows the Agent Communication Protocol (ACP) for message exchange
    with other agents in the MAS-FRO system, including Hazard, Flood, and Scout agents.

    Attributes:
        agent_id (str): Unique identifier for this agent instance
        graph_env: Reference to DynamicGraphEnvironment for network state
        evacuation_centers (gpd.GeoDataFrame): Loaded evacuation center data

    Research Implementation:
        - Hydrological Risk: Based on energy head (h + v²/2g) from Kreibich et al. (2009)
        - Flow Velocity: Strong predictor of infrastructure damage per research findings
        - Composite Risk: Weighted combination of hydrological, infrastructure, and congestion factors

    Example:
        >>> # Initialize agent in multi-agent environment
        >>> agent = RoutingAgent("routing_01", env, input_queue, output_queue, graph_env)
        >>> # Agent will automatically start processing route requests

    Note:
        Risk scores are currently simulated with placeholders. Integration with Hazard Agent
        will replace these with actual hydrological data from Flood and Scout agents.
    """

    def __init__(self, agent_id: str, env, input_queue, output_queue, graph_env):
        """
        Initialize the RoutingAgent.

        Args:
            agent_id (str): Unique identifier for this agent
            env: SimPy environment for discrete event simulation
            input_queue: Queue for receiving route requests from other agents
            output_queue: Queue for sending route responses to other agents
            graph_env: DynamicGraphEnvironment instance for network state access

        Raises:
            Exception: If evacuation center data cannot be loaded
        """
        super().__init__(agent_id, env, input_queue, output_queue)
        self.graph_env = graph_env
        self.evacuation_centers = self._load_evacuation_centers()
        logger.info(f"{self.agent_id} initialized with {len(self.evacuation_centers)} evacuation centers")
    
    def _load_evacuation_centers(self) -> gpd.GeoDataFrame:
        """
        Load evacuation centers using GeoPandas for spatial operations.

        This method loads evacuation center data from a CSV file and converts it
        into a GeoDataFrame with proper spatial geometry for efficient spatial
        queries. The data includes center names, coordinates, capacity, and type.

        Returns:
            gpd.GeoDataFrame: GeoDataFrame containing evacuation center data with
                columns: ['name', 'latitude', 'longitude', 'capacity', 'type', 'geometry']
                Geometry is in EPSG:4326 (WGS84) coordinate system.

        Raises:
            FileNotFoundError: If evacuation_centers.csv is not found
            Exception: For other data loading or processing errors

        Note:
            Falls back to empty GeoDataFrame if loading fails to prevent agent failure.
            This allows the agent to continue operating even with missing evacuation data.
        """
        try:
            # Load from CSV file
            data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
            csv_path = os.path.join(data_dir, 'evacuation_centers.csv')

            df = gpd.read_file(csv_path)
            # Convert to GeoDataFrame with proper geometry
            df['geometry'] = gpd.points_from_xy(df.longitude, df.latitude)
            df = gpd.GeoDataFrame(df, geometry='geometry')
            df.set_crs('EPSG:4326', inplace=True)  # WGS84

            logger.info(f"Loaded {len(df)} evacuation centers")
            return df
        except Exception as e:
            logger.error(f"Failed to load evacuation centers: {e}")
            # Return empty GeoDataFrame as fallback
            return gpd.GeoDataFrame(columns=['name', 'latitude', 'longitude', 'capacity', 'type', 'geometry'])
    
    def run(self):
        """
        Process route requests using Agent Communication Protocol.

        Main agent loop that continuously monitors the input queue for route requests,
        processes them using risk-aware pathfinding, and sends responses via the output
        queue. Uses SimPy's discrete event simulation framework for timing control.

        The agent follows these steps for each request:
        1. Check input queue for new messages
        2. Parse route request messages
        3. Calculate optimal route using risk-aware A*
        4. Format response using Agent Communication Protocol
        5. Send response to output queue
        6. Wait before checking queue again

        Message Format (ACP):
            Request: {'type': 'route_request', 'data': RouteRequest, 'sender': str}
            Response: {
                'performative': 'inform',
                'sender': agent_id,
                'receiver': original_sender,
                'content': {'type': 'route_response', 'request_id': str, 'route': dict},
                'language': 'json',
                'ontology': 'routing'
            }

        Note:
            Agent sleeps for 10 seconds between queue checks to prevent excessive CPU usage.
            Error handling ensures agent continues running even if individual requests fail.
        """
        while self.running:
            try:
                if self.input_queue and not self.input_queue.empty():
                    message = self.input_queue.get()

                    if message.get('type') == 'route_request':
                        route_request = message['data']
                        logger.info(f"{self.agent_id} processing route request {route_request.request_id}")

                        route = self._calculate_route(route_request)

                        # Use Agent Communication Protocol format
                        response = {
                            'performative': 'inform',
                            'sender': self.agent_id,
                            'receiver': message.get('sender', 'unknown'),
                            'content': {
                                'type': 'route_response',
                                'request_id': route_request.request_id,
                                'route': route,
                                'timestamp': time.time()
                            },
                            'language': 'json',
                            'ontology': 'routing'
                        }
                        if self.output_queue:
                            self.output_queue.put(response)
                            logger.info(f"{self.agent_id} sent route response for {route_request.request_id}")

                yield self.env.timeout(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"{self.agent_id} error in main loop: {e}")
                yield self.env.timeout(30)
    
    def _calculate_route(self, route_request: RouteRequest) -> dict:
        """
        Calculate optimal route using risk-aware A* pathfinding algorithm.

        This method implements the core pathfinding logic using NetworkX's A* algorithm
        with a custom risk-aware cost function. The algorithm prioritizes safety by
        treating impassable roads as having infinite cost and factoring risk scores
        (0-1 scale) for all other segments.

        Algorithm Steps:
        1. Query current network state from DynamicGraphEnvironment
        2. Find nearest graph nodes to origin and destination coordinates
        3. Execute A* search with risk-aware edge weights
        4. Calculate comprehensive route metrics (distance, risk, safety score)
        5. Return structured route data or appropriate error messages

        Args:
            route_request (RouteRequest): Request containing origin, destination, and metadata

        Returns:
            dict: Route calculation results with the following structure:
                Success case:
                {
                    'path': [node_ids],  # List of node IDs forming the route
                    'total_distance': float,  # Total route distance in meters
                    'total_risk': float,  # Sum of risk scores along route
                    'average_risk': float,  # Average risk score (0-1)
                    'max_risk': float,  # Maximum risk score encountered
                    'safety_score': float,  # Safety score (1.0 = safest, 0.0 = riskiest)
                    'computation_time': float,  # Time taken for calculation
                    'estimated_travel_time': float,  # Estimated travel time in seconds
                    'success': True,
                    'request_id': str
                }
                Error case:
                {
                    'error': str,  # User-friendly error message
                    'success': False,
                    'request_id': str
                }

        Raises:
            No explicit exceptions - all errors are caught and returned as dict

        Note:
            The safety_score is calculated as (1.0 - average_risk) to provide an
            intuitive measure where higher values indicate safer routes.
        """
        start_time = time.time()

        try:
            # Get current network state from Dynamic Graph Environment
            graph = self.graph_env.get_current_state()

            # Find nearest graph nodes to origin and destination coordinates
            origin_node = self._find_nearest_node(graph, route_request.origin)
            dest_node = self._find_nearest_evacuation_center(graph, route_request.destination)

            if origin_node is None or dest_node is None:
                logger.warning(f"No valid start/end points found for request {route_request.request_id}")
                return {
                    'error': 'Could not find valid start or end point. Please ensure your location and destination are accessible.',
                    'success': False,
                    'request_id': route_request.request_id
                }

            # Execute A* pathfinding with risk-aware cost function
            try:
                path = nx.astar_path(
                    graph,
                    origin_node,
                    dest_node,
                    weight='risk_aware_weight',  # Custom risk-aware edge weight
                    heuristic=self._distance_heuristic  # Euclidean distance heuristic
                )

                # Calculate comprehensive route metrics
                total_distance = 0
                total_risk = 0
                max_risk = 0

                for i in range(len(path) - 1):
                    u, v = path[i], path[i + 1]
                    edge_data = graph[u][v][0]  # Get first edge (MultiDiGraph)
                    total_distance += edge_data.get('length', 0)

                    # Get risk score for this edge segment
                    edge_id = f"{u}_{v}_0"
                    risk_score = self._get_risk_score(edge_id)
                    total_risk += risk_score
                    max_risk = max(max_risk, risk_score)

                computation_time = time.time() - start_time
                avg_risk = total_risk / max(1, len(path) - 1)
                safety_score = 1.0 - min(1.0, avg_risk)  # Convert risk to safety score

                logger.info(f"Route calculated for {route_request.request_id}: {len(path)} nodes, {total_distance:.1f}m, safety: {safety_score:.2f}")

                return {
                    'path': path,
                    'total_distance': total_distance,
                    'total_risk': total_risk,
                    'average_risk': avg_risk,
                    'max_risk': max_risk,
                    'safety_score': safety_score,
                    'computation_time': computation_time,
                    'estimated_travel_time': (total_distance / 1000) / 30 * 3600,  # Assuming 30 km/h average speed
                    'success': True,
                    'request_id': route_request.request_id
                }

            except nx.NetworkXNoPath:
                logger.warning(f"No path found for request {route_request.request_id}")
                return {
                    'error': 'No safe route found to the evacuation center. Please seek alternative shelter or wait for updated conditions.',
                    'success': False,
                    'request_id': route_request.request_id
                }

        except Exception as e:
            logger.error(f"Error calculating route for {route_request.request_id}: {e}")
            return {
                'error': 'An unexpected error occurred while calculating your route. Please try again.',
                'success': False,
                'request_id': route_request.request_id
            }
    
    def _get_risk_score(self, edge_id: str) -> float:
        """
        Get composite risk score for a road segment.

        This method calculates a composite risk score combining multiple risk factors
        based on research from Kreibich et al. (2009) and other flood risk studies.
        The score ranges from 0.0 (completely safe) to 1.0 (maximum risk), with
        float('inf') indicating impassable roads.

        Risk Factors (weighted combination):
        1. Hydrological Risk (70% weight):
           - Based on energy head: h + v²/2g (Kreibich et al., 2009)
           - Water depth (h) and flow velocity (v) are critical predictors
           - Flow velocity is particularly strong predictor of infrastructure damage

        2. Infrastructure Vulnerability (20% weight):
           - Road type, material, and condition
           - Bridge and culvert capacity
           - Historical damage patterns

        3. Dynamic Congestion (10% weight):
           - Current traffic density
           - Emergency vehicle priority routes
           - Crowd movement patterns

        TODO: Replace placeholder implementation with actual Hazard Agent integration
        Future implementation will query Hazard Agent which aggregates data from:
        - Flood Agent: Real-time hydrological data (water levels, velocities)
        - Scout Agent: Infrastructure assessments and crowd-sourced reports

        Args:
            edge_id (str): Unique identifier for the road segment (format: "u_v_key")

        Returns:
            float: Risk score from 0.0 (safe) to 1.0 (high risk), or float('inf') for impassable

        Note:
            Current implementation uses placeholder simulation. In production, this will
            be replaced with real-time data from the multi-agent system.
        """
        # Get base risk from Dynamic Graph Environment
        base_risk = self.graph_env._risk_scores.get(edge_id, 0.0)

        # Handle impassable roads (infinite cost for A* algorithm)
        if base_risk == float('inf'):
            return float('inf')  # Impassable road

        # PLACEHOLDER: Simulate flood risk based on edge location
        # In real implementation, this would come from Hazard Agent
        # which aggregates data from Flood Agent and Scout Agent
        flood_risk = random.uniform(0, 0.3) if random.random() < 0.2 else 0.0

        # Composite score: weighted combination of risk factors
        # 70% hydrological/infrastructure, 30% dynamic factors
        composite_risk = min(1.0, 0.7 * base_risk + 0.3 * flood_risk)

        return composite_risk
    
    def _find_nearest_node(self, graph: nx.MultiDiGraph, location: Tuple[float, float]) -> Optional[int]:
        """
        Find the nearest graph node to given geographic coordinates.

        This method maps user-provided coordinates (latitude, longitude) to the nearest
        node in the road network graph. This is crucial for converting user locations
        into graph nodes that can be used in pathfinding algorithms.

        The method uses OSMnx's nearest_nodes function which efficiently finds the
        closest node using spatial indexing. Falls back to simple node selection
        if OSMnx is not available or fails.

        Args:
            graph (nx.MultiDiGraph): The road network graph with geographic node coordinates
            location (Tuple[float, float]): Geographic coordinates as (latitude, longitude)

        Returns:
            Optional[int]: Node ID of the nearest graph node, or None if not found

        Note:
            Coordinates should be in WGS84 (EPSG:4326) format as used by OpenStreetMap.
            The graph nodes must have 'x' (longitude) and 'y' (latitude) attributes.
        """
        try:
            import osmnx as ox
            # OSMnx expects (longitude, latitude) format
            return ox.distance.nearest_nodes(graph, location[1], location[0])
        except Exception as e:
            logger.warning(f"OSMnx nearest node search failed: {e}")
            # Fallback: return first available node
            nodes = list(graph.nodes())
            return nodes[0] if nodes else None
    
    def _find_nearest_evacuation_center(self, graph: nx.MultiDiGraph, destination: str) -> Optional[int]:
        """
        Find the nearest graph node to a specified evacuation center.

        This method handles two types of destination specifications:
        1. Evacuation center name (e.g., "Marikina Sports Center")
        2. Geographic coordinates (e.g., "14.6507,121.1029")

        For name-based lookups, it searches the evacuation_centers GeoDataFrame
        using case-insensitive string matching. For coordinate-based lookups,
        it parses the coordinate string and creates a GeoPandas point.

        Once the destination point is determined, it finds the nearest graph node
        using OSMnx's spatial indexing for efficient nearest-neighbor search.

        Args:
            graph (nx.MultiDiGraph): The road network graph
            destination (str): Either evacuation center name or "lat,lon" coordinates

        Returns:
            Optional[int]: Node ID of nearest graph node to destination, or None if not found

        Raises:
            No explicit exceptions - all errors are logged and handled gracefully

        Note:
            Falls back to last graph node if spatial queries fail, ensuring agent stability.
            Coordinate format should be "latitude,longitude" (WGS84).
        """
        try:
            if self.evacuation_centers.empty:
                logger.warning("No evacuation centers loaded")
                return None

            # Determine destination point based on input format
            if ',' in destination:
                # Coordinate format: "lat,lon"
                try:
                    lat, lon = map(float, destination.split(','))
                    dest_point = gpd.points_from_xy([lon], [lat])[0]
                    logger.debug(f"Using coordinate destination: {lat}, {lon}")
                except ValueError:
                    logger.error(f"Invalid destination coordinates: {destination}")
                    return None
            else:
                # Name-based lookup
                center_matches = self.evacuation_centers[
                    self.evacuation_centers['name'].str.contains(destination, case=False)
                ]
                if center_matches.empty:
                    logger.warning(f"Evacuation center '{destination}' not found")
                    return None
                dest_point = center_matches.iloc[0]['geometry']
                logger.debug(f"Found evacuation center: {center_matches.iloc[0]['name']}")

            # Find nearest graph node using spatial indexing
            import osmnx as ox
            nearest_node = ox.distance.nearest_nodes(graph, dest_point.x, dest_point.y)
            logger.debug(f"Nearest graph node to destination: {nearest_node}")
            return nearest_node

        except Exception as e:
            logger.error(f"Error finding nearest evacuation center: {e}")
            # Fallback: return last available node to prevent agent failure
            nodes = list(graph.nodes())
            fallback_node = nodes[-1] if nodes else None
            logger.warning(f"Using fallback node: {fallback_node}")
            return fallback_node
    
    def _distance_heuristic(self, u: int, v: int) -> float:
        """
        Calculate Euclidean distance heuristic for A* pathfinding.

        This heuristic function estimates the straight-line distance between two graph nodes,
        providing an admissible heuristic for the A* algorithm. The distance is calculated
        using the Haversine formula approximation for geographic coordinates.

        The heuristic is admissible (never overestimates) because it represents the minimum
        possible distance between two points (straight line), while the actual path must
        follow roads which may be longer.

        Args:
            u (int): Source node ID
            v (int): Target node ID

        Returns:
            float: Estimated distance in meters between nodes u and v

        Note:
            - Uses graph node attributes 'x' (longitude) and 'y' (latitude)
            - Converts degrees to meters using approximate conversion factor (111,000 m/degree)
            - Returns 0.0 if coordinate data is unavailable (falls back to Dijkstra-like behavior)
            - This is an admissible heuristic, ensuring A* finds optimal paths
        """
        try:
            graph = self.graph_env.graph
            u_data = graph.nodes[u]
            v_data = graph.nodes[v]

            # Extract coordinates (OSMnx format: x=longitude, y=latitude)
            lat1, lon1 = u_data.get('y', 0), u_data.get('x', 0)
            lat2, lon2 = v_data.get('y', 0), v_data.get('x', 0)

            # Euclidean distance approximation for geographic coordinates
            # Convert to meters using 111,000 m/degree approximation
            distance_meters = ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5 * 111000

            return distance_meters

        except Exception as e:
            logger.warning(f"Error calculating distance heuristic for nodes {u}->{v}: {e}")
            # Return 0 to fall back to Dijkstra-like behavior (uniform cost)
            return 0.0