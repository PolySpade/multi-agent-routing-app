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
            for u, v, key in self.graph.edges(keys=True):
                # Access edge data directly to ensure modifications persist
                edge_data = self.graph[u][v][key]
                edge_data['risk_score'] = 0.0  # Start with safe roads (0.0), flood data will increase risk
                if 'length' not in edge_data:
                    edge_data['length'] = 1.0 # Should exist, but good to be safe
                edge_data['weight'] = edge_data['length'] * (1.0 + edge_data['risk_score'])  # Base distance + risk penalty

            # Verify preprocessing worked
            sample_count = 0
            verified_count = 0
            for u, v, key in list(self.graph.edges(keys=True))[:5]:
                edge_data = self.graph[u][v][key]
                has_risk = 'risk_score' in edge_data
                if has_risk:
                    verified_count += 1
                sample_count += 1
                if sample_count <= 3:
                    print(f"  Sample edge ({u},{v},{key}): risk_score={'YES' if has_risk else 'MISSING'}")

            print(f"Graph pre-processing complete. Verified {verified_count}/{sample_count} sample edges have risk_score.")

        except Exception as e:
            print(f"\n❌ An error occurred while loading or processing the graph file: {e}")
            self.graph = None

    # (The update_edge_risk and get_graph methods remain exactly the same as before)
    def update_edge_risk(self, u, v, key, risk_factor: float):
        if self.graph is None: return
        try:
            edge_data = self.graph.edges[u, v, key]
            edge_data['risk_score'] = risk_factor
            edge_data['weight'] = edge_data['length'] * (1.0 + risk_factor)  # Base distance + risk penalty
        except KeyError:
            print(f"Warning: Edge ({u}, {v}, {key}) not found in graph.")

    def get_graph(self) -> nx.MultiDiGraph:
        return self.graph