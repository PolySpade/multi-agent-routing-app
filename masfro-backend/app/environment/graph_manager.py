# filename: app/environment/graph_manager.py
import osmnx as ox
import networkx as nx
import os # Import the os module to check for file existence
from pathlib import Path

class DynamicGraphEnvironment:
    """
    Manages the road network graph for the simulation by loading it
    from a local .graphml file.
    """
    def __init__(self):
        base = Path(__file__).resolve().parent   # .../app/environment
        # If data folder is at mesfro-backend/data use parent.parent
        candidate = (base.parent.parent / "data" / "marikina_graph.graphml").resolve()
        # fallback: app/data (one-level up) if you actually have app/data
        if not candidate.exists():
            candidate = (base.parent / "data" / "marikina_graph.graphml").resolve()
        self.filepath = str(candidate)
        # print(f"Graph file path set to: {self.filepath}")    
        self.graph = None
        self._load_graph_from_file()

    def _load_graph_from_file(self):
        """
        Loads the graph from a local file and pre-processes it.
        """
        print(f"--- Attempting to load graph from local file: {self.filepath} ---")
        if not os.path.exists(self.filepath):
            print(f"\n❌ FAILURE: Map file not found at '{self.filepath}'.")
            print("   Please run the 'download_map.py' script first to download the map data.")
            return

        try:
            # Load the graph from the file
            self.graph = ox.load_graphml(self.filepath)
            print("Graph loaded successfully from file.")

            # --- Pre-processing Steps ---
            print("Pre-processing graph (adding/resetting risk and weight attributes)...")
            for u, v, data in self.graph.edges(data=True):
                data['risk_score'] = 1.0
                if 'length' not in data:
                    data['length'] = 1.0 # Should exist, but good to be safe
                data['weight'] = data['length'] * data['risk_score']

            print("Graph pre-processing complete.")

        except Exception as e:
            print(f"\n❌ An error occurred while loading or processing the graph file: {e}")
            self.graph = None

    # (The update_edge_risk and get_graph methods remain exactly the same as before)
    def update_edge_risk(self, u, v, key, risk_factor: float):
        if self.graph is None: return
        try:
            edge_data = self.graph.edges[u, v, key]
            edge_data['risk_score'] = risk_factor
            edge_data['weight'] = edge_data['length'] * risk_factor
        except KeyError:
            print(f"Warning: Edge ({u}, {v}, {key}) not found in graph.")

    def get_graph(self) -> nx.MultiDiGraph:
        return self.graph