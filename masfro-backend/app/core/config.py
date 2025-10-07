# filename: app/environment/graph_manager.py

import osmnx as ox
import networkx as nx

class DynamicGraphEnvironment:
    """
    Manages the road network graph for the simulation.

    This class handles the initial download of map data from OpenStreetMap,
    pre-processes the graph for routing calculations, and provides an
    interface for agents to update edge properties (like risk scores).
    """
    def __init__(self):
        # The geographical area of interest for the simulation.
        self.place_name = "Marikina City, Philippines"
        self.graph = None
        # Initialize the graph upon creation of the instance.
        self._load_and_preprocess_graph()

    def _load_and_preprocess_graph(self):
        """
        Downloads the road network from OSM and prepares it for the simulation.
        """
        print(f"Attempting to load graph for {self.place_name}...")
        try:
            # Download the street network for the specified location.
            self.graph = ox.graph_from_place(self.place_name, network_type='drive')
            print("Graph data downloaded successfully.")

            # --- Pre-processing Steps ---
            # Ensure every edge has the attributes needed for risk-aware routing.
            for u, v, data in self.graph.edges(data=True):
                # 1. Initialize a base 'risk_score'. 1.0 means normal conditions.
                data['risk_score'] = 1.0

                # 2. Ensure 'length' exists, as it's the base for our travel cost.
                if 'length' not in data:
                    data['length'] = 1.0 # Assign a default length if missing

                # 3. Initialize the 'weight' attribute used by the A* algorithm.
                # The weight will be a combination of distance and risk.
                data['weight'] = data['length'] * data['risk_score']

            print("Graph pre-processing complete. 'risk_score' and 'weight' attributes added.")

        except Exception as e:
            print(f"An error occurred while loading the graph: {e}")
            self.graph = None # Ensure graph is None if loading fails

    def update_edge_risk(self, u, v, key, risk_factor: float):
        """
        Updates the risk score and routing weight for a specific road segment.

        Args:
            u: The starting node of the edge.
            v: The ending node of the edge.
            key: The key of the edge (for multi-graphs).
            risk_factor: The new risk multiplier (e.g., 5.0 for a flooded road).
        """
        if self.graph is None:
            print("Warning: Graph is not loaded. Cannot update edge risk.")
            return

        try:
            edge_data = self.graph.edges[u, v, key]
            edge_data['risk_score'] = risk_factor
            # Recalculate the A* weight based on the new risk.
            edge_data['weight'] = edge_data['length'] * risk_factor
            # print(f"Updated risk for edge ({u}, {v}) to {risk_factor}.")
        except KeyError:
            print(f"Warning: Edge ({u}, {v}, {key}) not found in graph. Cannot update risk.")

    def get_graph(self) -> nx.MultiDiGraph:
        """
        Provides access to the current state of the graph.
        """
        return self.graph